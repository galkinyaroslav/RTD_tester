import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import sqlalchemy
from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import HTMLResponse
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates

import threading
import json

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src import schemas, models
from src.core.config import BASE_DIR
from src.database import get_async_session
from src.state import MeasurementState
from src.dependencies import get_ws_connection_manager_state, get_measurement_state, get_instrument_state, \
    get_templates_state
from src.meas_control import DAQ_34970A
from src.web_socket import ConnectionManager

logger = logging.getLogger(__name__)

# templates = Jinja2Templates(directory=Path(BASE_DIR,'templates'))

# pt100_controller = DAQ_34970A()

# manager = ConnectionManager()

router = APIRouter(
    prefix="/pt100",
    tags=["pt100"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request,
                    templates: Jinja2Templates = Depends(get_templates_state)):
    return templates.TemplateResponse("index.html", {"request": request})


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket,
                             manager: ConnectionManager = Depends(get_ws_connection_manager_state)
                             ):
    await manager.connect(websocket)
    try:
        while True:
            # Ожидаем сообщения от клиента (можно использовать для управления)
            data = await websocket.receive_text()
            # Обработка команд от клиента может быть добавлена здесь
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.patch("/test/last_run", response_model=schemas.LastRunRead)
async def edit_run(session: AsyncSession = Depends(get_async_session)):
    stmt = (
        update(models.LastRun)
        .where(models.LastRun.id == 1)
        .values(last_run=(models.LastRun.last_run + 1))
        .returning(models.LastRun.id, models.LastRun.last_run)
    )
    result = await session.execute(stmt)
    data = result.fetchall()[0]
    last = models.LastRun(id=data[0], last_run=data[1])
    await session.commit()
    return last


# получить все Run
@router.get("/test/last_run", response_model=list[schemas.LastRunRead])
async def get_runs(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(models.LastRun))
    runs = result.scalars().all()
    return runs


# add new row in LastRun -- raise error ("Only update id=1 is available!")
@router.post("/test/last_run", )
async def create_measurement(last_run: schemas.LastRunCreate, session: AsyncSession = Depends(get_async_session)):
    db_meas = models.LastRun(**last_run.model_dump())
    # db_meas.measure_datetime = datetime.now()
    try:
        session.add(db_meas)
        await session.commit()
        await session.refresh(db_meas)
    except sqlalchemy.exc.DBAPIError:
        logger.error("Only UPDATE id=1 is available!")

    return {'error': 'Only UPDATE id=1 is available!'}


# добавить измерение
@router.post("/test/", response_model=schemas.MeasurementRead)
async def create_measurement(meas: schemas.MeasurementCreate, session: AsyncSession = Depends(get_async_session)):
    db_meas = models.Measurement(**meas.model_dump())
    # db_meas.measure_datetime = datetime.now()
    session.add(db_meas)
    await session.commit()
    await session.refresh(db_meas)
    return db_meas


# получить все измерения
@router.get("/test/", response_model=list[schemas.MeasurementRead])
async def get_measurements(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(models.Measurement))
    return result.scalars().all()


@router.post("/api/start")
async def start_measurement(session: AsyncSession = Depends(get_async_session),
                            state=Depends(get_measurement_state),
                            instrument: DAQ_34970A = Depends(get_instrument_state),
                            manager: ConnectionManager = Depends(get_ws_connection_manager_state)
                            ):
    if state.is_measuring:
        return {"status": "already_running"}

    # получаем last_run из БД
    result = await session.execute(select(models.LastRun).limit(1))
    last_run = result.scalar_one_or_none()
    if not last_run:
        last_run = models.LastRun(id=1, last_run=0)
        session.add(last_run)

    # increment
    last_run.last_run += 1
    state.current_run_number = last_run.last_run
    await session.commit()
    if not state.is_configured:
        await instrument.configure()
        state.is_configured = True

    state.is_measuring = True

    # поток измерений
    async def measurement_loop():
        try:
            while state.is_measuring:
                # читаем данные с прибора
                t_values = await instrument.read_data()  # например, [t201, t202, ...]
                # сохраняем в БД
                record_t = {}
                for t in t_values.keys():
                    record_t[f't{t}'] = t_values.get(t)
                new_record = models.Measurement(
                    run_id=state.current_run_number,
                    **record_t
                )
                session.add(new_record)  # sync_session — если ты используешь async engine
                await session.commit()

                # отправка по WebSocket
                await manager.broadcast(message={'data': t_values,})
                await asyncio.sleep(state.timer_seconds)
        except asyncio.CancelledError:
            logger.error("Measurement loop cancelled")
        finally:
            state.is_measuring = False
            state.measurement_task = None
            logger.info("✅ Measurement loop stopped")

    task = asyncio.create_task(measurement_loop())
    state.measurement_task = task
    return {"status": "started", "run_number": state.current_run_number}


@router.post("/api/stop")
async def stop_measurement(state=Depends(get_measurement_state)):
    if not state.is_measuring:
        return {"status": "not_running"}

    state.is_measuring = False

    # корректно останавливаем задачу
    if state.measurement_task and not state.measurement_task.done():
        state.measurement_task.cancel()
        try:
            await state.measurement_task
        except asyncio.CancelledError:
            pass

    return {"status": "stopped"}


@router.post("/api/state/timer")
async def set_timer(state=Depends(get_measurement_state), payload: dict = None):
    timer = payload.get("timer", 5)
    state.timer_seconds = int(timer)
    return {"timer": state.timer_seconds}


@router.post("/api/configure")
async def configure_device(state=Depends(get_measurement_state),
                           instrument: DAQ_34970A = Depends(get_instrument_state), ):
    """Асинхронная конфигурация прибора"""
    if state.is_configured:
        return {"status": "already_configured"}

    try:
        await instrument.configure()
        if instrument.is_configured:
            state.is_configured = True
            return {"status": "configured"}

        else:
            state.is_configured = False
            return {"status": "NOT configured"}

    except Exception as e:
        state.is_configured = False
        return {"status": "error", "detail": str(e)}

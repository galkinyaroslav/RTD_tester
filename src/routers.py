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
from src.logic import measurement_loop, save_to_excel
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
                             manager: ConnectionManager = Depends(get_ws_connection_manager_state)):
    await manager.connect(websocket)
    try:
        while True:
            # Ожидаем сообщения от клиента (можно использовать для управления)
            data = await websocket.receive_text()
            # Обработка команд от клиента может быть добавлена здесь
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/api/data")
async def get_data(state: MeasurementState = Depends(get_measurement_state)):
    return state.current_data


@router.post("/api/start")
async def start_measurement(state: MeasurementState = Depends(get_measurement_state),
                            pt100_controller: DAQ_34970A = Depends(get_instrument_state),
                            manager: ConnectionManager = Depends(get_ws_connection_manager_state)):

    if not state.is_measuring:
        if pt100_controller.connect():
            if pt100_controller.configure():
                state.is_measuring = True
                measurement_thread = threading.Thread(target=measurement_loop, args=(state, pt100_controller, manager))
                measurement_thread.daemon = True
                measurement_thread.start()

                await manager.broadcast(json.dumps({
                    'type': 'status',
                    'measuring': True,
                    'recording': state.is_recording
                }))

                return {"status": "started", "message": "Измерения запущены"}

        return {"status": "error", "message": "Не удалось подключиться к прибору"}
    return {"status": "already_running", "message": "Измерения уже запущены"}


@router.post("/api/stop")
async def stop_measurement(pt100_controller: DAQ_34970A = Depends(get_instrument_state),
                           state: MeasurementState = Depends(get_measurement_state),
                           manager: ConnectionManager = Depends(get_ws_connection_manager_state)):

    state.is_measuring = False
    state.is_recording = False
    pt100_controller.disconnect()

    await manager.broadcast(json.dumps({
        'type': 'status',
        'measuring': False,
        'recording': False
    }))

    return {"status": "stopped", "message": "Измерения остановлены"}


@router.post("/api/record/start")
async def start_recording(state: MeasurementState = Depends(get_measurement_state),
                          manager: ConnectionManager = Depends(get_ws_connection_manager_state)):

    if state.is_measuring:
        state.is_recording = True

        await manager.broadcast(json.dumps({
            'type': 'status',
            'measuring': True,
            'recording': True
        }))

        return {"status": "recording_started", "message": "Запись данных начата"}
    else:
        return {"status": "error", "message": "Сначала запустите измерения"}


@router.post("/api/record/stop")
async def stop_recording(state: MeasurementState = Depends(get_measurement_state),
                         manager: ConnectionManager = Depends(get_ws_connection_manager_state)):
    state.is_recording = False
    save_to_excel()
    await manager.broadcast(json.dumps({
        'type': 'status',
        'measuring': state.is_measuring,
        'recording': False
    }))

    return {"status": "recording_stopped", "message": "Запись данных остановлена"}


@router.get("/api/status")
async def get_status(state: MeasurementState = Depends(get_measurement_state),
                     pt100_controller: DAQ_34970A = Depends(get_instrument_state),):
    return {
        "measuring": state.is_measuring,
        "recording": state.is_recording,
        "connected": pt100_controller.connected
    }


@router.get("/api/save")
async def save_data(state: MeasurementState = Depends(get_measurement_state),):
    """Скачивание файла с данными"""
    try:
        if Path(state.excel_filename).exists():
            from fastapi.responses import FileResponse
            return FileResponse(
                state.excel_filename,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                filename=f"pt100_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
        else:
            return {"status": "error", "message": "Файл данных не найден"}
    except Exception as e:
        return {"status": "error", "message": f"Ошибка при скачивании: {str(e)}"}






# добавить Run
@router.patch("/test/last_run", response_model=schemas.LastRunRead)
async def edit_run(session: AsyncSession = Depends(get_async_session)):

    stmt = (
        update(models.LastRun)
        .where(models.LastRun.id == 1)
        .values(last_run=(models.LastRun.last_run + 1 ))
        .returning(models.LastRun.id, models.LastRun.last_run)
    )
    result = await session.execute(stmt)
    data = result.fetchall()[0]
    last = models.LastRun(id=data[0],last_run=data[1])
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


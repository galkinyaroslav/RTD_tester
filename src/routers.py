import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import HTMLResponse
from fastapi import WebSocket, WebSocketDisconnect
import threading
import json

from fastapi.templating import Jinja2Templates

from src.core.config import BASE_DIR
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





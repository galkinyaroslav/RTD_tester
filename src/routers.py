import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi import WebSocket, WebSocketDisconnect
import threading
import json

from fastapi.templating import Jinja2Templates

from src.core.config import BASE_DIR
import src.glob
from src.meas_control import DAQ_34970A
from src.web_socket import ConnectionManager

logger = logging.getLogger("visa_client")

templates = Jinja2Templates(directory=Path(BASE_DIR,'templates'))

pt100_controller = DAQ_34970A()

manager = ConnectionManager()

router = APIRouter(
    prefix="/pt100",
    tags=["pt100"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):

    return templates.TemplateResponse("index.html", {"request": request})


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Ожидаем сообщения от клиента (можно использовать для управления)
            data = await websocket.receive_text()
            # Обработка команд от клиента может быть добавлена здесь
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/api/data")
async def get_data():
    return src.glob.current_data


@router.post("/api/start")
async def start_measurement():
    if not src.glob.is_measuring:
        if pt100_controller.connect():
            if pt100_controller.configure():
                src.glob.is_measuring = True
                measurement_thread = threading.Thread(target=measurement_loop)
                measurement_thread.daemon = True
                measurement_thread.start()

                await manager.broadcast(json.dumps({
                    'type': 'status',
                    'measuring': True,
                    'recording': src.glob.is_recording
                }))

                return {"status": "started", "message": "Измерения запущены"}

        return {"status": "error", "message": "Не удалось подключиться к прибору"}
    return {"status": "already_running", "message": "Измерения уже запущены"}


@router.post("/api/stop")
async def stop_measurement():

    src.glob.is_measuring = False
    src.glob.is_recording = False
    pt100_controller.disconnect()

    await manager.broadcast(json.dumps({
        'type': 'status',
        'measuring': False,
        'recording': False
    }))

    return {"status": "stopped", "message": "Измерения остановлены"}


@router.post("/api/record/start")
async def start_recording():

    if src.glob.is_measuring:
        src.glob.is_recording = True

        await manager.broadcast(json.dumps({
            'type': 'status',
            'measuring': True,
            'recording': True
        }))

        return {"status": "recording_started", "message": "Запись данных начата"}
    else:
        return {"status": "error", "message": "Сначала запустите измерения"}


@router.post("/api/record/stop")
async def stop_recording():
    src.glob.is_recording = False
    save_to_excel()
    await manager.broadcast(json.dumps({
        'type': 'status',
        'measuring': src.glob.is_measuring,
        'recording': False
    }))

    return {"status": "recording_stopped", "message": "Запись данных остановлена"}


@router.get("/api/status")
async def get_status():
    return {
        "measuring": src.glob.is_measuring,
        "recording": src.glob.is_recording,
        "connected": pt100_controller.connected
    }


@router.get("/api/download")
async def download_data():
    """Скачивание файла с данными"""
    try:
        if Path(src.glob.excel_filename).exists():
            from fastapi.responses import FileResponse
            return FileResponse(
                src.glob.excel_filename,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                filename=f"pt100_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
        else:
            return {"status": "error", "message": "Файл данных не найден"}
    except Exception as e:
        return {"status": "error", "message": f"Ошибка при скачивании: {str(e)}"}

def measurement_loop():
    """Цикл измерения в отдельном потоке"""
    # global is_measuring, is_recording, current_data, data_buffer

    # channels = ["101", "102", "103"]

    while src.glob.is_measuring:
        try:
            measurements = pt100_controller.read_data()
            if measurements:
                current_data = measurements

                # Асинхронная рассылка данных через WebSocket
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast(json.dumps({
                        'type': 'data',
                        'data': measurements
                    })),
                    asyncio.get_event_loop()
                )

                # Запись в буфер если включена запись
                if src.glob.is_recording:
                    record = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        **{f"temp_{ch}": measurements[ch] for ch in pt100_controller.channels},
                    }
                    src.glob.data_buffer.append(record)
                    logger.info(f"Data have been written: {measurements}")

            time.sleep(1)

        except Exception as e:
            logger.error(f"Error in measurement cycle: {e}")
            time.sleep(1)

def save_to_excel():
    """Сохранение данных из буфера в Excel"""
    # global data_buffer

    if src.glob.data_buffer:
        try:
            df = pd.DataFrame(src.glob.data_buffer)

            try:
                existing_df = pd.read_excel(src.glob.excel_filename)
                df = pd.concat([existing_df, df], ignore_index=True)
            except FileNotFoundError:
                pass

            df.to_excel(src.glob.excel_filename, index=False)
            logger.info(f"Данные сохранены в {src.glob.excel_filename}, записей: {len(src.glob.data_buffer)}")
            data_buffer = []
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения в Excel: {e}")
            return False
    return True



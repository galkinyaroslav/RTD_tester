from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi import WebSocket, WebSocketDisconnect
import threading
import json

from main import templates, manager, current_data, pt100_controller, measurement_loop

router = APIRouter(
    prefix="/pt100",
    tags=["pt100"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_class=HTMLResponse)
async def read_root():
    return templates.TemplateResponse("index.html", {"request": {}})


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
    return current_data


@router.post("/api/start")
async def start_measurement():
    global is_measuring, measurement_thread

    if not is_measuring:
        if pt100_controller.connect():
            if pt100_controller.configure_measurement():
                is_measuring = True
                measurement_thread = threading.Thread(target=measurement_loop)
                measurement_thread.daemon = True
                measurement_thread.start()

                await manager.broadcast(json.dumps({
                    'type': 'status',
                    'measuring': True,
                    'recording': is_recording
                }))

                return {"status": "started", "message": "Измерения запущены"}

        return {"status": "error", "message": "Не удалось подключиться к прибору"}
    return {"status": "already_running", "message": "Измерения уже запущены"}


@router.post("/api/stop")
async def stop_measurement():
    global is_measuring, is_recording

    is_measuring = False
    is_recording = False
    pt100_controller.disconnect()

    await manager.broadcast(json.dumps({
        'type': 'status',
        'measuring': False,
        'recording': False
    }))

    return {"status": "stopped", "message": "Измерения остановлены"}


@router.post("/api/record/start")
async def start_recording():
    global is_recording

    if is_measuring:
        is_recording = True

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
    is_recording = False
    save_to_excel()
    await manager.broadcast(json.dumps({
        'type': 'status',
        'measuring': is_measuring,
        'recording': False
    }))

    return {"status": "recording_stopped", "message": "Запись данных остановлена"}


@router.get("/api/status")
async def get_status():
    return {
        "measuring": is_measuring,
        "recording": is_recording,
        "connected": pt100_controller.connected
    }


@router.get("/api/download")
async def download_data():
    """Скачивание файла с данными"""
    try:
        import os
        if os.path.exists(excel_filename):
            from fastapi.responses import FileResponse
            return FileResponse(
                excel_filename,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                filename=f"pt100_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
        else:
            return {"status": "error", "message": "Файл данных не найден"}
    except Exception as e:
        return {"status": "error", "message": f"Ошибка при скачивании: {str(e)}"}


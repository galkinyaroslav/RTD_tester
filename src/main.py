from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import pyvisa
import threading
import time
import pandas as pd
from datetime import datetime
import logging
import json
import asyncio
from typing import Dict, List, Optional
import uvicorn

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные для управления
is_measuring = False
is_recording = False
current_data = {}
measurement_thread = None
data_buffer = []
excel_filename = "pt100_measurements.xlsx"


class PT100Controller:
    def __init__(self):
        self.rm = None
        self.instrument = None
        self.connected = False

    def connect(self, visa_address="GPIB0::22::INSTR"):
        """Подключение к Agilent 34970"""
        try:
            self.rm = pyvisa.ResourceManager()
            self.instrument = self.rm.open_resource(visa_address)
            self.instrument.timeout = 10000
            self.connected = True
            logger.info(f"Успешно подключено к {visa_address}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False

    def disconnect(self):
        """Отключение от прибора"""
        if self.instrument:
            self.instrument.close()
        if self.rm:
            self.rm.close()
        self.connected = False
        logger.info("Отключено от прибора")

    def configure_measurement(self, channels=["101", "102", "103"]):
        """Настройка измерения температуры PT100"""
        try:
            # Сброс прибора
            self.instrument.write("*RST")
            time.sleep(1)

            # Настройка для PT100 (4-проводное подключение)
            for channel in channels:
                # FRES - 4-проводное измерение сопротивления
                self.instrument.write(f"CONF:FRES {channel}")
                # Диапазон 100 Ом для PT100
                self.instrument.write(f"FRES:RANGE 100, {channel}")
                # Разрешение 0.001 Ом
                self.instrument.write(f"FRES:RES 0.001, {channel}")
                # NPLC = 1
                self.instrument.write(f"FRES:NPLC 1, {channel}")

            logger.info(f"Настроены каналы: {channels}")
            return True
        except Exception as e:
            logger.error(f"Ошибка настройки: {e}")
            return False

    def read_temperature(self, channels=["101", "102", "103"]):
        """Чтение температуры с каналов"""
        try:
            measurements = {}
            for channel in channels:
                # Чтение сопротивления
                resistance = float(self.instrument.query(f"READ? {channel}"))
                # Конвертация сопротивления в температуру
                temperature = self.resistance_to_temperature(resistance)
                measurements[channel] = {
                    'resistance': round(resistance, 4),
                    'temperature': temperature,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            return measurements
        except Exception as e:
            logger.error(f"Ошибка чтения: {e}")
            return None

    def resistance_to_temperature(self, resistance):
        """Конвертация сопротивления PT100 в температуру"""
        R0 = 100.0  # Сопротивление при 0°C
        A = 3.9083e-3
        B = -5.775e-7

        if resistance >= R0:
            temperature = (-A + (A ** 2 - 4 * B * (1 - resistance / R0)) ** 0.5) / (2 * B)
        else:
            temperature = (resistance - R0) / (R0 * A)

        return round(temperature, 2)


# Создаем экземпляр контроллера
pt100_controller = PT100Controller()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        disconnected_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected_connections.append(connection)

        for connection in disconnected_connections:
            self.disconnect(connection)


manager = ConnectionManager()


def measurement_loop():
    """Цикл измерения в отдельном потоке"""
    global is_measuring, is_recording, current_data, data_buffer

    channels = ["101", "102", "103"]

    while is_measuring:
        try:
            measurements = pt100_controller.read_temperature(channels)
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
                if is_recording:
                    record = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        **{f"temp_{ch}": measurements[ch]['temperature'] for ch in channels},
                        **{f"res_{ch}": measurements[ch]['resistance'] for ch in channels}
                    }
                    data_buffer.append(record)
                    logger.info(f"Записаны данные: {measurements}")

            time.sleep(1)

        except Exception as e:
            logger.error(f"Ошибка в цикле измерения: {e}")
            time.sleep(1)


def save_to_excel():
    """Сохранение данных из буфера в Excel"""
    global data_buffer

    if data_buffer:
        try:
            df = pd.DataFrame(data_buffer)

            try:
                existing_df = pd.read_excel(excel_filename)
                df = pd.concat([existing_df, df], ignore_index=True)
            except FileNotFoundError:
                pass

            df.to_excel(excel_filename, index=False)
            logger.info(f"Данные сохранены в {excel_filename}, записей: {len(data_buffer)}")
            data_buffer = []
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения в Excel: {e}")
            return False
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Запуск приложения PT100 Monitor")
    yield
    # Shutdown
    global is_measuring, is_recording
    is_measuring = False
    is_recording = False
    if pt100_controller.connected:
        pt100_controller.disconnect()
    logger.info("Остановка приложения PT100 Monitor")


app = FastAPI(
    title="PT100 Monitor API",
    description="API для мониторинга датчиков PT100 через Agilent 34970",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    return templates.TemplateResponse("index.html", {"request": {}})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Ожидаем сообщения от клиента (можно использовать для управления)
            data = await websocket.receive_text()
            # Обработка команд от клиента может быть добавлена здесь
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/data")
async def get_data():
    return current_data


@app.post("/api/start")
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


@app.post("/api/stop")
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


@app.post("/api/record/start")
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


@app.post("/api/record/stop")
async def stop_recording():
    global is_recording

    is_recording = False
    save_to_excel()

    await manager.broadcast(json.dumps({
        'type': 'status',
        'measuring': is_measuring,
        'recording': False
    }))

    return {"status": "recording_stopped", "message": "Запись данных остановлена"}


@app.get("/api/status")
async def get_status():
    return {
        "measuring": is_measuring,
        "recording": is_recording,
        "connected": pt100_controller.connected
    }


@app.get("/api/download")
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


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

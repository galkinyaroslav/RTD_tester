from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import pyvisa
import time
import pandas as pd
from datetime import datetime
import logging
import json
import asyncio
import uvicorn

from src.meas_control import DAQ_34970A
from web_socket import ConnectionManager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
is_measuring = False
is_recording = False
current_data = {}
measurement_thread = None
data_buffer = []
excel_filename = "pt100_measurements.xlsx"


# Создаем экземпляр контроллера
pt100_controller = DAQ_34970A()

manager = ConnectionManager()


def measurement_loop():
    """Цикл измерения в отдельном потоке"""
    global is_measuring, is_recording, current_data, data_buffer

    # channels = ["101", "102", "103"]

    while is_measuring:
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
                if is_recording:
                    record = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        **{f"temp_{ch}": measurements[ch] for ch in pt100_controller.channels},
                    }
                    data_buffer.append(record)
                    logger.info(f"Data have been written: {measurements}")

            time.sleep(1)

        except Exception as e:
            logger.error(f"Error in measurement cycle: {e}")
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
    logger.info("Run apt PT100 Monitor")
    yield
    # Shutdown
    global is_measuring, is_recording
    is_measuring = False
    is_recording = False
    if pt100_controller.connected:
        pt100_controller.disconnect()
    logger.info("Stop apt PT100 Monitor")


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


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    )

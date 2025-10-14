from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import logging
import uvicorn
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from starlette.datastructures import State

from src.state import MeasurementState
from src.routers import router
from src.meas_control import DAQ_34970A
from src.core.config import BASE_DIR, get_settings
from src.core.logging_config import setup_logging
from src.web_socket import ConnectionManager
from fastapi.templating import Jinja2Templates



# Logging setup
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Run apt PT100 Monitor")
    app.state.measurement = MeasurementState()
    app.state.ws_connection_manager = ConnectionManager()
    app.state.instrument = DAQ_34970A()
    await app.state.instrument.connect()
    app.state.dot_env = get_settings()
    app.state.templates = Jinja2Templates(directory=Path(BASE_DIR,'templates'))
    # DATABASE_URL = (f'postgresql+asyncpg://{app.state.dot_env.DB_USER}:'
    #                 f'{app.state.dot_env.DB_PASS}@'
    #                 f'{app.state.dot_env.DB_HOST}:'
    #                 f'{app.state.dot_env.DB_PORT}/'
    #                 f'{app.state.dot_env.DB_NAME}')

    app.state.engine = create_async_engine(app.state.dot_env.DB_URL)
    app.state.db_sessionmaker = async_sessionmaker(app.state.engine, expire_on_commit=False)

    yield # APP IS WORKING!

    # Shutdown
    app.state.measurement.is_measuring = False
    # app.state.measurement.is_recording = False
    if app.state.instrument.connected:
        await app.state.instrument.disconnect()
    # app.state.instrument.close()
    logger.info("Stop apt PT100 Monitor")



app = FastAPI(
    title="PT100 Monitor API",
    description="API для мониторинга датчиков PT100 через Agilent 34970",
    version="1.0.0",
    lifespan=lifespan
)

app.state: State  # type hint для IDE


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount('/static', StaticFiles(directory=Path(BASE_DIR, 'static')), name="static")

app.include_router(router)



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    )

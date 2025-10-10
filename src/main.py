from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import logging
import uvicorn

import src.glob as glob
from src.routers import router, pt100_controller
from src.core.config import BASE_DIR
from src.core.logging_config import setup_logging

# Logging setup
setup_logging()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Run apt PT100 Monitor")
    yield
    # Shutdown
    glob.is_measuring = False
    glob.is_recording = False
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

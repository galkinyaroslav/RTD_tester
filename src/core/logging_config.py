import logging
import sys
from pathlib import Path
from src.core.config import BASE_DIR


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

def setup_logging():
    """Global logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(Path(BASE_DIR, "app.log"), encoding="utf-8"),
        ],
    )

    # Layers configuration for external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.getLogger("pyvisa").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)  # less 2025-10-11 21:44:46,362 [INFO] watchfiles.main: 1 change detected.
    logging.getLogger("httpx").setLevel(logging.WARNING)


# src/dependencies/common.py
from fastapi import Request
from starlette.websockets import WebSocket


def get_measurement_state(request: Request):
    """
    Dependency, return MeasurementState from app.state
    """
    return request.app.state.measurement

def get_ws_connection_manager_state(ws: WebSocket):
    """
    Dependency, return ConnectionManager from app.state
    """
    return ws.app.state.ws_connection_manager

def get_instrument_state(request: Request):
    """
    Dependency, return DAQ_34970A from app.state
    """
    return request.app.state.instrument

def get_dot_env_state(request: Request):
    """
    Dependency, return .env data from app.state
    """
    return request.app.state.dot_env

def get_templates_state(request: Request):
    """
    Dependency, return templates from app.state
    """
    return request.app.state.templates





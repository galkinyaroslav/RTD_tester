# src/dependencies/common.py
from fastapi import Request

def get_measurement_state(request: Request):
    """
    Dependency, возвращающая MeasurementState из app.state
    """
    return request.app.state.measurement

def get_ws_connection_manager_state(request: Request):
    """
    Dependency, возвращающая ConnectionManager из app.state
    """
    return request.app.state.ws_connection_manager

def get_instrument_state(request: Request):
    """
    Dependency, возвращающая DAQ_34970A из app.state
    """
    return request.app.state.instrument

def get_dot_env_state(request: Request):
    """
    Dependency, возвращающая данные .env из app.state
    """
    return request.app.state.dot_env





# src/schemas.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

class MeasurementBase(BaseModel):
    t205: float
    t206: float
    t207: float
    t208: float
    t209: float
    t210: float

class MeasurementCreate(MeasurementBase):
    run_id: int

class MeasurementRead(MeasurementBase):
    run_id: int
    # measure_datetime: datetime
    model_config = ConfigDict(from_attributes=True)


class LastRunBase(BaseModel):
    id: int

class LastRunCreate(LastRunBase):
    pass

class LastRunRead(LastRunBase):
    last_run: int

    model_config = ConfigDict(from_attributes=True)

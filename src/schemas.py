# src/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class MeasurementBase(BaseModel):
    t1: float
    t2: float
    t3: float
    t4: float
    t5: float
    t6: float

class MeasurementCreate(MeasurementBase):
    run_id: int

class MeasurementRead(MeasurementBase):
    id: int
    time: datetime
    class Config:
        orm_mode = True

class RunBase(BaseModel):
    run_number: int

class RunCreate(RunBase):
    pass

class RunRead(RunBase):
    id: int
    measurements: Optional[List[MeasurementRead]] = None
    class Config:
        orm_mode = True

from datetime import datetime

from pydantic import BaseModel


class RainfallData(BaseModel):
    timestamp: datetime
    station: str
    rainfall_mm: float
    unit: str
    status: str
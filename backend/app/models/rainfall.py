from pydantic import BaseModel


class RainfallData(BaseModel):
    station: str
    rainfall_mm: float
    unit: str
    status: str
from datetime import datetime
from pydantic import BaseModel


class RainfallGridCell(BaseModel):
    """Rainfall value for one cell of the urban rainfall grid."""

    timestamp: datetime
    latitude: float
    longitude: float
    rainfall_mm: float


class RainfallGrid(BaseModel):
    """High-resolution rainfall grid used by the flood model."""

    timestamp: datetime
    source: str
    cell_size_m: float
    cells: list[RainfallGridCell]
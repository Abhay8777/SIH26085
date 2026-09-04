from pydantic import BaseModel


class FloodCell(BaseModel):
    row: int
    column: int
    latitude: float
    longitude: float
    elevation_m: float
    rainfall_mm: float
    runoff_mm: float
    water_depth_cm: float
    risk: str


class FloodGrid(BaseModel):
    source: str
    timestamp: str
    rows: int
    columns: int
    cells: list[FloodCell]
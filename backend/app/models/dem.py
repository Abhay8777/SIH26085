from pydantic import BaseModel, Field


class DEMCell(BaseModel):
    """Elevation information for one surface grid cell."""

    row: int = Field(
        ...,
        ge=0,
    )

    column: int = Field(
        ...,
        ge=0,
    )

    latitude: float

    longitude: float

    elevation_m: float = Field(
        ...,
        description="Ground elevation above mean sea level in metres",
    )


class DEMGrid(BaseModel):
    """Digital Elevation Model represented as a regular grid."""

    source: str

    cell_size_m: float = Field(
        ...,
        gt=0,
    )

    rows: int = Field(
        ...,
        gt=0,
    )

    columns: int = Field(
        ...,
        gt=0,
    )

    cells: list[DEMCell]
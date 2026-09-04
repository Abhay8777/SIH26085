from datetime import datetime

from pydantic import BaseModel, Field


class RainfallData(BaseModel):
    """
    Standardized rainfall response used by the SIH26085 backend.
    """

    timestamp: datetime

    station: str = Field(
        ...,
        description="Rainfall observation station"
    )

    rainfall_mm: float = Field(
        ...,
        ge=0,
        description="Rainfall amount in millimetres"
    )

    unit: str = Field(
        default="mm",
        description="Rainfall measurement unit"
    )

    status: str = Field(
        ...,
        description=(
            "Data status such as imd_live, "
            "waiting_for_imd_api_key or imd_api_error"
        )
    )
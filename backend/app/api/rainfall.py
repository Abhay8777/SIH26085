from fastapi import APIRouter

from backend.app.models.rainfall import RainfallData
from backend.app.services.rainfall_service import (
    get_latest_rainfall,
)


router = APIRouter()


# =========================================================
# LATEST RAINFALL
# =========================================================

@router.get(
    "/latest",
    response_model=RainfallData,
)
def latest_rainfall() -> RainfallData:
    """
    Return the latest standardized rainfall observation.

    Data source:
        IMD when API access is available.

    Development:
        Clearly marked fallback response while
        IMD access is unavailable.
    """

    return get_latest_rainfall()
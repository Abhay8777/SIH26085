from fastapi import APIRouter
from backend.app.models.rainfall import RainfallData
from backend.app.services.rainfall_service import get_latest_rainfall

router = APIRouter()


@router.get("/latest", response_model=RainfallData)
def latest_rainfall():
    return get_latest_rainfall()
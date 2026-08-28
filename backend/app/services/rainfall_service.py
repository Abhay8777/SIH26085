from datetime import datetime, timezone

from backend.app.models.rainfall import RainfallData


def get_latest_rainfall() -> RainfallData:
    return RainfallData(
        timestamp=datetime.now(timezone.utc),
        station="Mumbai",
        rainfall_mm=0.0,
        unit="mm",
        status="sample",
    )
from backend.app.models.rainfall import RainfallData


def get_latest_rainfall() -> RainfallData:
    return RainfallData(
        station="Mumbai",
        rainfall_mm=0,
        unit="mm",
        status="sample",
    )
from datetime import datetime, timezone

from backend.app.models.rainfall_grid import (
    RainfallGrid,
    RainfallGridCell,
)


# =========================================================
# GRID CONFIGURATION
# =========================================================

BASE_LATITUDE = 19.0500
BASE_LONGITUDE = 72.8500

LATITUDE_STEP = 0.009
LONGITUDE_STEP = 0.009

ROWS = 3
COLUMNS = 3
CELL_SIZE_M = 1000.0


# =========================================================
# DEVELOPMENT RAINFALL GRID
# =========================================================

def generate_development_rainfall_grid() -> RainfallGrid:
    """
    Generate a small Mumbai-area development rainfall grid.

    IMPORTANT:
    This is DEMO data only.

    It is used only when a live rainfall observation
    is not available.
    """

    timestamp = datetime.now(timezone.utc)

    rainfall_values = [
        [18.0, 22.0, 25.0],
        [20.0, 28.0, 32.0],
        [16.0, 24.0, 27.0],
    ]

    cells = []

    for row_index, row in enumerate(rainfall_values):

        for column_index, rainfall_mm in enumerate(row):

            cells.append(
                RainfallGridCell(
                    timestamp=timestamp,

                    latitude=(
                        BASE_LATITUDE
                        + row_index * LATITUDE_STEP
                    ),

                    longitude=(
                        BASE_LONGITUDE
                        + column_index * LONGITUDE_STEP
                    ),

                    rainfall_mm=float(rainfall_mm),
                )
            )

    return RainfallGrid(
        timestamp=timestamp,
        source="development_demo",
        cell_size_m=CELL_SIZE_M,
        cells=cells,
    )


# =========================================================
# UNIFORM RAINFALL GRID
# =========================================================

def generate_uniform_rainfall_grid(
    rainfall_mm: float,
) -> RainfallGrid:
    """
    Create a spatial rainfall grid from one rainfall
    observation.

    Current transition architecture:

        Single rainfall observation
                    ↓
            Uniform 3x3 grid
                    ↓
             Flood model

    This is NOT spatially varying rainfall.

    Later this function can be replaced by a real
    radar/grid rainfall product.
    """

    timestamp = datetime.now(timezone.utc)

    rainfall_mm = max(
        0.0,
        float(rainfall_mm),
    )

    cells = []

    for row_index in range(ROWS):

        for column_index in range(COLUMNS):

            cells.append(
                RainfallGridCell(
                    timestamp=timestamp,

                    latitude=(
                        BASE_LATITUDE
                        + row_index * LATITUDE_STEP
                    ),

                    longitude=(
                        BASE_LONGITUDE
                        + column_index * LONGITUDE_STEP
                    ),

                    rainfall_mm=rainfall_mm,
                )
            )

    return RainfallGrid(
        timestamp=timestamp,
        source="rainfall_observation_uniform",
        cell_size_m=CELL_SIZE_M,
        cells=cells,
    )


# =========================================================
# SELECT RAINFALL GRID
# =========================================================

def generate_rainfall_grid(
    rainfall_mm: float | None = None,
    live: bool = False,
) -> RainfallGrid:
    """
    Select the rainfall grid used by the flood model.

    live=True:
        Uses the supplied rainfall observation and creates
        a uniform spatial grid.

    live=False:
        Uses the controlled development rainfall grid.

    This keeps the flood model independent from the actual
    rainfall data source.
    """

    if live and rainfall_mm is not None:

        return generate_uniform_rainfall_grid(
            rainfall_mm
        )

    return generate_development_rainfall_grid()
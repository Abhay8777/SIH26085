from backend.app.models.dem import (
    DEMCell,
    DEMGrid,
)


# =========================================================
# DEVELOPMENT DEM CONFIGURATION
# =========================================================

BASE_LATITUDE = 19.0500
BASE_LONGITUDE = 72.8500

LATITUDE_STEP = 0.009
LONGITUDE_STEP = 0.009

CELL_SIZE_M = 1000.0

ROWS = 3
COLUMNS = 3


# =========================================================
# DEVELOPMENT DEM
# =========================================================

def generate_development_dem() -> DEMGrid:
    """
    Generate a small synthetic Mumbai-area terrain grid.

    IMPORTANT:
    This is NOT real Mumbai elevation data.

    It exists to validate the complete flood-model
    pipeline before a real DEM dataset is connected.
    """

    elevation_values = [
        [12.0, 11.5, 11.0],
        [10.5, 9.0, 8.0],
        [9.5, 8.0, 6.5],
    ]

    cells: list[DEMCell] = []

    for row_index in range(ROWS):

        for column_index in range(COLUMNS):

            elevation_m = float(
                elevation_values[
                    row_index
                ][
                    column_index
                ]
            )

            cells.append(
                DEMCell(
                    row=row_index,

                    column=column_index,

                    latitude=(
                        BASE_LATITUDE
                        + row_index * LATITUDE_STEP
                    ),

                    longitude=(
                        BASE_LONGITUDE
                        + column_index * LONGITUDE_STEP
                    ),

                    elevation_m=elevation_m,
                )
            )

    return DEMGrid(
        source="development_synthetic_dem",

        cell_size_m=CELL_SIZE_M,

        rows=ROWS,

        columns=COLUMNS,

        cells=cells,
    )
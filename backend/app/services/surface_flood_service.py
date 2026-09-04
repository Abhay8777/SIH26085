from backend.app.models.flood import FloodCell, FloodGrid
from backend.app.models.rainfall_grid import RainfallGrid

from backend.app.services.dem_service import (
    generate_development_dem,
)

from backend.app.services.rainfall_grid_service import (
    generate_development_rainfall_grid,
)

from backend.app.services.rainfall_service import (
    get_latest_rainfall,
)


# =========================================================
# MODEL PARAMETERS
# =========================================================

RUNOFF_COEFFICIENT = 0.80

# Prototype conversion:
# 1 mm of runoff = 0.1 cm water depth
MM_TO_CM = 0.10

# Terrain adjustment used ONLY for the development
# prototype. It represents greater accumulation potential
# at lower elevations.
#
# IMPORTANT:
# This is NOT a physical hydrodynamic equation.
TERRAIN_EFFECT_FACTOR = 0.05


# =========================================================
# RISK CLASSIFICATION
# =========================================================

def _calculate_risk(
    water_depth_cm: float,
) -> str:
    """
    Classify flooding severity from predicted
    surface-water depth.
    """

    if water_depth_cm < 2.0:
        return "low"

    if water_depth_cm < 10.0:
        return "moderate"

    if water_depth_cm < 20.0:
        return "high"

    return "severe"


# =========================================================
# APPLY OBSERVED RAINFALL TO GRID
# =========================================================

def _apply_rainfall_to_grid(
    development_grid: RainfallGrid,
    rainfall_mm: float,
    source: str,
) -> RainfallGrid:
    """
    Apply one rainfall observation uniformly across
    the development grid.

    This is a temporary bridge between a point rainfall
    observation and the spatial flood model.

    It is NOT a spatial rainfall field.
    """

    rainfall_mm = max(
        0.0,
        float(rainfall_mm),
    )

    updated_cells = []

    for cell in development_grid.cells:
        updated_cells.append(
            cell.model_copy(
                update={
                    "rainfall_mm": rainfall_mm,
                }
            )
        )

    return development_grid.model_copy(
        update={
            "source": source,
            "cells": updated_cells,
        }
    )


# =========================================================
# TERRAIN NORMALIZATION
# =========================================================

def _calculate_elevation_factor(
    elevation_m: float,
    minimum_elevation_m: float,
    maximum_elevation_m: float,
) -> float:
    """
    Calculate a normalized terrain factor.

    Lower-elevation cells receive a slightly larger
    accumulation factor.

    Output is approximately:

        1.00 → highest terrain
        >1.00 → lower terrain

    This is a prototype terrain adjustment only.
    """

    elevation_range = (
        maximum_elevation_m
        - minimum_elevation_m
    )

    if elevation_range <= 0:
        return 1.0

    normalized_low_point = (
        maximum_elevation_m
        - elevation_m
    ) / elevation_range

    factor = (
        1.0
        + normalized_low_point
        * TERRAIN_EFFECT_FACTOR
    )

    return max(
        1.0,
        factor,
    )


# =========================================================
# SURFACE FLOOD MODEL
# =========================================================

def generate_surface_flood_grid(
    rainfall_grid: RainfallGrid | None = None,
) -> FloodGrid:
    """
    Generate the surface flood prediction grid.

    Pipeline:

        Rainfall
            ↓
        Runoff
            ↓
        DEM / terrain adjustment
            ↓
        Water depth
            ↓
        Risk

    Current development assumptions:

        runoff coefficient = 0.80
        1 mm runoff = 0.1 cm depth

    IMPORTANT:

    This is still a prototype surface-flood model.
    Real flood depth requires hydrological/hydrodynamic
    modelling, drainage, infiltration, flow direction,
    storage and real terrain data.
    """

    # =====================================================
    # 1. DETERMINE RAINFALL GRID
    # =====================================================

    model_source = (
        "development_rainfall_surface_flood_model"
    )

    if rainfall_grid is None:

        rainfall_grid = (
            generate_development_rainfall_grid()
        )

        latest_rainfall = (
            get_latest_rainfall()
        )

        if latest_rainfall.status == "imd_live":

            rainfall_grid = (
                _apply_rainfall_to_grid(
                    development_grid=rainfall_grid,
                    rainfall_mm=(
                        latest_rainfall.rainfall_mm
                    ),
                    source="IMD_station_rainfall",
                )
            )

            model_source = (
                "imd_rainfall_surface_flood_model"
            )

    else:

        if (
            rainfall_grid.source
            == "IMD_station_rainfall"
        ):

            model_source = (
                "imd_rainfall_surface_flood_model"
            )

        else:

            model_source = (
                "development_rainfall_surface_flood_model"
            )

    # =====================================================
    # 2. LOAD DEM
    # =====================================================

    dem_grid = (
        generate_development_dem()
    )

    # =====================================================
    # 3. VALIDATE GRID CONTENT
    # =====================================================

    if not rainfall_grid.cells:

        return FloodGrid(
            source=model_source,
            timestamp=(
                rainfall_grid.timestamp.isoformat()
            ),
            rows=0,
            columns=0,
            cells=[],
        )

    if not dem_grid.cells:

        return FloodGrid(
            source=model_source,
            timestamp=(
                rainfall_grid.timestamp.isoformat()
            ),
            rows=0,
            columns=0,
            cells=[],
        )

    # =====================================================
    # 4. INDEX DEM CELLS
    # =====================================================

    dem_by_position = {
        (
            cell.row,
            cell.column,
        ): cell
        for cell in dem_grid.cells
    }

    elevations = [
        float(cell.elevation_m)
        for cell in dem_grid.cells
    ]

    minimum_elevation_m = min(
        elevations
    )

    maximum_elevation_m = max(
        elevations
    )

    # =====================================================
    # 5. CALCULATE FLOOD CELLS
    # =====================================================

    flood_cells = []

    for index, rainfall_cell in enumerate(
        rainfall_grid.cells
    ):

        row = index // dem_grid.columns

        column = index % dem_grid.columns

        dem_cell = dem_by_position.get(
            (
                row,
                column,
            )
        )

        if dem_cell is None:
            continue

        # -------------------------------------------------
        # Rainfall
        # -------------------------------------------------

        rainfall_mm = max(
            0.0,
            float(
                rainfall_cell.rainfall_mm
            ),
        )

        # -------------------------------------------------
        # Runoff
        # -------------------------------------------------

        runoff_mm = (
            rainfall_mm
            * RUNOFF_COEFFICIENT
        )

        # -------------------------------------------------
        # Base water depth
        # -------------------------------------------------

        base_depth_cm = (
            runoff_mm
            * MM_TO_CM
        )

        # -------------------------------------------------
        # Terrain factor
        # -------------------------------------------------

        terrain_factor = (
            _calculate_elevation_factor(
                elevation_m=float(
                    dem_cell.elevation_m
                ),
                minimum_elevation_m=(
                    minimum_elevation_m
                ),
                maximum_elevation_m=(
                    maximum_elevation_m
                ),
            )
        )

        # -------------------------------------------------
        # Terrain-adjusted water depth
        # -------------------------------------------------

        water_depth_cm = (
            base_depth_cm
            * terrain_factor
        )

        # -------------------------------------------------
        # Risk
        # -------------------------------------------------

        risk = _calculate_risk(
            water_depth_cm
        )

        # -------------------------------------------------
        # Create flood cell
        # -------------------------------------------------

        flood_cells.append(
            FloodCell(
                row=row,

                column=column,

                latitude=float(
                    rainfall_cell.latitude
                ),

                longitude=float(
                    rainfall_cell.longitude
                ),

                elevation_m=float(
                    dem_cell.elevation_m
                ),

                rainfall_mm=round(
                    rainfall_mm,
                    2,
                ),

                runoff_mm=round(
                    runoff_mm,
                    2,
                ),

                water_depth_cm=round(
                    water_depth_cm,
                    2,
                ),

                risk=risk,
            )
        )

    # =====================================================
    # 6. RETURN FLOOD GRID
    # =====================================================

    return FloodGrid(
        source=model_source,

        timestamp=(
            rainfall_grid.timestamp.isoformat()
        ),

        rows=dem_grid.rows,

        columns=dem_grid.columns,

        cells=flood_cells,
    )
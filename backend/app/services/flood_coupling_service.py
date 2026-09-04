from backend.app.services.surface_flood_service import (
    generate_surface_flood_grid,
)

from backend.app.services.drainage_analysis_service import (
    analyze_drainage_capacity,
)

from backend.app.services.rainfall_grid_service import (
    generate_development_rainfall_grid,
    generate_uniform_rainfall_grid,
)

from backend.app.services.rainfall_service import (
    get_latest_rainfall,
)


# =========================================================
# COUPLED FLOOD ANALYSIS
# =========================================================

def generate_coupled_flood_analysis() -> dict:
    """
    Combine rainfall, surface flooding and drainage.

    Architecture:

        Rainfall Observation
                ↓
        Rainfall Grid
                ↓
        Surface Flood Model
                ↓
        Drainage Analysis
                ↓
        Coupled Flood Result
    """

    # =====================================================
    # 1. GET RAINFALL ONCE
    # =====================================================

    rainfall = get_latest_rainfall()

    # =====================================================
    # 2. BUILD RAINFALL GRID
    # =====================================================

    if rainfall.status == "imd_live":

        rainfall_grid = generate_uniform_rainfall_grid(
            rainfall.rainfall_mm
        )

        # Mark this grid as IMD-based.
        rainfall_grid = rainfall_grid.model_copy(
            update={
                "source": "IMD_station_rainfall",
            }
        )

        rainfall_source = "IMD"

        model_source = (
            "IMD rainfall + coupled flood model"
        )

    else:

        rainfall_grid = (
            generate_development_rainfall_grid()
        )

        rainfall_source = "development"

        model_source = (
            "development rainfall grid + "
            "coupled flood model"
        )

    # =====================================================
    # 3. RUN SURFACE FLOOD MODEL
    # =====================================================

    surface_flood = generate_surface_flood_grid(
        rainfall_grid
    )

    # =====================================================
    # 4. RUN DRAINAGE ANALYSIS
    # =====================================================

    drainage_analysis = analyze_drainage_capacity(
        surface_flood
    
)

    # =====================================================
    # 5. COUNT RISK LEVELS
    # =====================================================

    risk_counts = {
        "low": 0,
        "moderate": 0,
        "high": 0,
        "severe": 0,
    }

    for cell in surface_flood.cells:

        risk = str(
            cell.risk
        ).lower()

        if risk in risk_counts:
            risk_counts[risk] += 1

    # =====================================================
    # 6. MAXIMUM WATER DEPTH
    # =====================================================

    max_depth_cm = 0.0

    if surface_flood.cells:

        max_depth_cm = max(
            float(
                cell.water_depth_cm
            )
            for cell in surface_flood.cells
        )

    # =====================================================
    # 7. OVERLOADED DRAINAGE EDGES
    # =====================================================

    overloaded_edges = [
        edge
        for edge in drainage_analysis.edges
        if float(edge.utilization) > 1.0
    ]

    # =====================================================
    # 8. OVERALL RISK
    # =====================================================

    if (
        risk_counts["severe"] > 0
        or len(overloaded_edges) > 0
    ):

        overall_status = "severe"

    elif risk_counts["high"] > 0:

        overall_status = "high"

    elif risk_counts["moderate"] > 0:

        overall_status = "moderate"

    else:

        overall_status = "low"

    # =====================================================
    # 9. RETURN COMPLETE RESULT
    # =====================================================

    return {

        # -------------------------------------------------
        # MODEL SOURCE
        # -------------------------------------------------

        "source": model_source,

        # -------------------------------------------------
        # RAINFALL
        # -------------------------------------------------

        "rainfall": {

            "source": rainfall_source,

            "station": rainfall.station,

            "rainfall_mm": round(
                float(
                    rainfall.rainfall_mm
                ),
                2,
            ),

            "timestamp": (
                rainfall.timestamp.isoformat()
            ),

            "status": rainfall.status,
        },

        # -------------------------------------------------
        # FLOOD SUMMARY
        # -------------------------------------------------

        "overall_status": overall_status,

        "max_water_depth_cm": round(
            max_depth_cm,
            2,
        ),

        "flooded_cells": {
            "low": risk_counts["low"],
            "moderate": risk_counts["moderate"],
            "high": risk_counts["high"],
            "severe": risk_counts["severe"],
        },

        # -------------------------------------------------
        # DRAINAGE
        # -------------------------------------------------

        "overloaded_drainage_edges": (
            len(overloaded_edges)
        ),

        # -------------------------------------------------
        # SURFACE FLOOD DETAILS
        # -------------------------------------------------

        "surface_flood": (
            surface_flood.model_dump()
        ),

        # -------------------------------------------------
        # DRAINAGE DETAILS
        # -------------------------------------------------

        "drainage_analysis": (
            drainage_analysis.model_dump()
        ),
    }
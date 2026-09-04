from datetime import datetime, timezone
from typing import Literal

from backend.app.services.rainfall_grid_service import (
    generate_uniform_rainfall_grid,
)

from backend.app.services.surface_flood_service import (
    generate_surface_flood_grid,
)

from backend.app.services.drainage_analysis_service import (
    analyze_drainage_capacity,
)


# ============================================================
# NOWCAST CONFIGURATION
# ============================================================

FORECAST_INTERVAL_MINUTES = 30
FORECAST_HORIZON_MINUTES = 180

RUNOFF_COEFFICIENT = 0.80


# ============================================================
# RAINFALL SCENARIOS
# ============================================================

SCENARIOS = {
    "normal": [
        20.0,
        22.0,
        24.0,
        26.0,
        28.0,
        30.0,
        32.0,
    ],

    "heavy": [
        30.0,
        40.0,
        50.0,
        65.0,
        80.0,
        95.0,
        110.0,
    ],

    "extreme": [
        40.0,
        60.0,
        80.0,
        105.0,
        130.0,
        155.0,
        180.0,
    ],
}


# ============================================================
# RISK CALCULATION
# ============================================================

def calculate_risk(
    water_depth_cm: float,
) -> str:
    """
    Classify flooding severity using the same
    depth thresholds as the surface flood model.

    < 2 cm   -> low
    < 10 cm  -> moderate
    < 20 cm  -> high
    >= 20 cm -> severe
    """

    depth = float(
        water_depth_cm
    )

    if depth < 2.0:
        return "low"

    if depth < 10.0:
        return "moderate"

    if depth < 20.0:
        return "high"

    return "severe"


# ============================================================
# FORECAST STEP
# ============================================================

def _run_forecast_step(
    rainfall_mm: float,
    minutes_ahead: int,
):
    """
    Run one forecast timestep:

        rainfall
            ↓
        DEM / surface model
            ↓
        surface flood
            ↓
        drainage capacity
            ↓
        risk

    This is a development simulation and does not
    represent live Doppler radar nowcasting.
    """

    # ========================================================
    # 1. RAINFALL GRID
    # ========================================================

    rainfall_grid = (
        generate_uniform_rainfall_grid(
            rainfall_mm
        )
    )

    # ========================================================
    # 2. SURFACE FLOOD
    # ========================================================

    surface_flood = (
        generate_surface_flood_grid(
            rainfall_grid
        )
    )

    # ========================================================
    # 3. DRAINAGE ANALYSIS
    # ========================================================

    drainage_analysis = (
        analyze_drainage_capacity(
            surface_flood
        )
    )

    # ========================================================
    # 4. FLOOD STATISTICS
    # ========================================================

    max_water_depth_cm = 0.0
    flooded_cells = 0
    severe_cells = 0

    flood_cells = []

    for cell in surface_flood.cells:

        depth = float(
            cell.water_depth_cm
        )

        max_water_depth_cm = max(
            max_water_depth_cm,
            depth,
        )

        if depth > 0.0:
            flooded_cells += 1

        # Recalculate using the common nowcast
        # risk classification.
        cell_risk = calculate_risk(
            depth
        )

        if cell_risk == "severe":
            severe_cells += 1

        flood_cells.append(
            {
                "row": cell.row,

                "column": cell.column,

                "latitude": cell.latitude,

                "longitude": cell.longitude,

                "elevation_m":
                    cell.elevation_m,

                "rainfall_mm":
                    cell.rainfall_mm,

                "runoff_mm":
                    cell.runoff_mm,

                "water_depth_cm":
                    cell.water_depth_cm,

                "risk":
                    cell_risk,
            }
        )

    # ========================================================
    # 5. DRAINAGE STATISTICS
    # ========================================================

    overloaded_drainage_edges = 0
    severe_surcharge_edges = 0
    max_utilization = 0.0

    drainage_edges = []

    for edge in drainage_analysis.edges:

        utilization = float(
            edge.utilization
        )

        max_utilization = max(
            max_utilization,
            utilization,
        )

        if utilization > 1.0:
            overloaded_drainage_edges += 1

        if (
            edge.status
            == "severe_surcharge"
        ):
            severe_surcharge_edges += 1

        drainage_edges.append(
            {
                "edge_id":
                    edge.edge_id,

                "from_node":
                    edge.from_node,

                "to_node":
                    edge.to_node,

                "rainfall_runoff_m3s":
                    edge.rainfall_runoff_m3s,

                "capacity_m3s":
                    edge.capacity_m3s,

                "utilization":
                    edge.utilization,

                "surcharge_m3s":
                    edge.surcharge_m3s,

                "status":
                    edge.status,
            }
        )

    # ========================================================
    # 6. OVERALL RISK
    # ========================================================

    if (
        severe_cells > 0
        or severe_surcharge_edges > 0
    ):

        overall_risk = "severe"

    elif (
        max_water_depth_cm >= 10.0
        or overloaded_drainage_edges > 0
    ):

        overall_risk = "high"

    elif max_water_depth_cm >= 2.0:

        overall_risk = "moderate"

    else:

        overall_risk = "low"

    # ========================================================
    # 7. RETURN FORECAST
    # ========================================================

    return {
        "minutes_ahead":
            minutes_ahead,

        "time_label":
            (
                "Now"
                if minutes_ahead == 0
                else f"+{minutes_ahead} min"
            ),

        "rainfall_mm":
            rainfall_mm,

        "runoff_mm":
            round(
                rainfall_mm
                * RUNOFF_COEFFICIENT,
                2,
            ),

        "max_water_depth_cm":
            round(
                max_water_depth_cm,
                2,
            ),

        "flooded_cells":
            flooded_cells,

        "overloaded_drainage_edges":
            overloaded_drainage_edges,

        "severe_surcharge_edges":
            severe_surcharge_edges,

        "max_drainage_utilization":
            round(
                max_utilization,
                3,
            ),

        "risk":
            overall_risk,

        "flood_cells":
            flood_cells,

        "drainage_edges":
            drainage_edges,
    }


# ============================================================
# GENERATE 0-3 HOUR NOWCAST
# ============================================================

def generate_nowcast(
    scenario: Literal[
        "normal",
        "heavy",
        "extreme",
    ] = "heavy",
):
    """
    Generate a 0-3 hour development nowcast.

    Forecast points:
        0
        +30
        +60
        +90
        +120
        +150
        +180 minutes

    Rainfall values represent the simulated rainfall
    scenario input at each forecast timestep.

    They are NOT cumulative rainfall totals.
    """

    if scenario not in SCENARIOS:
        scenario = "heavy"

    timestamp = datetime.now(
        timezone.utc
    )

    rainfall_forecast = (
        SCENARIOS[scenario]
    )

    forecasts = []

    # ========================================================
    # 0 → 180 MINUTES
    # ========================================================

    for index, rainfall_mm in enumerate(
        rainfall_forecast
    ):

        minutes_ahead = (
            index
            * FORECAST_INTERVAL_MINUTES
        )

        forecast_result = (
            _run_forecast_step(
                rainfall_mm=rainfall_mm,
                minutes_ahead=minutes_ahead,
            )
        )

        forecasts.append(
            forecast_result
        )

    # ========================================================
    # OVERALL SUMMARY
    # ========================================================

    max_forecast_depth_cm = max(
        (
            forecast[
                "max_water_depth_cm"
            ]
            for forecast in forecasts
        ),
        default=0.0,
    )

    max_forecast_rainfall_mm = max(
        (
            forecast[
                "rainfall_mm"
            ]
            for forecast in forecasts
        ),
        default=0.0,
    )

    peak_overloaded_edges = max(
        (
            forecast[
                "overloaded_drainage_edges"
            ]
            for forecast in forecasts
        ),
        default=0,
    )

    peak_drainage_utilization = max(
        (
            forecast[
                "max_drainage_utilization"
            ]
            for forecast in forecasts
        ),
        default=0.0,
    )

    risk_order = {
        "low": 0,
        "moderate": 1,
        "high": 2,
        "severe": 3,
    }

    peak_forecast_risk = max(
        (
            forecast["risk"]
            for forecast in forecasts
        ),
        key=lambda risk:
            risk_order[risk],
        default="low",
    )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "project":
            "SIH26085",

        "mode":
            "simulation",

        "rainfall_source":
            "development_scenario",

        "model_type":
            (
                "coupled_rainfall_dem_"
                "surface_flood_drainage_"
                "nowcast"
            ),

        "scenario":
            scenario,

        "generated_at":
            timestamp,

        "forecast_horizon_minutes":
            FORECAST_HORIZON_MINUTES,

        "interval_minutes":
            FORECAST_INTERVAL_MINUTES,

        "summary": {
            "peak_rainfall_mm":
                max_forecast_rainfall_mm,

            "peak_water_depth_cm":
                round(
                    max_forecast_depth_cm,
                    2,
                ),

            "peak_overloaded_drainage_edges":
                peak_overloaded_edges,

            "peak_drainage_utilization":
                round(
                    peak_drainage_utilization,
                    3,
                ),

            "peak_risk":
                peak_forecast_risk,
        },

        "forecasts":
            forecasts,
    }
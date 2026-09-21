from datetime import datetime, timezone
from typing import Literal

from backend.app.services.rainfall_service import (
    get_latest_rainfall,
)

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
# SIH26085 — URBAN FLOOD NOWCASTING
# NOWCAST SERVICE
# ============================================================

FORECAST_INTERVAL_MINUTES = 30
FORECAST_HORIZON_MINUTES = 180

RUNOFF_COEFFICIENT = 0.80


# ============================================================
# DEVELOPMENT RAINFALL SCENARIOS
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
# PROTOTYPE LIVE PROJECTION FACTORS
# ============================================================

# These factors are used ONLY when live IMD observation
# is available.
#
# IMPORTANT:
# IMD AWS value is an observation, not a Doppler forecast.
# Therefore this is explicitly treated as a prototype
# short-horizon projection.
#
# 0 min   -> 1.00 × current observation
# 30 min  -> 1.05 ×
# 60 min  -> 1.10 ×
# 90 min  -> 1.15 ×
# 120 min -> 1.20 ×
# 150 min -> 1.25 ×
# 180 min -> 1.30 ×

LIVE_PROJECTION_FACTORS = [
    1.00,
    1.05,
    1.10,
    1.15,
    1.20,
    1.25,
    1.30,
]


# ============================================================
# SPATIAL RAINFALL PATTERN
# ============================================================

SPATIAL_FACTORS = [
    [0.25, 0.55, 0.80],
    [0.40, 1.00, 1.35],
    [0.30, 1.10, 3.25],
]


# ============================================================
# RISK CALCULATION
# ============================================================

def calculate_risk(
    water_depth_cm: float,
) -> str:

    depth = max(
        0.0,
        float(water_depth_cm),
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
    rainfall_source: str = "development_scenario",
):
    """
    Run one forecast timestep.

    Pipeline:

        Rainfall
            ↓
        Spatial rainfall grid
            ↓
        Surface flood model
            ↓
        Drainage capacity analysis
    """

    rainfall_mm = max(
        0.0,
        float(rainfall_mm),
    )

    # ========================================================
    # 1. CREATE SPATIAL RAINFALL GRID
    # ========================================================

    rainfall_grid = generate_uniform_rainfall_grid(
        rainfall_mm
    )

    # ========================================================
    # 2. APPLY SPATIAL VARIATION
    # ========================================================

    # Development simulation uses a synthetic spatial pattern.
    #
    # Live IMD currently provides a station observation,
    # therefore we keep live rainfall spatially uniform across
    # the prototype grid.
    #
    # A future Doppler radar grid can replace this section.

    if rainfall_source == "development_scenario":

        columns = len(
            SPATIAL_FACTORS[0]
        )

        for cell_index, cell in enumerate(
            rainfall_grid.cells
        ):

            row = (
                cell_index
                // columns
            )

            column = (
                cell_index
                % columns
            )

            if (
                row < len(SPATIAL_FACTORS)
                and column
                < len(SPATIAL_FACTORS[row])
            ):
                factor = (
                    SPATIAL_FACTORS[
                        row
                    ][column]
                )
            else:
                factor = 1.0

            cell.rainfall_mm = round(
                rainfall_mm * factor,
                2,
            )

    # ========================================================
    # 3. SURFACE FLOOD MODEL
    # ========================================================

    surface_flood = (
        generate_surface_flood_grid(
            rainfall_grid
        )
    )

    # ========================================================
    # 4. DRAINAGE CAPACITY ANALYSIS
    # ========================================================

    drainage_analysis = (
        analyze_drainage_capacity(
            surface_flood
        )
    )

    # ========================================================
    # 5. FLOOD STATISTICS
    # ========================================================

    max_water_depth_cm = 0.0

    flooded_cells = 0

    severe_cells = 0
    high_cells = 0
    moderate_cells = 0
    low_cells = 0

    flood_cells = []

    for cell in surface_flood.cells:

        depth = max(
            0.0,
            float(
                cell.water_depth_cm
            ),
        )

        max_water_depth_cm = max(
            max_water_depth_cm,
            depth,
        )

        if depth > 0.0:
            flooded_cells += 1

        cell_risk = calculate_risk(
            depth
        )

        if cell_risk == "severe":
            severe_cells += 1

        elif cell_risk == "high":
            high_cells += 1

        elif cell_risk == "moderate":
            moderate_cells += 1

        else:
            low_cells += 1

        flood_cells.append(
            {
                "row": int(
                    cell.row
                ),

                "column": int(
                    cell.column
                ),

                "latitude": (
                    cell.latitude
                ),

                "longitude": (
                    cell.longitude
                ),

                "elevation_m": round(
                    float(
                        cell.elevation_m
                    ),
                    2,
                ),

                "rainfall_mm": round(
                    float(
                        cell.rainfall_mm
                    ),
                    2,
                ),

                "runoff_mm": round(
                    float(
                        cell.runoff_mm
                    ),
                    2,
                ),

                "water_depth_cm": round(
                    depth,
                    2,
                ),

                "risk": cell_risk,
            }
        )

    # ========================================================
    # 6. DRAINAGE STATISTICS
    # ========================================================

    overloaded_drainage_edges = 0
    severe_surcharge_edges = 0

    max_utilization = 0.0

    drainage_edges = []

    for edge in drainage_analysis.edges:

        utilization = max(
            0.0,
            float(
                edge.utilization
            ),
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
                "edge_id": (
                    edge.edge_id
                ),

                "from_node": (
                    edge.from_node
                ),

                "to_node": (
                    edge.to_node
                ),

                "rainfall_runoff_m3s":
                    round(
                        float(
                            edge.rainfall_runoff_m3s
                        ),
                        4,
                    ),

                "capacity_m3s":
                    round(
                        float(
                            edge.capacity_m3s
                        ),
                        4,
                    ),

                "utilization":
                    round(
                        utilization,
                        4,
                    ),

                "surcharge_m3s":
                    round(
                        float(
                            edge.surcharge_m3s
                        ),
                        4,
                    ),

                "status": (
                    edge.status
                ),
            }
        )

    # ========================================================
    # 7. OVERALL FLOOD RISK
    # ========================================================

    overall_risk = calculate_risk(
        max_water_depth_cm
    )

    # ========================================================
    # 8. RETURN FORECAST STEP
    # ========================================================

    return {
        "minutes_ahead":
            minutes_ahead,

        "time_label": (
            "Now"
            if minutes_ahead == 0
            else f"+{minutes_ahead} min"
        ),

        "rainfall_mm": round(
            rainfall_mm,
            2,
        ),

        "rainfall_source":
            rainfall_source,

        "runoff_mm": round(
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

        "risk_counts": {
            "low": low_cells,
            "moderate": moderate_cells,
            "high": high_cells,
            "severe": severe_cells,
        },

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
# GENERATE 0–3 HOUR NOWCAST
# ============================================================

def generate_nowcast(
    scenario: Literal[
        "live",
        "normal",
        "heavy",
        "extreme",
    ] = "live",
):
    """
    Generate the 0–3 hour coupled flood nowcast.

    LIVE MODE:
        Uses the latest IMD AWS observation as the baseline
        and applies a clearly-labelled prototype projection.

    SIMULATION MODE:
        Uses normal/heavy/extreme development scenarios.

    IMPORTANT:
        IMD AWS rainfall is an observation.
        It is NOT claimed to be a Doppler 0–3 hour forecast.
    """

    # ========================================================
    # 1. NORMALIZE SCENARIO
    # ========================================================

    scenario = scenario.lower().strip()

    # ========================================================
    # 2. LIVE MODE
    # ========================================================

    if scenario == "live":

        live_rainfall = (
            get_latest_rainfall()
        )

        if (
            live_rainfall.status
            == "imd_live"
        ):

            live_rainfall_mm = max(
                0.0,
                float(
                    live_rainfall.rainfall_mm
                ),
            )

            timestamp = (
                live_rainfall.timestamp
            )

            # ==================================================
            # PROTOTYPE 0–3H PROJECTION
            # ==================================================

            rainfall_values = []

            for factor in (
                LIVE_PROJECTION_FACTORS
            ):

                projected_rainfall = (
                    live_rainfall_mm
                    * factor
                )

                rainfall_values.append(
                    round(
                        projected_rainfall,
                        2,
                    )
                )

            rainfall_source = "IMD"
            mode = (
                "live_observation_projection"
            )

        else:

            # ==================================================
            # IMD FAILURE FALLBACK
            # ==================================================

            timestamp = (
                datetime.now(
                    timezone.utc
                )
            )

            rainfall_values = (
                SCENARIOS["heavy"]
            )

            rainfall_source = (
                "development_fallback"
            )

            mode = "simulation"

    # ========================================================
    # 3. DEVELOPMENT SCENARIO MODE
    # ========================================================

    else:

        timestamp = (
            datetime.now(
                timezone.utc
            )
        )

        rainfall_values = SCENARIOS.get(
            scenario,
            SCENARIOS["heavy"],
        )

        rainfall_source = (
            "development_scenario"
        )

        mode = "simulation"

    # ========================================================
    # 4. RUN 0–180 MINUTE FORECAST
    # ========================================================

    forecasts = []

    for index, rainfall_mm in enumerate(
        rainfall_values
    ):

        minutes_ahead = (
            index
            * FORECAST_INTERVAL_MINUTES
        )

        forecast_result = (
            _run_forecast_step(
                rainfall_mm=rainfall_mm,
                minutes_ahead=minutes_ahead,
                rainfall_source=(
                    rainfall_source
                ),
            )
        )

        forecasts.append(
            forecast_result
        )

    # ========================================================
    # 5. OVERALL SUMMARY
    # ========================================================

    max_forecast_depth_cm = max(
        (
            forecast[
                "max_water_depth_cm"
            ]
            for forecast
            in forecasts
        ),
        default=0.0,
    )

    max_forecast_rainfall_mm = max(
        (
            forecast[
                "rainfall_mm"
            ]
            for forecast
            in forecasts
        ),
        default=0.0,
    )

    peak_overloaded_edges = max(
        (
            forecast[
                "overloaded_drainage_edges"
            ]
            for forecast
            in forecasts
        ),
        default=0,
    )

    peak_drainage_utilization = max(
        (
            forecast[
                "max_drainage_utilization"
            ]
            for forecast
            in forecasts
        ),
        default=0.0,
    )

    peak_forecast_risk = (
        calculate_risk(
            max_forecast_depth_cm
        )
    )

    peak_forecast = max(
        forecasts,
        key=lambda forecast:
            forecast[
                "max_water_depth_cm"
            ],
        default=None,
    )

    peak_time_minutes = (
        peak_forecast[
            "minutes_ahead"
        ]
        if peak_forecast
        else 0
    )

    # ========================================================
    # 6. RETURN COMPLETE NOWCAST
    # ========================================================

    return {
        "project":
            "SIH26085",

        "mode":
            mode,

        "rainfall_source":
            rainfall_source,

        "model_type":
            (
                "coupled_rainfall_dem_"
                "surface_flood_drainage_"
                "nowcast"
            ),

        "scenario": (
            None
            if scenario == "live"
            else scenario
        ),

        "generated_at":
            timestamp,

        "forecast_horizon_minutes":
            FORECAST_HORIZON_MINUTES,

        "interval_minutes":
            FORECAST_INTERVAL_MINUTES,

        "summary": {
            "peak_rainfall_mm":
                round(
                    max_forecast_rainfall_mm,
                    2,
                ),

            "peak_water_depth_cm":
                round(
                    max_forecast_depth_cm,
                    2,
                ),

            "peak_time_minutes":
                peak_time_minutes,

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
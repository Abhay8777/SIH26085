from fastapi import APIRouter, Query

from backend.app.services.nowcast_service import (
    generate_nowcast,
)

from backend.app.services.safe_route_service import (
    calculate_safe_route,
)

from backend.app.services.blockage_service import (
    simulate_drainage_blockage,
)

from backend.app.services.drainage_service import (
    generate_development_drainage_network,
)


router = APIRouter()


# ============================================================
# VALIDATION CONFIGURATION
# ============================================================

VALID_FORECAST_MINUTES = {
    0,
    30,
    60,
    90,
    120,
    150,
    180,
}

VALID_SCENARIOS = {
    "normal",
    "heavy",
    "extreme",
}

VALID_DRAINAGE_EDGES = {
    "E1",
    "E2",
    "E3",
}


# ============================================================
# VALIDATION HELPERS
# ============================================================

def _validate_scenario(
    scenario: str,
) -> dict | None:

    if scenario not in VALID_SCENARIOS:
        return {
            "status": "error",
            "message": (
                "Invalid rainfall scenario. "
                "Use normal, heavy, or extreme."
            ),
        }

    return None


def _validate_forecast_minutes(
    minutes_ahead: int,
) -> dict | None:

    if minutes_ahead not in VALID_FORECAST_MINUTES:
        return {
            "status": "error",
            "message": (
                "Invalid forecast timestep. "
                "Use 0, 30, 60, 90, 120, 150, or 180."
            ),
        }

    return None


# ============================================================
# 0-3 HOUR FLOOD NOWCAST
# ============================================================

@router.get("/nowcast")
def flood_nowcast(
    scenario: str = Query(
        default="heavy",
        description=(
            "Rainfall scenario: "
            "normal, heavy, or extreme"
        ),
    )
):
    """
    Return the complete 0-3 hour coupled flood nowcast.

    Pipeline:

        Rainfall
            ↓
        Surface flood
            ↓
        Drainage capacity
            ↓
        Risk analysis
    """

    scenario_error = _validate_scenario(
        scenario
    )

    if scenario_error is not None:
        return scenario_error

    return generate_nowcast(
        scenario=scenario
    )


# ============================================================
# SPATIAL FLOOD NOWCAST MAP
# ============================================================

@router.get("/nowcast-map")
def flood_nowcast_map(
    scenario: str = Query(
        default="heavy",
        description=(
            "Rainfall scenario: "
            "normal, heavy, or extreme"
        ),
    ),

    minutes_ahead: int = Query(
        default=0,
        ge=0,
        le=180,
        description=(
            "Forecast timestep in minutes: "
            "0, 30, 60, 90, 120, 150, or 180"
        ),
    ),
):
    """
    Return spatial flood + drainage information
    for the selected 0-3 hour forecast timestep.
    """

    # ========================================================
    # VALIDATE INPUT
    # ========================================================

    scenario_error = _validate_scenario(
        scenario
    )

    if scenario_error is not None:
        return scenario_error

    timestep_error = _validate_forecast_minutes(
        minutes_ahead
    )

    if timestep_error is not None:
        return timestep_error

    # ========================================================
    # GENERATE NOWCAST
    # ========================================================

    nowcast = generate_nowcast(
        scenario=scenario
    )

    # ========================================================
    # FIND SELECTED FORECAST
    # ========================================================

    selected_forecast = None

    for forecast in nowcast["forecasts"]:

        if (
            forecast["minutes_ahead"]
            == minutes_ahead
        ):
            selected_forecast = forecast
            break

    if selected_forecast is None:
        return {
            "status": "error",
            "message": (
                "Forecast timestep is not available."
            ),
        }

    # ========================================================
    # EXTRACT DATA
    # ========================================================

    drainage_edges = (
        selected_forecast.get(
            "drainage_edges",
            [],
        )
    )

    flood_cells = (
        selected_forecast.get(
            "flood_cells",
            [],
        )
    )

    # ========================================================
    # RETURN MAP DATA
    # ========================================================

    return {
        "status": "success",
        "project": "SIH26085",
        "mode": nowcast["mode"],
        "rainfall_source": nowcast["rainfall_source"],
        "scenario": nowcast["scenario"],
        "generated_at": nowcast["generated_at"],
        "forecast_horizon_minutes": (
            nowcast["forecast_horizon_minutes"]
        ),

        "forecast": {
            "minutes_ahead": (
                selected_forecast["minutes_ahead"]
            ),
            "time_label": (
                selected_forecast["time_label"]
            ),
            "rainfall_mm": (
                selected_forecast["rainfall_mm"]
            ),
            "runoff_mm": (
                selected_forecast["runoff_mm"]
            ),
            "max_water_depth_cm": (
                selected_forecast["max_water_depth_cm"]
            ),
            "flooded_cells": (
                selected_forecast["flooded_cells"]
            ),
            "overloaded_drainage_edges": (
                selected_forecast[
                    "overloaded_drainage_edges"
                ]
            ),
            "severe_surcharge_edges": (
                selected_forecast[
                    "severe_surcharge_edges"
                ]
            ),
            "max_drainage_utilization": (
                selected_forecast[
                    "max_drainage_utilization"
                ]
            ),
            "risk": (
                selected_forecast["risk"]
            ),

            "flood_cells": flood_cells,

            "drainage_edges": drainage_edges,
        },
    }


# ============================================================
# FLOOD-SAFE ROUTE API
# ============================================================

@router.get("/safe-route")
def flood_safe_route(
    start_latitude: float = Query(
        default=19.0500,
        description="Starting latitude",
    ),

    start_longitude: float = Query(
        default=72.8500,
        description="Starting longitude",
    ),

    destination_latitude: float = Query(
        default=19.0680,
        description="Destination latitude",
    ),

    destination_longitude: float = Query(
        default=72.8590,
        description="Destination longitude",
    ),

    scenario: str = Query(
        default="heavy",
        description=(
            "Rainfall scenario: "
            "normal, heavy, or extreme"
        ),
    ),

    minutes_ahead: int = Query(
        default=60,
        ge=0,
        le=180,
        description=(
            "Forecast time in minutes: "
            "0, 30, 60, 90, 120, 150, or 180"
        ),
    ),
):
    """
    Calculate a flood-safe route using
    the selected coupled flood forecast.
    """

    # ========================================================
    # VALIDATE INPUT
    # ========================================================

    scenario_error = _validate_scenario(
        scenario
    )

    if scenario_error is not None:
        return scenario_error

    timestep_error = _validate_forecast_minutes(
        minutes_ahead
    )

    if timestep_error is not None:
        return timestep_error

    # ========================================================
    # GENERATE NOWCAST
    # ========================================================

    nowcast = generate_nowcast(
        scenario=scenario
    )

    # ========================================================
    # FIND FORECAST
    # ========================================================

    selected_forecast = None

    for forecast in nowcast["forecasts"]:

        if (
            forecast["minutes_ahead"]
            == minutes_ahead
        ):
            selected_forecast = forecast
            break

    if selected_forecast is None:
        return {
            "status": "error",
            "message": (
                "Forecast timestep is not available."
            ),
        }

    # ========================================================
    # FLOOD CELLS
    # ========================================================

    flood_cells = (
        selected_forecast.get(
            "flood_cells",
            [],
        )
    )

    # ========================================================
    # CALCULATE SAFE ROUTE
    # ========================================================

    result = calculate_safe_route(
        start_latitude=start_latitude,
        start_longitude=start_longitude,
        destination_latitude=destination_latitude,
        destination_longitude=destination_longitude,
        flood_cells=flood_cells,
    )

    # ========================================================
    # RETURN ROUTE
    # ========================================================

    return {
        "status": "success",
        "project": "SIH26085",
        "mode": nowcast["mode"],
        "rainfall_source": (
            nowcast["rainfall_source"]
        ),
        "scenario": nowcast["scenario"],

        "forecast": {
            "minutes_ahead": (
                selected_forecast["minutes_ahead"]
            ),
            "time_label": (
                selected_forecast["time_label"]
            ),
            "rainfall_mm": (
                selected_forecast["rainfall_mm"]
            ),
            "runoff_mm": (
                selected_forecast["runoff_mm"]
            ),
            "max_water_depth_cm": (
                selected_forecast[
                    "max_water_depth_cm"
                ]
            ),
            "risk": (
                selected_forecast["risk"]
            ),
        },

        "route": result,
    }


# ============================================================
# DRAINAGE BLOCKAGE SIMULATION
# ============================================================

@router.get("/blockage-simulation")
def blockage_simulation(
    edge_id: str = Query(
        default="E2",
        description=(
            "Drainage edge to simulate as blocked: "
            "E1, E2, or E3"
        ),
    ),

    scenario: str = Query(
        default="heavy",
        description=(
            "Rainfall scenario: "
            "normal, heavy, or extreme"
        ),
    ),

    minutes_ahead: int = Query(
        default=60,
        ge=0,
        le=180,
        description=(
            "Forecast timestep in minutes: "
            "0, 30, 60, 90, 120, 150, or 180"
        ),
    ),
):
    """
    Development-only drainage blockage simulation.

    Simulates an 80% drainage capacity loss and
    estimates the resulting flood-depth impact.
    """

    # ========================================================
    # VALIDATE INPUT
    # ========================================================

    scenario_error = _validate_scenario(
        scenario
    )

    if scenario_error is not None:
        return scenario_error

    timestep_error = _validate_forecast_minutes(
        minutes_ahead
    )

    if timestep_error is not None:
        return timestep_error

    # ========================================================
    # VALIDATE DRAINAGE EDGE
    # ========================================================

    edge_id = edge_id.upper().strip()

    if edge_id not in VALID_DRAINAGE_EDGES:
        return {
            "status": "error",
            "message": (
                "Invalid drainage edge. "
                "Use E1, E2, or E3."
            ),
        }

    # ========================================================
    # GENERATE NOWCAST
    # ========================================================

    nowcast = generate_nowcast(
        scenario=scenario
    )

    # ========================================================
    # FIND FORECAST
    # ========================================================

    selected_forecast = None

    for forecast in nowcast["forecasts"]:

        if (
            forecast["minutes_ahead"]
            == minutes_ahead
        ):
            selected_forecast = forecast
            break

    if selected_forecast is None:
        return {
            "status": "error",
            "message": (
                "Forecast timestep is not available."
            ),
        }

    # ========================================================
    # GET DRAINAGE ANALYSIS
    # ========================================================

    drainage_analysis = {
        "edges": []
    }

    for edge in selected_forecast.get(
        "drainage_edges",
        [],
    ):
        drainage_analysis["edges"].append(
            dict(edge)
        )

    # ========================================================
    # GET DEVELOPMENT DRAINAGE NETWORK
    # ========================================================

    network = (
        generate_development_drainage_network()
    )

    # ========================================================
    # NODE COORDINATES
    # ========================================================

    node_coordinates = {}

    for node in network.nodes:

        node_coordinates[node.node_id] = {
            "latitude": node.latitude,
            "longitude": node.longitude,
        }

    # ========================================================
    # ADD COORDINATES TO EDGES
    # ========================================================

    for edge in drainage_analysis["edges"]:

        from_node = edge.get(
            "from_node"
        )

        to_node = edge.get(
            "to_node"
        )

        from_coordinates = (
            node_coordinates.get(
                from_node,
                {},
            )
        )

        to_coordinates = (
            node_coordinates.get(
                to_node,
                {},
            )
        )

        edge["from_latitude"] = (
            from_coordinates.get(
                "latitude",
                0.0,
            )
        )

        edge["from_longitude"] = (
            from_coordinates.get(
                "longitude",
                0.0,
            )
        )

        edge["to_latitude"] = (
            to_coordinates.get(
                "latitude",
                0.0,
            )
        )

        edge["to_longitude"] = (
            to_coordinates.get(
                "longitude",
                0.0,
            )
        )

    # ========================================================
    # FLOOD CELLS
    # ========================================================

    flood_cells = (
        selected_forecast.get(
            "flood_cells",
            [],
        )
    )

    # ========================================================
    # RUN BLOCKAGE SIMULATION
    # ========================================================

    result = simulate_drainage_blockage(
        drainage_analysis=drainage_analysis,
        blocked_edges=[edge_id],
        flood_cells=flood_cells,
    )

    # ========================================================
    # RETURN BLOCKAGE RESULT
    # ========================================================

    return {
        "status": "success",
        "project": "SIH26085",
        "mode": "development_simulation",
        "rainfall_source": (
            nowcast["rainfall_source"]
        ),
        "scenario": scenario,

        "forecast": {
            "minutes_ahead": (
                selected_forecast["minutes_ahead"]
            ),
            "time_label": (
                selected_forecast["time_label"]
            ),
            "rainfall_mm": (
                selected_forecast["rainfall_mm"]
            ),
            "runoff_mm": (
                selected_forecast["runoff_mm"]
            ),
            "max_water_depth_cm": (
                selected_forecast[
                    "max_water_depth_cm"
                ]
            ),
            "risk": (
                selected_forecast["risk"]
            ),
        },

        "blocked_edge": edge_id,

        "blockage_simulation": (
            result["blockage_simulation"]
        ),

        "drainage_edges": (
            result["edges"]
        ),

        "flood_cells": (
            result["flood_cells"]
        ),
    }
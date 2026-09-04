# ============================================================
# SIH26085 — DRAINAGE BLOCKAGE SIMULATION
# Development / Demonstration Module
# ============================================================

from copy import deepcopy
from math import sqrt


# ============================================================
# BLOCKAGE CONFIGURATION
# ============================================================

CAPACITY_REDUCTION_PERCENT = 80.0
REMAINING_CAPACITY_PERCENT = 20.0

FLOOD_IMPACT_DISTANCE_DEG = 0.012


# ============================================================
# DISTANCE
# ============================================================

def _distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:

    return sqrt(
        (lat1 - lat2) ** 2
        +
        (lon1 - lon2) ** 2
    )


# ============================================================
# FLOOD RISK CLASSIFICATION
# ============================================================

def _calculate_flood_risk(
    water_depth_cm: float,
) -> str:
    """
    Keep blockage flood-risk thresholds consistent
    with the surface flood model.

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
# BLOCKAGE FLOOD IMPACT
# ============================================================

def _apply_blockage_flood_impact(
    flood_cells: list[dict],
    blocked_edges: list[str],
    edges: list[dict],
) -> list[dict]:

    updated_cells = deepcopy(
        flood_cells
    )

    if not blocked_edges:
        return updated_cells

    blocked_edge_objects = [
        edge
        for edge in edges
        if edge.get("edge_id")
        in blocked_edges
    ]

    if not blocked_edge_objects:
        return updated_cells

    for cell in updated_cells:

        cell_latitude = float(
            cell.get(
                "latitude",
                0.0,
            )
        )

        cell_longitude = float(
            cell.get(
                "longitude",
                0.0,
            )
        )

        maximum_impact = 1.0

        for edge in blocked_edge_objects:

            from_latitude = float(
                edge.get(
                    "from_latitude",
                    0.0,
                )
            )

            from_longitude = float(
                edge.get(
                    "from_longitude",
                    0.0,
                )
            )

            to_latitude = float(
                edge.get(
                    "to_latitude",
                    0.0,
                )
            )

            to_longitude = float(
                edge.get(
                    "to_longitude",
                    0.0,
                )
            )

            distance_from_start = _distance(
                cell_latitude,
                cell_longitude,
                from_latitude,
                from_longitude,
            )

            distance_from_end = _distance(
                cell_latitude,
                cell_longitude,
                to_latitude,
                to_longitude,
            )

            nearest_distance = min(
                distance_from_start,
                distance_from_end,
            )

            utilization = float(
                edge.get(
                    "utilization",
                    0.0,
                )
            )

            # Higher existing utilization means
            # greater blockage impact.
            if utilization > 1.5:

                impact_factor = 1.25

            elif utilization > 1.0:

                impact_factor = 1.15

            else:

                impact_factor = 1.05

            if (
                nearest_distance
                < FLOOD_IMPACT_DISTANCE_DEG
            ):

                maximum_impact = max(
                    maximum_impact,
                    impact_factor,
                )

        original_depth = float(
            cell.get(
                "water_depth_cm",
                0.0,
            )
        )

        simulated_depth = (
            original_depth
            * maximum_impact
        )

        cell[
            "original_water_depth_cm"
        ] = round(
            original_depth,
            3,
        )

        cell[
            "water_depth_cm"
        ] = round(
            simulated_depth,
            3,
        )

        cell[
            "blockage_impact_factor"
        ] = round(
            maximum_impact,
            3,
        )

        cell["risk"] = (
            _calculate_flood_risk(
                simulated_depth
            )
        )

    return updated_cells


# ============================================================
# DRAINAGE BLOCKAGE SIMULATION
# ============================================================

def simulate_drainage_blockage(
    drainage_analysis: dict,
    blocked_edges: list[str] | None = None,
    flood_cells: list[dict] | None = None,
) -> dict:

    blocked_edges = (
        blocked_edges
        or []
    )

    result = deepcopy(
        drainage_analysis
    )

    edges = result.get(
        "edges",
        [],
    )

    # ========================================================
    # VALID EDGE IDs
    # ========================================================

    valid_edge_ids = {
        edge.get("edge_id")
        for edge in edges
        if edge.get("edge_id")
    }

    valid_blocked_edges = [
        edge_id
        for edge_id in blocked_edges
        if edge_id in valid_edge_ids
    ]

    invalid_blocked_edges = [
        edge_id
        for edge_id in blocked_edges
        if edge_id not in valid_edge_ids
    ]

    blocked_count = 0

    # ========================================================
    # PROCESS DRAINAGE EDGES
    # ========================================================

    for edge in edges:

        edge_id = edge.get(
            "edge_id"
        )

        # Every edge gets an explicit default.
        edge["blocked"] = False

        if (
            edge_id
            not in valid_blocked_edges
        ):
            continue

        blocked_count += 1

        # ====================================================
        # ORIGINAL CAPACITY
        # ====================================================

        original_capacity = float(
            edge.get(
                "capacity_m3s",
                0.0,
            )
        )

        # ====================================================
        # APPLY 80% CAPACITY LOSS
        # ====================================================

        simulated_capacity = (
            original_capacity
            * (
                1.0
                - CAPACITY_REDUCTION_PERCENT
                / 100.0
            )
        )

        simulated_capacity = round(
            simulated_capacity,
            3,
        )

        edge[
            "original_capacity_m3s"
        ] = round(
            original_capacity,
            3,
        )

        edge[
            "capacity_m3s"
        ] = simulated_capacity

        edge[
            "simulated_capacity_m3s"
        ] = simulated_capacity

        edge[
            "capacity_reduction_percent"
        ] = CAPACITY_REDUCTION_PERCENT

        edge["blocked"] = True

        # ====================================================
        # FLOW / RUNOFF
        # ====================================================

        flow_value = float(
            edge.get(
                "rainfall_runoff_m3s",
                edge.get(
                    "flow_m3s",
                    0.0,
                ),
            )
        )

        edge[
            "rainfall_runoff_m3s"
        ] = round(
            flow_value,
            3,
        )

        # ====================================================
        # UTILIZATION
        # ====================================================

        if simulated_capacity > 0.0:

            utilization = (
                flow_value
                / simulated_capacity
            )

        else:

            utilization = 999.0

        edge[
            "utilization"
        ] = round(
            utilization,
            3,
        )

        # ====================================================
        # SURCHARGE
        # ====================================================

        surcharge = max(
            0.0,
            flow_value
            - simulated_capacity,
        )

        edge[
            "surcharge_m3s"
        ] = round(
            surcharge,
            3,
        )

        # ====================================================
        # STATUS
        # ====================================================

        if utilization > 1.5:

            edge[
                "status"
            ] = "severe_surcharge"

        elif utilization > 1.0:

            edge[
                "status"
            ] = "over_capacity"

        else:

            edge[
                "status"
            ] = "within_capacity"

    # ========================================================
    # BLOCKAGE FLOOD IMPACT
    # ========================================================

    simulated_flood_cells = []

    if flood_cells:

        simulated_flood_cells = (
            _apply_blockage_flood_impact(
                flood_cells=flood_cells,
                blocked_edges=valid_blocked_edges,
                edges=edges,
            )
        )

    # ========================================================
    # FLOOD SUMMARY
    # ========================================================

    peak_original_depth = 0.0
    peak_simulated_depth = 0.0
    impacted_cells = 0

    for cell in simulated_flood_cells:

        original_depth = float(
            cell.get(
                "original_water_depth_cm",
                cell.get(
                    "water_depth_cm",
                    0.0,
                ),
            )
        )

        simulated_depth = float(
            cell.get(
                "water_depth_cm",
                0.0,
            )
        )

        peak_original_depth = max(
            peak_original_depth,
            original_depth,
        )

        peak_simulated_depth = max(
            peak_simulated_depth,
            simulated_depth,
        )

        if (
            simulated_depth
            > original_depth
        ):

            impacted_cells += 1

    # ========================================================
    # BLOCKAGE SUMMARY
    # ========================================================

    result[
        "blockage_simulation"
    ] = {

        "enabled":
            len(valid_blocked_edges) > 0,

        "blocked_edges":
            valid_blocked_edges,

        "blocked_edge_count":
            blocked_count,

        "invalid_blocked_edges":
            invalid_blocked_edges,

        "capacity_reduction_percent":
            CAPACITY_REDUCTION_PERCENT,

        "remaining_capacity_percent":
            REMAINING_CAPACITY_PERCENT,

        "mode":
            "development_simulation",

        "flood_impact_enabled":
            len(simulated_flood_cells) > 0,

        "impacted_flood_cells":
            impacted_cells,

        "peak_original_water_depth_cm":
            round(
                peak_original_depth,
                3,
            ),

        "peak_simulated_water_depth_cm":
            round(
                peak_simulated_depth,
                3,
            ),
    }

    # ========================================================
    # RETURN SIMULATED FLOOD CELLS
    # ========================================================

    result[
        "flood_cells"
    ] = simulated_flood_cells

    return result
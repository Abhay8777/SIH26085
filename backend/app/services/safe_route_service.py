from math import hypot
from typing import Any

from backend.app.services.drainage_service import (
    generate_development_drainage_network,
)


# ============================================================
# ROUTE RISK THRESHOLDS
# ============================================================

SAFE_DEPTH_CM = 2.0
CAUTION_DEPTH_CM = 5.0
DANGEROUS_DEPTH_CM = 10.0


# ============================================================
# ROUTE SEARCH CONFIGURATION
# ============================================================

FLOOD_CELL_SEARCH_RADIUS_M = 1500.0

# Relative weight applied to flood depth when comparing
# possible route segments.
FLOOD_RISK_WEIGHT = 500.0


# ============================================================
# DISTANCE
# ============================================================

def _distance_m(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:

    latitude_difference = (
        (latitude_2 - latitude_1)
        * 111_000.0
    )

    longitude_difference = (
        (longitude_2 - longitude_1)
        * 111_000.0
        * 0.94
    )

    return hypot(
        latitude_difference,
        longitude_difference,
    )


# ============================================================
# FIND NEAREST NODE
# ============================================================

def _find_nearest_node(
    latitude: float,
    longitude: float,
    nodes,
):

    nearest_node = None
    nearest_distance = float("inf")

    for node in nodes:

        distance = _distance_m(
            latitude,
            longitude,
            node.latitude,
            node.longitude,
        )

        if distance < nearest_distance:

            nearest_distance = distance
            nearest_node = node

    return nearest_node, nearest_distance


# ============================================================
# ROUTE RISK CLASSIFICATION
# ============================================================

def _classify_route_risk(
    water_depth_cm: float,
) -> str:

    depth = float(
        water_depth_cm
    )

    if depth < SAFE_DEPTH_CM:
        return "safe"

    if depth < CAUTION_DEPTH_CM:
        return "caution"

    if depth < DANGEROUS_DEPTH_CM:
        return "dangerous"

    return "blocked"


# ============================================================
# GET SEGMENT FLOOD DEPTH
# ============================================================

def _get_segment_flood_depth(
    from_node,
    to_node,
    flood_cells: list[dict[str, Any]],
) -> float:

    segment_depths = []

    for cell in flood_cells:

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

        distance_from_start = _distance_m(
            cell_latitude,
            cell_longitude,
            from_node.latitude,
            from_node.longitude,
        )

        distance_from_end = _distance_m(
            cell_latitude,
            cell_longitude,
            to_node.latitude,
            to_node.longitude,
        )

        if (
            distance_from_start
            <= FLOOD_CELL_SEARCH_RADIUS_M
            or
            distance_from_end
            <= FLOOD_CELL_SEARCH_RADIUS_M
        ):

            segment_depths.append(
                float(
                    cell.get(
                        "water_depth_cm",
                        0.0,
                    )
                )
            )

    return max(
        segment_depths,
        default=0.0,
    )


# ============================================================
# EDGE COST
# ============================================================

def _calculate_edge_cost(
    edge,
    node_lookup,
    destination_latitude: float,
    destination_longitude: float,
    flood_cells: list[dict[str, Any]],
) -> tuple[float, float, str]:
    """
    Calculate route cost using:

        physical distance
              +
        flood-risk penalty
              +
        destination proximity

    Lower cost = safer/preferred route.
    """

    from_node = node_lookup[
        edge.from_node
    ]

    to_node = node_lookup[
        edge.to_node
    ]

    segment_depth_cm = (
        _get_segment_flood_depth(
            from_node,
            to_node,
            flood_cells,
        )
    )

    segment_risk = _classify_route_risk(
        segment_depth_cm
    )

    # --------------------------------------------------------
    # Flood penalty
    # --------------------------------------------------------

    if segment_risk == "safe":

        flood_penalty = 0.0

    elif segment_risk == "caution":

        flood_penalty = (
            segment_depth_cm
            * FLOOD_RISK_WEIGHT
        )

    elif segment_risk == "dangerous":

        flood_penalty = (
            segment_depth_cm
            * FLOOD_RISK_WEIGHT
            * 3.0
        )

    else:

        flood_penalty = (
            segment_depth_cm
            * FLOOD_RISK_WEIGHT
            * 10.0
        )

    # --------------------------------------------------------
    # Destination proximity
    # --------------------------------------------------------

    destination_distance = _distance_m(
        to_node.latitude,
        to_node.longitude,
        destination_latitude,
        destination_longitude,
    )

    # Small heuristic so routes generally progress
    # toward the destination.
    destination_penalty = (
        destination_distance
        * 0.05
    )

    total_cost = (
        float(edge.length_m)
        + flood_penalty
        + destination_penalty
    )

    return (
        total_cost,
        segment_depth_cm,
        segment_risk,
    )


# ============================================================
# BUILD SAFE ROUTE
# ============================================================

def calculate_safe_route(
    start_latitude: float,
    start_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
    flood_cells: list[dict[str, Any]],
) -> dict[str, Any]:

    network = (
        generate_development_drainage_network()
    )

    # --------------------------------------------------------
    # Find nearest nodes
    # --------------------------------------------------------

    start_node, start_distance = (
        _find_nearest_node(
            start_latitude,
            start_longitude,
            network.nodes,
        )
    )

    destination_node, destination_distance = (
        _find_nearest_node(
            destination_latitude,
            destination_longitude,
            network.nodes,
        )
    )

    if (
        start_node is None
        or destination_node is None
    ):

        return {
            "status": "error",
            "message": (
                "Unable to locate route nodes."
            ),
        }

    # --------------------------------------------------------
    # Same start and destination
    # --------------------------------------------------------

    if (
        start_node.node_id
        == destination_node.node_id
    ):

        return {
            "status": "success",
            "route_status": "safe",
            "start_node": start_node.node_id,
            "destination_node": (
                destination_node.node_id
            ),
            "start_snap_distance_m": round(
                start_distance,
                2,
            ),
            "destination_snap_distance_m": round(
                destination_distance,
                2,
            ),
            "route_distance_m": 0.0,
            "max_water_depth_cm": 0.0,
            "blocked_segments": 0,
            "dangerous_segments": 0,
            "route_coordinates": [
                {
                    "latitude": start_node.latitude,
                    "longitude": start_node.longitude,
                }
            ],
            "segments": [],
            "routing_source": (
                "development_synthetic_drainage_network"
            ),
            "warning": (
                "Prototype safe-route result. "
                "Road and drainage geometry are "
                "development/demo data, not real "
                "Mumbai infrastructure."
            ),
        }

    # --------------------------------------------------------
    # Node lookup
    # --------------------------------------------------------

    node_lookup = {
        node.node_id: node
        for node in network.nodes
    }

    # --------------------------------------------------------
    # Directed graph
    # --------------------------------------------------------

    graph = {
        node.node_id: []
        for node in network.nodes
    }

    for edge in network.edges:

        graph[
            edge.from_node
        ].append(edge)

    # --------------------------------------------------------
    # Risk-aware route search
    # --------------------------------------------------------

    # Each item stores:
    #
    #   total_cost
    #   current_node
    #   route_edges
    #
    search_states = [
        (
            0.0,
            start_node.node_id,
            [],
        )
    ]

    best_cost = {
        start_node.node_id: 0.0
    }

    best_route = None

    visited = set()

    while search_states:

        # ----------------------------------------------------
        # Select lowest-cost state
        # ----------------------------------------------------

        search_states.sort(
            key=lambda item: item[0]
        )

        (
            current_cost,
            current_node_id,
            current_route_edges,
        ) = search_states.pop(0)

        if current_node_id in visited:
            continue

        visited.add(
            current_node_id
        )

        # ----------------------------------------------------
        # Destination reached
        # ----------------------------------------------------

        if (
            current_node_id
            == destination_node.node_id
        ):

            best_route = (
                current_route_edges
            )

            break

        # ----------------------------------------------------
        # Explore outgoing edges
        # ----------------------------------------------------

        outgoing_edges = graph.get(
            current_node_id,
            [],
        )

        for edge in outgoing_edges:

            next_node_id = (
                edge.to_node
            )

            if next_node_id in visited:
                continue

            (
                edge_cost,
                _,
                _,
            ) = _calculate_edge_cost(
                edge=edge,
                node_lookup=node_lookup,
                destination_latitude=(
                    destination_latitude
                ),
                destination_longitude=(
                    destination_longitude
                ),
                flood_cells=flood_cells,
            )

            new_cost = (
                current_cost
                + edge_cost
            )

            if (
                new_cost
                < best_cost.get(
                    next_node_id,
                    float("inf"),
                )
            ):

                best_cost[
                    next_node_id
                ] = new_cost

                search_states.append(
                    (
                        new_cost,
                        next_node_id,
                        (
                            current_route_edges
                            + [edge]
                        ),
                    )
                )

    # --------------------------------------------------------
    # No connected route
    # --------------------------------------------------------

    if best_route is None:

        return {
            "status": "no_route",
            "message": (
                "No connected route found "
                "between the selected locations."
            ),
            "start_node": start_node.node_id,
            "destination_node": (
                destination_node.node_id
            ),
        }

    route_edges = best_route

    # --------------------------------------------------------
    # Evaluate selected route
    # --------------------------------------------------------

    route_points = []

    max_depth_cm = 0.0
    blocked_segments = 0
    dangerous_segments = 0

    for edge in route_edges:

        from_node = node_lookup[
            edge.from_node
        ]

        to_node = node_lookup[
            edge.to_node
        ]

        segment_depth_cm = (
            _get_segment_flood_depth(
                from_node,
                to_node,
                flood_cells,
            )
        )

        max_depth_cm = max(
            max_depth_cm,
            segment_depth_cm,
        )

        segment_risk = (
            _classify_route_risk(
                segment_depth_cm
            )
        )

        if segment_risk == "blocked":

            blocked_segments += 1

        elif segment_risk == "dangerous":

            dangerous_segments += 1

        route_points.append(
            {
                "edge_id":
                    edge.edge_id,

                "from_node":
                    edge.from_node,

                "to_node":
                    edge.to_node,

                "length_m":
                    edge.length_m,

                "water_depth_cm":
                    round(
                        segment_depth_cm,
                        2,
                    ),

                "risk":
                    segment_risk,

                "from_latitude":
                    from_node.latitude,

                "from_longitude":
                    from_node.longitude,

                "to_latitude":
                    to_node.latitude,

                "to_longitude":
                    to_node.longitude,
            }
        )

    # --------------------------------------------------------
    # Overall route status
    # --------------------------------------------------------

    if blocked_segments > 0:

        route_status = "blocked"

    elif dangerous_segments > 0:

        route_status = "dangerous"

    elif max_depth_cm >= SAFE_DEPTH_CM:

        route_status = "caution"

    else:

        route_status = "safe"

    # --------------------------------------------------------
    # Route distance
    # --------------------------------------------------------

    route_distance_m = sum(
        float(edge.length_m)
        for edge in route_edges
    )

    # --------------------------------------------------------
    # Route coordinates
    # --------------------------------------------------------

    coordinates = []

    if route_edges:

        first_node = node_lookup[
            route_edges[0].from_node
        ]

        coordinates.append(
            {
                "latitude":
                    first_node.latitude,

                "longitude":
                    first_node.longitude,
            }
        )

        for edge in route_edges:

            node = node_lookup[
                edge.to_node
            ]

            coordinates.append(
                {
                    "latitude":
                        node.latitude,

                    "longitude":
                        node.longitude,
                }
            )

    # --------------------------------------------------------
    # Final response
    # --------------------------------------------------------

    return {
        "status":
            "success",

        "route_status":
            route_status,

        "start_node":
            start_node.node_id,

        "destination_node":
            destination_node.node_id,

        "start_snap_distance_m":
            round(
                start_distance,
                2,
            ),

        "destination_snap_distance_m":
            round(
                destination_distance,
                2,
            ),

        "route_distance_m":
            round(
                route_distance_m,
                2,
            ),

        "max_water_depth_cm":
            round(
                max_depth_cm,
                2,
            ),

        "blocked_segments":
            blocked_segments,

        "dangerous_segments":
            dangerous_segments,

        "route_coordinates":
            coordinates,

        "segments":
            route_points,

        "routing_source":
            "development_risk_aware_routing",

        "warning":
            (
                "Prototype safe-route result. "
                "Route selection uses flood-depth "
                "risk scoring over the development "
                "synthetic drainage network. "
                "Road and drainage geometry are "
                "development/demo data, not real "
                "Mumbai infrastructure."
            ),
    }
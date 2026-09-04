from backend.app.models.drainage_analysis import (
    DrainageAnalysis,
    DrainageEdgeAnalysis,
)

from backend.app.models.flood import FloodGrid

from backend.app.services.drainage_service import (
    generate_development_drainage_network,
)


# =========================================================
# SIH26085 — DRAINAGE CAPACITY ANALYSIS
# Development / Demonstration Module
# =========================================================

SECONDS_PER_HOUR = 3600.0

# Synthetic catchment area represented by each
# development flood-grid cell.
#
# IMPORTANT:
# This is NOT real municipal catchment geometry.
#
# It is used only for development-stage validation
# of rainfall-to-drainage coupling.

RUNOFF_AREA_M2 = 100_000.0


# =========================================================
# RUNOFF COEFFICIENT
# =========================================================
#
# High urban imperviousness is represented by an
# effective runoff coefficient of 0.80.
#
# This is intentionally aligned with the surface
# flood model so that the coupled prototype uses
# one consistent rainfall -> runoff assumption.
#
# IMPORTANT:
# This is a development-model assumption.
# It must be calibrated when real municipal
# land-use / drainage data becomes available.

RUNOFF_COEFFICIENT = 0.80


# =========================================================
# STATUS CLASSIFICATION
# =========================================================

def classify_drainage_status(
    utilization: float,
) -> str:

    utilization = max(
        0.0,
        float(utilization),
    )

    if utilization <= 0.75:
        return "within_capacity"

    if utilization <= 1.00:
        return "near_capacity"

    if utilization <= 1.50:
        return "over_capacity"

    return "severe_surcharge"


# =========================================================
# RAINFALL → RUNOFF
# =========================================================

def rainfall_to_runoff_m3s(
    rainfall_mm: float,
) -> float:

    rainfall_mm = max(
        0.0,
        float(rainfall_mm),
    )

    runoff_mm = (
        rainfall_mm
        * RUNOFF_COEFFICIENT
    )

    runoff_volume_m3 = (
        runoff_mm
        / 1000.0
        * RUNOFF_AREA_M2
    )

    runoff_m3s = (
        runoff_volume_m3
        / SECONDS_PER_HOUR
    )

    return runoff_m3s


# =========================================================
# DRAINAGE CAPACITY ANALYSIS
# =========================================================

def analyze_drainage_capacity(
    flood_grid: FloodGrid,
) -> DrainageAnalysis:

    network = (
        generate_development_drainage_network()
    )

    edges = network.edges

    if not edges:

        return DrainageAnalysis(
            source="development_synthetic_network",
            edges=[],
        )


    # =====================================================
    # ASSIGN FLOOD-GRID ROWS TO DRAINAGE CATCHMENTS
    # =====================================================

    rows_per_edge = max(
        1,
        flood_grid.rows // len(edges),
    )


    results = []


    # =====================================================
    # ANALYZE EACH DRAINAGE EDGE
    # =====================================================

    for edge_index, edge in enumerate(edges):

        start_row = (
            edge_index
            * rows_per_edge
        )

        if edge_index == len(edges) - 1:

            end_row = flood_grid.rows

        else:

            end_row = min(
                flood_grid.rows,
                start_row + rows_per_edge,
            )


        # -------------------------------------------------
        # Select cells belonging to this catchment
        # -------------------------------------------------

        selected_cells = [

            cell

            for cell in flood_grid.cells

            if (
                start_row
                <= cell.row
                < end_row
            )

        ]


        # -------------------------------------------------
        # Average rainfall in catchment
        # -------------------------------------------------

        if selected_cells:

            average_rainfall_mm = (

                sum(
                    float(cell.rainfall_mm)
                    for cell in selected_cells
                )

                / len(selected_cells)

            )

        else:

            average_rainfall_mm = 0.0


        # -------------------------------------------------
        # Convert rainfall to runoff flow
        # -------------------------------------------------

        runoff_per_cell_m3s = (
            rainfall_to_runoff_m3s(
                average_rainfall_mm
            )
        )


        # -------------------------------------------------
        # Total catchment runoff
        # -------------------------------------------------

        catchment_runoff_m3s = (

            runoff_per_cell_m3s
            * len(selected_cells)

        )


        # -------------------------------------------------
        # Drainage capacity
        # -------------------------------------------------

        capacity_m3s = max(
            0.01,
            float(edge.capacity_m3s),
        )


        # -------------------------------------------------
        # Utilization
        # -------------------------------------------------

        utilization = (

            catchment_runoff_m3s
            / capacity_m3s

        )


        # -------------------------------------------------
        # Surcharge
        # -------------------------------------------------

        surcharge_m3s = max(

            0.0,

            catchment_runoff_m3s
            - capacity_m3s,

        )


        # -------------------------------------------------
        # Status
        # -------------------------------------------------

        status = classify_drainage_status(
            utilization
        )


        # -------------------------------------------------
        # Analysis result
        # -------------------------------------------------

        results.append(

            DrainageEdgeAnalysis(

                edge_id=edge.edge_id,

                from_node=edge.from_node,

                to_node=edge.to_node,

                rainfall_runoff_m3s=round(
                    catchment_runoff_m3s,
                    4,
                ),

                capacity_m3s=round(
                    capacity_m3s,
                    4,
                ),

                utilization=round(
                    utilization,
                    4,
                ),

                surcharge_m3s=round(
                    surcharge_m3s,
                    4,
                ),

                status=status,
            )

        )


    # =====================================================
    # RETURN DRAINAGE ANALYSIS
    # =====================================================

    return DrainageAnalysis(

        source="development_synthetic_network",

        edges=results,

    )
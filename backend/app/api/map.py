from fastapi import APIRouter

from backend.app.services.flood_coupling_service import (
    generate_coupled_flood_analysis,
)


router = APIRouter()


# =========================================================
# FLOOD RISK GEOJSON LAYER
# =========================================================

@router.get("/flood-layer")
def flood_layer():
    """
    Return the current flood prediction as GeoJSON.

    Each flood-grid cell is represented as a Point feature.

    Every feature contains:
        - row
        - column
        - elevation
        - rainfall
        - runoff
        - water depth
        - risk
    """

    analysis = generate_coupled_flood_analysis()

    features = []

    surface_cells = analysis.get(
        "surface_flood",
        {},
    ).get(
        "cells",
        [],
    )

    # -----------------------------------------------------
    # Convert flood cells → GeoJSON
    # -----------------------------------------------------

    for cell in surface_cells:

        risk = str(
            cell.get("risk", "unknown")
        ).lower()

        features.append(
            {
                "type": "Feature",

                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        cell["longitude"],
                        cell["latitude"],
                    ],
                },

                "properties": {
                    "row": cell.get(
                        "row",
                        "--",
                    ),

                    "column": cell.get(
                        "column",
                        "--",
                    ),

                    "elevation_m": cell.get(
                        "elevation_m",
                        0.0,
                    ),

                    "rainfall_mm": cell.get(
                        "rainfall_mm",
                        0.0,
                    ),

                    "runoff_mm": cell.get(
                        "runoff_mm",
                        0.0,
                    ),

                    "water_depth_cm": cell.get(
                        "water_depth_cm",
                        0.0,
                    ),

                    "risk": risk,

                    # Important for frontend/debugging.
                    "risk_source": (
                        "backend_risk_field"
                    ),
                },
            }
        )

    # -----------------------------------------------------
    # GeoJSON response
    # -----------------------------------------------------

    return {
        "type": "FeatureCollection",

        "properties": {
            "project": "SIH26085",

            "source": analysis.get(
                "source",
                "unknown",
            ),

            "overall_status": analysis.get(
                "overall_status",
                "unknown",
            ),

            "max_water_depth_cm": analysis.get(
                "max_water_depth_cm",
                0.0,
            ),

            "flooded_cells": analysis.get(
                "flooded_cells",
                {},
            ),

            "overloaded_drainage_edges": analysis.get(
                "overloaded_drainage_edges",
                0,
            ),
            "timestamp": analysis.get(
    "surface_flood",
    {},
).get(
    "timestamp",
    None,
),
        },

        "features": features,
    }
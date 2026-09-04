from fastapi import APIRouter

from backend.app.services.flood_coupling_service import (
    generate_coupled_flood_analysis,
)


router = APIRouter()


# =========================================================
# FLOOD ANALYSIS
# =========================================================

@router.get("/analysis")
def flood_analysis():
    """
    Run the coupled urban flood analysis.

    Current pipeline:

        Rainfall Grid
             ↓
        Surface Flood Model
             ↓
        Drainage Analysis
             ↓
        Coupled Flood Result
    """

    analysis = generate_coupled_flood_analysis()

    return {
        "status": "success",
        "project": "SIH26085",
        "analysis": analysis,
    }


# =========================================================
# DRAINAGE ANALYSIS
# =========================================================

@router.get("/drainage-analysis")
def drainage_analysis():
    """
    Return drainage capacity analysis from the
    coupled flood model.
    """

    analysis = generate_coupled_flood_analysis()

    return {
        "status": "success",
        "project": "SIH26085",
        "drainage_analysis": analysis[
            "drainage_analysis"
        ],
    }
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.rainfall import router as rainfall_router
from backend.app.api.flood import router as flood_router
from backend.app.api.map import router as map_router
from backend.app.api.nowcast import router as nowcast_router

# =========================================================
# SIH26085 URBAN FLOOD NOWCASTING API
# =========================================================

app = FastAPI(
    title="SIH26085 Urban Flood Nowcasting API",
    version="0.2.0",
    description=(
        "Backend API for Mumbai urban rainfall, "
        "runoff and flood nowcasting."
    ),
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "project": "SIH26085",
        "service": "Urban Flood Nowcasting API",
        "status": "online",
        "version": "0.2.0",
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "SIH26085 backend",
    }


# =========================================================
# DATA SOURCE STATUS
# =========================================================

@app.get("/data-status")
def data_status():
    return {
        "project": "SIH26085",
        "rainfall_provider": "IMD",
        "imd_approval": "pending",
        "mode": "development_until_imd_access_is_available",
    }


# =========================================================
# API ROUTERS
# =========================================================

app.include_router(
    rainfall_router,
    prefix="/rainfall",
    tags=["Rainfall"],
)

app.include_router(
    flood_router,
    prefix="/flood",
    tags=["Flood"],
)

app.include_router(
    map_router,
    prefix="/map",
    tags=["Map"],
)

app.include_router(
    nowcast_router,
    prefix="/flood",
    tags=["Flood Nowcast"],
)


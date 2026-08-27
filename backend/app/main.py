from fastapi import FastAPI
from backend.app.api.rainfall import router as rainfall_router

app = FastAPI(
    title="SIH26085 Urban Flood Nowcasting API",
    version="0.1.0",
    description="Backend API for Mumbai urban rainfall and flood nowcasting",
)


@app.get("/")
def root():
    return {
        "project": "SIH26085",
        "message": "Urban Flood Nowcasting API is running",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "SIH26085 backend",
    }


app.include_router(rainfall_router, prefix="/rainfall", tags=["Rainfall"])
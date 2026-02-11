"""FastAPI example application."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="FastAPI Example App",
    description="A production-ready FastAPI application",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class StatusResponse(BaseModel):
    """Status response model."""
    status: str
    service: str
    version: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str


# Routes
@app.get("/", response_model=StatusResponse)
async def root():
    """Welcome endpoint."""
    return StatusResponse(
        status="running",
        service="fastapi-app",
        version="1.0.0",
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        database="connected",
    )


@app.get("/api/status")
async def api_status():
    """API status endpoint."""
    return {
        "service": "fastapi-api",
        "status": "operational",
        "debug": os.getenv("DEBUG", "False").lower() == "true",
    }


@app.exception_handler(Exception)
async def exception_handler(request, exc):
    """Global exception handler."""
    return {
        "error": str(exc),
        "status_code": 500,
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
    )

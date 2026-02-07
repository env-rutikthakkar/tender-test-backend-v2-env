"""
FastAPI Application - Tender Eligibility Summary System
Main entry point for the Groq LPU-powered tender processing API
"""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables before importing app modules
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.tender import router as tender_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    yield


# Create FastAPI application
app = FastAPI(
    title="Tender Eligibility Summary System",
    description="""
    ## Groq Cloud (LPU) - Powered Tender Processing API

    **Purpose**: Generate structured eligibility summaries from government tender PDFs
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(tender_router)


# Health Check Endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": "Tender Eligibility Summary System",
        "version": "1.0.0"
    }


# Root Endpoint
@app.get("/", tags=["system"])
async def root():
    """API root endpoint with welcome message."""
    return {
        "message": "Tender Eligibility Summary System API",
        "version": "1.0.0",
        "powered_by": "Groq Cloud LPU",
        "documentation": "/docs",
        "health_check": "/health"
    }


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An internal server error occurred",
            "detail": str(exc) if os.getenv("DEBUG") == "true" else "Contact support"
        }
    )


# Run application
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))

    uvicorn.run(
        "api.index:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

"""FastAPI main application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.api.process_invoice import router as process_invoice_router
from backend.api.active_learning import router as active_learning_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="FinScribe Smart Scan API",
    description="AI-powered invoice processing with OCR, validation, and active learning",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(process_invoice_router)
app.include_router(active_learning_router)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "FinScribe Smart Scan API is running"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "FinScribe Smart Scan API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "process_invoice": "/process_invoice",
            "active_learning": "/active_learning"
        }
    }


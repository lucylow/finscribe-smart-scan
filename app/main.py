"""
FinScribe AI Backend - Main Application Entry Point

This module:
1. Initializes FastAPI application with CORS middleware
2. Registers API routers (endpoints, metrics, billing, CAMEL, Unsloth, etc.)
3. Handles global exception handling for consistent error responses
4. Provides health check endpoint

Used by: Docker containers, local development, production deployments
"""
import uvicorn
import logging
import uuid
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import os
from .api.v1.endpoints import router as api_router
from .api.v1.metrics import router as metrics_router
from .core.logging_config import setup_logging, set_request_id, get_logger

# Set up structured logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"), json_format=True)

# Initialize logger
logger = get_logger(__name__)

try:
    from .api.v1.endpoints_enhanced import router as enhanced_router
    ENHANCED_ENDPOINTS_AVAILABLE = True
except ImportError:
    ENHANCED_ENDPOINTS_AVAILABLE = False
    logger.warning("Enhanced endpoints not available")
try:
    from .api.v1.billing import router as billing_router
    BILLING_AVAILABLE = True
except ImportError:
    BILLING_AVAILABLE = False
try:
    from .api.v1.unsloth import router as unsloth_router
    UNSLOTH_AVAILABLE = True
except ImportError:
    UNSLOTH_AVAILABLE = False
    logger.warning("Unsloth endpoints not available")
try:
    from .api.v1.camel_endpoints import router as camel_router
    CAMEL_AVAILABLE = True
except ImportError:
    CAMEL_AVAILABLE = False
    logger.warning("CAMEL endpoints not available")
try:
    from .api.v1.exports import router as exports_router
    EXPORTS_AVAILABLE = True
except ImportError:
    EXPORTS_AVAILABLE = False
    logger.warning("Exports endpoints not available")
try:
    from .api.v1.demo import router as demo_router
    DEMO_AVAILABLE = True
except ImportError:
    DEMO_AVAILABLE = False
    logger.warning("Demo endpoints not available")
try:
    from .api.v1.etl import router as etl_router
    ETL_AVAILABLE = True
except ImportError:
    ETL_AVAILABLE = False
    logger.warning("ETL endpoints not available")
try:
    from .api.v1.process_invoice import router as process_invoice_router
    PROCESS_INVOICE_AVAILABLE = True
except ImportError:
    PROCESS_INVOICE_AVAILABLE = False
    logger.warning("Process invoice endpoint not available")
try:
    from .api.v1.active_learning import router as active_learning_router
    ACTIVE_LEARNING_AVAILABLE = True
except ImportError:
    ACTIVE_LEARNING_AVAILABLE = False
    logger.warning("Active learning endpoint not available")
try:
    from .api.v1.ocr_endpoints import router as ocr_router
    OCR_ENDPOINTS_AVAILABLE = True
except ImportError:
    OCR_ENDPOINTS_AVAILABLE = False
    logger.warning("OCR endpoints not available")

app = FastAPI(
    title="FinScribe AI Backend",
    description="Backend API for Financial Document Analyzer",
    version="1.0.0",
)


# Request ID middleware for tracing
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID for tracing."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)

# CORS Middleware for frontend communication
origins = [
    "http://localhost:5173",  # Frontend development server
    "http://localhost",
    "*" # Allow all for now, should be restricted in production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent error format."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(f"Validation error: {exc.errors()} - Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "detail": exc.errors(),
            "status_code": 422,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)} - Path: {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
            "status_code": 500,
            "path": str(request.url.path)
        }
    )

app.include_router(api_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
if ENHANCED_ENDPOINTS_AVAILABLE:
    app.include_router(enhanced_router, prefix="/api/v1", tags=["enhanced"])
if BILLING_AVAILABLE:
    app.include_router(billing_router, prefix="/api/v1/billing", tags=["billing"])
if UNSLOTH_AVAILABLE:
    app.include_router(unsloth_router, prefix="/api/v1", tags=["unsloth"])
if CAMEL_AVAILABLE:
    app.include_router(camel_router, prefix="/api/v1", tags=["camel"])
if DEMO_AVAILABLE:
    app.include_router(demo_router, prefix="/api/v1", tags=["demo"])
if EXPORTS_AVAILABLE:
    app.include_router(exports_router, prefix="/api/v1", tags=["exports"])
if ETL_AVAILABLE:
    app.include_router(etl_router, prefix="/api/v1", tags=["etl"])
if PROCESS_INVOICE_AVAILABLE:
    app.include_router(process_invoice_router, prefix="/api/v1", tags=["invoice"])
if ACTIVE_LEARNING_AVAILABLE:
    app.include_router(active_learning_router, prefix="/api/v1", tags=["training"])
if OCR_ENDPOINTS_AVAILABLE:
    app.include_router(ocr_router, prefix="/api/v1", tags=["ocr"])

@app.get("/")
def read_root():
    return {"message": "Welcome to FinScribe AI Backend"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

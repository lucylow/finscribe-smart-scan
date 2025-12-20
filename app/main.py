import uvicorn
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from .api.v1.endpoints import router as api_router
from .api.v1.metrics import router as metrics_router
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

logger = logging.getLogger(__name__)

app = FastAPI(
    title="FinScribe AI Backend",
    description="Backend API for Financial Document Analyzer",
    version="1.0.0",
)

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

@app.get("/")
def read_root():
    return {"message": "Welcome to FinScribe AI Backend"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.endpoints import router as api_router

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

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to FinScribe AI Backend"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

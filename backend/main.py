# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.api.process_invoice import router as process_router
from backend.api.active_learning import router as active_learning_router

app = FastAPI(title="FinScribe Backend")

# Allow local frontend / docker-compose host
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # narrow in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(process_router, prefix="/api")
app.include_router(active_learning_router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


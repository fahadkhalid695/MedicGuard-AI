"""
MediGuard AI — Patient-Facing Alert API

Provides endpoints for:
- Sending simplified, patient-friendly alert notifications (SMS/push)
- Receiving patient responses and triggering re-analysis if they feel worse

Usage:
    uvicorn app.main:app --port 8001 --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import close_pool, get_pool
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage DB pool lifecycle."""
    await get_pool()
    print("✓ Patient API: Database connected")
    yield
    await close_pool()
    print("✓ Patient API: Connections closed")


app = FastAPI(
    title="MediGuard AI — Patient Alert API",
    description=(
        "Patient-facing endpoints for receiving simplified health alerts "
        "and submitting responses. Integrates with the agent pipeline for "
        "automatic re-analysis when patients report worsening."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "patient-api"}


if __name__ == "__main__":
    import uvicorn
    from app.config import PORT

    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)

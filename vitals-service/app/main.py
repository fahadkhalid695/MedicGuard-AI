from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import close_pool, get_pool
from app.redis_client import close_redis, get_redis
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage connection pools on startup/shutdown."""
    # Startup
    await get_pool()
    await get_redis()
    print("✓ PostgreSQL and Redis connections established")
    yield
    # Shutdown
    await close_pool()
    await close_redis()
    print("✓ Connections closed")


app = FastAPI(
    title="MediGuard AI — Vitals Ingestion Service",
    description="Real-time vitals ingestion with PostgreSQL persistence and Redis caching/pub-sub.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

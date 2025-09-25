"""FastAPI app factory for Olive."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from olive.config import OliveConfig
from olive.router import router, set_temporal_worker
from olive.temporal.worker import TemporalWorker

# Global worker instance
_worker: TemporalWorker | None = None


def get_worker() -> TemporalWorker:
    """Get the global worker instance."""
    if _worker is None:
        raise RuntimeError("Worker not initialized")
    return _worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle."""
    # Startup
    global _worker
    config = getattr(app.state, "config", OliveConfig())
    _worker = TemporalWorker(config)
    _worker.start_background()

    # Set the worker on the router for v1 mode
    set_temporal_worker(_worker)

    yield

    # Shutdown
    if _worker:
        _worker.stop()
        set_temporal_worker(None)


def create_app(config: OliveConfig | None = None) -> FastAPI:
    """Create the FastAPI application."""
    if config is None:
        config = OliveConfig.from_file().merge_with_env()

    app = FastAPI(
        title="Olive Tool Server",
        description="🫒 FastAPI + Temporal tool framework",
        version="1.1.1",
        lifespan=lifespan,
    )

    # Store config in app state
    app.state.config = config

    # Add Olive router
    app.include_router(router, prefix="/olive")

    # Add root endpoint
    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "name": "Olive Tool Server",
            "version": "1.1.1",
            "description": "FastAPI + Temporal tool framework",
            "endpoints": {
                "tools": "/olive/tools",
                "call": "/olive/tools/call",
                "docs": "/docs",
            },
        }

    return app

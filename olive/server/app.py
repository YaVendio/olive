"""FastAPI app factory for Olive."""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from olive.config import OliveConfig
from olive.router import router, set_temporal_worker
from olive.temporal.worker import TemporalWorker

logger = logging.getLogger(__name__)

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
    
    # Try to start Temporal worker, but gracefully fall back if unavailable
    try:
        _worker = TemporalWorker(config)
        
        # Check if Temporal is available before starting background thread
        if await _worker.check_connection():
            _worker.start_background()
            set_temporal_worker(_worker)
            logger.info("✅ Temporal worker started - tools will execute with retry/durability")
        else:
            logger.info(
                "⚠️  Temporal server not available, using direct execution mode. "
                "Tools will work but without retry/durability features."
            )
            _worker = None
            set_temporal_worker(None)
    except Exception as e:
        logger.info(
            "⚠️  Could not start Temporal worker, using direct execution mode. "
            "Tools will work but without retry/durability features. "
            f"(Reason: {type(e).__name__})"
        )
        _worker = None
        set_temporal_worker(None)

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
        version="1.3.0",
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
            "version": "1.3.0",
            "description": "FastAPI + Temporal tool framework",
            "endpoints": {
                "tools": "/olive/tools",
                "tools_elevenlabs": "/olive/tools/elevenlabs",
                "call": "/olive/tools/call",
                "docs": "/docs",
            },
        }

    return app

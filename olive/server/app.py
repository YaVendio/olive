"""FastAPI app factory for Olive."""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from olive.config import OliveConfig
from olive.router import router, set_temporal_worker

logger = logging.getLogger(__name__)


def _import_temporal_worker():
    """Lazily import TemporalWorker, raising clear error if not available."""
    try:
        from olive.temporal.worker import TemporalWorker

        return TemporalWorker
    except ImportError as e:
        raise RuntimeError(
            "Temporal integration enabled but 'temporalio' package not installed. "
            "Install with: pip install olive[temporal]"
        ) from e


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle."""
    config = getattr(app.state, "config", OliveConfig())

    # Check if Temporal is enabled in config
    if config.temporal.enabled:
        logger.info("Temporal enabled in config, initializing worker...")

        # Lazy import - fails fast if package not installed
        try:
            TemporalWorker = _import_temporal_worker()
        except RuntimeError as e:
            logger.error(str(e))
            raise  # Fail startup with clear error

        # Try to connect
        worker = TemporalWorker(config)
        if await worker.check_connection():
            worker.start_background()
            app.state.temporal_worker = worker
            # Also set the fallback for backward compat with code using set_temporal_worker()
            set_temporal_worker(worker)
            logger.info("Temporal worker started successfully")
        else:
            # Config says enabled, but server not reachable
            error_msg = (
                f"Temporal enabled but server not reachable at {config.temporal.address}. "
                "Start Temporal server or set temporal.enabled=false"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    else:
        # Temporal disabled - direct execution mode
        logger.info("Temporal disabled, using direct execution mode")
        app.state.temporal_worker = None
        set_temporal_worker(None)

    yield

    # Shutdown
    worker = getattr(app.state, "temporal_worker", None)
    if worker:
        worker.stop()
        app.state.temporal_worker = None
        set_temporal_worker(None)


def create_app(config: OliveConfig | None = None) -> FastAPI:
    """Create the FastAPI application."""
    if config is None:
        config = OliveConfig.from_file().merge_with_env()

    app = FastAPI(
        title="Olive Tool Server",
        description="Expose Python functions as LangChain tools",
        version="1.5.0",
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
            "version": "1.5.0",
            "description": "Expose Python functions as LangChain tools",
            "endpoints": {
                "tools": "/olive/tools",
                "tools_elevenlabs": "/olive/tools/elevenlabs",
                "call": "/olive/tools/call",
                "health": "/olive/health",
                "docs": "/docs",
            },
        }

    return app

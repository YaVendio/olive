"""Olive - Minimal framework for exposing FastAPI endpoints as LangChain tools."""

# Only import minimal required exports to avoid FastAPI imports in workflow context
from olive.decorator import olive_tool
from olive.schemas import Inject

__version__ = "1.2.0"
__all__ = ["olive_tool", "setup_olive", "create_app", "Inject"]


# Lazy imports to avoid importing FastAPI in workflow context
def setup_olive(*args, **kwargs):
    """Lazy import of setup_olive to avoid FastAPI imports."""
    from olive.setup import setup_olive as _setup_olive

    return _setup_olive(*args, **kwargs)


def create_app(*args, **kwargs):
    """Lazy import of create_app to avoid FastAPI imports."""
    from olive.server import create_app as _create_app

    return _create_app(*args, **kwargs)


def run_dev():
    """Run Olive in development mode (called by CLI or main.py)."""
    from olive.cli import dev

    dev()

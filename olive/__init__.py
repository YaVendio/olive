"""Olive - Minimal framework for exposing FastAPI endpoints as LangChain tools."""

from olive.decorator import olive_tool
from olive.server import create_app
from olive.setup import setup_olive

__version__ = "1.0.0"
__all__ = ["olive_tool", "setup_olive", "create_app"]


def run_dev():
    """Run Olive in development mode (called by CLI or main.py)."""
    from olive.cli import dev

    dev()

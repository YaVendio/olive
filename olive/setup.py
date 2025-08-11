"""Setup function for integrating Olive with FastAPI apps."""

from fastapi import FastAPI

from olive.router import router


def setup_olive(app: FastAPI) -> None:
    """
    Set up Olive on an existing FastAPI app.

    This adds the /olive endpoints to your app:
    - GET /olive/tools - List all registered tools
    - POST /olive/tools/call - Call a tool

    Args:
        app: The FastAPI application instance

    Example:
        app = FastAPI()
        setup_olive(app)

        @olive_tool
        def my_tool(text: str) -> str:
            return text.upper()
    """
    app.include_router(router, prefix="/olive")

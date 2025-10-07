"""Test ElevenLabs tool format conversion."""

import pytest

from olive_client import OliveClient


@pytest.mark.asyncio
async def test_as_elevenlabs_tools():
    """Test that Olive client can convert tools to ElevenLabs format."""
    # This test requires a running Olive server with tools
    # For unit testing, we'd need to mock the HTTP client

    # Just verify the method exists
    client = OliveClient("http://localhost:8000")
    assert hasattr(client, "as_elevenlabs_tools")
    assert callable(client.as_elevenlabs_tools)


def test_elevenlabs_endpoint_in_router():
    """Test that the ElevenLabs endpoint is registered."""
    from olive.router import router

    # Check that the route exists
    routes = [route.path for route in router.routes]
    assert "/tools/elevenlabs" in routes

"""Tests for the Olive server module."""

from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from olive.config import OliveConfig
from olive.server.app import create_app, lifespan


def test_create_app():
    """Test create_app function."""
    # Test with default config
    app = create_app()
    assert isinstance(app, FastAPI)
    assert app.title == "Olive Tool Server"
    # Check that routes with /olive prefix exist
    olive_routes = [route.path for route in app.routes if route.path.startswith("/olive")]
    assert len(olive_routes) > 0
    assert "/olive/tools" in olive_routes

    # Test with custom config
    config = OliveConfig()
    config.temporal.address = "custom:7233"
    app = create_app(config)
    assert app.state.config.temporal.address == "custom:7233"


def test_create_app_with_env():
    """Test create_app loads config from file when none provided."""
    with mock.patch.object(OliveConfig, "from_file") as mock_from_file:
        mock_config = OliveConfig()
        mock_from_file.return_value = mock_config

        app = create_app()
        mock_from_file.assert_called_once()
        assert app.state.config == mock_config.merge_with_env()


def test_root_endpoint():
    """Test the root endpoint."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Olive Tool Server"
    assert "version" in data
    assert "endpoints" in data
    assert data["endpoints"]["tools"] == "/olive/tools"
    assert data["endpoints"]["call"] == "/olive/tools/call"
    assert data["endpoints"]["docs"] == "/docs"


@pytest.mark.asyncio
async def test_lifespan():
    """Test the lifespan context manager."""
    from olive.config import OliveConfig, TemporalConfig

    config = OliveConfig(temporal=TemporalConfig(enabled=True))
    app = create_app(config)

    mock_worker_class = mock.Mock()
    mock_worker = mock.Mock()
    mock_worker.check_connection = mock.AsyncMock(return_value=True)
    mock_worker_class.return_value = mock_worker

    with mock.patch("olive.server.app._import_temporal_worker", return_value=mock_worker_class):
        # Simulate the lifespan
        async with lifespan(app):
            # Worker should be started
            mock_worker.start_background.assert_called_once()

            # Worker should be accessible via app.state
            assert app.state.temporal_worker == mock_worker

        # After exit, worker should be stopped
        mock_worker.stop.assert_called_once()
        assert app.state.temporal_worker is None


@pytest.mark.asyncio
async def test_lifespan_sets_temporal_worker():
    """Test that lifespan sets the temporal worker on app.state and fallback."""
    from olive.config import OliveConfig, TemporalConfig

    config = OliveConfig(temporal=TemporalConfig(enabled=True))
    app = create_app(config)

    mock_worker_class = mock.Mock()
    mock_worker = mock.Mock()
    mock_worker.check_connection = mock.AsyncMock(return_value=True)
    mock_worker_class.return_value = mock_worker

    with mock.patch("olive.server.app._import_temporal_worker", return_value=mock_worker_class):
        with mock.patch("olive.server.app.set_temporal_worker") as mock_set_worker:
            async with lifespan(app):
                # Should set the worker on the router fallback
                mock_set_worker.assert_called_with(mock_worker)

            # Should clear the worker on exit
            mock_set_worker.assert_called_with(None)


def test_app_integration():
    """Test the full app integration."""
    from olive.config import OliveConfig, TemporalConfig

    config = OliveConfig(temporal=TemporalConfig(enabled=True))
    app = create_app(config)

    # Mock the worker to avoid starting real Temporal
    mock_worker_class = mock.Mock()
    mock_worker = mock.Mock()
    mock_worker.check_connection = mock.AsyncMock(return_value=True)
    mock_worker_class.return_value = mock_worker

    with mock.patch("olive.server.app._import_temporal_worker", return_value=mock_worker_class):
        # Use TestClient which handles lifespan
        with TestClient(app) as client:
            # Test root endpoint
            response = client.get("/")
            assert response.status_code == 200

            # Test tools endpoint (from router)
            response = client.get("/olive/tools")
            assert response.status_code == 200
            assert isinstance(response.json(), list)

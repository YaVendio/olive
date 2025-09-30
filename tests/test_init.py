"""Tests for olive __init__ module."""

from unittest import mock

import pytest

from olive import __version__, run_dev


def test_version():
    """Test version is defined."""
    assert __version__ == "1.2.2"


def test_run_dev():
    """Test run_dev function."""
    with mock.patch("olive.cli.dev") as mock_dev:
        run_dev()
        mock_dev.assert_called_once()


def test_imports():
    """Test that all public API is importable."""
    from olive import create_app, olive_tool, setup_olive

    assert callable(olive_tool)
    assert callable(setup_olive)
    assert callable(create_app)

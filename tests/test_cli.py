"""Tests for Olive CLI module."""

import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest
import typer
from typer.testing import CliRunner

from olive import __version__
from olive.cli import (
    app,
    check_temporal_running,
    dev,
    init,
    serve,
    start_temporal_dev_server,
    version,
)
from olive.config import OliveConfig

runner = CliRunner()


def test_check_temporal_running():
    """Test Temporal server check."""
    with mock.patch("socket.create_connection") as mock_conn:
        # Test success
        mock_conn.return_value.__enter__.return_value = True
        assert check_temporal_running("localhost:7233") is True

        # Test failure
        mock_conn.side_effect = Exception("Connection error")
        assert check_temporal_running("localhost:7233") is False


def test_start_temporal_dev_server():
    """Test starting Temporal dev server."""
    with mock.patch("subprocess.Popen") as mock_popen:
        mock_process = mock.Mock()
        mock_popen.return_value = mock_process

        process = start_temporal_dev_server()
        assert process == mock_process
        mock_popen.assert_called_once()


def test_version_command():
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    # Strip ANSI color codes
    import re

    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert __version__ in clean_output


def test_init_command(tmp_path):
    """Test init command."""
    # Pass path explicitly
    result = runner.invoke(app, ["init", str(tmp_path)])
    if result.exit_code != 0:
        print(f"Exit code: {result.exit_code}")
        print(f"Output: {result.output}")
        if result.exception:
            raise result.exception
    assert result.exit_code == 0

    # Check files created
    assert (tmp_path / "main.py").exists()
    assert (tmp_path / ".olive.yaml").exists()

    # Test with --force
    result = runner.invoke(app, ["init", str(tmp_path), "--force"])
    assert result.exit_code == 0

    # Test when files already exist (to cover line 322)
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "Files already exist" in result.output


def test_dev_command():
    """Test dev command."""
    with (
        mock.patch("olive.cli.check_temporal_running", return_value=True),
        mock.patch("olive.cli.TemporalWorker") as mock_worker_class,
        mock.patch("uvicorn.run") as mock_uvicorn,
    ):
        mock_worker = mock.Mock()
        mock_worker_class.return_value = mock_worker

        # Run dev command
        try:
            dev(host="127.0.0.1", port=8001, reload=False)
        except KeyboardInterrupt:
            pass  # Expected when uvicorn.run is mocked

        # Verify worker was started
        mock_worker.start_background.assert_called_once()

        # Verify uvicorn was called
        mock_uvicorn.assert_called_once()


def test_dev_command_starts_temporal():
    """Test dev command starts Temporal if not running."""
    with (
        mock.patch("olive.cli.check_temporal_running") as mock_check,
        mock.patch("olive.cli.start_temporal_dev_server") as mock_start,
        mock.patch("olive.cli.TemporalWorker") as mock_worker_class,
        mock.patch("uvicorn.run"),
        mock.patch("time.sleep"),
    ):
        # First check returns False, then True
        mock_check.side_effect = [False, True]
        mock_process = mock.Mock()
        mock_start.return_value = mock_process

        mock_worker = mock.Mock()
        mock_worker_class.return_value = mock_worker

        try:
            dev(host="0.0.0.0", port=8000, reload=True, config_file=None)
        except KeyboardInterrupt:
            pass

        # Verify Temporal was started
        mock_start.assert_called_once()


def test_dev_command_temporal_timeout():
    """Test dev command exits if Temporal doesn't start."""
    with (
        mock.patch("olive.cli.check_temporal_running", return_value=False),
        mock.patch("olive.cli.start_temporal_dev_server") as mock_start,
        mock.patch("time.sleep"),
    ):
        mock_process = mock.Mock()
        mock_start.return_value = mock_process

        with pytest.raises(typer.Exit):
            dev(host="0.0.0.0", port=8000, reload=True, config_file=None)


def test_dev_command_cleanup():
    """Test dev command cleanup on exit."""
    with (
        mock.patch("olive.cli.check_temporal_running") as mock_check,
        mock.patch("olive.cli.start_temporal_dev_server") as mock_start,
        mock.patch("olive.cli.TemporalWorker") as mock_worker_class,
        mock.patch("uvicorn.run") as mock_uvicorn,
        mock.patch("time.sleep"),
    ):
        # First check returns False (not running), then True (started successfully)
        mock_check.side_effect = [False, True]

        mock_process = mock.Mock()
        mock_start.return_value = mock_process

        mock_worker = mock.Mock()
        mock_worker_class.return_value = mock_worker

        # Make uvicorn raise KeyboardInterrupt
        mock_uvicorn.side_effect = KeyboardInterrupt

        # Run and expect clean exit
        dev(host="0.0.0.0", port=8000, reload=True, config_file=None)

        # Verify cleanup
        mock_worker.stop.assert_called_once()
        mock_process.terminate.assert_called_once()


def test_serve_command():
    """Test serve command."""
    with mock.patch("olive.cli.TemporalWorker") as mock_worker_class, mock.patch("uvicorn.run") as mock_uvicorn:
        mock_worker = mock.Mock()
        mock_worker_class.return_value = mock_worker

        try:
            serve(host="127.0.0.1", port=8001, temporal_address="localhost:7234", temporal_namespace="test-namespace")
        except KeyboardInterrupt:
            pass

        # Verify worker was created with correct config
        mock_worker_class.assert_called_once()
        config = mock_worker_class.call_args[0][0]
        assert config.temporal.address == "localhost:7234"
        assert config.temporal.namespace == "test-namespace"

        # Verify worker was started
        mock_worker.start_background.assert_called_once()

        # Verify uvicorn was called
        mock_uvicorn.assert_called_once()


def test_serve_command_cleanup():
    """Test serve command cleanup on exit."""
    with mock.patch("olive.cli.TemporalWorker") as mock_worker_class, mock.patch("uvicorn.run") as mock_uvicorn:
        mock_worker = mock.Mock()
        mock_worker_class.return_value = mock_worker

        # Make uvicorn raise KeyboardInterrupt
        mock_uvicorn.side_effect = KeyboardInterrupt

        # Run and expect clean exit
        serve(host="0.0.0.0", port=8000, temporal_address=None, temporal_namespace=None, config_file=None)

        # Verify cleanup
        mock_worker.stop.assert_called_once()


def test_dev_with_config_file(tmp_path):
    """Test dev command with config file."""
    config_file = tmp_path / ".olive.yaml"
    config_file.write_text("""
temporal:
  address: custom:7233
  namespace: custom-ns
""")

    with (
        mock.patch("olive.cli.check_temporal_running", return_value=True),
        mock.patch("olive.cli.TemporalWorker") as mock_worker_class,
        mock.patch("uvicorn.run"),
    ):
        mock_worker = mock.Mock()
        mock_worker_class.return_value = mock_worker

        try:
            dev(config_file=config_file)
        except KeyboardInterrupt:
            pass

        # Verify config was loaded
        config = mock_worker_class.call_args[0][0]
        assert config.temporal.address == "custom:7233"
        assert config.temporal.namespace == "custom-ns"


def test_serve_with_config_file(tmp_path):
    """Test serve command with config file."""
    config_file = tmp_path / ".olive.yaml"
    config_file.write_text("""
temporal:
  address: prod:7233
  namespace: prod-ns
""")

    with mock.patch("olive.cli.TemporalWorker") as mock_worker_class, mock.patch("uvicorn.run"):
        mock_worker = mock.Mock()
        mock_worker_class.return_value = mock_worker

        try:
            serve(config_file=config_file)
        except KeyboardInterrupt:
            pass

        # Verify config was loaded
        config = mock_worker_class.call_args[0][0]
        assert config.temporal.address == "prod:7233"
        assert config.temporal.namespace == "prod-ns"


def test_main_py_detection():
    """Test that CLI detects main.py vs module import."""
    with (
        mock.patch("pathlib.Path.exists") as mock_exists,
        mock.patch("olive.cli.check_temporal_running", return_value=True),
        mock.patch("olive.cli.TemporalWorker"),
        mock.patch("uvicorn.run") as mock_uvicorn,
    ):
        # Test with main.py present
        mock_exists.return_value = True

        try:
            dev(host="0.0.0.0", port=8000, reload=True, config_file=None)
        except KeyboardInterrupt:
            pass

        # Should use main:app
        call_args = mock_uvicorn.call_args
        assert call_args[0][0] == "main:app"
        assert call_args[1]["factory"] is False

        # Test without main.py
        mock_exists.return_value = False

        try:
            dev(host="0.0.0.0", port=8000, reload=True, config_file=None)
        except KeyboardInterrupt:
            pass

        # Should use factory
        call_args = mock_uvicorn.call_args
        assert call_args[0][0] == "olive.server.app:create_app"
        assert call_args[1]["factory"] is True


def test_main_function():
    """Test main function."""
    with mock.patch("olive.cli.app") as mock_app:
        from olive.cli import main

        main()
        mock_app.assert_called_once()


def test_main_module():
    """Test __main__ execution."""
    # Get the path to the cli module
    import olive.cli

    cli_path = olive.cli.__file__

    # Run the cli module as __main__ with a mocked app
    test_script = f"""
import sys
import unittest.mock

# Add parent directory to path so we can import olive
import os
sys.path.insert(0, os.path.dirname(os.path.dirname("{cli_path}")))

# Add a command argument to avoid "Missing command" error
sys.argv = ["olive", "version"]

# Mock the app object before importing
with unittest.mock.patch("olive.cli.app") as mock_app:
    # Mock app() to avoid actually running the CLI
    mock_app.return_value = None

    # Run the cli module as __main__
    import runpy
    runpy.run_path("{cli_path}", run_name="__main__")

    # Verify app was called (through main())
    assert mock_app.called
"""

    # Run the script

    result = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True)

    # Check result
    if result.returncode != 0:
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
    assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

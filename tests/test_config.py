"""Tests for Olive configuration module."""

import os
from pathlib import Path
from unittest import mock

import pytest
import yaml

from olive.config import OliveConfig, ServerConfig, TemporalConfig, ToolsConfig


def test_temporal_config_defaults():
    """Test TemporalConfig default values."""
    config = TemporalConfig()
    assert config.enabled is False  # Default should be disabled
    assert config.address == "localhost:7233"
    assert config.namespace_endpoint is None
    assert config.namespace == "default"
    assert config.task_queue == "olive-tools"
    assert config.cloud_namespace is None
    assert config.cloud_api_key is None
    assert config.client_cert_path is None
    assert config.client_key_path is None
    assert config.server_root_ca_path is None
    assert config.server_name is None


def test_temporal_config_auto_enable_with_custom_address():
    """Test that custom address auto-enables Temporal."""
    config = TemporalConfig(address="prod-temporal.example.com:7233")
    assert config.enabled is True


def test_temporal_config_auto_enable_with_cloud_namespace():
    """Test that cloud namespace auto-enables Temporal."""
    config = TemporalConfig(cloud_namespace="my-namespace")
    assert config.enabled is True


def test_temporal_config_auto_enable_with_cloud_api_key():
    """Test that cloud API key auto-enables Temporal."""
    config = TemporalConfig(cloud_api_key="my-key")
    assert config.enabled is True


def test_temporal_config_auto_enable_with_namespace_endpoint():
    """Test that namespace endpoint auto-enables Temporal."""
    config = TemporalConfig(namespace_endpoint="namespace.tmprl.cloud:7233")
    assert config.enabled is True


def test_temporal_config_auto_enable_with_custom_namespace():
    """Test that custom namespace auto-enables Temporal."""
    config = TemporalConfig(namespace="production")
    assert config.enabled is True


def test_temporal_config_auto_enable_with_tls():
    """Test that TLS configuration auto-enables Temporal."""
    config = TemporalConfig(client_cert_path="/path/to/cert.pem")
    assert config.enabled is True


def test_temporal_config_no_auto_enable_with_defaults():
    """Test that default config does NOT auto-enable."""
    config = TemporalConfig()
    assert config.enabled is False


def test_temporal_config_explicit_enabled_respected():
    """Test that explicit enabled=True is respected."""
    config = TemporalConfig(enabled=True)
    assert config.enabled is True


def test_temporal_config_explicit_disabled_with_custom_config():
    """Test that explicit enabled=False is respected even with custom config.

    This allows users to have Temporal configuration but explicitly disable it
    (e.g., during migration, testing, or gradual rollout).
    """
    config = TemporalConfig(enabled=False, address="custom:7233")
    # Should respect explicit enabled=False even with custom address
    assert config.enabled is False


def test_temporal_config_is_cloud():
    """Test TemporalConfig is_cloud property."""
    config = TemporalConfig()
    assert not config.is_cloud

    config.cloud_namespace = "my-namespace"
    config.cloud_api_key = "my-key"
    assert config.is_cloud

    # Only namespace is not enough
    config.cloud_api_key = None
    assert not config.is_cloud


def test_server_config_defaults():
    """Test ServerConfig default values."""
    config = ServerConfig()
    assert config.host == "0.0.0.0"
    assert config.port == 8000


def test_tools_config_defaults():
    """Test ToolsConfig default values."""
    config = ToolsConfig()
    assert config.default_timeout == 300
    assert config.default_retry_attempts == 3


def test_olive_config_defaults():
    """Test OliveConfig default values."""
    config = OliveConfig()
    assert isinstance(config.temporal, TemporalConfig)
    assert isinstance(config.server, ServerConfig)
    assert isinstance(config.tools, ToolsConfig)


def test_olive_config_from_file(tmp_path):
    """Test loading config from file."""
    # Create a config file
    config_file = tmp_path / ".olive.yaml"
    config_data = {
        "temporal": {"address": "custom:7233", "namespace": "custom-ns", "task_queue": "custom-queue"},
        "server": {"host": "127.0.0.1", "port": 9000},
        "tools": {"default_timeout": 600, "default_retry_attempts": 5},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    # Load config from file
    config = OliveConfig.from_file(config_file)

    assert config.temporal.address == "custom:7233"
    assert config.temporal.namespace == "custom-ns"
    assert config.temporal.task_queue == "custom-queue"
    assert config.server.host == "127.0.0.1"
    assert config.server.port == 9000
    assert config.tools.default_timeout == 600
    assert config.tools.default_retry_attempts == 5


def test_olive_config_from_file_default_locations(tmp_path):
    """Test loading config from default locations."""
    # Test .olive.yaml
    with mock.patch("pathlib.Path.cwd", return_value=tmp_path):
        config_file = tmp_path / ".olive.yaml"
        config_file.write_text("temporal:\n  address: test1:7233\n")

        config = OliveConfig.from_file()
        assert config.temporal.address == "test1:7233"

    # Test olive.yaml fallback
    with mock.patch("pathlib.Path.cwd", return_value=tmp_path):
        # Remove .olive.yaml
        config_file.unlink()

        # Create olive.yaml
        config_file = tmp_path / "olive.yaml"
        config_file.write_text("temporal:\n  address: test2:7233\n")

        config = OliveConfig.from_file()
        assert config.temporal.address == "test2:7233"


def test_olive_config_from_file_not_found():
    """Test loading config when file doesn't exist."""
    config = OliveConfig.from_file(Path("/nonexistent/path"))
    # Should return default config
    assert config.temporal.address == "localhost:7233"


def test_olive_config_from_env():
    """Test loading config from environment variables."""
    with mock.patch.dict(
        os.environ,
        {
            "OLIVE_TEMPORAL_ADDRESS": "env:7233",
            "OLIVE_TEMPORAL_NAMESPACE_ENDPOINT": "env-endpoint:7233",
            "OLIVE_TEMPORAL_NAMESPACE": "env-ns",
            "OLIVE_TEMPORAL_CLOUD_NAMESPACE": "cloud-ns",
            "OLIVE_TEMPORAL_CLOUD_API_KEY": "cloud-key",
            "OLIVE_TEMPORAL_CLIENT_CERT_PATH": "/tmp/cert.pem",
            "OLIVE_TEMPORAL_CLIENT_KEY_PATH": "/tmp/key.pem",
            "OLIVE_TEMPORAL_SERVER_ROOT_CA_PATH": "/tmp/ca.pem",
            "OLIVE_TEMPORAL_SERVER_NAME": "temporal.example.com",
            "OLIVE_SERVER_HOST": "0.0.0.0",
            "OLIVE_SERVER_PORT": "8080",
            "OLIVE_TOOLS_DEFAULT_TIMEOUT": "900",
            "OLIVE_TOOLS_DEFAULT_RETRY_ATTEMPTS": "10",
        },
    ):
        config = OliveConfig.from_env()

        assert config.temporal.address == "env-endpoint:7233"
        assert config.temporal.namespace_endpoint == "env-endpoint:7233"
        assert config.temporal.namespace == "env-ns"
        assert config.temporal.cloud_namespace == "cloud-ns"
        assert config.temporal.cloud_api_key == "cloud-key"
        assert config.temporal.client_cert_path == "/tmp/cert.pem"
        assert config.temporal.client_key_path == "/tmp/key.pem"
        assert config.temporal.server_root_ca_path == "/tmp/ca.pem"
        assert config.temporal.server_name == "temporal.example.com"
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8080
        assert config.tools.default_timeout == 900
        assert config.tools.default_retry_attempts == 10


def test_olive_config_from_env_task_queue():
    """Test loading task queue from environment."""
    with mock.patch.dict(os.environ, {"OLIVE_TEMPORAL_TASK_QUEUE": "custom-queue"}):
        config = OliveConfig.from_env()
        assert config.temporal.task_queue == "custom-queue"


def test_olive_config_merge_with_env_all_vars():
    """Test merging config with all environment variables."""
    config = OliveConfig()

    with mock.patch.dict(
        os.environ,
        {
            "OLIVE_TEMPORAL_ADDRESS": "env:7233",
            "OLIVE_TEMPORAL_NAMESPACE_ENDPOINT": "env-endpoint:7233",
            "OLIVE_TEMPORAL_NAMESPACE": "env-ns",
            "OLIVE_TEMPORAL_TASK_QUEUE": "env-queue",
            "OLIVE_TEMPORAL_CLOUD_NAMESPACE": "cloud-ns",
            "OLIVE_TEMPORAL_CLOUD_API_KEY": "cloud-key",
            "OLIVE_TEMPORAL_CLIENT_CERT_PATH": "/tmp/cert.pem",
            "OLIVE_TEMPORAL_CLIENT_KEY_PATH": "/tmp/key.pem",
            "OLIVE_TEMPORAL_SERVER_ROOT_CA_PATH": "/tmp/ca.pem",
            "OLIVE_TEMPORAL_SERVER_NAME": "temporal.example.com",
            "OLIVE_SERVER_HOST": "127.0.0.1",
            "OLIVE_SERVER_PORT": "9000",
            "OLIVE_TOOLS_DEFAULT_TIMEOUT": "1200",
            "OLIVE_TOOLS_DEFAULT_RETRY_ATTEMPTS": "15",
        },
    ):
        result = config.merge_with_env()

        assert result.temporal.address == "env-endpoint:7233"
        assert result.temporal.namespace_endpoint == "env-endpoint:7233"
        assert result.temporal.namespace == "env-ns"
        assert result.temporal.task_queue == "env-queue"
        assert result.temporal.cloud_namespace == "cloud-ns"
        assert result.temporal.cloud_api_key == "cloud-key"
        assert result.temporal.client_cert_path == "/tmp/cert.pem"
        assert result.temporal.client_key_path == "/tmp/key.pem"
        assert result.temporal.server_root_ca_path == "/tmp/ca.pem"
        assert result.temporal.server_name == "temporal.example.com"
        assert result.server.host == "127.0.0.1"
        assert result.server.port == 9000
        assert result.tools.default_timeout == 1200
        assert result.tools.default_retry_attempts == 15


def test_olive_config_merge_with_env():
    """Test merging config with environment variables."""
    # Start with base config
    config = OliveConfig(temporal=TemporalConfig(address="base:7233"), server=ServerConfig(port=8000))

    with mock.patch.dict(os.environ, {"OLIVE_TEMPORAL_NAMESPACE": "env-override", "OLIVE_SERVER_PORT": "9000"}):
        # merge_with_env modifies the config in place and returns self
        result = config.merge_with_env()

        # Result is the same object
        assert result is config

        # Config has been modified with overrides
        assert config.temporal.address == "base:7233"  # kept from base
        assert config.temporal.namespace == "env-override"  # overridden
        assert config.server.port == 9000  # overridden


def test_olive_config_handles_option_info():
    """Test that from_file handles typer OptionInfo objects."""
    # Mock a typer OptionInfo object
    mock_option_info = mock.Mock()
    mock_option_info.default = Path("/test/path")

    with mock.patch("pathlib.Path.exists", return_value=False):
        config = OliveConfig.from_file(mock_option_info)
        # Should use the default value and return default config
        assert config.temporal.address == "localhost:7233"

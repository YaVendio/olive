"""Configuration management for Olive."""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class TemporalConfig(BaseModel):
    """Temporal configuration."""

    address: str = Field(default="localhost:7233", description="Temporal server address")
    namespace: str = Field(default="default", description="Temporal namespace")
    task_queue: str = Field(default="olive-tools", description="Task queue name")

    # Cloud configuration
    cloud_namespace: str | None = Field(default=None, description="Temporal Cloud namespace")
    cloud_api_key: str | None = Field(default=None, description="Temporal Cloud API key")

    # TLS configuration
    client_cert_path: str | None = Field(default=None, description="Path to TLS client certificate")
    client_key_path: str | None = Field(default=None, description="Path to TLS client private key")
    server_root_ca_path: str | None = Field(default=None, description="Path to Temporal server root CA certificate")
    server_name: str | None = Field(default=None, description="Override server name for TLS verification")

    @property
    def is_cloud(self) -> bool:
        """Check if using Temporal Cloud."""
        return bool(self.cloud_namespace and self.cloud_api_key)


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=True, description="Enable auto-reload in dev mode")
    # Import path for FastAPI app or factory, e.g. "app.main:app" or
    # "olive.server.app:create_app" when using a factory
    app: str = Field(default="olive.server.app:create_app", description="Uvicorn app import path")
    factory: bool = Field(default=True, description="Whether the app import is a factory")


class ToolsConfig(BaseModel):
    """Tools default configuration."""

    default_timeout: int = Field(default=300, description="Default timeout in seconds")
    default_retry_attempts: int = Field(default=3, description="Default retry attempts")


class OliveConfig(BaseModel):
    """Main Olive configuration."""

    temporal: TemporalConfig = Field(default_factory=TemporalConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)

    @classmethod
    def from_file(cls, path: Path | None = None) -> "OliveConfig":
        """Load configuration from file."""
        # Handle case where path might be a typer OptionInfo object
        if hasattr(path, "default"):
            path = path.default

        if path is None:
            # Look for .olive.yaml in current directory
            path = Path.cwd() / ".olive.yaml"
            if not path.exists():
                # Look for olive.yaml
                path = Path.cwd() / "olive.yaml"

        if path and path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)

        return cls()

    @classmethod
    def from_env(cls) -> "OliveConfig":
        """Load configuration from environment variables."""
        config = cls()

        # Temporal settings
        if address := os.getenv("OLIVE_TEMPORAL_ADDRESS"):
            config.temporal.address = address
        if namespace := os.getenv("OLIVE_TEMPORAL_NAMESPACE"):
            config.temporal.namespace = namespace
        if task_queue := os.getenv("OLIVE_TEMPORAL_TASK_QUEUE"):
            config.temporal.task_queue = task_queue

        # Temporal Cloud
        if cloud_ns := os.getenv("OLIVE_TEMPORAL_CLOUD_NAMESPACE"):
            config.temporal.cloud_namespace = cloud_ns
        if cloud_key := os.getenv("OLIVE_TEMPORAL_CLOUD_API_KEY"):
            config.temporal.cloud_api_key = cloud_key
        if cert_path := os.getenv("OLIVE_TEMPORAL_CLIENT_CERT_PATH"):
            config.temporal.client_cert_path = cert_path
        if key_path := os.getenv("OLIVE_TEMPORAL_CLIENT_KEY_PATH"):
            config.temporal.client_key_path = key_path
        if ca_path := os.getenv("OLIVE_TEMPORAL_SERVER_ROOT_CA_PATH"):
            config.temporal.server_root_ca_path = ca_path
        if server_name := os.getenv("OLIVE_TEMPORAL_SERVER_NAME"):
            config.temporal.server_name = server_name

        # Server settings
        if host := os.getenv("OLIVE_SERVER_HOST"):
            config.server.host = host
        if port := os.getenv("OLIVE_SERVER_PORT"):
            config.server.port = int(port)
        if app := os.getenv("OLIVE_SERVER_APP"):
            config.server.app = app
        if factory := os.getenv("OLIVE_SERVER_FACTORY"):
            # Accept common truthy strings
            config.server.factory = factory.lower() in {"1", "true", "yes"}

        # Tools settings
        if timeout := os.getenv("OLIVE_TOOLS_DEFAULT_TIMEOUT"):
            config.tools.default_timeout = int(timeout)
        if retry := os.getenv("OLIVE_TOOLS_DEFAULT_RETRY_ATTEMPTS"):
            config.tools.default_retry_attempts = int(retry)

        return config

    def merge_with_env(self) -> "OliveConfig":
        """Merge current config with environment variables."""
        env_config = self.from_env()

        # Only override if env vars are set
        if os.getenv("OLIVE_TEMPORAL_ADDRESS"):
            self.temporal.address = env_config.temporal.address
        if os.getenv("OLIVE_TEMPORAL_NAMESPACE"):
            self.temporal.namespace = env_config.temporal.namespace
        if os.getenv("OLIVE_TEMPORAL_TASK_QUEUE"):
            self.temporal.task_queue = env_config.temporal.task_queue
        if os.getenv("OLIVE_TEMPORAL_CLOUD_NAMESPACE"):
            self.temporal.cloud_namespace = env_config.temporal.cloud_namespace
        if os.getenv("OLIVE_TEMPORAL_CLOUD_API_KEY"):
            self.temporal.cloud_api_key = env_config.temporal.cloud_api_key
        if os.getenv("OLIVE_TEMPORAL_CLIENT_CERT_PATH"):
            self.temporal.client_cert_path = env_config.temporal.client_cert_path
        if os.getenv("OLIVE_TEMPORAL_CLIENT_KEY_PATH"):
            self.temporal.client_key_path = env_config.temporal.client_key_path
        if os.getenv("OLIVE_TEMPORAL_SERVER_ROOT_CA_PATH"):
            self.temporal.server_root_ca_path = env_config.temporal.server_root_ca_path
        if os.getenv("OLIVE_TEMPORAL_SERVER_NAME"):
            self.temporal.server_name = env_config.temporal.server_name
        if os.getenv("OLIVE_SERVER_HOST"):
            self.server.host = env_config.server.host
        if os.getenv("OLIVE_SERVER_PORT"):
            self.server.port = env_config.server.port
        if os.getenv("OLIVE_SERVER_APP"):
            self.server.app = env_config.server.app
        if os.getenv("OLIVE_SERVER_FACTORY"):
            self.server.factory = env_config.server.factory
        if os.getenv("OLIVE_TOOLS_DEFAULT_TIMEOUT"):
            self.tools.default_timeout = env_config.tools.default_timeout
        if os.getenv("OLIVE_TOOLS_DEFAULT_RETRY_ATTEMPTS"):
            self.tools.default_retry_attempts = env_config.tools.default_retry_attempts

        return self

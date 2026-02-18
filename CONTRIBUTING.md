# Contributing to Olive

Thank you for your interest in contributing. This guide covers the development setup, standards, and workflow.

## Development Setup

```bash
git clone git@github.com:YaVendio/olive.git
cd olive
uv sync --all-extras
```

This installs all dependencies including Temporal and dev tools.

## Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=olive --cov=olive_client --cov-report=html

# Single file
uv run pytest tests/test_router.py -x
```

## Code Quality

```bash
# Lint
uv run ruff check olive/ olive_client/ tests/

# Format
uv run ruff format olive/ olive_client/ tests/

# Type check
uv run basedpyright olive/ olive_client/
```

Run all three before opening a PR.

## Standards

- **Python 3.12+**
- **Ruff** for linting and formatting (line-length 120, target py313)
- **basedpyright** for type checking (standard mode)
- **Type hints** on all function signatures
- **Tests** for every new feature or bug fix
- **pytest** with `asyncio_mode=auto`

## Workflow

1. Fork the repository
2. Create a feature branch

   ```bash
   git checkout -b feature/new-feature
   ```

3. Make your changes
4. Add or update tests
5. Run lint, format, and type check
6. Commit using [Conventional Commits](https://www.conventionalcommits.org/)

   ```bash
   git commit -m "feat: add new feature X"
   git commit -m "fix: handle missing context in injection"
   ```

7. Push and open a Pull Request

   ```bash
   git push origin feature/new-feature
   ```

## Project Structure

```
olive/
  olive/                  # Server package
    __init__.py           # Public exports (olive_tool, Inject, create_app, setup_olive)
    decorator.py          # @olive_tool decorator
    registry.py           # Thread-safe ToolRegistry singleton
    router.py             # FastAPI router (endpoints, injection, execution)
    schemas.py            # Pydantic models (ToolInfo, ToolCallRequest/Response, Inject)
    config.py             # OliveConfig (.olive.yaml + env vars)
    cli.py                # CLI commands (dev, serve, init, version)
    setup.py              # setup_olive() for mounting on existing apps
    server/
      __init__.py
      app.py              # create_app() factory with lifespan
    temporal/
      __init__.py
      worker.py           # TemporalWorker lifecycle
      workflows.py        # OliveToolWorkflow, OliveToolInput
      activities.py       # Activity wrappers for tools
  olive_client/           # Client package
    __init__.py
    client.py             # OliveClient (langgraph, langchain, elevenlabs)
  tests/                  # Test suite
  pyproject.toml
```

## Types of Contributions

- **Bug reports** -- open a GitHub Issue with reproduction steps
- **Feature requests** -- open a discussion first to align on approach
- **Documentation** -- always welcome, especially examples
- **Test coverage** -- help close gaps in edge cases
- **Bug fixes** -- check open issues for things to pick up

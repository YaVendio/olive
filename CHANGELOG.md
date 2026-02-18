# Changelog

All notable changes to Olive will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2026-02-18

### Added
- **Structured error types**: `ToolCallResponse` now includes `error_type` field with values `tool_not_found`, `missing_context`, `validation_error`, `execution_error`, `timeout`
- **Request timeouts**: Direct execution (non-Temporal) mode enforces `timeout_seconds` via `asyncio.wait_for()` for both sync and async tools
- **Context type validation**: Injected parameters are type-checked at call time against their declared type hints. Mismatches return `validation_error`
- **Health endpoint**: `GET /olive/health` returns tool count and Temporal connection status
- **Thread-safe registry**: `ToolRegistry` operations guarded by `threading.Lock`. `list_all()` returns snapshot copies
- **UUID workflow IDs**: Both `execute_tool()` and `start_tool()` use `uuid4()` for collision-free workflow identifiers
- **Workflow config passthrough**: `OliveToolInput` dataclass carries `timeout_seconds` and `retry_policy` from `@olive_tool` decorator through to Temporal `execute_activity()`. No more hardcoded values

### Changed
- **Global state removed**: Temporal worker reference moved from module-level global to `app.state.temporal_worker`. Router reads via `request.app.state`. Backward-compat shim retained for `set_temporal_worker()`
- **Busy loop eliminated**: Temporal worker uses `asyncio.Event.wait()` instead of `while/sleep(0.1)` polling
- **Client SDK DRY**: Shared `_build_args_schema()` static method replaces duplicated schema building across `as_langchain_tools()`, `as_langchain_tools_injecting()`, and `as_langgraph_tools()`
- **CLI dedup**: Shared `_run_server()` helper consolidates common logic between `olive dev` and `olive serve`
- **Router parameter renamed**: `call_tool()` endpoint uses `tool_request: ToolCallRequest` instead of shadowing `request`
- **Logging moved to module level**: Logger initialized once at module scope instead of inline per request
- **Context injection checks required injections even when context is None**: Previously, missing context dict silently skipped required injection checks

### Deprecated
- `as_langchain_tools_injecting()` — use `as_langgraph_tools()` instead. Emits `DeprecationWarning`
- `set_temporal_worker()` — set `app.state.temporal_worker` directly in lifespan instead

### Fixed
- Required context injections now return `missing_context` error when called without context, instead of failing with `TypeError` deep in tool function
- Full stack traces preserved in logs via `logger.exception()` before returning sanitized error to client

## [1.4.2] - 2025-10-15

### Fixed
- `olive dev` and `olive serve` respect `temporal.enabled: false` when set explicitly in config
- Temporal auto-enable logic no longer overrides explicit `enabled: false`

## [1.4.0] - 2025-10-12

### Added
- **Profiles**: Tools declare membership in profiles via `@olive_tool(profiles=["base", "shopify"])`. Clients filter with `?profile=` query param
- **Context injection**: `Annotated[str, Inject(key="...")]` marks parameters as injected from runtime context, excluded from LLM-visible schema
- **`as_langgraph_tools()`**: Primary client method for LangGraph agents with `ToolRuntime.context` integration
- **`as_langchain_tools_injecting()`**: LangChain client method with `context_provider` callback
- **CLI**: `olive dev`, `olive serve`, `olive init`, `olive version` commands
- **Configuration**: `.olive.yaml` file with environment variable overrides

## [1.3.2] - 2025-10-07

### Fixed
- Fixed test suite to properly mock HTTP calls in ElevenLabs integration tests
- Fixed ElevenLabs tool type format to use "client" and "server" instead of "client_tool" and "server_tool"

## [1.3.0] - 2025-10-01

### Added
- **ElevenLabs support**: `as_elevenlabs_tools()` method and `GET /olive/tools/elevenlabs` endpoint
- Voice agent integration with the same tool set used for LangChain agents

## [1.2.2] - Previous Release

Previous stable version with LangChain tools only.

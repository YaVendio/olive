# Changelog

All notable changes to Olive will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-10-01

### Added
- **ElevenLabs Agents Platform support**: New `as_elevenlabs_tools()` method in `OliveClient` to convert tools to ElevenLabs format
- **ElevenLabs endpoint**: New `GET /olive/tools/elevenlabs` endpoint that returns tools in ElevenLabs Agents Platform format
- Support for voice agent integration with the same tool set used for LangChain agents

### Changed
- Updated server root endpoint to include new `tools_elevenlabs` endpoint in response
- Version bumped to 1.3.0

### Technical Details
- ElevenLabs tools format: `{type, name, description, parameters}`
- Compatible with ElevenLabs WebSocket API conversation initialization
- No breaking changes to existing LangChain tool functionality

## [1.2.2] - Previous Release

Previous stable version with LangChain tools only.


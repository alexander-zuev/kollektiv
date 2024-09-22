# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added streaming of responses to the main response method

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.1.3] - XXX
### Added
- Added caching of system prompt and tool definitions
- Introduced sliding context window into conversation history based on token counts

## Changed
- Refactored conversation history handling
- Refactored tool use and response handling


## [0.1.2] - 2024-09-21
- Introduced conventional commit styles
- Refactored conversation history handling
- Introduced sliding context window
- Refactored tool use and response handling

## [0.1.1] - 2024-09-18
- Minor fixes, doc updates, basic tests setup
- Minor CI changes

## [0.1.0] - 2024-09-15
Initial release of OmniClaude with the following features:
  - crawling of documentation with FireCrawl
  - custom markdown chunking
  - embedding and storage with ChromaDB
  - custom retrieval with multi-query expansion and re-ranking
  - chat with Sonnet 3.5 with rag search tool

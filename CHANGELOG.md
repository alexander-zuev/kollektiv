# Kollektiv Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Web Interface: Added Chainlit-based web UI for improved user experience
- Interactive Document Management: Added support for managing documents via web interface
- Improved Command Handling: Enhanced @docs commands with better validation and feedback
- URL Validation: Added robust URL validation with support for common formats
- Pattern Validation: Added validation for exclude patterns in crawling configuration

### Changed
- Updated documentation to reflect web interface usage
- Refactored command handling for better user interaction
- Improved error messages and user feedback
- Enhanced help messages with clearer examples
- Simplified document management workflow

### Fixed
- Fixed URL validation in document addition process
- Improved error handling in crawling process
- Added validation for exclude patterns format
- Fixed inconsistencies in command documentation

### Deprecated

### Removed

### Security


## [0.1.6] - 2024-10-19
### Added
- Web UI: You can now chat with synced content via web interface. Built using Chainlit.

### Under development
- Basic evaluation suite is setup using Weave.

## [0.1.5] - 2024-10-19
### Changed
- Kollektiv is born - the project was renamed in order to exclude confusion with regards to Anthropic's Claude
  family of models.


## [0.1.4] - 2024-09-28

### Added
- Added Anthropic API exception handling

### Changed
- Updated pre-processing of chunker to remove images due to lack of multi-modal embeddings support

### Removed
- Removed redundant QueryGenerator class

### Fixed
- Fixed errors in streaming & non-streaming responses


## [0.1.3] - 2024-09-22
### Added
- Added caching of system prompt and tool definitions
- Introduced sliding context window into conversation history based on token counts
- Added streaming of assistant responses

### Changed
- Refactored conversation history handling
- Refactored tool use and response handling
- Refactored response generation to support both streaming and non-streaming
- Updated logging
- Improved vector db loading logic to handle missing chunks better
- Improved summary generation logic by vector db


## [0.1.2] - 2024-09-21
- Introduced conventional commit styles
- Refactored conversation history handling
- Introduced sliding context window
- Refactored tool use and response handling


## [0.1.1] - 2024-09-18
- Minor fixes, doc updates, basic tests setup
- Minor CI changes


## [0.1.0] - 2024-09-15
Initial release of Kollektiv (called OmniClaude back then) with the following features:
  - Crawling of documentation with FireCrawl
  - Custom markdown chunking
  - Embedding and storage with ChromaDB
  - Custom retrieval with multi-query expansion and re-ranking
  - Chat with Sonnet 3.5 with rag search tool

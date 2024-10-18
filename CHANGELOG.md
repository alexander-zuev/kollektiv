# OmniClaude Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- (WIP) added basic eval suite to measure retrieval and end-to-end accuracy
- Added chainlit UI that allows users:
  - sync web content on demand (using FireCrawl)
  - chat with the loaded web content

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.1.4] - 2024-09-28

### Added
- added Anthropic API exception handling

### Changed
- updated pre-processing of chunker to remove images due to lack of multi-modal embeddings support

### Removed
- removed redundant QueryGenerator class

### Fixed
- fixed errors in streaming & non-streaming responses



## [0.1.3] - 2024-09-22
### Added
- Added caching of system prompt and tool definitions
- Introduced sliding context window into conversation history based on token counts
- Added streaming of assistant responses

## Changed
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
Initial release of OmniClaude with the following features:
  - crawling of documentation with FireCrawl
  - custom markdown chunking
  - embedding and storage with ChromaDB
  - custom retrieval with multi-query expansion and re-ranking
  - chat with Sonnet 3.5 with rag search tool
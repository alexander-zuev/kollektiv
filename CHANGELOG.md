# Kollektiv Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Web Interface: Added Chainlit-based web UI for improved user experience
- Interactive Document Management (WIP): Added support for managing documents via web interface
- FastAPI: Added health checks and webhook handlers

### Changed
- Updated documentation to reflect new startup process

### Fixed


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

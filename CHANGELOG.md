# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- added pull request template and a basic GitHub Action to automatically append commit messages to PR requests

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.1.1] - 2024-09-18
Minor fixes, doc updates, basic tests setup.

## [0.1.0] - 2024-09-15
Initial release of RAG Docs with the following features:
  - crawling of documentation with FireCrawl
  - custom markdown chunking
  - embedding and storage with ChromaDB
  - custom retrieval with multi-query expansion and re-ranking
  - chat with Sonnet 3.5 with rag search tool

# Crawler Module Test Setup

## Overview

This document outlines the testing strategy for the `crawler` module, encompassing unit, integration, and end-to-end (E2E) tests. The primary goal is to ensure comprehensive test coverage of the `FireCrawler` class and its interactions with other system components. This document details the test structure, required dependencies, specific scenarios for each test category, best practices for maintaining a robust and reliable test suite, and a clear execution plan. It also addresses data management for test fixtures and mock responses.

## Test Structure

```
tests/
├── unit/
│   └── test_crawler.py      # Unit tests for FireCrawler methods
├── integration/
│   └── test_crawler_flow.py # Integration tests for crawler workflows
├── e2e/
│   └── test_crawler_e2e.py   # End-to-end tests with a live environment
├── data/                # Directory for mock data and fixtures
│   ├── mock_responses/    # Sample API responses for mocking
│   ├── jobs/              # Test job data files
│   └── results/           # Expected crawl result files
└── conftest.py            # Pytest fixtures and shared test utilities
```

## Required Test Dependencies

```python
# Core testing libraries
from unittest.mock import AsyncMock, Mock, patch
import pytest
from pydantic import HttpUrl

# Application imports
from src.core.content.crawler.crawler import FireCrawler  # Correct import path
from src.models.common.jobs import CrawlJob, CrawlJobStatus
from src.models.content.firecrawl_models import CrawlRequest, CrawlParams, CrawlResult
from src.core._exceptions import JobNotCompletedError, FireCrawlAPIError, FireCrawlTimeoutError, FireCrawlConnectionError # Correct import path for custom exceptions
```

## Test Categories

### 1. Unit Tests (`tests/unit/test_crawler.py`)

These tests focus on isolated units of the `FireCrawler` class, mocking external dependencies. They ensure each method functions correctly in isolation, handling various input scenarios and edge cases.  **Given that we use Pydantic models for data validation, unit tests should primarily focus on logic and behavior, not basic data type validation that Pydantic already handles.**

#### Test Scenarios

* **`_build_params(self, request: CrawlRequest) -> CrawlParams`**: Converts a user's `CrawlRequest` into parameters for the Firecrawl API.
    * **Focus:**  Webhook URL construction (with and without custom URL), proper handling of optional fields (page_limit, max_depth), and correct mapping of include/exclude patterns.  **Avoid redundant URL validation already covered by Pydantic.**

* **`_fetch_results_from_url(self, next_url: str) -> tuple[dict[str, Any], str | None]`**: Fetches data from a single URL.
    * **Focus:** Handling paginated responses (following "next" links), Firecrawl API error handling (status codes, content), timeout handling, and handling malformed responses (invalid JSON).  **Avoid redundant URL validation.**
    * **Additional Test Cases:** Implement a test case that simulates a successful paginated response involving following multiple "next" links. This ensures the crawler correctly handles multi-page responses and accumulates all data.

* **`start_crawl(self, request: CrawlRequest) -> CrawlJob`**: Initiates a crawl job.
    * **Focus:** Successful crawl initiation (interaction with `FirecrawlApp`), Firecrawl API error handling during initiation, correct handling of API key, and interaction with the `JobManager`.  **Avoid redundant URL validation.**

* **`get_results(self, job_id: str) -> CrawlResult`**: Retrieves results of a completed crawl job.
    * **Focus:** Successful result retrieval, handling incomplete jobs, handling failed jobs (error retrieval and appropriate response), data validation of the returned `CrawlResult` (ensure correct structure and data types), handling of empty crawl data, and correct extraction of unique links from metadata (including edge cases like missing metadata or duplicate URLs).

#### Mocking Strategy

```python
@pytest.fixture
async def mock_firecrawl_app():
    """Mocks the FirecrawlApp for unit tests."""
    with patch("src.core.content.crawler.crawler.FirecrawlApp") as MockFirecrawlApp:  # Correct import path
        mock_app = MockFirecrawlApp.return_value
        yield mock_app

@pytest.fixture
async def crawler(mock_firecrawl_app):
    """Provides a configured crawler instance with mocked dependencies."""
    job_manager = AsyncMock()
    file_manager = AsyncMock()
    return FireCrawler(job_manager=job_manager, file_manager=file_manager)

@pytest.fixture
def crawl_request():
    """Provides a sample CrawlRequest object."""
    return CrawlRequest(url="https://www.example.com")
```

### 2. Integration Tests (`tests/integration/test_crawler_flow.py`)

These tests verify interactions between the `FireCrawler` and other components like `JobManager`, `FileManager`, and webhook handling. They ensure that the crawler correctly integrates with these services in a realistic environment.

#### Test Scenarios

* **Job Lifecycle**: Test the complete job lifecycle: creation, status updates (in progress, completed, failed), and result retrieval.  This includes testing error handling and retry mechanisms.  Use real `JobManager` and `FileManager` instances.
* **Component Interactions**:
    * `FireCrawler` with `JobManager` (job creation, updates, retrieval). Verify correct job status transitions and data persistence.
    * `FireCrawler` with `FileManager` (result saving and loading).  Verify correct file handling and data integrity.
    * **Webhook handling (simulated webhook calls with various payloads).**  This requires mocking the webhook endpoint and verifying the crawler's response.  Test different webhook scenarios:
        * **Success:**  Webhook received with successful job completion status.
        * **Failure:** Webhook received with job failure status.  Verify error handling.
        * **Retries:** Simulate multiple webhook calls for the same job with different statuses (e.g., in progress, then completed).
        * **Malformed Webhook:**  Send a webhook with an invalid or incomplete payload.  Verify that the crawler handles this gracefully.

#### Test Implementation Example

```python
import pytest
from src.models.common.jobs import CrawlJobStatus
from src.core.system.job_manager import JobManager
from src.infrastructure.common.file_manager import FileManager

@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_crawl_flow(mock_firecrawl_app, tmp_path):  # Example using fixtures
    """Tests the complete crawl flow with simulated webhook updates."""
    job_manager = JobManager(tmp_path / "jobs") # Use temporary directory for job storage
    file_manager = FileManager(tmp_path / "results") # Use temporary directory for result storage
    crawler = FireCrawler(job_manager=job_manager, file_manager=file_manager)

    request = CrawlRequest(url="https://www.example.com")
    job = await crawler.crawl(request)
    assert job.status == CrawlJobStatus.IN_PROGRESS
    # ... Simulate webhook updates and assert job status changes ...
    # ... Finally, assert job completion and result retrieval ...
```

### 3. End-to-End Tests (`tests/e2e/test_crawler_e2e.py`)

These tests exercise the entire crawl process in a near-live environment, using a real Firecrawl API key and a test website. They provide the highest level of confidence in the system's functionality.  These tests should run against a dedicated test environment with access to external dependencies.

#### Setup Requirements

1. **ngrok Configuration**: Use `ngrok` to expose the local webhook endpoint for testing. Configure environment variables for the `ngrok` auth token.  This allows Firecrawl to send webhooks to your local test environment.  Ensure `ngrok` is properly authenticated and configured.

```python
import pytest
from pyngrok import ngrok

@pytest.fixture(scope="session")
async def ngrok_tunnel():
    """Provides an ngrok tunnel for webhook testing."""
    tunnel = ngrok.connect(8000, bind_tls=True) # Expose port 8000 with TLS
    yield tunnel.public_url
    ngrok.disconnect(tunnel.public_url)
```

2. **API Configuration**: Use test API keys and consider rate limits. Implement robust error handling for API interactions. Store API keys securely (e.g., environment variables).  Ensure all required API keys are set and valid.  Use a dedicated set of test credentials for these tests.

#### Test Scenarios

 **Full Crawl Process**:  Focus on these key scenarios:
    * **Successful Crawl (Multi-page):** Verify a successful crawl of a small, multi-page website.  Validate data integrity and completeness.  This confirms the core crawling functionality.
    * **Handling Redirects:** Crawl a website with redirects. Verify correct handling of redirects and data consistency.
    * **Firecrawl API Error:** Simulate a Firecrawl API error response (e.g., using a mock server or by injecting a failure). Verify error reporting and job status update.


## Test Data Management

### Response Templates (`tests/data/mock_responses/*.json`)

Store sample JSON responses for mocking API calls in unit and integration tests.  This promotes consistency and maintainability. Examples: `successful_crawl.json`, `failed_crawl.json`, `paginated_results.json`.  Keep these responses up-to-date with the Firecrawl API.

### File Structure for Test Data

```
tests/data/
├── mock_responses/
│   ├── successful_crawl.json
│   ├── failed_crawl.json
│   ├── paginated_results.json  # Example paginated response
│   └── rate_limited_response.json # Example rate-limited response
├── jobs/
│   └── test_job_data.json      # Example job data for testing job management
└── results/
    └── test_crawl_results.json # Example crawl results for comparison
```

### Example Mock Response (`tests/data/mock_responses/successful_crawl.json`)

```json
{
    "id": "test_firecrawl_id",
    "status": "completed",
    "data": [
        {"markdown": "# Test Content", "metadata": {"url": "https://test.com/page1"}},
        {"markdown": "## More Content", "metadata": {"url": "https://test.com/page2"}}
    ]
}
```

## Best Practices and Test Design Principles

Here are some specific test design principles aligned with your system's design:

* **Prioritize Unit Tests:** Focus on comprehensive unit test coverage for core logic and edge cases.  This provides a fast feedback loop and isolates issues effectively.
* **Strategic Integration Tests:** Use integration tests to verify interactions between components, focusing on critical workflows and data flow.
* **Targeted E2E Tests:** Limit E2E tests to a small set of critical user journeys and happy path flows.  Avoid testing edge cases and performance in E2E.
* **Mock External Dependencies:**  Aggressively mock external services (like the Firecrawl API) in unit and integration tests to ensure speed and reliability.
* **Use Realistic Test Data:**  Employ test data that closely resembles real-world data to ensure test relevance.
* **Maintain Test Data:** Keep mock responses and test data files up-to-date with the Firecrawl API and your application's schema.
* **Test Error Handling:**  Thoroughly test error handling and retry mechanisms at all levels (unit, integration, and E2E).
* **Document Test Cases:**  Clearly document test scenarios and expected outcomes to improve maintainability and understanding.

## Test Execution


### Local Development

To integrate unit, integration, and (optionally) E2E tests into pre-commit hooks, you can add a `pytest-check` hook to your `.pre-commit-config.yaml` file.  This allows you to run tests automatically before each commit.

```yaml:.pre-commit-config.yaml
repos:
-   repo: local
    hooks:
    -   id: pytest-check
        name: Run pytest suite
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        stages: [commit]  # Run on commit
        require_serial: true # Run tests serially
        args: [
            "--quiet", # Reduce output verbosity
            "-ra", # Show extra test summary info
            "--cov=src", # Generate coverage report
            "--cov-report=term-missing:skip-covered", # Format coverage report
            "--run-integration", # Include integration tests
            # "--ignore=tests/e2e" # Exclude E2E tests from pre-commit (uncomment if needed)
        ]
```

### CI Pipeline

```yaml:.github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10' # Replace with your project's Python version
      - name: Install dependencies
        run: pip install -r requirements-dev.txt # Replace with your requirements file
      - name: Run unit and integration tests
        run: pytest --cov=src --cov-report=xml --run-integration
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          token: ${{ secrets.CODECOV_TOKEN }}
      - name: Run E2E tests (if on main branch)
        if: github.ref == 'refs/heads/main'
        env:
          FIRECRAWL_API_KEY: ${{ secrets.FIRECRAWL_API_KEY }} # Store API key as a secret
          NGROK_AUTH_TOKEN: ${{ secrets.NGROK_AUTH_TOKEN }} # Store ngrok auth token as a secret
        run: |
          # Start your application's webhook server in the background
          # ... your command to start the server ... &
          # Start ngrok tunnel (replace 8000 with your webhook server's port)
          ./ngrok http 8000 &
          sleep 5 # Wait for ngrok to establish the tunnel
          # Get the ngrok URL
          NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')
          echo "NGROK_URL=$NGROK_URL" >> $GITHUB_ENV
          # Run E2E tests, using the NGROK_URL environment variable
          pytest tests/e2e/ -s --ngrok-url="$NGROK_URL"
```

Key improvements in this CI configuration:

* **Conditional E2E Tests:** E2E tests are only run on the `main` branch, reducing unnecessary execution on other branches.
* **Secrets Management:**  Sensitive information like the `FIRECRAWL_API_KEY` and `NGROK_AUTH_TOKEN` are stored as GitHub secrets and accessed securely within the workflow.
* **Background Server:** The application's webhook server is started in the background before running E2E tests.
* **Dynamic ngrok URL:** The `ngrok` URL is dynamically retrieved and passed to the `pytest` command as an environment variable, ensuring that the tests use the correct webhook URL.  This avoids hardcoding the `ngrok` URL.
* **Serial Test Execution:** The `require_serial: true` option in the pre-commit configuration ensures that tests are run serially, preventing potential conflicts and improving reliability.

import os
from unittest.mock import patch

import numpy as np
import pytest
from chromadb.api.types import Document, Documents, Embedding, EmbeddingFunction


class MockEmbeddingFunction(EmbeddingFunction):
    """Mock embedding function that follows ChromaDB's interface."""

    def __call__(self, input: Document | Documents) -> list[Embedding]:
        """Return mock embeddings that match ChromaDB's expected types."""
        # Convert float lists to numpy arrays to match Embedding type
        mock_embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)

        if isinstance(input, str):
            return [mock_embedding]
        return [mock_embedding for _ in input]


@pytest.fixture
def mock_openai_embeddings(monkeypatch):
    """Mock OpenAI embeddings for unit tests."""
    mock_func = MockEmbeddingFunction()
    monkeypatch.setattr("chromadb.utils.embedding_functions.OpenAIEmbeddingFunction", lambda **kwargs: mock_func)
    return mock_func


@pytest.fixture(autouse=True)
def mock_environment_variables():
    """Set required environment variables for tests."""
    env_vars = {
        "WANDB_MODE": "disabled",
        "WEAVE_PROJECT_NAME": "",
        "ANTHROPIC_API_KEY": "test-key",
        "COHERE_API_KEY": "test-key",
        "OPENAI_API_KEY": "test-key",
        "CO_API_KEY": "test-key",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption("--run-integration", action="store_true", default=False, help="run integration tests")


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration is specified."""
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

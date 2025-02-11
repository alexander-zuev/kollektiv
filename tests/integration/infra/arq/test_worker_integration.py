"""Integration tests for ARQ worker functionality."""

import sys
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_run_worker():
    """Test that worker runs through CLI with correct settings."""
    with patch.object(sys, "argv", ["arq", "src.infra.arq.worker.WorkerSettings"]), patch("arq.cli.cli") as mock_cli:
        from src.infra.arq.worker import run_worker

        run_worker()

        # Verify CLI was called
        mock_cli.assert_called_once()

        # Verify argv was set correctly
        assert sys.argv == ["arq", "src.infra.arq.worker.WorkerSettings"]

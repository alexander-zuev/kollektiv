"""Unit tests for CLI commands."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from src.cli import main


@pytest.fixture
def cli_runner():
    """Fixture for CLI testing."""
    return CliRunner()


def test_cli_commands_registered():
    """Test that both commands are properly registered with the CLI."""
    commands = main.commands.keys()
    assert "api" in commands
    assert "worker" in commands


def test_api_command_imports():
    """Test that api command can import its dependencies."""
    from src.app import run

    assert run is not None


def test_worker_command_imports():
    """Test that worker command can import its dependencies."""
    from src.infra.arq.worker import run_worker

    assert run_worker is not None


def test_api_command_execution(cli_runner):
    """Test that api command calls the correct function."""
    with patch("src.app.run") as mock_run:
        result = cli_runner.invoke(main, ["api"])
        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_worker_command_execution(cli_runner):
    """Test that worker command calls the correct function."""
    with patch("src.infra.arq.worker.run_worker") as mock_run_worker:
        result = cli_runner.invoke(main, ["worker"])
        assert result.exit_code == 0
        mock_run_worker.assert_called_once()

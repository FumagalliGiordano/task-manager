"""
Unit Test — app/cli.py

Usa Click's CliRunner per testare i comandi CLI in isolamento.
Patch diretta su _get_service per iniettare uno storage temporaneo isolato.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from app.cli import cli
from app.service import TaskService
from utils.storage import JsonStorage


@pytest.fixture
def runner():
    """Click CliRunner isolato."""
    return CliRunner()


@pytest.fixture
def invoke_cli(tmp_dir: Path):
    """
    Restituisce una funzione invoke che usa uno storage completamente isolato.
    Patcha _get_service per iniettare un TaskService su file temporaneo.
    """
    storage_path = str(tmp_dir / "tasks_cli_test.json")

    def _invoke(args, input=None):
        def fake_get_service():
            return TaskService(storage=JsonStorage(filepath=storage_path))

        runner = CliRunner()
        with patch("app.cli._get_service", side_effect=fake_get_service):
            return runner.invoke(cli, args, input=input)

    return _invoke


class TestCliHelp:
    def test_help_shows_commands(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "add" in result.output
        assert "list" in result.output
        assert "done" in result.output
        assert "delete" in result.output

    def test_add_help(self, runner):
        result = runner.invoke(cli, ["add", "--help"])
        assert result.exit_code == 0
        assert "Aggiunge" in result.output

    def test_list_help(self, runner):
        result = runner.invoke(cli, ["list", "--help"])
        assert result.exit_code == 0

    def test_done_help(self, runner):
        result = runner.invoke(cli, ["done", "--help"])
        assert result.exit_code == 0

    def test_delete_help(self, runner):
        result = runner.invoke(cli, ["delete", "--help"])
        assert result.exit_code == 0


class TestCliAdd:
    def test_add_task_success(self, invoke_cli):
        result = invoke_cli(["add", "Nuovo task"])
        assert result.exit_code == 0
        assert "Nuovo task" in result.output

    def test_add_task_shows_checkmark(self, invoke_cli):
        result = invoke_cli(["add", "Task test"])
        assert "✅" in result.output

    def test_add_empty_title_fails(self, invoke_cli):
        result = invoke_cli(["add", ""])
        assert result.exit_code == 1

    def test_add_whitespace_title_fails(self, invoke_cli):
        result = invoke_cli(["add", "   "])
        assert result.exit_code == 1

    def test_add_multiple_tasks(self, invoke_cli):
        invoke_cli(["add", "Task 1"])
        invoke_cli(["add", "Task 2"])
        result = invoke_cli(["list"])
        assert "Task 1" in result.output
        assert "Task 2" in result.output


class TestCliList:
    def test_list_empty(self, invoke_cli):
        result = invoke_cli(["list"])
        assert result.exit_code == 0
        assert "Nessun task" in result.output

    def test_list_shows_active_tasks(self, invoke_cli):
        invoke_cli(["add", "Task attivo"])
        result = invoke_cli(["list"])
        assert "Task attivo" in result.output

    def test_list_hides_completed_by_default(self, invoke_cli):
        invoke_cli(["add", "Task da completare"])
        invoke_cli(["done", "1"])
        result = invoke_cli(["list"])
        assert "Nessun task" in result.output

    def test_list_all_shows_completed(self, invoke_cli):
        invoke_cli(["add", "Task completato"])
        invoke_cli(["done", "1"])
        result = invoke_cli(["list", "--all"])
        assert "Task completato" in result.output

    def test_list_shows_count(self, invoke_cli):
        invoke_cli(["add", "Task 1"])
        invoke_cli(["add", "Task 2"])
        result = invoke_cli(["list"])
        assert "2" in result.output


class TestCliDone:
    def test_done_existing_task(self, invoke_cli):
        invoke_cli(["add", "Task da completare"])
        result = invoke_cli(["done", "1"])
        assert result.exit_code == 0
        assert "✅" in result.output

    def test_done_nonexistent_task(self, invoke_cli):
        result = invoke_cli(["done", "999"])
        assert result.exit_code == 0
        assert "❌" in result.output
        assert "999" in result.output


class TestCliDelete:
    def test_delete_existing_task_confirmed(self, invoke_cli):
        invoke_cli(["add", "Task da eliminare"])
        result = invoke_cli(["delete", "1"], input="y\n")
        assert result.exit_code == 0
        assert "1" in result.output

    def test_delete_aborted(self, invoke_cli):
        invoke_cli(["add", "Task da mantenere"])
        invoke_cli(["delete", "1"], input="n\n")
        result = invoke_cli(["list"])
        assert "Task da mantenere" in result.output

    def test_delete_nonexistent_task(self, invoke_cli):
        result = invoke_cli(["delete", "999"], input="y\n")
        assert result.exit_code == 0
        assert "❌" in result.output

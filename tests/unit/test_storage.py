"""
Unit Test — utils/storage.py (JsonStorage)

Copertura target: 95%+
Test case:
- TC-02: Scrittura atomica (file intatto in caso di errore)
- TC-05: File corrotto → RuntimeError + backup .bak
- TC-07: Backup .bak creato correttamente
- Load da file vuoto
- Load da file con dati
- Save e reload
- Timeout lock
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from filelock import Timeout

from utils.storage import JsonStorage


class TestJsonStorageLoad:
    """Test del metodo load()."""

    def test_load_empty_file(self, storage_empty: JsonStorage):
        """File JSON vuoto deve ritornare lista vuota."""
        result = storage_empty.load()
        assert result == []

    def test_load_nonexistent_file(self, tmp_dir: Path):
        """File non esistente deve ritornare lista vuota senza errori."""
        storage = JsonStorage(filepath=str(tmp_dir / "nonexistent.json"))
        result = storage.load()
        assert result == []

    def test_load_populated_file(self, storage_populated: JsonStorage):
        """File con 3 task deve caricare tutti i task."""
        result = storage_populated.load()
        assert len(result) == 3
        assert result[0]["id"] == 1
        assert result[1]["title"] == "Secondo task"

    def test_load_preserves_all_fields(self, storage_populated: JsonStorage):
        """Tutti i campi dei task devono essere preservati dopo il load."""
        result = storage_populated.load()
        completed_tasks = [t for t in result if t["completed"]]
        assert len(completed_tasks) == 1
        assert completed_tasks[0]["id"] == 2

    # ─── TC-05: File corrotto ──────────────────────────────────────────────────

    def test_load_corrupt_file_raises_runtime_error(self, corrupt_json_file: Path):
        """[TC-05] File JSON corrotto deve sollevare RuntimeError."""
        storage = JsonStorage(filepath=str(corrupt_json_file))
        with pytest.raises(RuntimeError) as exc_info:
            storage.load()
        assert "corrotto" in str(exc_info.value).lower()

    # ─── TC-07: Backup .bak ───────────────────────────────────────────────────

    def test_load_corrupt_file_creates_backup(self, corrupt_json_file: Path):
        """[TC-07] File corrotto deve generare un backup .bak."""
        storage = JsonStorage(filepath=str(corrupt_json_file))
        backup_path = corrupt_json_file.with_suffix(".json.bak")

        with pytest.raises(RuntimeError):
            storage.load()

        assert backup_path.exists(), "Il file di backup .bak deve essere creato"

    def test_backup_contains_original_content(self, corrupt_json_file: Path):
        """[TC-07] Il backup deve contenere esattamente il contenuto originale corrotto."""
        original_content = corrupt_json_file.read_text(encoding="utf-8")
        storage = JsonStorage(filepath=str(corrupt_json_file))
        backup_path = corrupt_json_file.with_suffix(".json.bak")

        with pytest.raises(RuntimeError):
            storage.load()

        assert backup_path.read_text(encoding="utf-8") == original_content

    def test_load_non_list_json_raises_runtime_error(self, tmp_dir: Path):
        """JSON valido ma non lista (es. dizionario) deve sollevare RuntimeError."""
        path = tmp_dir / "tasks.json"
        path.write_text('{"key": "value"}', encoding="utf-8")
        storage = JsonStorage(filepath=str(path))

        with pytest.raises(RuntimeError):
            storage.load()

    def test_load_timeout_raises_runtime_error(self, locked_json_file):
        """[Lock] Timeout acquisizione lock deve sollevare RuntimeError."""
        path, _lock = locked_json_file
        storage = JsonStorage(filepath=str(path))

        with pytest.raises(RuntimeError) as exc_info:
            storage.load()
        assert "processo" in str(exc_info.value).lower()


class TestJsonStorageSave:
    """Test del metodo save()."""

    def test_save_empty_list(self, storage_empty: JsonStorage, empty_json_file: Path):
        """Salvataggio lista vuota deve produrre file JSON con []."""
        storage_empty.save([])
        content = json.loads(empty_json_file.read_text(encoding="utf-8"))
        assert content == []

    def test_save_and_reload(self, storage_empty: JsonStorage):
        """Dati salvati devono essere recuperabili con load."""
        tasks = [{"id": 1, "title": "Test", "completed": False}]
        storage_empty.save(tasks)
        reloaded = storage_empty.load()
        assert reloaded == tasks

    def test_save_utf8_characters(self, storage_empty: JsonStorage):
        """[TC-03] Caratteri speciali UTF-8 devono essere preservati."""
        tasks = [{"id": 1, "title": "Lavoro & Co. — §42", "completed": False}]
        storage_empty.save(tasks)
        reloaded = storage_empty.load()
        assert reloaded[0]["title"] == "Lavoro & Co. — §42"

    def test_save_multiple_tasks(self, storage_empty: JsonStorage):
        """Salvataggio di N task deve preservare tutti i record."""
        tasks = [{"id": i, "title": f"Task {i}", "completed": False} for i in range(1, 11)]
        storage_empty.save(tasks)
        reloaded = storage_empty.load()
        assert len(reloaded) == 10

    # ─── TC-02: Scrittura atomica ─────────────────────────────────────────────

    def test_atomic_write_original_intact_on_error(self, populated_json_file: Path):
        """[TC-02] Se la rename atomica fallisce, il file originale deve rimanere intatto."""
        storage = JsonStorage(filepath=str(populated_json_file))
        original_content = populated_json_file.read_text(encoding="utf-8")
        original_tasks = json.loads(original_content)

        # Simula errore durante il replace (rename atomica)
        with patch("pathlib.Path.replace", side_effect=OSError("Disk full")):
            with pytest.raises(OSError):
                storage.save([{"id": 99, "title": "Nuovo", "completed": False}])

        # Il file originale deve essere intatto
        current_tasks = json.loads(populated_json_file.read_text(encoding="utf-8"))
        assert current_tasks == original_tasks

    def test_atomic_write_no_temp_file_left(self, storage_empty: JsonStorage, empty_json_file: Path):
        """Dopo un salvataggio riuscito non devono restare file .tmp."""
        storage_empty.save([{"id": 1, "title": "Test", "completed": False}])
        tmp_files = list(empty_json_file.parent.glob("*.tmp"))
        assert len(tmp_files) == 0, f"File temporanei trovati: {tmp_files}"

    def test_save_timeout_raises_runtime_error(self, locked_json_file):
        """[Lock] Timeout acquisizione lock durante save deve sollevare RuntimeError."""
        path, _lock = locked_json_file
        storage = JsonStorage(filepath=str(path))

        with pytest.raises(RuntimeError) as exc_info:
            storage.save([{"id": 99, "title": "Test", "completed": False}])
        assert "processo" in str(exc_info.value).lower()

    def test_save_overwrites_previous_data(self, storage_populated: JsonStorage):
        """Il save deve sovrascrivere completamente i dati precedenti."""
        new_tasks = [{"id": 99, "title": "Solo questo", "completed": True}]
        storage_populated.save(new_tasks)
        reloaded = storage_populated.load()
        assert len(reloaded) == 1
        assert reloaded[0]["id"] == 99

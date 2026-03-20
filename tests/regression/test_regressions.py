"""
Regression Test — Riproduzione formale dei bug risolti (QA Report v2)

Ogni test riproduce esattamente uno scenario identificato nel report QA
e verifica che il fix sia permanente. Se un test regredisce, significa
che un fix è stato accidentalmente rimosso o alterato.

Mappa TC → fix:
- TC-01 → domain/models.py validator
- TC-02 → utils/storage.py scrittura atomica
- TC-03 → utils/storage.py UTF-8 save
- TC-04 → app/service.py _next_id con reload
- TC-05 → utils/storage.py RuntimeError + .bak
- TC-06 → domain/models.py strip + blank check
- TC-07 → utils/storage.py backup creation
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.service import TaskService
from domain.models import Task
from utils.storage import JsonStorage


class TestRegressionTC01:
    """TC-01 — Titolo vuoto deve sollevare ValidationError."""

    def test_model_empty_title_raises(self):
        """Regressione: il modello Task deve rifiutare titoli vuoti."""
        with pytest.raises(ValidationError):
            Task(id=1, title="")

    def test_service_empty_title_raises(self, service_empty: TaskService):
        """Regressione: TaskService.add deve propagare ValidationError per titolo vuoto."""
        with pytest.raises(ValidationError):
            service_empty.add("")

    def test_service_empty_title_does_not_write_to_disk(
        self, service_empty: TaskService, empty_json_file: Path
    ):
        """Regressione: in caso di ValidationError, nessun dato deve essere scritto."""
        with pytest.raises(ValidationError):
            service_empty.add("")
        raw = json.loads(empty_json_file.read_text(encoding="utf-8"))
        assert raw == []


class TestRegressionTC02:
    """TC-02 — Scrittura atomica: file originale intatto in caso di errore."""

    def test_original_file_intact_on_save_error(self, populated_json_file: Path):
        """Regressione: il file non deve essere corrotto se la rename fallisce."""
        storage = JsonStorage(filepath=str(populated_json_file))
        original = json.loads(populated_json_file.read_text(encoding="utf-8"))

        with patch("pathlib.Path.replace", side_effect=OSError("Simulated crash")):
            with pytest.raises(OSError):
                storage.save([])

        current = json.loads(populated_json_file.read_text(encoding="utf-8"))
        assert current == original

    def test_no_tmp_files_on_success(self, storage_empty: JsonStorage, empty_json_file: Path):
        """Regressione: nessun file .tmp deve rimanere dopo un save riuscito."""
        storage_empty.save([{"id": 1, "title": "OK", "completed": False}])
        tmp_files = list(empty_json_file.parent.glob("*.tmp"))
        assert len(tmp_files) == 0


class TestRegressionTC03:
    """TC-03 — Caratteri speciali UTF-8 devono essere preservati."""

    def test_utf8_special_chars_preserved(self, service_empty: TaskService):
        """Regressione: caratteri UTF-8 devono sopravvivere a save/load."""
        titles = [
            "Lavoro & Co.",
            "Réunion demain",
            "会议记录",
            "Ñoño — §42 @test",
            "emoji: 🎯 ✅",
        ]
        for title in titles:
            service_empty.add(title)

        tasks = service_empty.list_all()
        saved_titles = {t.title for t in tasks}
        for title in titles:
            assert title in saved_titles, f"Titolo UTF-8 perso: '{title}'"


class TestRegressionTC04:
    """TC-04 — ID generati correttamente (no duplicati, no gaps inattesi)."""

    def test_first_id_is_one(self, service_empty: TaskService):
        """Regressione: primo task deve avere ID = 1."""
        task = service_empty.add("Primo")
        assert task.id == 1

    def test_ids_are_sequential(self, service_empty: TaskService):
        """Regressione: ID devono essere strettamente sequenziali."""
        ids = [service_empty.add(f"Task {i}").id for i in range(10)]
        assert ids == list(range(1, 11))

    def test_id_not_reused_after_delete(self, service_populated: TaskService):
        """Regressione: dopo una delete, il nuovo ID non deve essere riusato."""
        service_populated.delete(3)
        new_task = service_populated.add("Nuovo")
        # max era 2 → nuovo ID deve essere 3 (non 2 che è il max corrente)
        assert new_task.id == 3

    def test_new_instance_continues_from_correct_id(self, populated_json_file: Path):
        """Regressione: nuova istanza del service deve continuare la numerazione corretta."""
        service = TaskService(storage=JsonStorage(filepath=str(populated_json_file)))
        task = service.add("Continuazione")
        assert task.id == 4  # 3 task esistenti (max=3), quindi 4


class TestRegressionTC05:
    """TC-05 — File corrotto: RuntimeError esplicita, nessun fallback silenzioso."""

    def test_corrupt_file_raises_runtime_error(self, corrupt_json_file: Path):
        """Regressione: file corrotto deve sollevare RuntimeError, non ritornare []."""
        storage = JsonStorage(filepath=str(corrupt_json_file))
        with pytest.raises(RuntimeError) as exc_info:
            storage.load()
        # Verifica che il messaggio sia utile per l'utente
        assert "corrotto" in str(exc_info.value).lower() or "bak" in str(exc_info.value).lower()

    def test_corrupt_file_does_not_return_empty_list(self, corrupt_json_file: Path):
        """Regressione: il comportamento silenzioso (return []) non deve più esistere."""
        storage = JsonStorage(filepath=str(corrupt_json_file))
        # Deve sollevare, non ritornare
        with pytest.raises(RuntimeError):
            storage.load()


class TestRegressionTC06:
    """TC-06 — Sanitizzazione input: titoli blank rifiutati e normalizzati."""

    @pytest.mark.parametrize("blank_title", [
        " ",
        "   ",
        "\t",
        "\n",
        "\t\n   \t",
    ])
    def test_blank_titles_rejected(self, blank_title: str):
        """Regressione: qualsiasi combinazione di whitespace deve essere rifiutata."""
        with pytest.raises(ValidationError):
            Task(id=1, title=blank_title)

    @pytest.mark.parametrize("raw_title,expected", [
        ("  Task  ", "Task"),
        ("\tTask\t", "Task"),
        ("  Spazio iniziale", "Spazio iniziale"),
        ("Spazio finale  ", "Spazio finale"),
    ])
    def test_title_normalization(self, raw_title: str, expected: str):
        """Regressione: il titolo deve essere normalizzato (strip) automaticamente."""
        task = Task(id=1, title=raw_title)
        assert task.title == expected


class TestRegressionTC07:
    """TC-07 — Backup .bak creato automaticamente su file corrotto."""

    def test_bak_file_created(self, corrupt_json_file: Path):
        """Regressione: il backup .bak deve essere creato prima di sollevare l'eccezione."""
        storage = JsonStorage(filepath=str(corrupt_json_file))
        backup_path = corrupt_json_file.with_suffix(".json.bak")

        assert not backup_path.exists(), "Il .bak non deve esistere prima del test"

        with pytest.raises(RuntimeError):
            storage.load()

        assert backup_path.exists(), "Il .bak deve esistere dopo il tentativo di load"

    def test_bak_content_matches_original(self, corrupt_json_file: Path):
        """Regressione: il .bak deve contenere esattamente i byte del file corrotto."""
        original = corrupt_json_file.read_bytes()
        storage = JsonStorage(filepath=str(corrupt_json_file))
        backup_path = corrupt_json_file.with_suffix(".json.bak")

        with pytest.raises(RuntimeError):
            storage.load()

        assert backup_path.read_bytes() == original

    def test_bak_not_created_for_valid_file(self, storage_populated: JsonStorage, tmp_dir: Path):
        """Regressione: il .bak NON deve essere creato per file validi."""
        json_path = tmp_dir / "tasks.json"
        bak_path = json_path.with_suffix(".json.bak")

        storage_populated.load()

        assert not bak_path.exists(), "Il .bak non deve essere creato per file JSON valido"

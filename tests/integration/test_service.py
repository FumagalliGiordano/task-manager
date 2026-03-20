"""
Integration Test — app/service.py + utils/storage.py

Copertura target: 90%+
Usa file system reale (temporaneo) — nessun mock.

Test case:
- TC-04: Generazione ID univoci e sequenziali
- Flusso completo add → list → complete → delete
- Persistenza tra istanze diverse di TaskService
- Reload-before-write (dati freschi da disco)
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.service import TaskService
from domain.models import Task
from utils.storage import JsonStorage


class TestTaskServiceAdd:
    """Test del metodo add()."""

    def test_add_returns_task(self, service_empty: TaskService):
        """add deve restituire un oggetto Task valido."""
        task = service_empty.add("Nuovo task")
        assert isinstance(task, Task)
        assert task.title == "Nuovo task"
        assert task.completed is False

    def test_add_persists_to_disk(self, service_empty: TaskService, empty_json_file: Path):
        """Il task aggiunto deve essere scritto sul file JSON."""
        service_empty.add("Task persistente")
        raw = json.loads(empty_json_file.read_text(encoding="utf-8"))
        assert len(raw) == 1
        assert raw[0]["title"] == "Task persistente"

    def test_add_multiple_tasks(self, service_empty: TaskService):
        """Aggiungere N task deve risultare in N record persistiti."""
        for i in range(5):
            service_empty.add(f"Task {i}")
        tasks = service_empty.list_all()
        assert len(tasks) == 5

    def test_add_strips_whitespace_title(self, service_empty: TaskService):
        """[TC-06] Il titolo deve essere normalizzato (strip) prima del salvataggio."""
        task = service_empty.add("  Task con spazi  ")
        assert task.title == "Task con spazi"

    def test_add_empty_title_raises_validation_error(self, service_empty: TaskService):
        """[TC-01] Titolo vuoto deve sollevare ValidationError."""
        with pytest.raises(ValidationError):
            service_empty.add("")

    def test_add_whitespace_title_raises_validation_error(self, service_empty: TaskService):
        """[TC-06] Titolo di soli spazi deve sollevare ValidationError."""
        with pytest.raises(ValidationError):
            service_empty.add("   ")

    # ─── TC-04: Generazione ID ────────────────────────────────────────────────

    def test_add_first_task_gets_id_1(self, service_empty: TaskService):
        """[TC-04] Il primo task su storage vuoto deve avere ID = 1."""
        task = service_empty.add("Primo")
        assert task.id == 1

    def test_add_sequential_ids(self, service_empty: TaskService):
        """[TC-04] I task aggiunti devono avere ID sequenziali."""
        ids = [service_empty.add(f"Task {i}").id for i in range(5)]
        assert ids == list(range(1, 6))

    def test_add_id_after_existing_tasks(self, service_populated: TaskService):
        """[TC-04] Il nuovo task deve avere ID = max(esistenti) + 1."""
        task = service_populated.add("Quarto task")
        assert task.id == 4  # I task esistenti hanno ID 1, 2, 3

    def test_add_id_continues_after_delete(self, service_populated: TaskService):
        """[TC-04] Dopo una delete, il nuovo ID non riusa il vecchio ID."""
        service_populated.delete(3)
        task = service_populated.add("Nuovo dopo delete")
        assert task.id == 3  # max era 2, quindi 3


class TestTaskServiceList:
    """Test del metodo list_all()."""

    def test_list_empty_storage(self, service_empty: TaskService):
        """Su storage vuoto deve ritornare lista vuota."""
        assert service_empty.list_all() == []

    def test_list_returns_all_tasks(self, service_populated: TaskService):
        """Deve ritornare tutti i task inclusi i completati."""
        tasks = service_populated.list_all()
        assert len(tasks) == 3

    def test_list_returns_task_objects(self, service_populated: TaskService):
        """list_all deve restituire istanze Task (non dict raw)."""
        tasks = service_populated.list_all()
        assert all(isinstance(t, Task) for t in tasks)

    def test_list_reflects_disk_state(self, populated_json_file: Path):
        """
        list_all deve leggere SEMPRE da disco.
        Modifica esterna al file deve essere visibile alla chiamata successiva.
        """
        service = TaskService(storage=JsonStorage(filepath=str(populated_json_file)))
        original = service.list_all()
        assert len(original) == 3

        # Modifica esterna al file (simula altro processo)
        raw = json.loads(populated_json_file.read_text())
        raw.append({"id": 99, "title": "Aggiunto esternamente", "completed": False})
        populated_json_file.write_text(json.dumps(raw))

        # La nuova chiamata deve vedere il task aggiunto esternamente
        updated = service.list_all()
        assert len(updated) == 4
        assert any(t.id == 99 for t in updated)


class TestTaskServiceComplete:
    """Test del metodo complete()."""

    def test_complete_existing_task(self, service_populated: TaskService):
        """Completare un task esistente deve impostare completed=True."""
        task = service_populated.complete(1)
        assert task is not None
        assert task.completed is True

    def test_complete_nonexistent_task_returns_none(self, service_populated: TaskService):
        """[TC-02] Task inesistente deve ritornare None."""
        result = service_populated.complete(999)
        assert result is None

    def test_complete_persists_to_disk(self, service_populated: TaskService, populated_json_file: Path):
        """Lo stato completato deve essere scritto su disco."""
        service_populated.complete(1)
        raw = json.loads(populated_json_file.read_text(encoding="utf-8"))
        task1 = next(t for t in raw if t["id"] == 1)
        assert task1["completed"] is True

    def test_complete_already_completed_task(self, service_populated: TaskService):
        """Completare un task già completato non deve causare errori."""
        task = service_populated.complete(2)  # Task 2 è già completed=True
        assert task is not None
        assert task.completed is True

    def test_complete_preserves_other_tasks(self, service_populated: TaskService, populated_json_file: Path):
        """Completare un task non deve alterare gli altri task."""
        service_populated.complete(1)
        raw = json.loads(populated_json_file.read_text(encoding="utf-8"))
        task3 = next(t for t in raw if t["id"] == 3)
        assert task3["completed"] is False


class TestTaskServiceDelete:
    """Test del metodo delete()."""

    def test_delete_existing_task_returns_true(self, service_populated: TaskService):
        """Eliminare un task esistente deve ritornare True."""
        result = service_populated.delete(1)
        assert result is True

    def test_delete_nonexistent_task_returns_false(self, service_populated: TaskService):
        """Eliminare un task non esistente deve ritornare False."""
        result = service_populated.delete(999)
        assert result is False

    def test_delete_removes_from_disk(self, service_populated: TaskService, populated_json_file: Path):
        """Il task eliminato non deve essere presente nel file JSON."""
        service_populated.delete(2)
        raw = json.loads(populated_json_file.read_text(encoding="utf-8"))
        ids = [t["id"] for t in raw]
        assert 2 not in ids

    def test_delete_preserves_other_tasks(self, service_populated: TaskService, populated_json_file: Path):
        """Eliminare un task non deve alterare gli altri task."""
        service_populated.delete(2)
        raw = json.loads(populated_json_file.read_text(encoding="utf-8"))
        assert len(raw) == 2
        ids = [t["id"] for t in raw]
        assert 1 in ids and 3 in ids

    def test_delete_all_tasks(self, service_populated: TaskService):
        """Eliminare tutti i task deve lasciare lo storage vuoto."""
        for task_id in [1, 2, 3]:
            service_populated.delete(task_id)
        assert service_populated.list_all() == []


class TestTaskServicePersistenceBetweenInstances:
    """
    Test di persistenza cross-istanza:
    verifica che due istanze diverse di TaskService sullo stesso file
    vedano i dati reciproci (no cache in memoria).
    """

    def test_add_visible_to_second_instance(self, empty_json_file: Path):
        """Task aggiunto da istanza A deve essere visibile all'istanza B."""
        service_a = TaskService(storage=JsonStorage(filepath=str(empty_json_file)))
        service_b = TaskService(storage=JsonStorage(filepath=str(empty_json_file)))

        service_a.add("Task da A")

        tasks_b = service_b.list_all()
        assert len(tasks_b) == 1
        assert tasks_b[0].title == "Task da A"

    def test_complete_visible_to_second_instance(self, populated_json_file: Path):
        """Completamento da istanza A deve essere visibile all'istanza B."""
        service_a = TaskService(storage=JsonStorage(filepath=str(populated_json_file)))
        service_b = TaskService(storage=JsonStorage(filepath=str(populated_json_file)))

        service_a.complete(1)

        tasks_b = service_b.list_all()
        task1 = next(t for t in tasks_b if t.id == 1)
        assert task1.completed is True

    def test_delete_visible_to_second_instance(self, populated_json_file: Path):
        """Eliminazione da istanza A deve essere visibile all'istanza B."""
        service_a = TaskService(storage=JsonStorage(filepath=str(populated_json_file)))
        service_b = TaskService(storage=JsonStorage(filepath=str(populated_json_file)))

        service_a.delete(2)

        tasks_b = service_b.list_all()
        ids = [t.id for t in tasks_b]
        assert 2 not in ids

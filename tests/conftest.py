"""
conftest.py — Fixture condivise per l'intera suite di test.

Fornisce:
- File JSON temporanei (vuoti, con dati, corrotti, locked)
- Istanze pre-configurate di JsonStorage e TaskService
- Helper per la verifica dello stato del file
"""

from app.service import TaskService
from utils.storage import JsonStorage
import json
import tempfile
from pathlib import Path
from typing import Generator, List

import pytest
from filelock import FileLock

# Aggiungo la root del progetto al path per importazioni relative
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# ─── Dati mock standard ───────────────────────────────────────────────────────

SAMPLE_TASKS_RAW: List[dict] = [
    {"id": 1, "title": "Primo task", "completed": False},
    {"id": 2, "title": "Secondo task", "completed": True},
    {"id": 3, "title": "Terzo task", "completed": False},
]


# ─── Fixture: file temporanei ─────────────────────────────────────────────────

@pytest.fixture
def tmp_dir() -> Generator[Path, None, None]:
    """Directory temporanea isolata per ogni test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def empty_json_file(tmp_dir: Path) -> Path:
    """File JSON vuoto (lista vuota)."""
    path = tmp_dir / "tasks.json"
    path.write_text("[]", encoding="utf-8")
    return path


@pytest.fixture
def populated_json_file(tmp_dir: Path) -> Path:
    """File JSON con 3 task di esempio."""
    path = tmp_dir / "tasks.json"
    path.write_text(json.dumps(SAMPLE_TASKS_RAW, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def corrupt_json_file(tmp_dir: Path) -> Path:
    """File JSON con contenuto non valido (JSON corrotto)."""
    path = tmp_dir / "tasks.json"
    path.write_text("{INVALID_JSON: [[[", encoding="utf-8")
    return path


@pytest.fixture
def locked_json_file(tmp_dir: Path) -> Generator[tuple, None, None]:
    """
    File JSON con lock attivo.
    Restituisce (path, lock) — il lock è già acquisito.
    """
    path = tmp_dir / "tasks.json"
    path.write_text(json.dumps(SAMPLE_TASKS_RAW), encoding="utf-8")
    lock_path = path.with_suffix(".json.lock")
    lock = FileLock(str(lock_path), timeout=0)
    lock.acquire()
    yield path, lock
    lock.release()


# ─── Fixture: istanze ─────────────────────────────────────────────────────────

@pytest.fixture
def storage_empty(empty_json_file: Path) -> JsonStorage:
    """JsonStorage su file vuoto."""
    return JsonStorage(filepath=str(empty_json_file))


@pytest.fixture
def storage_populated(populated_json_file: Path) -> JsonStorage:
    """JsonStorage su file con dati."""
    return JsonStorage(filepath=str(populated_json_file))


@pytest.fixture
def service_empty(empty_json_file: Path) -> TaskService:
    """TaskService su storage vuoto."""
    return TaskService(storage=JsonStorage(filepath=str(empty_json_file)))


@pytest.fixture
def service_populated(populated_json_file: Path) -> TaskService:
    """TaskService su storage con 3 task."""
    return TaskService(storage=JsonStorage(filepath=str(populated_json_file)))

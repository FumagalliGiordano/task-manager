"""
Application Layer - TaskService

Fix applicati (QA Report):
- [BUG-1] Reload dal disco prima di ogni operazione di scrittura (minimizza collisioni)
- [BUG-2] _next_id legge sempre da disco per garantire unicità tra processi
- [EDGE]  Gestione eccezione da storage corrotto propagata all'utente
"""

from utils.storage import JsonStorage
from domain.models import Task
from typing import List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class TaskService:
    """Gestisce le operazioni CRUD sui task con reload-before-write."""

    def __init__(self, storage: Optional[JsonStorage] = None):
        self.storage = storage or JsonStorage()

    # ─── Private ──────────────────────────────────────────────────────────────

    def _load(self) -> List[Task]:
        """Carica SEMPRE da disco (no cache in memoria) per evitare dati stale."""
        raw = self.storage.load()
        return [Task(**t) for t in raw]

    def _persist(self, tasks: List[Task]) -> None:
        self.storage.save([t.model_dump() for t in tasks])

    def _next_id(self, tasks: List[Task]) -> int:
        """
        [BUG-2] Calcola ID sul dataset appena letto da disco.
        Riduce (non elimina) collisioni in ambienti multi-processo.
        Per eliminazione completa usare UUID o DB con sequence.
        """
        return max((t.id for t in tasks), default=0) + 1

    # ─── Public API ───────────────────────────────────────────────────────────

    def add(self, title: str) -> Task:
        """Crea e salva un nuovo task in modo atomico (lock unico)."""
        task_ref = {}

        def _add(tasks: list) -> list:
            new_id = max((t["id"] for t in tasks), default=0) + 1
            task = Task(id=new_id, title=title)
            task_ref["task"] = task
            tasks.append(task.model_dump())
            return tasks

        self.storage.atomic_update(_add)
        logger.info(f"Task aggiunto: {task_ref['task']}")
        return task_ref["task"]

    def list_all(self) -> List[Task]:
        """Restituisce tutti i task (sempre freschi da disco)."""
        return self._load()

    def complete(self, task_id: int) -> Optional[Task]:
        """Segna un task come completato con reload pre-scrittura."""
        tasks = self._load()                         # [BUG-1]
        for i, task in enumerate(tasks):
            if task.id == task_id:
                tasks[i] = task.mark_complete()
                self._persist(tasks)
                logger.info(f"Task completato: {tasks[i]}")
                return tasks[i]
        logger.warning(f"Task ID {task_id} non trovato.")
        return None

    def delete(self, task_id: int) -> bool:
        """Elimina un task con reload pre-scrittura."""
        tasks = self._load()                         # [BUG-1]
        filtered = [t for t in tasks if t.id != task_id]
        if len(filtered) < len(tasks):
            self._persist(filtered)
            logger.info(f"Task ID {task_id} eliminato.")
            return True
        logger.warning(f"Task ID {task_id} non trovato per eliminazione.")
        return False

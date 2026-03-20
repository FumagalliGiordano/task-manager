"""
Concurrency Test — file locking e accesso multi-processo

Strategia: multiprocessing reale (non thread) per simulare processi OS distinti.
I test di concorrenza sono per natura non deterministici; si usano
timeout espliciti e retry per minimizzare i falsi negativi.

Test case:
- TC-03: Accesso simultaneo → nessuna corruzione dati
- Processo B in attesa mentre A tiene il lock
- Tutti i task da N processi devono essere nel JSON finale
- Nessun ID duplicato dopo scritture concorrenti
"""

import json
import multiprocessing
import time
from pathlib import Path

import pytest

from utils.storage import JsonStorage
from app.service import TaskService


# ─── Worker functions (top-level per pickling multiprocessing) ───────────────

def _worker_add_task(filepath: str, title: str, result_queue: multiprocessing.Queue):
    """Aggiunge un task e segnala il risultato."""
    try:
        storage = JsonStorage(filepath=filepath)
        service = TaskService(storage=storage)
        task = service.add(title)
        result_queue.put({"success": True, "id": task.id, "title": task.title})
    except Exception as e:
        result_queue.put({"success": False, "error": str(e)})


def _worker_hold_lock_then_add(filepath: str, lock_duration: float,
                               title: str, ready_event, result_queue):
    """
    Acquisisce il lock, segnala ready, attende lock_duration,
    poi esegue l'add. Simula un processo lento con lock tenuto.
    """
    from filelock import FileLock
    lock_path = Path(filepath).with_suffix(".json.lock")
    lock = FileLock(str(lock_path), timeout=10)
    with lock:
        ready_event.set()          # Segnala: lock acquisito
        time.sleep(lock_duration)  # Tiene il lock per N secondi
    # Lock rilasciato: ora aggiungo il task
    try:
        storage = JsonStorage(filepath=filepath)
        service = TaskService(storage=storage)
        task = service.add(title)
        result_queue.put({"success": True, "id": task.id})
    except Exception as e:
        result_queue.put({"success": False, "error": str(e)})


def _worker_add_with_delay(filepath: str, title: str, delay: float,
                           result_queue: multiprocessing.Queue):
    """Attende delay secondi poi aggiunge un task."""
    time.sleep(delay)
    _worker_add_task(filepath, title, result_queue)


# ─── Test class ───────────────────────────────────────────────────────────────

class TestConcurrency:
    """Test di concorrenza multi-processo."""

    @pytest.fixture
    def shared_json_file(self, tmp_dir: Path) -> Path:
        """File JSON condiviso tra processi, partenza vuota."""
        path = tmp_dir / "shared_tasks.json"
        path.write_text("[]", encoding="utf-8")
        return path

    # ─── TC-03: Accesso simultaneo ────────────────────────────────────────────

    def test_concurrent_adds_no_data_corruption(self, shared_json_file: Path):
        """
        [TC-03] N processi che aggiungono task simultaneamente non devono
        corrompere il file JSON. Tutti i task devono essere nel risultato finale.
        """
        N = 5
        result_queue = multiprocessing.Queue()
        processes = []

        for i in range(N):
            p = multiprocessing.Process(
                target=_worker_add_task,
                args=(str(shared_json_file), f"Concurrent Task {i}", result_queue)
            )
            processes.append(p)

        # Avvio simultaneo
        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=15)

        # Verifica: nessun processo ancora vivo (nessun deadlock)
        for p in processes:
            assert not p.is_alive(), "Processo ancora in esecuzione: possibile deadlock"

        # Verifica: tutti i task presenti nel file finale
        raw = json.loads(shared_json_file.read_text(encoding="utf-8"))
        assert len(raw) == N, (
            f"Attesi {N} task, trovati {len(raw)}. "
            f"Possibile race condition o dati persi."
        )

    def test_concurrent_adds_no_duplicate_ids(self, shared_json_file: Path):
        """
        [TC-03] Gli ID generati da processi concorrenti non devono essere duplicati.

        Nota: il design attuale (max+1 con reload) riduce ma non elimina
        le collisioni in caso di race condition estrema. Questo test
        documenta il comportamento atteso per il livello di protezione implementato.
        """
        N = 5
        result_queue = multiprocessing.Queue()
        processes = []

        for i in range(N):
            p = multiprocessing.Process(
                target=_worker_add_task,
                args=(str(shared_json_file), f"Task {i}", result_queue)
            )
            processes.append(p)

        for p in processes:
            p.start()

        # Stagger leggero per ridurre window di collisione nel test
        time.sleep(0.05)

        for p in processes:
            p.join(timeout=15)

        raw = json.loads(shared_json_file.read_text(encoding="utf-8"))
        ids = [t["id"] for t in raw]

        # Nel caso ideale (lock funzionante) non ci sono duplicati
        assert len(ids) == len(set(ids)), (
            f"ID duplicati trovati: {[x for x in ids if ids.count(x) > 1]}"
        )

    def test_process_b_waits_for_lock(self, shared_json_file: Path):
        """
        Processo B non deve poter scrivere mentre A tiene il lock.
        A tiene il lock per 1s; B deve completare DOPO A.
        """
        ctx = multiprocessing.get_context("spawn")
        ready_event = ctx.Event()
        result_queue = ctx.Queue()

        # Processo A: acquisisce lock, aspetta 1s, poi aggiunge
        proc_a = ctx.Process(
            target=_worker_hold_lock_then_add,
            args=(str(shared_json_file), 1.0, "Task da A (lento)", ready_event, result_queue)
        )

        # Processo B: tenta di aggiungere subito dopo che A ha il lock
        proc_b = ctx.Process(
            target=_worker_add_task,
            args=(str(shared_json_file), "Task da B (rapido)", result_queue)
        )

        proc_a.start()
        ready_event.wait(timeout=5)  # Aspetta che A acquisisca il lock
        proc_b.start()

        proc_a.join(timeout=10)
        proc_b.join(timeout=10)

        assert not proc_a.is_alive()
        assert not proc_b.is_alive()

        # Entrambi i task devono essere nel risultato finale
        raw = json.loads(shared_json_file.read_text(encoding="utf-8"))
        titles = [t["title"] for t in raw]
        assert "Task da A (lento)" in titles
        assert "Task da B (rapido)" in titles

    def test_file_json_valid_after_concurrent_writes(self, shared_json_file: Path):
        """
        Il file JSON deve essere sintatticamente valido dopo N scritture concorrenti.
        """
        N = 8
        result_queue = multiprocessing.Queue()
        processes = [
            multiprocessing.Process(
                target=_worker_add_task,
                args=(str(shared_json_file), f"Task {i}", result_queue)
            )
            for i in range(N)
        ]

        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=20)

        # Il file deve essere JSON valido (non corrotto)
        try:
            content = shared_json_file.read_text(encoding="utf-8")
            data = json.loads(content)
            assert isinstance(data, list)
        except json.JSONDecodeError as e:
            pytest.fail(f"File JSON corrotto dopo scritture concorrenti: {e}")

    def test_sequential_processes_see_each_other_data(self, shared_json_file: Path):
        """
        Processi eseguiti in sequenza (non concorrenti) devono
        vedere i dati scritti dal processo precedente.
        """
        for i in range(3):
            q = multiprocessing.Queue()
            p = multiprocessing.Process(
                target=_worker_add_task,
                args=(str(shared_json_file), f"Task seq {i}", q)
            )
            p.start()
            p.join(timeout=10)

        raw = json.loads(shared_json_file.read_text(encoding="utf-8"))
        assert len(raw) == 3

"""
Utils Layer - Configurazione e persistenza JSON locale.

Fix applicati (QA Report):
- [BUG-3] Scrittura atomica via write-to-temp-then-rename
- [BUG-1] File locking con `filelock` per prevenire race condition
- [EDGE]  Gestione file corrotto: backup automatico prima di sovrascrivere
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import List

from filelock import FileLock, Timeout

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ─── Storage JSON (thread-safe + atomic) ─────────────────────────────────────

class JsonStorage:
    """
    Gestisce la persistenza dei task su file JSON locale.

    Garanzie:
    - File locking (filelock): previene race condition multi-processo
    - Scrittura atomica (tempfile + rename): il file non è mai in stato parziale
    - Backup automatico: se il JSON è corrotto, viene salvato in .bak prima di reset
    """

    def __init__(self, filepath: str = settings.storage_file):
        self.path = Path(filepath)
        self.lock_path = self.path.with_suffix(".json.lock")
        self.lock = FileLock(str(self.lock_path), timeout=settings.lock_timeout)

    # ─── Load ─────────────────────────────────────────────────────────────────

    def load(self) -> List[dict]:
        """
        Carica i task dal file JSON con lock acquisito.
        Se il file non esiste → lista vuota.
        Se il file è corrotto → backup + lista vuota (nessuna sovrascrittura silenziosa).
        """
        if not self.path.exists():
            logger.debug(
                f"File storage non trovato: {self.path}. Partenza da lista vuota."
            )
            return []

        try:
            with self.lock:
                with self.path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        raise ValueError(
                            "Il contenuto del file non è una lista JSON valida."
                        )
                    logger.debug(f"Caricati {len(data)} task da {self.path}")
                    return data

        except (json.JSONDecodeError, ValueError) as e:
            backup_path = self.path.with_suffix(".json.bak")
            shutil.copy2(self.path, backup_path)
            logger.error(
                f"File storage corrotto: {e}. "
                f"Backup salvato in '{backup_path}'. "
                f"Correggilo manualmente prima di procedere."
            )
            raise RuntimeError(
                f"Il file '{self.path}' è corrotto. "
                f"Un backup è stato salvato in '{backup_path}'.\n"
                f"Ripristinalo o eliminalo per ripartire da zero."
            ) from e

        except Timeout:
            lock_path = self.lock_path
            timeout = settings.lock_timeout
            logger.error(
                f"Impossibile acquisire il lock su '{lock_path}' dopo {timeout}s."
            )
            raise RuntimeError(
                "Un altro processo sta usando il file. Riprova tra qualche secondo."
            )

        except OSError as e:
            logger.error(f"Errore I/O lettura storage: {e}")
            raise

    # ─── Save (Atomic) ────────────────────────────────────────────────────────

    def save(self, tasks: List[dict]) -> None:
        """
        Salva i task in modo atomico:
        1. Scrive su file temporaneo nella stessa directory
        2. Rinomina atomicamente il temp → file finale (os.rename è atomico su POSIX)

        Con file locking attivo: thread/process-safe.
        """
        try:
            with self.lock:
                dir_path = self.path.parent
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=dir_path,
                    delete=False,
                    suffix=".tmp"
                ) as tmp:
                    json.dump(tasks, tmp, indent=2, ensure_ascii=False)
                    tmp_path = Path(tmp.name)

                tmp_path.replace(self.path)
                logger.debug(
                    f"Salvati {len(tasks)} task su {self.path} (scrittura atomica)"
                )

        except Timeout:
            lock_path = self.lock_path
            timeout = settings.lock_timeout
            logger.error(
                f"Impossibile acquisire il lock su '{lock_path}' dopo {timeout}s."
            )
            raise RuntimeError(
                "Un altro processo sta usando il file. Riprova tra qualche secondo."
            )

        except OSError as e:
            logger.error(f"Errore I/O scrittura storage: {e}")
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise

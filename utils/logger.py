"""
Logging strutturato — loguru con sink JSON (prod) o testo (dev/test)

Utilizzo:
  from utils.logger import get_logger
  logger = get_logger(__name__)
  logger.info("Task aggiunto", task_id=1, title="...")   # log con contesto
  logger.bind(user="admin").info("Azione privilegiata")

Formato JSON (prod/quando LOG_FORMAT=json):
  {
    "timestamp": "2026-03-19T10:00:00.000Z",
    "level": "INFO",
    "module": "app.service",
    "function": "add",
    "line": 42,
    "message": "Task aggiunto",
    "extra": {"task_id": 1}
  }

Formato testo (dev):
  10:00:00 | INFO     | app.service:add:42 - Task aggiunto
"""

import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger as _loguru_logger

from config.settings import settings

# ─── Formato JSON strutturato ─────────────────────────────────────────────────

def _json_formatter(record: dict) -> str:
    """
    Serializza il record di log in JSON su una singola riga.
    Compatibile con log aggregator (ELK, Loki, CloudWatch).
    """
    log_entry = {
        "timestamp": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "level": record["level"].name,
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
    }
    # Aggiunge campi extra (es. task_id, user, env)
    if record["extra"]:
        log_entry["extra"] = record["extra"]
    if record["exception"]:
        log_entry["exception"] = str(record["exception"])

    return json.dumps(log_entry, ensure_ascii=False) + "\n"


# ─── Formato testo human-readable ─────────────────────────────────────────────

_TEXT_FORMAT = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "{message}"
)

# ─── Setup sink ───────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    """Configura loguru in base a settings. Chiamato una volta all'avvio."""
    _loguru_logger.remove()  # Rimuove handler di default

    use_json = settings.log_format == "json"

    # ── Sink console (stderr) ─────────────────────────────────────────────────
    if use_json:
        _loguru_logger.add(
            sys.stderr,
            level=settings.log_level,
            format=_json_formatter,
            colorize=False,
        )
    else:
        _loguru_logger.add(
            sys.stderr,
            level=settings.log_level,
            format=_TEXT_FORMAT,
            colorize=True,
        )

    # ── Sink file (opzionale) ─────────────────────────────────────────────────
    if settings.log_file_enabled:
        _loguru_logger.add(
            settings.log_file,
            level="DEBUG",                # Su file sempre DEBUG completo
            format=_json_formatter if use_json else _TEXT_FORMAT,
            rotation="1 MB",
            retention="7 days",
            encoding="utf-8",
            colorize=False,
        )

    # Aggiunge sempre l'ambiente attivo come campo extra globale
    _loguru_logger.configure(extra={"env": settings.env})


# Inizializza al momento dell'import del modulo
_setup_logging()


# ─── API pubblica ─────────────────────────────────────────────────────────────

def get_logger(name: str = "app") -> Any:
    """
    Ritorna un logger contestualizzato con il nome del modulo.

    Uso consigliato:
      from utils.logger import get_logger
      logger = get_logger(__name__)
    """
    return _loguru_logger.bind(module_name=name)


# Logger di default (compatibilità con import diretti)
logger = get_logger("app")

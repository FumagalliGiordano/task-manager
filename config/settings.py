"""
Config Layer — Configurazione multi-ambiente (dev / test / prod)

Strategia:
  1. Legge APP_ENV da variabile d'ambiente (default: "dev")
  2. Carica il file .env.<ambiente> se presente (via python-dotenv)
  3. Espone un'istanza singleton `settings` già risolta

Utilizzo:
  from config.settings import settings
  print(settings.storage_file)
  print(settings.env)

Variabili d'ambiente supportate:
  APP_ENV             → "dev" | "test" | "prod"  (default: "dev")
  STORAGE_FILE        → path del file JSON
  LOG_LEVEL           → "DEBUG" | "INFO" | "WARNING" | "ERROR"
  LOG_FORMAT          → "text" | "json"
  LOCK_TIMEOUT        → float in secondi
  LOG_FILE            → path del file di log (vuoto = disabilitato)
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root del progetto (directory che contiene questa cartella)
PROJECT_ROOT = Path(__file__).parent.parent


def _resolve_env_file() -> Path:
    """Risolve il file .env corretto in base ad APP_ENV."""
    env = os.getenv("APP_ENV", "dev").lower()
    candidate = PROJECT_ROOT / f".env.{env}"
    if candidate.exists():
        return candidate
    # Fallback: .env generico
    fallback = PROJECT_ROOT / ".env"
    return fallback if fallback.exists() else candidate


class Settings(BaseSettings):
    """
    Configurazione centralizzata dell'applicazione.
    I valori vengono letti (in ordine di priorità):
      1. Variabili d'ambiente di sistema
      2. File .env.<APP_ENV>
      3. Valori default qui sotto
    """

    model_config = SettingsConfigDict(
        env_file=str(_resolve_env_file()),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Ambiente ─────────────────────────────────────────────────────────────
    env: Literal["dev", "test", "prod"] = Field(
        default="dev",
        alias="APP_ENV",
        description="Ambiente attivo",
    )

    # ─── Storage ──────────────────────────────────────────────────────────────
    storage_file: str = Field(
        default="tasks.json",
        description="Path del file JSON per la persistenza",
    )
    lock_timeout: float = Field(
        default=5.0,
        gt=0,
        description="Secondi massimi per acquisire il file lock",
    )

    # ─── Logging ──────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Livello minimo di log",
    )
    log_format: Literal["text", "json"] = Field(
        default="text",
        description="Formato output log: testo umano o JSON strutturato",
    )
    log_file: str = Field(
        default="task_manager.log",
        description="Path file di log. Stringa vuota = log su file disabilitato",
    )

    @field_validator("env", mode="before")
    @classmethod
    def normalize_env(cls, v: str) -> str:
        return v.lower().strip()

    # ─── Proprietà derivate ───────────────────────────────────────────────────

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"

    @property
    def is_test(self) -> bool:
        return self.env == "test"

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @property
    def log_file_enabled(self) -> bool:
        return bool(self.log_file.strip())


# ─── Singleton ────────────────────────────────────────────────────────────────
# Importa questo in tutti i moduli che necessitano di configurazione.
settings = Settings()

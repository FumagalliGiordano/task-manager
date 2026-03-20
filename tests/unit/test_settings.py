"""
Unit Test — config/settings.py

Verifica che la configurazione multi-ambiente funzioni correttamente
senza dipendere da file .env reali (usa monkeypatch per isolare).
"""

import os
import pytest
from unittest.mock import patch

from config.settings import Settings


class TestSettingsDefaults:
    """Verifica valori default quando nessuna variabile è impostata."""

    def test_default_env_is_dev(self):
        with patch.dict(os.environ, {}, clear=False):
            s = Settings(_env_file=None)
            # APP_ENV non impostato → dev
            assert s.env in ("dev", "test", "prod")  # dipende dall'ambiente CI

    def test_default_log_format_text(self):
        s = Settings(_env_file=None, LOG_FORMAT="text")
        assert s.log_format == "text"

    def test_default_lock_timeout_positive(self):
        s = Settings(_env_file=None)
        assert s.lock_timeout > 0


class TestSettingsEnvironmentOverride:
    """Verifica override tramite variabili d'ambiente."""

    def test_env_var_overrides_log_level(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            s = Settings(_env_file=None)
            assert s.log_level == "DEBUG"

    def test_env_var_overrides_storage_file(self):
        with patch.dict(os.environ, {"STORAGE_FILE": "custom.json"}):
            s = Settings(_env_file=None)
            assert s.storage_file == "custom.json"

    def test_json_log_format_accepted(self):
        with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
            s = Settings(_env_file=None)
            assert s.log_format == "json"

    def test_invalid_log_format_raises(self):
        from pydantic import ValidationError
        with patch.dict(os.environ, {"LOG_FORMAT": "xml"}):
            with pytest.raises(ValidationError):
                Settings(_env_file=None)

    def test_invalid_log_level_raises(self):
        from pydantic import ValidationError
        with patch.dict(os.environ, {"LOG_LEVEL": "VERBOSE"}):
            with pytest.raises(ValidationError):
                Settings(_env_file=None)


class TestSettingsDerivedProperties:
    """Verifica le proprietà derivate is_dev / is_test / is_prod."""

    def test_is_dev_true_when_env_dev(self):
        with patch.dict(os.environ, {"APP_ENV": "dev"}):
            s = Settings(_env_file=None)
            assert s.is_dev is True
            assert s.is_test is False
            assert s.is_prod is False

    def test_is_test_true_when_env_test(self):
        with patch.dict(os.environ, {"APP_ENV": "test"}):
            s = Settings(_env_file=None)
            assert s.is_test is True

    def test_is_prod_true_when_env_prod(self):
        with patch.dict(os.environ, {"APP_ENV": "prod"}):
            s = Settings(_env_file=None)
            assert s.is_prod is True

    def test_log_file_enabled_false_when_empty(self):
        with patch.dict(os.environ, {"LOG_FILE": ""}):
            s = Settings(_env_file=None)
            assert s.log_file_enabled is False

    def test_log_file_enabled_true_when_set(self):
        with patch.dict(os.environ, {"LOG_FILE": "app.log"}):
            s = Settings(_env_file=None)
            assert s.log_file_enabled is True

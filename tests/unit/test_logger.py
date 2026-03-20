"""
Unit Test — utils/logger.py

Verifica i due formati di output (text e json) e il sink su file.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch


class TestLoggerJsonFormat:
    """Test del formatter JSON strutturato."""

    def test_json_formatter_produces_valid_json(self):
        """Il formatter JSON deve produrre una riga JSON valida."""
        with patch.dict(os.environ, {"LOG_FORMAT": "json", "LOG_FILE": ""}):
            # Reimporta il modulo con la nuova config
            import importlib
            import utils.logger as log_module
            importlib.reload(log_module)

            from utils.logger import _json_formatter

            # Simula un record loguru minimale
            from datetime import datetime
            record = {
                "time": datetime.now(),
                "level": type("L", (), {"name": "INFO"})(),
                "module": "test_module",
                "function": "test_func",
                "line": 42,
                "message": "Messaggio di test",
                "extra": {"env": "test"},
                "exception": None,
            }
            result = _json_formatter(record)
            parsed = json.loads(result.strip())

            assert parsed["level"] == "INFO"
            assert parsed["message"] == "Messaggio di test"
            assert parsed["module"] == "test_module"
            assert parsed["line"] == 42

    def test_json_formatter_includes_extra(self):
        """Il formatter JSON deve includere i campi extra."""
        from utils.logger import _json_formatter
        from datetime import datetime

        record = {
            "time": datetime.now(),
            "level": type("L", (), {"name": "DEBUG"})(),
            "module": "m",
            "function": "f",
            "line": 1,
            "message": "test",
            "extra": {"task_id": 99, "env": "test"},
            "exception": None,
        }
        result = _json_formatter(record)
        parsed = json.loads(result.strip())
        assert "extra" in parsed
        assert parsed["extra"]["task_id"] == 99

    def test_json_formatter_includes_exception(self):
        """Il formatter JSON deve includere l'eccezione se presente."""
        from utils.logger import _json_formatter
        from datetime import datetime

        record = {
            "time": datetime.now(),
            "level": type("L", (), {"name": "ERROR"})(),
            "module": "m",
            "function": "f",
            "line": 1,
            "message": "errore",
            "extra": {},
            "exception": "ValueError: something went wrong",
        }
        result = _json_formatter(record)
        parsed = json.loads(result.strip())
        assert "exception" in parsed


class TestLoggerSetup:
    """Test della configurazione del logger."""

    def test_get_logger_returns_logger(self):
        """get_logger deve restituire un oggetto logger utilizzabile."""
        from utils.logger import get_logger
        log = get_logger("test")
        assert log is not None

    def test_default_logger_available(self):
        """Il logger di default deve essere importabile."""
        from utils.logger import logger
        assert logger is not None

    def test_get_logger_with_module_name(self):
        """get_logger con nome modulo deve funzionare."""
        from utils.logger import get_logger
        log = get_logger(__name__)
        assert log is not None

    def test_logger_text_format_setup(self):
        """Setup con LOG_FORMAT=text non deve sollevare errori."""
        with patch.dict(os.environ, {"LOG_FORMAT": "text", "LOG_FILE": ""}):
            import importlib
            import utils.logger as log_module
            importlib.reload(log_module)
            assert log_module.logger is not None

    def test_logger_json_format_setup(self):
        """Setup con LOG_FORMAT=json non deve sollevare errori."""
        with patch.dict(os.environ, {"LOG_FORMAT": "json", "LOG_FILE": ""}):
            import importlib
            import utils.logger as log_module
            importlib.reload(log_module)
            assert log_module.logger is not None

    def test_logger_with_file_sink(self, tmp_dir: Path):
        """Setup con LOG_FILE abilitato non deve sollevare errori."""
        log_file = str(tmp_dir / "test.log")
        with patch.dict(os.environ, {"LOG_FORMAT": "text", "LOG_FILE": log_file}):
            import importlib
            import utils.logger as log_module
            importlib.reload(log_module)
            assert log_module.logger is not None

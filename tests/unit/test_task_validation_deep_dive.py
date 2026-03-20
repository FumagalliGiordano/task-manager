"""
Unit Test — Validazione granulare Task (QA Extra Suite)

Test aggiunti dalla revisione QA esterna:
- [QA-EXTRA] ID <= 0: verifica campo specifico negli errori Pydantic
- Limite superiore titolo (201 char)
- [TC-06 Regression] Tutti i tipi di whitespace bloccati con messaggio esatto
- Serialization roundtrip: model_dump → ricreazione → uguaglianza
"""

import pytest
from pydantic import ValidationError

from domain.models import Task


class TestTaskValidationDeepDive:
    """
    Test di validazione granulare per il modello Task.
    Copertura: Edge Case ID <= 0 e integrità metadati Pydantic.
    """

    @pytest.mark.parametrize("invalid_id", [0, -1, -99])
    def test_id_must_be_greater_than_zero(self, invalid_id):
        """[QA-EXTRA] Verifica che l'ID sia strettamente positivo (>0)."""
        with pytest.raises(ValidationError) as exc_info:
            Task(id=invalid_id, title="Task non valido")

        # Verifica che l'errore sia specifico per il campo 'id'
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("id",) for e in errors)
        assert "greater than 0" in str(errors)

    def test_title_max_length_enforcement(self):
        """Verifica il limite superiore della lunghezza del titolo (200 char)."""
        long_title = "A" * 201
        with pytest.raises(ValidationError):
            Task(id=1, title=long_title)

    @pytest.mark.parametrize("blank_title", [
        " ",          # Spazio singolo
        "  \t  ",     # Tabulazioni e spazi
        "\n\n",       # Newlines
        " \r\n "      # Mix di whitespace
    ])
    def test_various_whitespace_types(self, blank_title):
        """[TC-06 Regression] Verifica che ogni tipo di whitespace venga bloccato."""
        with pytest.raises(ValidationError) as exc_info:
            Task(id=1, title=blank_title)
        assert "Il titolo non può essere composto solo da spazi bianchi" in str(exc_info.value)

    def test_task_serialization_roundtrip(self):
        """Verifica che model_dump e la ricreazione non perdano dati."""
        original_data = {"id": 10, "title": "Test Roundtrip", "completed": True}
        task = Task(**original_data)
        dumped = task.model_dump()

        assert dumped == original_data
        assert Task(**dumped) == task

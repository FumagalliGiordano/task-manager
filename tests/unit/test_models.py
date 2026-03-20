"""
Unit Test — domain/models.py

Copertura target: 100%
Isolamento: nessun I/O, nessuna dipendenza esterna

Test case:
- TC-01: Titolo vuoto → ValidationError
- TC-06: Sanitizzazione input (strip spazi)
- Creazione task valido
- mark_complete (immutabilità)
- Validazione id > 0
- Titolo: lunghezza massima
"""

import pytest
from pydantic import ValidationError

from domain.models import Task


class TestTaskCreation:
    """Test di creazione e validazione del modello Task."""

    def test_create_valid_task(self):
        """Task con dati validi deve essere creato correttamente."""
        task = Task(id=1, title="Studiare Python")
        assert task.id == 1
        assert task.title == "Studiare Python"
        assert task.completed is False

    def test_create_task_completed_default_false(self):
        """Il campo completed deve essere False per default."""
        task = Task(id=1, title="Task senza completed")
        assert task.completed is False

    def test_create_task_with_completed_true(self):
        """Deve poter creare un task già completato."""
        task = Task(id=5, title="Task già fatto", completed=True)
        assert task.completed is True

    # ─── TC-01: Titolo vuoto ──────────────────────────────────────────────────

    def test_empty_title_raises_validation_error(self):
        """[TC-01] Titolo vuoto deve sollevare ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Task(id=1, title="")
        errors = exc_info.value.errors()
        assert any("title" in str(e["loc"]) for e in errors)

    # ─── TC-06: Sanitizzazione input ──────────────────────────────────────────

    def test_whitespace_only_title_raises_validation_error(self):
        """[TC-06] Titolo con soli spazi deve sollevare ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Task(id=1, title="   ")
        errors = exc_info.value.errors()
        assert any("title" in str(e["loc"]) for e in errors)

    def test_tab_only_title_raises_validation_error(self):
        """[TC-06] Titolo con soli tab deve sollevare ValidationError."""
        with pytest.raises(ValidationError):
            Task(id=1, title="\t\t")

    def test_newline_only_title_raises_validation_error(self):
        """[TC-06] Titolo con soli newline deve sollevare ValidationError."""
        with pytest.raises(ValidationError):
            Task(id=1, title="\n\n")

    def test_title_is_stripped(self):
        """[TC-06] Il titolo deve essere normalizzato (strip) al momento della creazione."""
        task = Task(id=1, title="  Task con spazi  ")
        assert task.title == "Task con spazi"

    def test_title_max_length_accepted(self):
        """Titolo di esattamente 200 caratteri deve essere accettato."""
        task = Task(id=1, title="A" * 200)
        assert len(task.title) == 200

    def test_title_exceeds_max_length_raises_error(self):
        """Titolo oltre 200 caratteri deve sollevare ValidationError."""
        with pytest.raises(ValidationError):
            Task(id=1, title="A" * 201)

    def test_title_with_special_chars_accepted(self):
        """[TC-03] Titolo con caratteri speciali UTF-8 deve essere accettato."""
        task = Task(id=1, title="Lavoro & Co. — §42 @test")
        assert "Lavoro & Co." in task.title

    # ─── ID validation ────────────────────────────────────────────────────────

    def test_id_zero_raises_validation_error(self):
        """ID = 0 non deve essere accettato (gt=0)."""
        with pytest.raises(ValidationError):
            Task(id=0, title="Task zero")

    def test_id_negative_raises_validation_error(self):
        """ID negativo non deve essere accettato."""
        with pytest.raises(ValidationError):
            Task(id=-1, title="Task negativo")

    def test_id_large_number_accepted(self):
        """ID molto grande deve essere accettato."""
        task = Task(id=999999, title="Task con ID grande")
        assert task.id == 999999


class TestTaskBehavior:
    """Test dei metodi di comportamento del Task."""

    def test_mark_complete_returns_new_instance(self):
        """mark_complete deve restituire una NUOVA istanza (immutabilità)."""
        original = Task(id=1, title="Da completare")
        completed = original.mark_complete()
        assert completed is not original

    def test_mark_complete_sets_completed_true(self):
        """mark_complete deve impostare completed=True."""
        task = Task(id=1, title="Da completare")
        completed = task.mark_complete()
        assert completed.completed is True

    def test_mark_complete_preserves_other_fields(self):
        """mark_complete non deve alterare id e title."""
        task = Task(id=42, title="Titolo originale")
        completed = task.mark_complete()
        assert completed.id == 42
        assert completed.title == "Titolo originale"

    def test_original_unchanged_after_mark_complete(self):
        """Il task originale non deve essere modificato da mark_complete."""
        task = Task(id=1, title="Originale")
        task.mark_complete()
        assert task.completed is False

    def test_str_pending_task(self):
        """__str__ per task non completato deve contenere ⬜."""
        task = Task(id=1, title="In attesa")
        result = str(task)
        assert "⬜" in result
        assert "In attesa" in result
        assert "[1]" in result

    def test_str_completed_task(self):
        """__str__ per task completato deve contenere ✅."""
        task = Task(id=2, title="Finito", completed=True)
        result = str(task)
        assert "✅" in result
        assert "Finito" in result

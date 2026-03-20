"""
Domain Layer - Modello Task

Fix applicati (QA Report):
- [EDGE] Validator Pydantic che rifiuta titoli composti da soli spazi bianchi
"""

from pydantic import BaseModel, Field, field_validator


class Task(BaseModel):
    """Rappresenta un singolo task nel sistema."""

    id: int = Field(..., gt=0, description="ID univoco, deve essere > 0")
    title: str = Field(..., min_length=1, max_length=200)
    completed: bool = False

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        """[EDGE] Rifiuta titoli composti solo da spazi/tab/newline."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Il titolo non può essere composto solo da spazi bianchi.")
        return stripped  # Normalizza rimuovendo spazi iniziali/finali

    def mark_complete(self) -> "Task":
        """Restituisce una copia del task con stato completato."""
        return self.model_copy(update={"completed": True})

    def __str__(self) -> str:
        status = "✅" if self.completed else "⬜"
        return f"[{self.id}] {status} {self.title}"

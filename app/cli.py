"""
CLI Layer - Interfaccia a riga di comando.

Fix applicati (QA Report):
- [EDGE] Gestione esplicita RuntimeError da storage corrotto (non più silenzioso)
- [EDGE] Gestione ValidationError Pydantic per input non validi (titolo vuoto/spazi)

Aggiornamenti v3:
- Logging delegato a utils/logger.py (config-aware: text vs JSON)
- Ambiente attivo mostrato nel banner --help
"""

import sys

import click
from pydantic import ValidationError

from app.service import TaskService
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@click.group()
def cli():
    """📋 Task Manager — Gestisci i tuoi task da terminale.

    \b
    Ambiente: {env} | Storage: {storage} | Log: {log_level}
    """.format(
        env=settings.env.upper(),
        storage=settings.storage_file,
        log_level=settings.log_level,
    )


def _get_service() -> TaskService:
    return TaskService()


def _handle_storage_error(e: RuntimeError) -> None:
    click.echo(click.style(f"\n⛔ ERRORE STORAGE: {e}", fg="red"), err=True)
    sys.exit(1)


@cli.command("add")
@click.argument("title")
def add_task(title: str):
    """Aggiunge un nuovo task.\n\nEsempio: python main.py add "Studiare Python" """
    try:
        service = _get_service()
        task = service.add(title)
        click.echo(click.style(f"✅ Task aggiunto: {task}", fg="green"))
    except ValidationError as e:
        msgs = "; ".join(err["msg"] for err in e.errors())
        click.echo(click.style(f"❌ Input non valido: {msgs}", fg="red"), err=True)
        sys.exit(1)
    except RuntimeError as e:
        _handle_storage_error(e)


@cli.command("list")
@click.option("--all", "show_all", is_flag=True, default=False,
              help="Mostra tutti i task (inclusi completati)")
def list_tasks(show_all: bool):
    """Elenca i task attivi (o tutti con --all)."""
    try:
        service = _get_service()
        tasks = service.list_all()
    except RuntimeError as e:
        _handle_storage_error(e)
        return
    if not show_all:
        tasks = [t for t in tasks if not t.completed]
    if not tasks:
        click.echo(click.style("📭 Nessun task trovato.", fg="yellow"))
        return
    click.echo(click.style(f"\n📋 Task ({len(tasks)}):\n", bold=True))
    for task in tasks:
        color = "bright_black" if task.completed else "white"
        click.echo(click.style(f"  {task}", fg=color))
    click.echo()


@cli.command("done")
@click.argument("task_id", type=int)
def complete_task(task_id: int):
    """Segna un task come completato.\n\nEsempio: python main.py done 1"""
    try:
        service = _get_service()
        task = service.complete(task_id)
        if task:
            click.echo(click.style(f"✅ Completato: {task}", fg="green"))
        else:
            click.echo(click.style(f"❌ Task ID {task_id} non trovato.", fg="red"))
    except RuntimeError as e:
        _handle_storage_error(e)


@cli.command("delete")
@click.argument("task_id", type=int)
@click.confirmation_option(prompt="⚠️  Sei sicuro di voler eliminare questo task?")
def delete_task(task_id: int):
    """Elimina un task.\n\nEsempio: python main.py delete 1"""
    try:
        service = _get_service()
        success = service.delete(task_id)
        if success:
            click.echo(click.style(f"🗑️  Task ID {task_id} eliminato.", fg="yellow"))
        else:
            click.echo(click.style(f"❌ Task ID {task_id} non trovato.", fg="red"))
    except RuntimeError as e:
        _handle_storage_error(e)

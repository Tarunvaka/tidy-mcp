"""Command-line interface: thin wrapper over tidy_mcp.core.service."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.table import Table

from tidy_mcp import __version__
from tidy_mcp.core import service
from tidy_mcp.core.config import Config
from tidy_mcp.core.llm import OllamaUnavailable
from tidy_mcp.core.models import Move, MoveAction, Plan

app = typer.Typer(
    help="Clean up messy folders with a local AI. Private, undoable.", no_args_is_help=True
)
console = Console()

_STYLE = {MoveAction.RENAME: "cyan", MoveAction.MOVE: "green", MoveAction.TRASH: "yellow"}

Folder = Annotated[
    Path, typer.Argument(exists=True, file_okay=False, resolve_path=True, help="Folder to tidy")
]


@app.command()
def version() -> None:
    """Print the tidy version."""
    console.print(__version__)


@app.command()
def plan(
    path: Folder,
    limit: Annotated[int | None, typer.Option(help="Max files to look at")] = None,
) -> None:
    """Build a dry-run plan for a folder. Nothing is moved."""
    config = Config()
    try:
        with Progress(
            TextColumn("[bold]Reading files"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("", total=None)

            def tick(info) -> None:
                progress.update(task, advance=1, description=info.path.name)

            result = service.plan(
                path,
                config=config,
                limit=limit,
                on_start=lambda n: progress.update(task, total=n),
                on_file=tick,
            )
    except OllamaUnavailable as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e

    if not result.moves:
        console.print("[green]Nothing to tidy.[/green]")
        return
    console.print(_table(result))
    console.print(
        f"\nPlan [bold]{result.id}[/bold]: {len(result.moves)} changes. "
        f"Apply with [bold]tidy apply {result.id}[/bold]"
    )


@app.command()
def apply(
    plan_id: str,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation")] = False,
) -> None:
    """Apply a plan by its ID."""
    try:
        result = service.store.load_plan(plan_id)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
    console.print(_table(result))
    if not yes and not typer.confirm(f"Apply {len(result.moves)} changes?"):
        raise typer.Exit()
    done = service.apply(plan_id)
    console.print(f"[green]Done. {len(done)} files tidied.[/green] Undo with tidy undo {plan_id}")


@app.command()
def undo(plan_id: str) -> None:
    """Put every file from an applied plan back where it was."""
    try:
        restored = service.undo(plan_id)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
    console.print(f"[green]Restored {len(restored)} files.[/green]")


@app.command()
def dupes(path: Folder) -> None:
    """List duplicate files in a folder."""
    groups = service.duplicates(path)
    if not groups:
        console.print("[green]No duplicates.[/green]")
        return
    for group in groups:
        console.print(f"[bold]{group[0].path.name}[/bold] (kept)")
        for f in group[1:]:
            console.print(f"  [yellow]{f.path.name}[/yellow]")


def _table(p: Plan) -> Table:
    table = Table(title=f"tidy plan {p.id} for {p.root}", show_lines=False)
    table.add_column("")
    table.add_column("From")
    table.add_column("To")
    table.add_column("Why", style="dim", overflow="fold")
    for m in p.moves:
        style = _STYLE[m.action]
        table.add_row(
            f"[{style}]{m.action.value}[/{style}]", m.source.name, _short(m, p.root), m.reason
        )
    return table


def _short(m: Move, root: Path) -> str:
    try:
        return str(m.destination.relative_to(root))
    except ValueError:
        return str(m.destination)

"""Command-line interface: thin wrapper over tidy_mcp.core."""

import typer

from tidy_mcp import __version__

app = typer.Typer(help="Clean up messy folders with a local AI. Private, undoable.")


@app.command()
def version() -> None:
    """Print the tidy version."""
    typer.echo(__version__)


@app.command()
def plan(path: str) -> None:
    """Build a dry-run plan for a folder."""
    raise typer.Exit(code=_not_ready("plan"))


@app.command()
def apply(plan_id: str) -> None:
    """Apply a plan by its ID."""
    raise typer.Exit(code=_not_ready("apply"))


@app.command()
def undo(plan_id: str) -> None:
    """Undo an applied plan."""
    raise typer.Exit(code=_not_ready("undo"))


@app.command()
def dupes(path: str) -> None:
    """Find duplicate files in a folder."""
    raise typer.Exit(code=_not_ready("dupes"))


def _not_ready(name: str) -> int:
    typer.echo(f"`tidy {name}` is not implemented yet.", err=True)
    return 1

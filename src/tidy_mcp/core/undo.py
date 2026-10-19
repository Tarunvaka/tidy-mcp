"""Reverse an applied plan using its undo log."""

from pathlib import Path

from tidy_mcp.core import store
from tidy_mcp.core.executor import move_file
from tidy_mcp.core.models import Move


def undo(plan_id: str) -> list[Move]:
    """Move every file back where it came from, newest move first.

    Files that were moved again or deleted since are skipped, and nothing is overwritten.
    Folders tidy created are removed once they are empty.
    """
    plan = store.load_plan(plan_id)
    root = plan.root.resolve()
    restored: list[Move] = []
    for move in reversed(store.read_log(plan_id)):
        if not move.destination.is_file() or move.source.exists():
            continue
        move.source.parent.mkdir(parents=True, exist_ok=True)
        move_file(move.destination, move.source)
        restored.append(move)
        _remove_empty_parents(move.destination.parent, root)
    store.write_log(plan_id, [])
    return restored


def _remove_empty_parents(folder: Path, root: Path) -> None:
    while folder.resolve() != root and folder.resolve().is_relative_to(root):
        try:
            folder.rmdir()
        except OSError:
            return
        folder = folder.parent

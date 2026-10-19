"""Carry out a plan. Files are only ever moved, never deleted."""

import os
from pathlib import Path

from tidy_mcp.core import store
from tidy_mcp.core.models import Move, Plan


class UnsafeMove(RuntimeError):
    """A move would leave the plan's folder or overwrite a file."""


def apply_plan(plan: Plan) -> list[Move]:
    """Run every move in the plan and return what was done.

    The undo log is written after each move, so a crash halfway can still be undone.
    Moves whose source has vanished are skipped.
    """
    root = plan.root.resolve()
    done: list[Move] = []
    store.write_log(plan.id, done)
    for move in plan.moves:
        if not move.source.is_file() or move.source.is_symlink():
            continue
        dest = _unused(move.destination)
        if not move.source.resolve().is_relative_to(root):
            raise UnsafeMove(f"{move.source} is outside {root}")
        if not plan.allows(dest):
            raise UnsafeMove(f"{dest} is outside the folders this plan may use")
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
        except (FileExistsError, NotADirectoryError):
            continue  # a file now sits where the folder should go; leave this one alone
        move_file(move.source, dest)
        done.append(move.model_copy(update={"destination": dest}))
        store.write_log(plan.id, done)
    return done


def _unused(path: Path) -> Path:
    candidate, n = path, 1
    while candidate.exists():
        n += 1
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
    return candidate


def move_file(source: Path, dest: Path) -> None:
    if dest.exists():
        raise UnsafeMove(f"{dest} already exists")
    os.rename(source, dest)

"""Turn scanned files into a dry-run plan. Nothing on disk changes here."""

import uuid
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

from tidy_mcp.core.models import Description, FileInfo, FileKind, Move, MoveAction, Plan
from tidy_mcp.core.scanner import TRASH_DIR

STALE_INSTALLER_DAYS = 30


def find_duplicates(files: list[FileInfo]) -> list[list[FileInfo]]:
    """Groups of identical files. The first in each group is the original (oldest) and is kept."""
    groups: dict[str, list[FileInfo]] = defaultdict(list)
    for f in files:
        groups[f.hash].append(f)
    return [
        sorted(g, key=lambda f: (f.modified, len(f.path.name)))
        for g in groups.values()
        if len(g) > 1
    ]


def build_plan(
    root: Path,
    files: list[FileInfo],
    describe: Callable[[FileInfo], Description],
    now: datetime | None = None,
    rule_folder: Callable[[Description], Path | None] | None = None,
    workers: int = 1,
) -> Plan:
    root = root.expanduser().resolve()
    now = now or datetime.now()
    taken: set[Path] = set()
    moves: list[Move] = []
    extra_roots: set[Path] = set()

    duplicates = {f.path: group[0].path.name for group in find_duplicates(files) for f in group[1:]}

    def stale_installer(f: FileInfo) -> bool:
        return f.kind == FileKind.INSTALLER and now - f.modified > timedelta(
            days=STALE_INSTALLER_DAYS
        )

    to_describe = [f for f in files if f.path not in duplicates and not stale_installer(f)]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        descriptions = dict(zip(map(id, to_describe), pool.map(describe, to_describe), strict=True))

    for f in files:
        if f.path in duplicates:
            dest = _free(_usable_folder(root, TRASH_DIR) / f.path.name, taken)
            moves.append(
                Move(
                    source=f.path,
                    destination=dest,
                    action=MoveAction.TRASH,
                    reason=f"duplicate of {duplicates[f.path]}",
                )
            )
            continue

        if stale_installer(f):
            dest = _free(_usable_folder(root, TRASH_DIR) / f.path.name, taken)
            moves.append(
                Move(
                    source=f.path,
                    destination=dest,
                    action=MoveAction.TRASH,
                    reason=f"installer older than {STALE_INSTALLER_DAYS} days",
                )
            )
            continue

        desc = descriptions[id(f)]
        folder = rule_folder(desc) if rule_folder else None
        if folder is not None:
            extra_roots.add(folder.resolve())
            target = folder.resolve() / f"{desc.name}{f.path.suffix.lower()}"
        else:
            folder = _usable_folder(root, desc.category)
            target = folder / f"{desc.name}{f.path.suffix.lower()}"
            if not _inside(target, root):
                continue
        if target == f.path:
            taken.add(f.path)
            continue
        dest = _free(target, taken, source=f.path)
        action = MoveAction.RENAME if dest.parent == f.path.parent else MoveAction.MOVE
        moves.append(Move(source=f.path, destination=dest, action=action, reason=desc.summary))

    return Plan(
        id=uuid.uuid4().hex[:8],
        root=root,
        created=now,
        moves=moves,
        extra_roots=sorted(extra_roots),
    )


def _usable_folder(root: Path, category: str) -> Path:
    """root/category, renaming any level that a file already occupies (Other -> Other-2).

    Checked on disk, so it also catches case-insensitive clashes like a file named OTHER.
    """
    folder = root
    for part in Path(category).parts:
        candidate, n = folder / part, 1
        while candidate.exists() and not candidate.is_dir():
            n += 1
            candidate = folder / f"{part}-{n}"
        folder = candidate
    return folder


def _inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root)


def _free(path: Path, taken: set[Path], source: Path | None = None) -> Path:
    """First name like path, path-2, path-3 ... that no other file or plan entry uses."""
    candidate, n = path, 1
    while candidate in taken or (candidate.exists() and candidate != source):
        n += 1
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
    taken.add(candidate)
    return candidate

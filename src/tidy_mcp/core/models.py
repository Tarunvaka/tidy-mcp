"""Data contracts shared by every part of tidy. Build everything against these."""

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class FileKind(StrEnum):
    DOCUMENT = "document"
    IMAGE = "image"
    CODE = "code"
    ARCHIVE = "archive"
    INSTALLER = "installer"
    AUDIO = "audio"
    VIDEO = "video"
    OTHER = "other"


class FileInfo(BaseModel):
    """One file found by the scanner."""

    path: Path
    kind: FileKind
    size: int
    modified: datetime
    hash: str = Field(description="xxhash of the file contents; shared by dedupe and cache")


class Description(BaseModel):
    """What the local model says about a file. Also the Ollama structured-output schema."""

    name: str = Field(description="New file name without extension, e.g. 2026-06-12_Amazon_receipt")
    category: str = Field(description="Folder to put it in, e.g. Receipts or Screenshots/Code")
    summary: str = Field(description="One short sentence about the file")


class MoveAction(StrEnum):
    RENAME = "rename"
    MOVE = "move"
    TRASH = "trash"


class Move(BaseModel):
    """One planned or executed change. The undo log is a list of these."""

    source: Path
    destination: Path
    action: MoveAction
    reason: str = ""


class Plan(BaseModel):
    """A dry-run plan for one folder. Nothing changes until it is applied."""

    id: str
    root: Path
    created: datetime
    moves: list[Move] = Field(default_factory=list)
    extra_roots: list[Path] = Field(
        default_factory=list,
        description="Folders outside root that config rules may move files into",
    )

    def allows(self, path: Path) -> bool:
        resolved = path.resolve()
        return any(resolved.is_relative_to(r.resolve()) for r in [self.root, *self.extra_roots])

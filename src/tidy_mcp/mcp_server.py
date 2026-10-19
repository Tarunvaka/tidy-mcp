"""MCP server: thin wrapper over tidy_mcp.core.service.

Nothing moves until the user has seen a plan and the client calls apply_plan with its ID.
"""

from collections.abc import Callable
from functools import wraps
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from tidy_mcp.core import service
from tidy_mcp.core.config import Config
from tidy_mcp.core.executor import UnsafeMove
from tidy_mcp.core.llm import OllamaUnavailable
from tidy_mcp.core.models import Description, FileInfo, Move, Plan
from tidy_mcp.core.scanner import scan

mcp = MCPServer(
    "tidy",
    instructions=(
        "tidy organizes messy folders with a local AI. Always call plan_tidy first, show the "
        "user every change in the plan, and call apply_plan only after the user agrees. "
        "Files are never deleted; duplicates and old installers go to _tidy_trash. "
        "Every applied plan can be reversed with undo."
    ),
)

_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
_MOVES_FILES = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)


class Files(BaseModel):
    files: list[FileInfo]


class Moves(BaseModel):
    moves: list[Move]


class DuplicateGroups(BaseModel):
    groups: list[list[FileInfo]]


def _friendly[F: Callable](fn: F) -> F:
    """Turn expected failures into readable tool errors."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (OllamaUnavailable, UnsafeMove) as e:
            raise ToolError(str(e)) from e
        except FileNotFoundError as e:
            raise ToolError(str(e)) from e
        except NotADirectoryError as e:
            raise ToolError(f"{e} is not a folder") from e

    return wrapper  # type: ignore[return-value]


@mcp.tool(annotations=_READ_ONLY)
@_friendly
def scan_folder(path: str, limit: int = 500) -> Files:
    """List the files tidy would look at in a folder (top level only, no hidden files)."""
    return Files(files=scan(Path(path), limit=limit))


@mcp.tool(annotations=_READ_ONLY)
@_friendly
def describe_file(path: str) -> Description:
    """Ask the local model for a better name and folder for one file."""
    file = Path(path).expanduser().resolve()
    info = next((f for f in scan(file.parent, limit=10_000) if f.path == file), None)
    if info is None:
        raise ToolError(f"{path} is not a file tidy can read")
    describer = service.make_describer(Config())
    describer.check()
    return describer.describe(info)


@mcp.tool(annotations=_MOVES_FILES)
@_friendly
def plan_tidy(path: str, limit: int = 500) -> Plan:
    """Build a dry-run plan for a folder. Nothing is moved. Show the plan to the user."""
    return service.plan(Path(path), limit=limit)


@mcp.tool(annotations=_MOVES_FILES)
@_friendly
def apply_plan(plan_id: str) -> Moves:
    """Apply a plan the user has approved. Files are moved, never deleted."""
    return Moves(moves=service.apply(plan_id))


@mcp.tool(annotations=_MOVES_FILES)
@_friendly
def undo(plan_id: str) -> Moves:
    """Put every file from an applied plan back where it was."""
    return Moves(moves=service.undo(plan_id))


@mcp.tool(annotations=_READ_ONLY)
@_friendly
def find_duplicates(path: str) -> DuplicateGroups:
    """Groups of identical files. The first in each group is the original and is kept."""
    return DuplicateGroups(groups=service.duplicates(Path(path)))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

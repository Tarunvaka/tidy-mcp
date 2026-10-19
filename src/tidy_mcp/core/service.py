"""The four things tidy does, shared by the CLI and the MCP server."""

from collections.abc import Callable
from pathlib import Path

from tidy_mcp.core import store
from tidy_mcp.core.cache import DescriptionCache
from tidy_mcp.core.config import Config
from tidy_mcp.core.executor import apply_plan
from tidy_mcp.core.llm import Describer
from tidy_mcp.core.models import Description, FileInfo, Move, Plan
from tidy_mcp.core.planner import build_plan, find_duplicates
from tidy_mcp.core.scanner import scan
from tidy_mcp.core.undo import undo as undo_log


def make_describer(config: Config) -> Describer:
    return Describer(
        text_model=config.text_model,
        vision_model=config.vision_model,
        host=config.ollama_host,
        cache=DescriptionCache(store.home() / "cache.db"),
    )


def plan(
    path: Path,
    config: Config | None = None,
    describe: Callable[[FileInfo], Description] | None = None,
    limit: int | None = None,
    on_start: Callable[[int], None] | None = None,
    on_file: Callable[[FileInfo], None] | None = None,
) -> Plan:
    """Scan a folder, describe every file and save a dry-run plan."""
    config = config or Config()
    if describe is None:
        describer = make_describer(config)
        describer.check()
        describe = describer.describe
    files = [f for f in scan(path, limit=limit or config.limit) if not config.ignored(f)]
    if on_start:
        on_start(len(files))

    def described(info: FileInfo) -> Description:
        if on_file:
            on_file(info)
        return describe(info)

    result = build_plan(
        path, files, described, rule_folder=config.rule_folder, workers=config.workers
    )
    store.save_plan(result)
    return result


def apply(plan_id: str) -> list[Move]:
    return apply_plan(store.load_plan(plan_id))


def undo(plan_id: str) -> list[Move]:
    return undo_log(plan_id)


def duplicates(path: Path, limit: int = 500) -> list[list[FileInfo]]:
    return find_duplicates(scan(path, limit=limit))

"""Where tidy keeps plans and undo logs: $TIDY_HOME, default ~/.tidy."""

import os
from pathlib import Path

from pydantic import TypeAdapter

from tidy_mcp.core.models import Move, Plan

_MOVES = TypeAdapter(list[Move])


def home() -> Path:
    return Path(os.environ.get("TIDY_HOME", "~/.tidy")).expanduser()


def _plan_path(plan_id: str) -> Path:
    return home() / "plans" / f"{plan_id}.json"


def _log_path(plan_id: str) -> Path:
    return home() / "logs" / f"{plan_id}.json"


def save_plan(plan: Plan) -> Path:
    path = _plan_path(plan.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan.model_dump_json(indent=2))
    return path


def load_plan(plan_id: str) -> Plan:
    path = _plan_path(plan_id)
    if not path.exists():
        raise FileNotFoundError(f"No plan with id {plan_id}")
    return Plan.model_validate_json(path.read_text())


def write_log(plan_id: str, done: list[Move]) -> None:
    path = _log_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_MOVES.dump_json(done, indent=2))


def read_log(plan_id: str) -> list[Move]:
    path = _log_path(plan_id)
    if not path.exists():
        raise FileNotFoundError(f"Plan {plan_id} was never applied")
    return _MOVES.validate_json(path.read_bytes())

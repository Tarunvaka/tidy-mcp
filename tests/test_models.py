from datetime import datetime
from pathlib import Path

from tidy_mcp.core.models import Description, Move, MoveAction, Plan


def test_plan_round_trips_through_json():
    plan = Plan(
        id="abc123",
        root=Path("/tmp/downloads"),
        created=datetime(2026, 10, 19),
        moves=[
            Move(
                source=Path("/tmp/downloads/IMG_1.png"),
                destination=Path("/tmp/downloads/Screenshots/error.png"),
                action=MoveAction.MOVE,
            )
        ],
    )
    assert Plan.model_validate_json(plan.model_dump_json()) == plan


def test_description_schema_has_required_fields():
    schema = Description.model_json_schema()
    assert set(schema["required"]) == {"name", "category", "summary"}

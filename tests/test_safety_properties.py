"""Random folders and random (even hostile) model answers must never break the safety rules:

1. Planning never changes the disk.
2. Every destination stays inside the folders the plan may use.
3. No two moves share a destination.
4. Applying never loses or duplicates file contents.
5. Undo restores the folder exactly.
"""

import os
import shutil
import tempfile
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tidy_mcp.core import store
from tidy_mcp.core.executor import apply_plan
from tidy_mcp.core.models import Description, FileInfo
from tidy_mcp.core.planner import build_plan
from tidy_mcp.core.scanner import scan
from tidy_mcp.core.undo import undo

_EXTS = [".pdf", ".png", ".txt", ".py", ".zip", ".dmg", ".md", ""]
_name_chars = st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_().")
file_names = st.builds(
    lambda stem, ext: stem.strip(" .") + ext,
    st.text(_name_chars, min_size=1, max_size=20),
    st.sampled_from(_EXTS),
).filter(lambda n: n and not n.startswith(".") and n.strip(" .") != "")

folder_contents = st.dictionaries(
    file_names, st.sampled_from([b"a", b"b", b"same", b"\x00" * 10, b"hello world"]), max_size=12
)

hostile_text = st.one_of(
    st.text(max_size=30),
    st.sampled_from(
        ["../../etc", "/etc/passwd", "..", ".", "", "a/../../b", "~/x", "CON", "a" * 300]
    ),
)
answers = st.builds(Description, name=hostile_text, category=hostile_text, summary=st.just(""))


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(contents=folder_contents, answer_list=st.lists(answers, min_size=1, max_size=12))
def test_safety_invariants(contents, answer_list):
    from tidy_mcp.core.llm import _clean

    base = Path(tempfile.mkdtemp())
    try:
        root = base / "Downloads"
        root.mkdir()
        outside = base / "outside.txt"
        outside.write_bytes(b"do not touch")
        for name, data in contents.items():
            (root / name).write_bytes(data)
        os.environ["TIDY_HOME"] = str(base / "home")

        before = snapshot(root)
        answers_iter = iter(answer_list * 20)

        def describe(info: FileInfo) -> Description:
            return _clean(next(answers_iter), info)

        plan = build_plan(root, scan(root), describe)

        assert snapshot(root) == before
        dests = [m.destination for m in plan.moves]
        assert len(dests) == len(set(dests))
        assert all(plan.allows(d) for d in dests)

        store.save_plan(plan)
        apply_plan(plan)
        after = snapshot(root)
        assert sorted(after.values()) == sorted(before.values())
        assert outside.read_bytes() == b"do not touch"

        undo(plan.id)
        assert snapshot(root) == before
        assert [p for p in root.iterdir() if p.is_dir()] == []
    finally:
        os.environ.pop("TIDY_HOME", None)
        shutil.rmtree(base)

from pathlib import Path

from tidy_mcp.core import store
from tidy_mcp.core.executor import apply_plan
from tidy_mcp.core.extract import extract_text
from tidy_mcp.core.llm import Describer, safe_name
from tidy_mcp.core.models import Description, FileInfo, FileKind, MoveAction
from tidy_mcp.core.planner import build_plan, find_duplicates
from tidy_mcp.core.scanner import TRASH_DIR, scan
from tidy_mcp.core.undo import undo


def fake_describe(info: FileInfo) -> Description:
    return Description(name=f"named_{info.path.stem}", category=info.kind.value.title(), summary="")


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_scan_skips_hidden_and_symlinks(messy):
    (messy / "link.txt").symlink_to(messy / "notes.txt")
    names = {f.path.name for f in scan(messy)}
    assert ".DS_Store" not in names
    assert "link.txt" not in names
    assert "notes.txt" in names


def test_scan_respects_limit(messy):
    assert len(scan(messy, limit=3)) == 3


def test_extract_reads_pdf_title_and_text(messy):
    files = {f.path.name: f for f in scan(messy)}
    assert "Lease Agreement" in extract_text(files["final_v3_real.pdf"])
    assert "Grocery list" in extract_text(files["Untitled-1.md"])
    assert extract_text(files["Docker.dmg"]) == ""


def test_duplicates_are_found(messy):
    groups = find_duplicates(scan(messy))
    assert sorted(len(g) for g in groups) == [2, 2]


def test_plan_trashes_duplicates_and_stale_installers(messy):
    plan = build_plan(messy, scan(messy), fake_describe)
    trashed = {m.source.name for m in plan.moves if m.action == MoveAction.TRASH}
    assert {"Docker.dmg", "zoom_installer.pkg"} <= trashed
    assert len(trashed) == 4
    assert all(m.destination.parent.name == TRASH_DIR for m in plan.moves if m.action == "trash")


def test_plan_does_not_touch_disk(messy):
    before = snapshot(messy)
    build_plan(messy, scan(messy), fake_describe)
    assert snapshot(messy) == before


def test_plan_resolves_name_collisions(messy):
    plan = build_plan(
        messy, scan(messy), lambda f: Description(name="same", category="X", summary="")
    )
    dests = [m.destination for m in plan.moves]
    assert len(dests) == len(set(dests))


def test_plan_ignores_categories_escaping_root(messy):
    evil = Description(name="x", category="../../etc", summary="")
    plan = build_plan(messy, scan(messy), lambda f: evil)
    assert all(m.destination.resolve().is_relative_to(messy) for m in plan.moves)


def test_apply_then_undo_restores_everything(messy):
    before = snapshot(messy)
    plan = build_plan(messy, scan(messy), fake_describe)
    store.save_plan(plan)

    done = apply_plan(plan)
    assert len(done) == len(plan.moves)
    after = snapshot(messy)
    assert sorted(after.values()) == sorted(before.values())  # nothing deleted
    assert after != before

    undo(plan.id)
    assert snapshot(messy) == before
    assert {p.name for p in messy.iterdir() if p.is_dir()} == set()


def test_describer_falls_back_when_ollama_is_down(messy):
    describer = Describer(host="http://127.0.0.1:9")
    info = next(f for f in scan(messy) if f.kind == FileKind.DOCUMENT)
    desc = describer.describe(info)
    assert desc.name == info.path.stem
    assert desc.category == "Documents"


def test_safe_name():
    assert safe_name("2026/06 Amazon: receipt?") == "202606_Amazon_receipt"
    assert safe_name("../..") == ""


def test_invented_dates_are_dropped():
    from tidy_mcp.core.llm import _drop_invented_dates

    assert (
        _drop_invented_dates("2023-10-05_Meeting_notes", "notes.txt\nship tidy") == "Meeting_notes"
    )
    assert (
        _drop_invented_dates("2026-10-02_KeyError", "Screenshot 2026-10-02 at 11.04.12.png")
        == "2026-10-02_KeyError"
    )
    assert _drop_invented_dates("Invoice_2025-01-31", "Due 2025.01.31") == "Invoice_2025-01-31"

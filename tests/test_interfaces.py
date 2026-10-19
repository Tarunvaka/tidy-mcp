import asyncio
import json

import pytest
from typer.testing import CliRunner

from tidy_mcp import mcp_server
from tidy_mcp.cli import app
from tidy_mcp.core import service
from tidy_mcp.core.config import Config, Rule
from tidy_mcp.core.models import Description, FileInfo
from tidy_mcp.core.scanner import scan

runner = CliRunner()


class FakeDescriber:
    def check(self) -> None:
        pass

    def describe(self, info: FileInfo) -> Description:
        return Description(
            name=f"named_{info.path.stem}", category=info.kind.value.title(), summary=info.path.stem
        )


@pytest.fixture(autouse=True)
def fake_ollama(monkeypatch):
    monkeypatch.setattr(service, "make_describer", lambda config: FakeDescriber())


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def plan_id_from(output: str) -> str:
    return output.split("tidy apply ")[-1].split()[0]


def test_cli_plan_apply_undo(messy):
    before = snapshot(messy)

    result = runner.invoke(app, ["plan", str(messy)])
    assert result.exit_code == 0, result.output
    plan_id = plan_id_from(result.output)
    assert snapshot(messy) == before

    result = runner.invoke(app, ["apply", plan_id], input="n\n")
    assert snapshot(messy) == before

    result = runner.invoke(app, ["apply", plan_id, "--yes"])
    assert result.exit_code == 0, result.output
    assert snapshot(messy) != before

    result = runner.invoke(app, ["undo", plan_id])
    assert result.exit_code == 0, result.output
    assert snapshot(messy) == before


def test_cli_unknown_plan_fails_cleanly(messy):
    result = runner.invoke(app, ["apply", "nope"])
    assert result.exit_code == 1
    assert "No plan" in result.output


def test_cli_dupes(messy):
    result = runner.invoke(app, ["dupes", str(messy)])
    assert result.exit_code == 0
    assert "IMG_2931" in result.output


def test_config_ignore_and_rules(messy, tmp_path):
    finance = tmp_path / "Finance"
    config = Config(ignore=["*.md"], rules=[Rule(match="document", folder=str(finance))])
    plan = service.plan(messy, config=config)

    assert all(m.source.suffix != ".md" for m in plan.moves)
    routed = [m for m in plan.moves if m.destination.parent == finance.resolve()]
    assert routed
    assert finance.resolve() in plan.extra_roots

    service.apply(plan.id)
    assert any(finance.iterdir())
    service.undo(plan.id)
    assert not any(finance.iterdir())


def test_config_reads_toml(tmp_path, monkeypatch):
    monkeypatch.setenv("TIDY_HOME", str(tmp_path))
    (tmp_path / "config.toml").write_text(
        'text_model = "llama3.2:3b"\n[[rules]]\nmatch = "invoice"\nfolder = "~/Finance"\n'
    )
    config = Config()
    assert config.text_model == "llama3.2:3b"
    assert config.rules[0].match == "invoice"


def call(tool: str, **args):
    result = asyncio.run(mcp_server.mcp.call_tool(tool, args))
    return json.loads(result.content[0].text)


def test_mcp_plan_apply_undo(messy):
    before = snapshot(messy)
    plan = call("plan_tidy", path=str(messy))
    assert snapshot(messy) == before
    assert plan["moves"]

    call("apply_plan", plan_id=plan["id"])
    assert snapshot(messy) != before

    call("undo", plan_id=plan["id"])
    assert snapshot(messy) == before


def test_mcp_read_only_tools(messy):
    assert len(call("scan_folder", path=str(messy))["files"]) == len(scan(messy))
    assert len(call("find_duplicates", path=str(messy))["groups"]) == 2
    desc = call("describe_file", path=str(messy / "notes.txt"))
    assert desc["name"] == "named_notes"


def test_mcp_errors_are_readable(messy):
    with pytest.raises(Exception, match="No plan"):
        call("apply_plan", plan_id="nope")

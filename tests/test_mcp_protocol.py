"""Call the tools through a real MCP client, which checks results against each tool's schema."""

import asyncio

import jsonschema
import pytest
from mcp import Client
from test_interfaces import FakeDescriber

from tidy_mcp import mcp_server
from tidy_mcp.core import service


@pytest.fixture(autouse=True)
def fake_ollama(monkeypatch):
    monkeypatch.setattr(service, "make_describer", lambda config: FakeDescriber())


def run(messy):
    async def go():
        async with Client(mcp_server.mcp) as client:
            schemas = {t.name: t.output_schema for t in (await client.list_tools()).tools}
            results = {}

            async def call(name, **args):
                result = await client.call_tool(name, args)
                assert not result.is_error, result.content
                results[name] = result.structured_content
                return result.structured_content

            plan = await call("plan_tidy", path=str(messy))
            await call("apply_plan", plan_id=plan["id"])
            await call("undo", plan_id=plan["id"])
            await call("scan_folder", path=str(messy))
            await call("find_duplicates", path=str(messy))
            await call("describe_file", path=str(messy / "notes.txt"))
            return schemas, results

    return asyncio.run(go())


def test_every_tool_result_matches_its_schema_including_formats(messy):
    schemas, results = run(messy)
    checker = jsonschema.Draft202012Validator.FORMAT_CHECKER
    for name, data in results.items():
        jsonschema.validate(data, schemas[name], format_checker=checker)

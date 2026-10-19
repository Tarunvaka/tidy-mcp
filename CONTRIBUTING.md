# Contributing to tidy-mcp

Thanks for helping. Small, focused pull requests are the easiest to review.

## Setup

```bash
git clone https://github.com/Tarunvaka/tidy-mcp && cd tidy-mcp
uv sync
uv run pytest
```

To try real naming, install [Ollama](https://ollama.com) and pull the models:

```bash
ollama pull qwen2.5:7b
ollama pull qwen2.5vl:7b
uv run python scripts/make_fixtures.py
uv run tidy plan tests/fixtures/messy_downloads
```

## How the code is laid out

```
src/tidy_mcp/
  core/
    models.py     data shapes shared by everything
    scanner.py    which files to look at
    extract.py    text samples from PDFs, Word, code
    llm.py        asks Ollama for a name and folder
    planner.py    builds the dry-run plan
    executor.py   moves files and writes the undo log
    undo.py       reverses a plan
    service.py    the four actions the CLI and MCP server share
  cli.py          `tidy` command
  mcp_server.py   MCP tools
```

The CLI and MCP server are thin wrappers. New behavior goes in `core/`.

## Safety rules

These are the project's promises. A change that breaks one will not be merged.

1. Never delete a file. Unwanted files move to `_tidy_trash/`.
2. Never touch anything outside the chosen folder (plus folders a user's config rules name).
3. Planning never changes the disk.
4. Every applied plan can be undone exactly.

`tests/test_safety_properties.py` checks these with random folders. Keep it passing.

## Before opening a PR

Run these locally first. Please don't push just to see whether CI passes.

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

If you change the prompt or naming rules, run `uv run python scripts/eval_quality.py` before and after, and put both scores in the PR description.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `chore:`.

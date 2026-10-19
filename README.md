# tidy-mcp

**Your Downloads folder, cleaned by a local AI. Private. Undoable.**

Point tidy at a messy folder. A local model looks at every file, gives it a real name and sorts it into folders. Nothing leaves your machine, and every run can be undone.

> 🚧 Work in progress. Not ready to use yet.

## How it works

```
scan → plan (dry run) → preview → apply → undo
```

- Runs on [Ollama](https://ollama.com), fully offline
- Never deletes anything; duplicates go to `_tidy_trash/`
- Works as a CLI (`tidy`) and as an MCP server for Claude, Cursor and other clients

## Development

```bash
uv sync
uv run python scripts/make_fixtures.py
uv run pytest
```

## License

MIT

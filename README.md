# tidy-mcp

**Your Downloads folder, cleaned by a local AI. Private. Undoable.**

Point tidy at a messy folder. A local model looks at every file, gives it a real name and sorts it into folders. Nothing leaves your machine, and every run can be undone.

> 🚧 Work in progress. Not on PyPI yet.

```
IMG_2931.png            →  Receipts/2026-06-12_Amazon_receipt.png
Screenshot 11.04.12.png →  Screenshots/Code/python_KeyError_traceback.png
final_v3_real.pdf       →  Documents/Housing/Lease_Agreement_Bangalore_2025.pdf
IMG_2931 (1).png        →  _tidy_trash/   (duplicate)
Docker.dmg              →  _tidy_trash/   (installer older than 30 days)
```

## How it works

```
scan → plan (dry run) → preview → apply → undo
```

- Runs on [Ollama](https://ollama.com), fully offline
- Never deletes anything. Duplicates and old installers go to `_tidy_trash/`
- Every applied plan can be undone
- Only touches the top level of the folder you give it. Hidden files and symlinks are skipped
- Works as a CLI (`tidy`) and as an MCP server for Claude, Cursor and other clients

## Setup

1. Install [Ollama](https://ollama.com) and pull the models:

   ```bash
   ollama pull qwen2.5:7b
   ollama pull qwen2.5vl:7b
   ```

2. Install tidy from source:

   ```bash
   git clone https://github.com/Tarunvaka/tidy-mcp && cd tidy-mcp
   uv tool install .
   ```

## CLI

```bash
tidy plan ~/Downloads      # dry run: shows every change, moves nothing
tidy apply <plan-id>       # asks before moving
tidy undo <plan-id>        # puts everything back
tidy dupes ~/Downloads     # list duplicate files
```

## MCP server

Add tidy to your MCP client. For Claude Desktop, edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tidy": {
      "command": "uv",
      "args": ["--directory", "/path/to/tidy-mcp", "run", "tidy-mcp"]
    }
  }
}
```

For Claude Code:

```bash
claude mcp add tidy -- uv --directory /path/to/tidy-mcp run tidy-mcp
```

For Cursor, add the same `command` and `args` under `mcpServers` in `~/.cursor/mcp.json`.

Then ask: *"Tidy my Downloads folder."* The assistant shows the plan and only applies it after you agree.

| Tool | What it does |
|---|---|
| `scan_folder` | List the files tidy would look at |
| `describe_file` | Suggested name and folder for one file |
| `plan_tidy` | Build a dry-run plan |
| `apply_plan` | Apply an approved plan |
| `undo` | Reverse an applied plan |
| `find_duplicates` | Groups of identical files |

## Configuration

Optional. Create `~/.tidy/config.toml`:

```toml
text_model = "qwen2.5:7b"
vision_model = "qwen2.5vl:7b"
limit = 500                      # max files per run
ignore = ["*.part", "keep-*"]    # file name patterns to leave alone

[[rules]]                        # send matching files to a fixed folder
match = "invoice"
folder = "~/Finance/Invoices"
```

Any setting can also come from an environment variable such as `TIDY_TEXT_MODEL`. Plans and undo logs live in `~/.tidy` (or `$TIDY_HOME`).

## Development

```bash
uv sync
uv run python scripts/make_fixtures.py   # builds a fake messy folder
uv run pytest
```

## License

MIT

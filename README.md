# tidy-mcp

**Your Downloads folder, cleaned by a local AI. Private. Undoable.**

Point tidy at a messy folder. A local model looks at every file, gives it a real name and sorts it into folders. Nothing leaves your machine, and every run can be undone.

> 🚧 Early release. Feedback welcome.

![tidy planning, applying and undoing a messy Downloads folder](docs/demo.gif)

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

2. Install tidy:

   ```bash
   uv tool install tidy-mcp      # or: pipx install tidy-mcp
   ```

## CLI

```bash
tidy plan ~/Downloads      # dry run: shows every change, moves nothing
tidy apply last           # asks before moving (or pass a plan ID)
tidy undo last            # puts everything back
tidy dupes ~/Downloads     # list duplicate files
```

## MCP server

Add tidy to your MCP client. For Claude Desktop, edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tidy": {
      "command": "uvx",
      "args": ["tidy-mcp"]
    }
  }
}
```

For Claude Code:

```bash
claude mcp add tidy -- uvx tidy-mcp
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

`workers` (default 4) sets how many files are described at once. Answers are cached, so re-running on the same files is instant.

Any setting can also come from an environment variable such as `TIDY_TEXT_MODEL`. Plans and undo logs live in `~/.tidy` (or `$TIDY_HOME`).

## Development

```bash
uv sync
uv run python scripts/make_fixtures.py   # builds a fake messy folder
uv run pytest                            # includes property-based safety tests
uv run python scripts/eval_quality.py    # scores naming on 30 varied files (needs Ollama)
```

Current score with `qwen2.5:7b` + `qwen2.5vl:7b`: 29/30 folders correct, 30/30 names contain the key words.

## Contributing

Issues labeled [good first issue](https://github.com/Tarunvaka/tidy-mcp/labels/good%20first%20issue) are a good place to start. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Releasing

1. Move the `Unreleased` notes in `CHANGELOG.md` under a new version heading.
2. `uv version --bump minor` (or `patch` / `major`) and commit.
3. `git tag v$(uv version --short) && git push --tags`

The Release workflow tests, builds, publishes to PyPI and creates the GitHub release.

## License

MIT

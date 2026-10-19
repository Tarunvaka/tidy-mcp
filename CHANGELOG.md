# Changelog

All notable changes to tidy-mcp are listed here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-19

First release.

### Added

- `tidy plan / apply / undo / dupes` CLI with a preview table, progress bar and confirmation before applying.
- MCP server (`tidy-mcp`) with `scan_folder`, `describe_file`, `plan_tidy`, `apply_plan`, `undo` and `find_duplicates`.
- Local naming and sorting with Ollama: `qwen2.5:7b` for documents and code, `qwen2.5vl:7b` for images.
- Reads PDFs, Word files, text and code; uses photo EXIF dates.
- Duplicates and installers older than 30 days go to `_tidy_trash/`. Nothing is ever deleted.
- Every applied plan can be undone.
- Config file at `~/.tidy/config.toml`: models, file limit, ignore patterns, folder rules, parallel workers.
- Answer cache, so re-running on the same files is instant.

### Safety

- Plans are dry runs. Files only move after an explicit apply.
- Only the top level of the chosen folder is touched. Hidden files and symlinks are skipped.
- Property-based tests check that no file escapes the allowed folders, nothing is lost, and undo restores everything.

[Unreleased]: https://github.com/Tarunvaka/tidy-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Tarunvaka/tidy-mcp/releases/tag/v0.1.0

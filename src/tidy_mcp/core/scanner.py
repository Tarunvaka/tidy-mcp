"""Find the files in a folder that tidy is allowed to touch."""

from datetime import datetime
from pathlib import Path

import xxhash

from tidy_mcp.core.models import FileInfo, FileKind

TRASH_DIR = "_tidy_trash"

_KINDS: dict[FileKind, set[str]] = {
    FileKind.DOCUMENT: {
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".md",
        ".rtf",
        ".odt",
        ".csv",
        ".xlsx",
        ".xls",
        ".pptx",
        ".ppt",
        ".pages",
        ".numbers",
        ".key",
        ".epub",
    },
    FileKind.IMAGE: {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".bmp", ".tiff", ".svg"},
    FileKind.CODE: {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".c",
        ".cpp",
        ".h",
        ".swift",
        ".kt",
        ".sh",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".html",
        ".css",
        ".sql",
        ".ipynb",
    },
    FileKind.ARCHIVE: {".zip", ".tar", ".gz", ".tgz", ".rar", ".7z", ".bz2", ".xz"},
    FileKind.INSTALLER: {".dmg", ".pkg", ".exe", ".msi", ".deb", ".rpm", ".appimage", ".apk"},
    FileKind.AUDIO: {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"},
    FileKind.VIDEO: {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"},
}
_EXT_TO_KIND = {ext: kind for kind, exts in _KINDS.items() for ext in exts}


def kind_of(path: Path) -> FileKind:
    return _EXT_TO_KIND.get(path.suffix.lower(), FileKind.OTHER)


def file_hash(path: Path) -> str:
    h = xxhash.xxh3_64()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def scan(root: Path, limit: int = 500) -> list[FileInfo]:
    """List regular, non-hidden files directly inside root.

    Only the top level is scanned, so folders the user already organized are left alone.
    Symlinks are skipped so tidy can never reach outside root.
    """
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)

    files: list[FileInfo] = []
    for path in sorted(root.iterdir()):
        if path.name.startswith(".") or path.is_symlink() or not path.is_file():
            continue
        stat = path.stat()
        files.append(
            FileInfo(
                path=path,
                kind=kind_of(path),
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                hash=file_hash(path),
            )
        )
        if len(files) >= limit:
            break
    return files

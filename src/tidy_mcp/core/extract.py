"""Pull a short text sample out of a file so the model has something to read."""

from datetime import datetime
from pathlib import Path

import exifread
from docx import Document
from pypdf import PdfReader

from tidy_mcp.core.models import FileInfo, FileKind

MAX_CHARS = 4000
_TEXT_SUFFIXES = {".txt", ".md", ".csv", ".rtf"}


def extract_text(info: FileInfo, max_chars: int = MAX_CHARS) -> str:
    """Return up to max_chars of readable text, or "" when there is none."""
    try:
        suffix = info.path.suffix.lower()
        if suffix == ".pdf":
            text = _pdf_text(info.path, max_chars)
        elif suffix == ".docx":
            text = "\n".join(p.text for p in Document(str(info.path)).paragraphs)
        elif info.kind == FileKind.CODE or suffix in _TEXT_SUFFIXES:
            with info.path.open("r", encoding="utf-8", errors="replace") as f:
                text = f.read(max_chars)
        else:
            text = ""
    except Exception:
        return ""
    return text[:max_chars].strip()


def _pdf_text(path: Path, max_chars: int) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    title = reader.metadata.title if reader.metadata else None
    if title:
        parts.append(f"Title: {title}")
    for page in reader.pages[:5]:
        parts.append(page.extract_text() or "")
        if sum(map(len, parts)) >= max_chars:
            break
    return "\n".join(parts)


def photo_date(path: Path) -> datetime | None:
    """The date a photo was taken, from EXIF, if present."""
    try:
        with path.open("rb") as f:
            tags = exifread.process_file(f, details=False, stop_tag="DateTimeOriginal")
        value = tags.get("EXIF DateTimeOriginal")
        return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S") if value else None
    except Exception:
        return None

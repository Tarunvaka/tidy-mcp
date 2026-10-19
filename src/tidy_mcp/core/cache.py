"""Remember model answers so re-running tidy on the same files is instant.

Keyed by file contents, file name, the models and the prompt version, so any change re-asks.
"""

import sqlite3
import threading
from pathlib import Path

from tidy_mcp.core.models import Description


class DescriptionCache:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS descriptions (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )

    def get(self, key: str) -> Description | None:
        with self._lock:
            row = self._db.execute(
                "SELECT value FROM descriptions WHERE key = ?", (key,)
            ).fetchone()
        return Description.model_validate_json(row[0]) if row else None

    def put(self, key: str, desc: Description) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO descriptions VALUES (?, ?)", (key, desc.model_dump_json())
            )
            self._db.commit()

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from make_fixtures import make  # noqa: E402


@pytest.fixture
def messy(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("TIDY_HOME", str(tmp_path / "home"))
    return make(tmp_path / "Downloads")

"""User settings from $TIDY_HOME/config.toml, overridable with TIDY_* environment variables.

Example config.toml:

    text_model = "qwen2.5:7b"
    ignore = ["*.part", "keep-*"]

    [[rules]]
    match = "invoice"
    folder = "~/Finance/Invoices"
"""

import fnmatch
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from tidy_mcp.core import store
from tidy_mcp.core.llm import DEFAULT_TEXT_MODEL, DEFAULT_VISION_MODEL
from tidy_mcp.core.models import Description, FileInfo


class Rule(BaseModel):
    """Send files whose new name, category or summary contains `match` to `folder`."""

    match: str
    folder: str

    def applies(self, desc: Description) -> bool:
        needle = self.match.lower()
        return any(needle in s.lower() for s in (desc.name, desc.category, desc.summary))


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TIDY_", extra="ignore")

    text_model: str = DEFAULT_TEXT_MODEL
    vision_model: str = DEFAULT_VISION_MODEL
    ollama_host: str | None = None
    limit: int = 500
    workers: int = 4  # files described at once; Ollama queues anything beyond its own limit
    ignore: list[str] = []
    rules: list[Rule] = []

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        toml = TomlConfigSettingsSource(settings_cls, toml_file=store.home() / "config.toml")
        return init_settings, env_settings, toml

    def ignored(self, info: FileInfo) -> bool:
        return any(fnmatch.fnmatch(info.path.name, pattern) for pattern in self.ignore)

    def rule_folder(self, desc: Description) -> Path | None:
        for rule in self.rules:
            if rule.applies(desc):
                return Path(rule.folder).expanduser()
        return None

"""Ask a local Ollama model to name and categorize a file."""

import re
from dataclasses import dataclass, field

import ollama

from tidy_mcp.core.extract import extract_text, photo_date
from tidy_mcp.core.models import Description, FileInfo, FileKind

DEFAULT_TEXT_MODEL = "qwen2.5:7b"
DEFAULT_VISION_MODEL = "qwen2.5vl:7b"

_DEFAULT_CATEGORY = {
    FileKind.DOCUMENT: "Documents",
    FileKind.IMAGE: "Images",
    FileKind.CODE: "Code",
    FileKind.ARCHIVE: "Archives",
    FileKind.INSTALLER: "Installers",
    FileKind.AUDIO: "Audio",
    FileKind.VIDEO: "Videos",
    FileKind.OTHER: "Other",
}

_PROMPT = """You organize a messy Downloads folder.
Give this file a clear new name and a folder.

Rules:
- name: short, descriptive, words joined by underscores, no extension.
  Start with a date (YYYY-MM-DD) only if the content shows one.
  Examples: 2026-06-12_Amazon_receipt, Lease_Agreement_Bangalore_2025, python_KeyError_traceback
- category: one folder, or two levels joined by "/".
  Prefer: Receipts, Invoices, Documents, Documents/Housing, Travel, Screenshots,
  Screenshots/Code, Photos, Notes, Code, Archives, Installers, Audio, Videos.
- summary: one short sentence.

Current name: {filename}
Type: {kind}
{details}"""


class OllamaUnavailable(RuntimeError):
    """Ollama is not running or a required model is missing."""


@dataclass
class Describer:
    text_model: str = DEFAULT_TEXT_MODEL
    vision_model: str = DEFAULT_VISION_MODEL
    host: str | None = None
    client: ollama.Client = field(init=False)

    def __post_init__(self) -> None:
        self.client = ollama.Client(host=self.host)

    def check(self) -> None:
        """Raise OllamaUnavailable with a fix-it message if tidy cannot run."""
        try:
            installed = {m.model for m in self.client.list().models}
        except Exception as e:
            raise OllamaUnavailable(
                "Can't reach Ollama. Install it from https://ollama.com and start it."
            ) from e
        for model in (self.text_model, self.vision_model):
            if model not in installed and f"{model}:latest" not in installed:
                raise OllamaUnavailable(f"Model {model} is missing. Run: ollama pull {model}")

    def describe(self, info: FileInfo) -> Description:
        """Describe one file. Falls back to a safe default if the model fails."""
        try:
            return _clean(self._ask(info), info)
        except Exception:
            return fallback(info)

    def _ask(self, info: FileInfo) -> Description:
        details: list[str] = []
        images: list[str] | None = None
        model = self.text_model

        if info.kind == FileKind.IMAGE and info.path.suffix.lower() != ".svg":
            model, images = self.vision_model, [str(info.path)]
            details.append("Look at the attached image.")
            if taken := photo_date(info.path):
                details.append(f"Photo taken: {taken:%Y-%m-%d}")
        elif text := extract_text(info):
            details.append(f"Content:\n{text}")
        else:
            details.append(f"No readable content. Modified {info.modified:%Y-%m-%d}.")

        prompt = _PROMPT.format(
            filename=info.path.name, kind=info.kind.value, details="\n".join(details)
        )
        message: dict = {"role": "user", "content": prompt}
        if images:
            message["images"] = images
        response = self.client.chat(
            model=model,
            messages=[message],
            format=Description.model_json_schema(),
            options={"temperature": 0},
        )
        return Description.model_validate_json(response.message.content)


def fallback(info: FileInfo) -> Description:
    return Description(name=info.path.stem, category=_DEFAULT_CATEGORY[info.kind], summary="")


def _clean(desc: Description, info: FileInfo) -> Description:
    name = safe_name(desc.name) or info.path.stem
    parts = [safe_name(p) for p in desc.category.replace("\\", "/").split("/")]
    category = "/".join(p for p in parts[:2] if p) or _DEFAULT_CATEGORY[info.kind]
    return Description(name=name, category=category, summary=desc.summary.strip())


def safe_name(text: str, max_len: int = 80) -> str:
    """Make a string safe to use as a file or folder name."""
    text = re.sub(r"[^\w\-. ]+", "", text, flags=re.UNICODE).strip(" .")
    text = re.sub(r"\s+", "_", text)
    return text[:max_len].strip("_.")

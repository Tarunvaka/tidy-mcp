"""Ask a local Ollama model to name and categorize a file."""

import logging
import re
from dataclasses import dataclass, field

import ollama

from tidy_mcp.core.cache import DescriptionCache
from tidy_mcp.core.extract import extract_text, photo_date
from tidy_mcp.core.models import Description, FileInfo, FileKind

logging.getLogger("exifread").setLevel(logging.ERROR)

DEFAULT_TEXT_MODEL = "qwen2.5:7b"
DEFAULT_VISION_MODEL = "qwen2.5vl:7b"
PROMPT_VERSION = 4  # bump when the prompt or cleanup changes, so cached answers are redone

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

name: short, specific, words joined by underscores, no extension.
  Say what is inside, not just the document type: what the code does, which test a report
  covers, who sent an invoice. Start with a date (YYYY-MM-DD) only if the content shows one.
  Good: Uber_ride_receipt, Blood_test_report_Apollo, SQL_user_order_counts,
  Lease_Agreement_Bangalore_2025, python_KeyError_traceback

category: pick from this list. Add one sub-folder with "/" only when it clearly helps.
  Receipts      - proof of payment: shop, food, ride, app store receipts
  Invoices      - bills asking for payment
  Finance       - bank statements, tax forms, salary slips, expense data
  Work          - resumes, offer letters, meeting notes, pitch decks, work documents
  Travel        - tickets, boarding passes, hotel and travel bookings
  Health        - medical reports, prescriptions
  Documents     - contracts, agreements, warranties, IDs and other official papers
  Papers        - research papers and academic articles
  Notes         - personal notes, to-do lists, shopping lists, recipes, lyrics, study notes
  Screenshots   - every screenshot; use Screenshots/Code for screenshots of code or errors
  Code          - source code, scripts and config files only
  Photos        - camera photos of people, places and things
  Images        - other pictures and graphics
  Data          - spreadsheets and data files
  Archives, Installers, Audio, Videos, Other

summary: one short sentence.

Current name: {filename}
Type: {kind}{screenshot}
{details}"""


class OllamaUnavailable(RuntimeError):
    """Ollama is not running or a required model is missing."""


@dataclass
class Describer:
    text_model: str = DEFAULT_TEXT_MODEL
    vision_model: str = DEFAULT_VISION_MODEL
    host: str | None = None
    cache: DescriptionCache | None = None
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
        key = f"{info.hash}|{info.path.name}|{self.text_model}|{self.vision_model}|{PROMPT_VERSION}"
        if self.cache and (hit := self.cache.get(key)):
            return hit
        try:
            desc, evidence = self._ask(info)
            result = _clean(desc, info, evidence)
        except Exception:
            return fallback(info)
        if self.cache:
            self.cache.put(key, result)
        return result

    def _ask(self, info: FileInfo) -> tuple[Description, str]:
        """The model's answer plus the text it was shown, used to check its dates."""
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
            details.append("No readable content. Name it from the file name and type.")

        screenshot = (
            " (a screenshot)"
            if info.path.name.lower().startswith(("screenshot", "screen shot"))
            else ""
        )
        prompt = _PROMPT.format(
            filename=info.path.name,
            kind=info.kind.value,
            screenshot=screenshot,
            details="\n".join(details),
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
        evidence = info.path.name + "\n" + "\n".join(details)
        return Description.model_validate_json(response.message.content), evidence


def fallback(info: FileInfo) -> Description:
    return Description(name=info.path.stem, category=_DEFAULT_CATEGORY[info.kind], summary="")


_DATE = re.compile(r"(\d{4})[-_.](\d{2})[-_.](\d{2})")


def _drop_invented_dates(name: str, evidence: str) -> str:
    """Remove dates the model made up. A date stays only if the file itself shows it."""
    seen = {m.groups() for m in _DATE.finditer(evidence)}

    def keep(m: re.Match) -> str:
        return m.group(0) if m.groups() in seen else ""

    return re.sub(r"_{2,}", "_", _DATE.sub(keep, name)).strip("_-. ")


def _clean(desc: Description, info: FileInfo, evidence: str = "") -> Description:
    name = safe_name(_drop_invented_dates(desc.name, evidence)) or info.path.stem
    parts = [safe_name(p) for p in desc.category.replace("\\", "/").split("/")]
    category = "/".join(p for p in parts[:2] if p) or _DEFAULT_CATEGORY[info.kind]
    return Description(
        name=name, category=_fix_category(category, info), summary=desc.summary.strip()
    )


def is_screenshot(info: FileInfo) -> bool:
    return info.kind == FileKind.IMAGE and info.path.name.lower().startswith(
        ("screenshot", "screen shot", "cleanshot")
    )


def _fix_category(category: str, info: FileInfo) -> str:
    """Rules the model sometimes breaks: screenshots stay together, Code is for code files."""
    top = category.split("/")[0].lower()
    if is_screenshot(info):
        if top == "screenshots":
            return category
        return "Screenshots/Code" if top == "code" else "Screenshots"
    if top == "code" and info.kind != FileKind.CODE:
        return _DEFAULT_CATEGORY[info.kind]
    return category


def safe_name(text: str, max_len: int = 80) -> str:
    """Make a string safe to use as a file or folder name."""
    text = re.sub(r"[^\w\-. ]+", "", text, flags=re.UNICODE).strip(" .")
    text = re.sub(r"\s+", "_", text)
    return text[:max_len].strip("_.")

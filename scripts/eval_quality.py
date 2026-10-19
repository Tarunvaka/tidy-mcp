"""Score how well the local models name and file a varied set of fake downloads.

Usage: uv run python scripts/eval_quality.py [--workers N]

Each case lists the folders that count as correct (top level) and words the new name must
contain. Needs Ollama running with the configured models.
"""

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from PIL import Image, ImageDraw
from pypdf import PdfWriter

from tidy_mcp.core.config import Config
from tidy_mcp.core.llm import Describer
from tidy_mcp.core.scanner import scan


@dataclass
class Case:
    file: str
    folders: set[str]
    words: list[str]  # each must appear in the name; "a|b" accepts either
    text: str | list[str] = ""


def pdf(path: Path, text: str) -> None:
    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    w.add_metadata({"/Title": text})
    with path.open("wb") as f:
        w.write(f)


def image(path: Path, lines: list[str]) -> None:
    img = Image.new("RGB", (900, 40 + 34 * len(lines)), "white")
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((24, 20 + i * 34), line, fill="black", font_size=24)
    img.save(path)


def docx(path: Path, text: str) -> None:
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    doc.save(str(path))


CASES = [
    Case(
        "IMG_4410.png",
        {"Receipts"},
        ["uber"],
        ["Uber", "Thanks for riding, Tarun", "Trip fare  Rs 312.40", "Total  Rs 312.40"],
    ),
    Case(
        "IMG_4411.png",
        {"Receipts"},
        ["swiggy"],
        ["Swiggy order delivered", "Paneer butter masala x1", "Paid via UPI  Rs 289"],
    ),
    Case(
        "receipt (2).pdf",
        {"Receipts", "Invoices"},
        ["apple"],
        "Apple Store receipt - AirPods Pro - Order W1234 - Total 24,900 INR",
    ),
    Case(
        "doc_2291.pdf",
        {"Invoices"},
        ["invoice"],
        "Invoice INV-7781 from DigitalOcean for cloud hosting, amount due 18 USD",
    ),
    Case(
        "statement.pdf",
        {"Finance"},
        ["statement"],
        "HDFC Bank account statement for September 2026",
    ),
    Case(
        "Form16_final.pdf",
        {"Finance"},
        ["form", "16"],
        "Form 16 TDS certificate for assessment year 2026-27",
    ),
    Case(
        "cv_new_new.docx",
        {"Work"},
        ["resume|cv"],
        "Tarun Vaka\nSoftware Engineer\nExperience: Python, iOS\nEducation: B.Tech CSE",
    ),
    Case(
        "letter.pdf",
        {"Work"},
        ["offer"],
        "Offer letter from Acme Corp for the role of Software Engineer",
    ),
    Case(
        "report_scan.pdf",
        {"Health"},
        ["blood"],
        "Apollo Diagnostics blood test report - hemoglobin, cholesterol, vitamin D",
    ),
    Case(
        "ticket.pdf",
        {"Travel"},
        ["ticket"],
        "IndiGo e-ticket BLR to GOI flight 6E-532, passenger Tarun Vaka",
    ),
    Case(
        "booking-confirmation.pdf",
        {"Travel"},
        ["hotel"],
        "Hotel booking confirmation - Taj Fort Aguada, Goa - 2 nights",
    ),
    Case(
        "Screenshot 2026-10-11 at 09.12.44.png",
        {"Screenshots"},
        ["error"],
        [
            "TypeError: Cannot read properties of undefined (reading 'map')",
            "    at App.render (App.jsx:42)",
        ],
    ),
    Case(
        "Screenshot 2026-10-12 at 18.30.01.png",
        {"Screenshots"},
        ["chat|whatsapp|conversation"],
        ["WhatsApp", "Mom: Did you eat?", "Me: Yes, just had lunch", "Mom: Call me tonight"],
    ),
    Case(
        "image (7).png",
        {"Images", "Notes", "Documents"},
        ["wifi"],
        ["Office WiFi", "Network: ACME-GUEST", "Password: welcome123"],
    ),
    Case(
        "untitled-3.js",
        {"Code"},
        ["debounce"],
        "export function debounce(fn, ms) {\n  let t;\n  return (...a) => {\n"
        "    clearTimeout(t);\n    t = setTimeout(() => fn(...a), ms);\n  };\n}\n",
    ),
    Case(
        "query.sql",
        {"Code"},
        ["user"],
        "SELECT u.id, u.email, COUNT(o.id) AS orders\nFROM users u LEFT JOIN orders o "
        "ON o.user_id = u.id\nGROUP BY u.id;\n",
    ),
    Case(
        "script(1).sh",
        {"Code"},
        ["backup"],
        "#!/bin/bash\n# nightly backup of photos to external drive\n"
        "rsync -av ~/Pictures /Volumes/Backup/\n",
    ),
    Case(
        "config.json",
        {"Code"},
        ["config"],
        '{"apiUrl": "https://api.example.com", "retries": 3, "theme": "dark"}',
    ),
    Case(
        "New Text Document.txt",
        {"Notes"},
        ["todo"],
        "TODO\n- renew passport\n- pay electricity bill\n- book dentist\n",
    ),
    Case(
        "Untitled-7.md",
        {"Notes", "Recipes"},
        ["biryani"],
        "# Chicken biryani\n- basmati rice\n- chicken\n- saffron\nCook rice 70%...",
    ),
    Case(
        "lecture.txt",
        {"Notes"},
        ["neural"],
        "Lecture 4 notes: neural networks, backpropagation, gradient descent.",
    ),
    Case(
        "data.csv",
        {"Data", "Finance"},
        ["expense"],
        "date,category,amount\n2026-10-01,groceries,1200\n2026-10-02,fuel,800\n",
    ),
    Case(
        "2406.01234v2.pdf",
        {"Papers"},
        ["attention"],
        "Paper: Sparse Attention for Long-Context Language Models",
    ),
    Case(
        "minutes.docx",
        {"Work", "Notes"},
        ["meeting"],
        "Team meeting minutes\nAttendees: Tarun, Priya\nDecisions: ship v2 on Friday",
    ),
    Case(
        "agreement_signed.pdf",
        {"Documents"},
        ["rental", "agreement"],
        "Rental agreement between landlord and tenant for flat 302, Indiranagar",
    ),
    Case(
        "warranty.pdf",
        {"Documents"},
        ["warranty"],
        "Samsung refrigerator warranty card, model RT28, valid 1 year",
    ),
    Case(
        "IMG_5001.png",
        {"Documents", "Images"},
        ["id"],
        ["GOVERNMENT OF INDIA", "Identity card (sample)", "Name: SAMPLE PERSON"],
    ),
    Case(
        "slides_export.pdf",
        {"Work"},
        ["pitch"],
        "Pitch deck: tidy-mcp, local AI file organizer, seed round",
    ),
    Case(
        "song_lyrics.txt",
        {"Notes"},
        ["lyrics"],
        "Lyrics draft for my band's new song, verse 1 and chorus",
    ),
    Case("Untitled.txt", {"Notes"}, ["grocery"], "Grocery: milk, eggs, bread, onions, tomatoes"),
]


def build(folder: Path) -> None:
    for case in CASES:
        path = folder / case.file
        if path.suffix == ".pdf":
            pdf(path, str(case.text))
        elif path.suffix == ".png":
            image(path, list(case.text))
        elif path.suffix == ".docx":
            docx(path, str(case.text))
        else:
            path.write_text(str(case.text))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print machine-readable results")
    args = parser.parse_args()

    config = Config()
    describer = Describer(text_model=config.text_model, vision_model=config.vision_model)
    describer.check()

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        build(folder)
        files = {f.path.name: f for f in scan(folder)}
        results = []
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(config.workers) as pool:
            descs = list(pool.map(lambda c: describer.describe(files[c.file]), CASES))
        for case, desc in zip(CASES, descs, strict=True):
            top = desc.category.split("/")[0]
            folder_ok = top in case.folders
            name = desc.name.lower()
            name_ok = all(any(alt in name for alt in w.split("|")) for w in case.words)
            results.append(
                {
                    "file": case.file,
                    "name": desc.name,
                    "category": desc.category,
                    "folder_ok": folder_ok,
                    "name_ok": name_ok,
                }
            )

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            mark = ("✓" if r["folder_ok"] else "✗") + ("✓" if r["name_ok"] else "✗")
            print(f"{mark}  {r['file'][:34]:34}  →  {r['category']}/{r['name']}")
    n = len(results)
    folders = sum(r["folder_ok"] for r in results)
    names = sum(r["name_ok"] for r in results)
    print(f"\nFolder correct: {folders}/{n}   Name has key words: {names}/{n}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

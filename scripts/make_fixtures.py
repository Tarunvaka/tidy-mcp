"""Generate a fake messy Downloads folder for tests and demos.

Usage: uv run python scripts/make_fixtures.py [output_dir]
"""

import os
import shutil
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfWriter

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "messy_downloads"


def _image_with_text(path: Path, lines: list[str], size=(800, 500)) -> None:
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((30, 30 + i * 30), line, fill="black")
    img.save(path)


def _pdf(path: Path, title: str) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": title})
    with path.open("wb") as f:
        writer.write(f)


def make(out: Path) -> Path:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    _image_with_text(
        out / "IMG_2931.png",
        ["Amazon.in Order Receipt", "Order #402-118", "Wireless mouse  Rs 899", "Total  Rs 899"],
    )
    _image_with_text(
        out / "Screenshot 2026-10-02 at 11.04.12.png",
        ["Traceback (most recent call last):", '  File "app.py", line 12', "KeyError: 'user_id'"],
    )
    _image_with_text(out / "image (3).png", ["Boarding pass", "BLR -> DEL", "Seat 14C"])
    _pdf(out / "final_v3_real.pdf", "Residential Lease Agreement Bangalore 2025")
    _pdf(out / "document(1).pdf", "Invoice INV-2041 Acme Cloud Services")
    (out / "notes.txt").write_text(
        "Meeting notes: ship tidy v0.1, record demo GIF, post to Show HN.\n"
    )
    (out / "untitled.py").write_text("def add(a, b):\n    return a + b\n")
    (out / "Untitled-1.md").write_text("# Grocery list\n- milk\n- eggs\n- rice\n")
    (out / "Docker.dmg").write_bytes(os.urandom(2048))
    (out / "zoom_installer.pkg").write_bytes(os.urandom(2048))
    (out / "archive.zip").write_bytes(b"PK\x05\x06" + bytes(18))

    shutil.copy(out / "IMG_2931.png", out / "IMG_2931 (1).png")
    shutil.copy(out / "document(1).pdf", out / "document(2).pdf")

    (out / ".DS_Store").write_bytes(b"\x00")

    old = time.time() - 60 * 60 * 24 * 45
    for name in ("Docker.dmg", "zoom_installer.pkg"):
        os.utime(out / name, (old, old))

    return out


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    print(make(target))

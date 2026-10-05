"""Generate a multi-page test PDF with headings, tables and a planted sentence.

Used by the Stage 4 upload check, the Stage 5 ingestion test, the Stage 7
retrieval probe, and the frontend demo. Run inside the api container:

    docker compose run --rm api python /scripts/seed_demo_pdf.py --out /data/demo.pdf
"""

from __future__ import annotations

import argparse

# `import fitz` is a deprecated alias; bind the modern module name instead.
import pymupdf as fitz

# The planted fact the retrieval probe looks for. Keep this in sync with
# scripts/query_probe.py.
PLANTED_SENTENCE = "The refund window is 30 days from the date of purchase."

SECTIONS: list[tuple[str, str]] = [
    (
        "Refund Policy",
        "Customers may request a refund within the standard window. "
        f"{PLANTED_SENTENCE} Refunds are issued to the original payment method. "
        "Partial refunds apply to used items that fail inspection.",
    ),
    (
        "Shipping Times",
        "Standard shipping takes three to five business days. Express shipping "
        "is available for next-day delivery on orders placed before 14:00. "
        "Remote regions may add two business days.",
    ),
    (
        "Warranty Coverage",
        "All hardware carries a 24-month warranty covering manufacturing "
        "defects. Accidental damage is not covered. Warranty service requires "
        "the original order number.",
    ),
]

TABLE_HEADING = "Plan Comparison"
TABLE_INTRO = "Plans differ in seat count, retention and support response times."

TABLE_ROWS = [
    ["Plan", "Seats", "Retention", "Support"],
    ["Starter", "1", "7 days", "Email (48h)"],
    ["Team", "10", "90 days", "Email (24h)"],
    ["Enterprise", "Unlimited", "Unlimited", "Dedicated (4h)"],
]

FOOTER = "Contexta Py Demo Handbook"


def _footer(page: fitz.Page, page_number: int) -> None:
    """Draw the running footer that also acts as a repeated-line test case."""
    page.insert_text(
        fitz.Point(72, 760),
        f"{FOOTER} - page {page_number}",
        fontsize=8,
        fontname="cour",
    )


def _draw_table(page: fitz.Page, top: float) -> None:
    """Draw a simple comparison table; ``find_tables`` should pick it up."""
    widths = [120, 90, 110, 140]
    x0, row_height = 50, 26
    y = top
    for row_index, row in enumerate(TABLE_ROWS):
        x = x0
        for col_index, cell in enumerate(row):
            rect = fitz.Rect(x, y, x + widths[col_index], y + row_height)
            page.draw_rect(
                rect,
                color=(0.4, 0.4, 0.4),
                fill=(0.92, 0.94, 0.98) if row_index == 0 else None,
                width=0.7,
            )
            inset = fitz.Rect(rect.x0 + 4, rect.y0 + 4, rect.x1 - 4, rect.y1 - 4)
            page.insert_textbox(inset, cell, fontsize=9, fontname="helv", align=0)
            x += widths[col_index]
        y += row_height


def build(path: str, filler_pages: int = 0) -> str:
    doc = fitz.open()
    page_number = 0

    title = doc.new_page()
    page_number += 1
    title.insert_text(fitz.Point(72, 120), "Contexta Py", fontsize=28, fontname="hebo")
    title.insert_text(
        fitz.Point(72, 150),
        "Demo Handbook for Retrieval Testing",
        fontsize=14,
        fontname="helv",
    )
    title.insert_text(
        fitz.Point(72, 200),
        f"Page 1 of a synthetic test document.",
        fontsize=10,
        fontname="cour",
    )

    for heading, body in SECTIONS:
        page = doc.new_page()
        page_number += 1
        page.insert_text(fitz.Point(72, 80), heading, fontsize=18, fontname="hebo")
        page.insert_textbox(
            fitz.Rect(72, 100, 540, 700), body, fontsize=11, fontname="helv", lineheight=1.4
        )
        _footer(page, page_number)

    page = doc.new_page()
    page_number += 1
    page.insert_text(fitz.Point(72, 80), TABLE_HEADING, fontsize=18, fontname="hebo")
    page.insert_textbox(
        fitz.Rect(72, 100, 540, 140), TABLE_INTRO, fontsize=11, fontname="helv"
    )
    _draw_table(page, 170)
    _footer(page, page_number)

    for index in range(filler_pages):
        page = doc.new_page()
        page_number += 1
        page.insert_text(
            fitz.Point(72, 80), f"Appendix {index + 1}", fontsize=16, fontname="hebo"
        )
        page.insert_textbox(
            fitz.Rect(72, 110, 540, 700),
            (
                "This filler page exists to exercise the ingestion pipeline. "
                f"Section {index + 1} describes operational detail number "
                f"{index * 7 + 3} for the processing benchmark."
            ),
            fontsize=11,
            fontname="helv",
            lineheight=1.4,
        )
        _footer(page, page_number)

    doc.set_metadata({"title": "Contexta Py Demo Handbook", "author": "seed_demo_pdf.py"})
    doc.save(path)
    count = doc.page_count
    doc.close()
    print(f"wrote {path} ({count} pages, planted: {PLANTED_SENTENCE!r})")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic test PDF.")
    parser.add_argument("--out", default="/data/contexta-demo.pdf", help="output path")
    parser.add_argument(
        "--filler-pages", type=int, default=0, help="extra pages for load testing"
    )
    args = parser.parse_args()
    build(args.out, args.filler_pages)


if __name__ == "__main__":
    main()

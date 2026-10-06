"""Layout-aware PDF parsing.

PyMuPDF (via ``pymupdf4llm``) converts each page to Markdown, which preserves
headings, reading order, lists and code blocks far better than raw text
extraction. Tables are additionally extracted through ``page.find_tables()`` so
they can be indexed and summarised as first-class chunks.

Everything here is CPU-bound and therefore runs in a worker thread; the public
API is async so callers never block the event loop.
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

import pymupdf
import pymupdf4llm
import structlog

from app.core.config import Settings, get_settings

log = structlog.get_logger("contexta.parser")

_WHITESPACE_RUN = re.compile(r"\n{3,}")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")


@dataclass
class ParsedPage:
    """One page of the document."""

    page_number: int
    #: Prose only; text belonging to detected tables is excluded.
    markdown: str
    #: Table Markdown blocks found on this page.
    tables: list[str] = field(default_factory=list)


@dataclass
class ParsedDocument:
    pages: list[ParsedPage]
    page_count: int

    @property
    def full_markdown(self) -> str:
        return "\n\n".join(
            f"<!-- page {page.page_number} -->\n{page.markdown}" for page in self.pages
        )

    def iter_tables(self) -> list[tuple[int, str]]:
        """Yield `(page_number, table_markdown)` for every table in order."""
        return [(page.page_number, table) for page in self.pages for table in page.tables]


def _normalise(text: str) -> str:
    """Collapse whitespace runs and strip trailing spaces per line."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return _WHITESPACE_RUN.sub("\n\n", "\n".join(lines)).strip()


def _repeated_lines(page_texts: Sequence[str], ratio: float) -> set[str]:
    """Find lines that appear on more than `ratio` of pages.

    These are page headers/footers (running titles, page numbers) rather than
    content, and they pollute both embeddings and citations if left in.
    """
    if len(page_texts) < 3:
        return set()
    counter: Counter[str] = Counter()
    for text in page_texts:
        # Count each line once per page at most.
        for line in {stripped for stripped in (ln.strip() for ln in text.split("\n"))}:
            if len(line) >= 3 and not _BULLET.match(line):
                counter[line] += 1
    threshold = max(2, int(len(page_texts) * ratio))
    return {line for line, count in counter.items() if count > threshold}


def _strip_repeated(text: str, repeated: set[str]) -> str:
    if not repeated:
        return text
    kept = [line for line in text.split("\n") if line.strip() not in repeated]
    return _normalise("\n".join(kept))


def _blocks_excluding(page: pymupdf.Page, bboxes: Sequence[Sequence[float]]) -> str:
    """Re-extract a page's prose from text blocks, skipping table regions.

    `pymupdf4llm` already renders detected tables inside the page Markdown.
    Rebuilding prose from blocks for table pages lets the table chunks own that
    content exclusively, so it is not embedded twice.
    """
    if not bboxes:
        return ""
    try:
        blocks = page.get_text("blocks")
    except Exception:  # fall back to the Markdown we already have
        return ""
    keep: list[tuple[float, float, str]] = []
    for block in blocks:
        x0, y0, x1, y1, content = block[0], block[1], block[2], block[3], block[4]
        if not isinstance(content, str) or not content.strip():
            continue
        overlaps = any(
            not (x1 <= bx0 or x0 >= bx1 or y1 <= by0 or y0 >= by1) for bx0, by0, bx1, by1 in bboxes
        )
        if not overlaps:
            keep.append((y0, x0, content))
    keep.sort(key=lambda item: (round(item[0], 1), item[1]))
    return _normalise("\n".join(text for _, _, text in keep))


def _extract_tables(page: pymupdf.Page) -> tuple[list[str], list[tuple[float, ...]]]:
    """Return `(table markdown, bounding boxes)` for one page."""
    try:
        finder = page.find_tables()
    except Exception:  # table detection is best effort
        return [], []
    tables: list[str] = []
    bboxes: list[tuple[float, ...]] = []
    for table in finder.tables:
        try:
            markdown = table.to_markdown()
        except Exception:
            continue
        if not markdown or not markdown.strip():
            continue
        tables.append(markdown.strip())
        bbox = tuple(float(v) for v in table.bbox)
        bboxes.append(bbox)  # type: ignore[arg-type]
    return tables, bboxes


def _parse_sync(data: bytes, settings: Settings) -> ParsedDocument:
    """Blocking parse; always invoked through `asyncio.to_thread`."""
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        chunks = pymupdf4llm.to_markdown(doc, page_chunks=True)
        raw: dict[int, str] = {}
        for index, chunk in enumerate(chunks):
            page_number = int(chunk.get("metadata", {}).get("page_number") or index + 1)
            raw[page_number] = chunk.get("text", "") or ""

        repeated = _repeated_lines(
            [raw.get(n, "") for n in sorted(raw)], settings.header_footer_ratio
        )
        if repeated:
            log.debug("stripping_repeated_lines", count=len(repeated))

        pages: list[ParsedPage] = []
        for page in doc:
            page_number = page.number + 1
            markdown = _strip_repeated(raw.get(page_number, ""), repeated)
            tables, bboxes = _extract_tables(page)
            if tables:
                # Drop the table text from the prose so it is not double-embedded.
                prose = _blocks_excluding(page, bboxes)
                markdown = _strip_repeated(prose, repeated) or markdown
            if not markdown and not tables:
                # Image-only page: keep a placeholder so page numbers stay aligned.
                markdown = f"<!-- page {page_number}: no extractable text -->"
            pages.append(ParsedPage(page_number=page_number, markdown=markdown, tables=tables))
        page_count = doc.page_count
    return ParsedDocument(pages=pages, page_count=page_count)


async def parse_pdf(data: bytes, *, settings: Settings | None = None) -> ParsedDocument:
    """Parse PDF bytes into per-page Markdown plus extracted tables."""
    cfg = settings or get_settings()
    if cfg.parser == "docling":
        # Reserved for the optional heavy path; see PLAN.md S19.06.
        log.warning("parser_downgrade", requested="docling", using="pymupdf")
    return await asyncio.to_thread(_parse_sync, data, cfg)

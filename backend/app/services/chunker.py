"""Hierarchical (parent-child) chunking.

Large *parent* windows (~2000 chars) preserve the surrounding context; small
*child* windows (~400 chars) are what actually gets embedded and indexed.
Retrieval therefore stays precise while the generator can still be shown the
parent paragraph when it needs to expand on a hit.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.services.parser import ParsedDocument

#: Split after sentence punctuation, keeping the delimiter with the sentence.
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_WHITESPACE = re.compile(r"[ \t]+")


@dataclass
class ChunkDraft:
    """A chunk awaiting persistence and embedding."""

    content: str
    parent_content: str
    page_number: int
    is_table: bool = False
    char_start: int | None = None
    char_end: int | None = None
    #: Index of the parent window this child came from.
    parent_index: int = 0
    #: LLM-written summary, populated for table chunks during ingestion.
    summary: str | None = None

    @property
    def search_text(self) -> str:
        """Text handed to the embedder; a table summary leads its cell values."""
        if self.is_table and self.summary:
            return f"{self.summary}\n\n{self.content}"
        return self.content


def _normalise(text: str) -> str:
    text = _WHITESPACE.sub(" ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _sentences(text: str) -> Iterator[str]:
    """Yield sentence-ish units, preserving order."""
    for part in _SENTENCE.split(text):
        part = part.strip()
        if part:
            yield part


def _windows(
    sentences: list[str], size: int, overlap: int, min_size: int
) -> Iterator[tuple[str, int, int]]:
    """Greedy sentence packing into `size`-char windows with `overlap` carry-back.

    Yields `(text, start_offset, end_offset)`. Offsets are relative to the input
    string and are approximate, which is sufficient for citation highlighting.
    """
    if not sentences:
        return
    start = 0
    cursor = 0
    buffer: list[str] = []
    length = 0
    for sentence in sentences:
        # A single oversized sentence (a wide table row, for example) still
        # becomes its own window rather than being dropped.
        if buffer and length + len(sentence) + 1 > size:
            text = " ".join(buffer)
            yield text, start, cursor
            carry: list[str] = []
            carried = 0
            for previous in reversed(buffer):
                if carried + len(previous) > overlap:
                    break
                carry.insert(0, previous)
                carried += len(previous) + 1
            buffer = carry
            length = carried
            start = cursor
        buffer.append(sentence)
        length += len(sentence) + 1
        cursor += len(sentence) + 1
    if buffer:
        text = " ".join(buffer)
        yield text, start, cursor


def _child_windows(
    parent: str, child_size: int, overlap: int, min_size: int
) -> Iterator[tuple[str, int, int]]:
    """Split one parent window into overlapping child windows."""
    sentences = list(_sentences(parent))
    if not sentences:
        return
    if len(parent) <= child_size:
        yield parent, 0, len(parent)
        return
    yield from _windows(sentences, child_size, overlap, min_size)


def build_drafts(parsed: ParsedDocument, settings: Settings | None = None) -> list[ChunkDraft]:
    """Turn a parsed document into ordered child chunks.

    Tables become their own chunks (`is_table=True`) so they can receive an LLM
    summary, which is what makes them findable by meaning rather than by exact
    cell values.
    """
    cfg = settings or get_settings()
    drafts: list[ChunkDraft] = []
    parent_index = 0

    for page in parsed.pages:
        prose = page.markdown
        parent_offsets: list[tuple[int, int]] = []
        for text, start, end in _windows(
            list(_sentences(prose)),
            cfg.chunk_parent_size,
            cfg.chunk_child_overlap,
            cfg.chunk_min_size,
        ):
            parent_offsets.append((start, end))
            for child, child_start, child_end in _child_windows(
                text, cfg.chunk_child_size, cfg.chunk_child_overlap, cfg.chunk_min_size
            ):
                drafts.append(
                    ChunkDraft(
                        content=child,
                        parent_content=text,
                        page_number=page.page_number,
                        is_table=False,
                        char_start=child_start,
                        char_end=child_end,
                        parent_index=parent_index,
                    )
                )
            parent_index += 1

        for table in page.tables:
            for text, start, end in _child_windows(
                table, cfg.chunk_child_size, cfg.chunk_child_overlap, cfg.chunk_min_size
            ):
                drafts.append(
                    ChunkDraft(
                        content=text,
                        parent_content=table,
                        page_number=page.page_number,
                        is_table=True,
                        char_start=start,
                        char_end=end,
                        parent_index=parent_index,
                    )
                )
            parent_index += 1

    return [draft for draft in drafts if draft.content.strip()]


def iter_tables(parsed: ParsedDocument) -> Iterable[tuple[int, str]]:
    """Expose `(page_number, markdown)` table pairs."""
    return parsed.iter_tables()

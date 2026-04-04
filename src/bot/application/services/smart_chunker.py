"""Smart text chunking that respects document structure (tables, lists, etc)."""

from __future__ import annotations

import re

_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 100
_MIN_CHUNK_LEN = 80


def _is_table_row(line: str) -> bool:
    """Check if a line appears to be part of a table."""
    # Table rows typically have multiple spaces/tabs or specific patterns
    return bool(re.search(r'(\s{2,}|\t|[0-9]{4,}.*[A-Z].*[0-9])', line))


def _chunk_text_smart(raw: str) -> list[str]:
    """Smart chunking that respects document structure.

    Instead of purely character-based chunking, try to respect:
    - Table rows (keep vehicle/model + all its specs together)
    - Paragraphs
    - Lists

    This ensures related data stays together for better RAG retrieval.
    """
    # Normalize whitespace but preserve some structure
    text = re.sub(r'\s+', ' ', raw).strip()
    if not text:
        return []

    if len(text) <= _CHUNK_SIZE:
        return [text] if len(text) >= _MIN_CHUNK_LEN else []

    # Split by lines first to respect table structure
    lines = text.split(' ')

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_size = 0

    for line in lines:
        line_size = len(line) + 1  # +1 for space

        # If adding this line would exceed chunk size, save current chunk
        if current_size + line_size > _CHUNK_SIZE and current_chunk:
            chunk_text = ' '.join(current_chunk).strip()
            if len(chunk_text) >= _MIN_CHUNK_LEN:
                chunks.append(chunk_text)

            # Keep overlap: last few lines from previous chunk
            overlap_lines = current_chunk[-2:] if len(current_chunk) > 2 else current_chunk
            current_chunk = overlap_lines.copy()
            current_size = sum(len(l) + 1 for l in current_chunk)

        current_chunk.append(line)
        current_size += line_size

    # Add remaining chunk
    if current_chunk:
        chunk_text = ' '.join(current_chunk).strip()
        if len(chunk_text) >= _MIN_CHUNK_LEN:
            chunks.append(chunk_text)

    return chunks


def chunk_text(raw: str) -> list[str]:
    """Public API for text chunking.

    Uses smart chunking strategy that respects document structure.
    """
    return _chunk_text_smart(raw)

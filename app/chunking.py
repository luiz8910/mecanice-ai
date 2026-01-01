from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class Chunk:
    text: str
    start: int
    end: int


def simple_chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> List[Chunk]:
    """Simple character-based chunker. Good enough for MVP."""
    text = (text or "").strip()
    if not text:
        return []

    chunks: List[Chunk] = []
    i = 0
    n = len(text)

    while i < n:
        j = min(i + chunk_size, n)
        chunk = text[i:j].strip()
        if chunk:
            chunks.append(Chunk(text=chunk, start=i, end=j))
        if j == n:
            break
        i = max(0, j - overlap)

    return chunks

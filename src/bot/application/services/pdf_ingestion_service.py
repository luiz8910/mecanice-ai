"""PDF ingestion service: extract text → chunk → embed → store in rag_chunks.

Pipeline per catalog:
  1. Mark catalog as 'processing'
  2. Auto-detect brand from filename/content
  3. Delete any previously stored chunks for this catalog
  4. Open PDF with PyMuPDF, extract text page by page
  5. Split each page into overlapping character-level chunks
  6. Embed chunks in batches via EmbeddingsAdapter
  7. Persist chunks to rag_chunks
  8. Mark catalog as 'ready' (or 'error' on failure)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import fitz  # PyMuPDF

from src.bot.application.services.brand_detector import extract_brand
from src.bot.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from src.bot.adapters.driven.db.repositories.catalog_repo_sa import (
        CatalogRepoSqlAlchemy,
    )
    from src.bot.adapters.driven.db.repositories.rag_chunk_repo_sa import (
        RagChunkRepoSqlAlchemy,
    )
    from src.bot.adapters.driven.llm.embeddings_adapter import EmbeddingsAdapter

logger = get_logger(__name__)

_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 100
_MIN_CHUNK_LEN = 80
_EMBED_BATCH = 50


def _chunk_text(raw: str) -> list[str]:
    """Normalize whitespace then split into overlapping chunks."""
    text = re.sub(r"\s+", " ", raw).strip()
    if not text:
        return []
    if len(text) <= _CHUNK_SIZE:
        return [text] if len(text) >= _MIN_CHUNK_LEN else []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + _CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if len(chunk) >= _MIN_CHUNK_LEN:
            chunks.append(chunk)
        start += _CHUNK_SIZE - _CHUNK_OVERLAP

    return chunks


class PdfIngestionService:
    def __init__(
        self,
        catalog_repo: "CatalogRepoSqlAlchemy",
        chunk_repo: "RagChunkRepoSqlAlchemy",
        embeddings: "EmbeddingsAdapter",
    ) -> None:
        self._catalog_repo = catalog_repo
        self._chunk_repo = chunk_repo
        self._embeddings = embeddings

    async def ingest(self, catalog_id: int, pdf_path: str) -> None:
        """Full ingestion pipeline for one PDF.  Raises on unrecoverable errors."""
        try:
            self._catalog_repo.update_status(catalog_id, "processing")
            self._chunk_repo.delete_by_catalog_id(catalog_id)

            catalog = self._catalog_repo.get_by_id(catalog_id)
            chunks_data: list[dict] = []

            # Auto-detect brand from filename
            detected_brand = extract_brand(catalog["original_filename"])
            if detected_brand and not catalog.get("brand"):
                logger.info("Catalog %d: auto-detected brand = %s", catalog_id, detected_brand)
                # Update catalog with detected brand
                self._catalog_repo.update_brand(catalog_id, detected_brand)
                catalog["brand"] = detected_brand
            else:
                brand_source = "provided" if catalog.get("brand") else "not found"
                logger.info("Catalog %d: brand = %s (%s)", catalog_id, catalog.get("brand"), brand_source)

            with fitz.open(pdf_path) as doc:
                page_count = len(doc)
                for page_num, page in enumerate(doc, start=1):
                    page_text = page.get_text()
                    if not page_text or not page_text.strip():
                        continue
                    for chunk_idx, chunk in enumerate(_chunk_text(page_text)):
                        chunks_data.append(
                            {
                                "source_id": str(catalog_id),
                                "source_type": "catalog",
                                "chunk_text": chunk,
                                "brand": catalog.get("brand"),
                                "metadata": {
                                    "catalog_id": catalog_id,
                                    "manufacturer_id": catalog.get("manufacturer_id"),
                                    "original_filename": catalog["original_filename"],
                                    "page": page_num,
                                    "chunk_index": chunk_idx,
                                },
                            }
                        )

            if not chunks_data:
                logger.warning(
                    "No text extracted from catalog %d — PDF may be image-only", catalog_id
                )
                self._catalog_repo.update_status(
                    catalog_id,
                    "error",
                    page_count=page_count,
                    chunk_count=0,
                    error_message=(
                        "Nenhum texto extraído. O PDF pode ser baseado em imagens "
                        "(scans sem OCR)."
                    ),
                )
                return

            # ── embed in batches ──────────────────────────────────────
            texts = [c["chunk_text"] for c in chunks_data]
            total_batches = (len(texts) + _EMBED_BATCH - 1) // _EMBED_BATCH
            all_embeddings: list[list[float]] = []

            for i in range(0, len(texts), _EMBED_BATCH):
                batch_texts = texts[i : i + _EMBED_BATCH]
                batch_embs = await self._embeddings.embed_texts(batch_texts)
                all_embeddings.extend(batch_embs)
                logger.info(
                    "Catalog %d: embedded batch %d/%d",
                    catalog_id,
                    i // _EMBED_BATCH + 1,
                    total_batches,
                )

            for i, emb in enumerate(all_embeddings):
                chunks_data[i]["embedding"] = emb

            self._chunk_repo.insert_chunks(chunks_data)

            self._catalog_repo.update_status(
                catalog_id,
                "ready",
                page_count=page_count,
                chunk_count=len(chunks_data),
            )
            logger.info(
                "Catalog %d ingested successfully: %d pages, %d chunks",
                catalog_id,
                page_count,
                len(chunks_data),
            )

        except Exception as exc:
            logger.exception("Ingestion failed for catalog %d: %s", catalog_id, exc)
            try:
                self._catalog_repo.update_status(
                    catalog_id,
                    "error",
                    error_message=str(exc)[:500],
                )
            except Exception:
                pass
            raise

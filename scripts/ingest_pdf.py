from __future__ import annotations

import argparse
from pathlib import Path
import fitz  # PyMuPDF

from app.chunking import simple_chunk_text
from app.embeddings import get_embeddings_provider
from app.db import insert_chunk


def extract_text_from_pdf(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    parts = []
    for page in doc:
        parts.append(page.get_text("text"))
    return "\n".join(parts)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="Path to PDF")
    parser.add_argument("--source-id", required=False, help="Logical source id (default=filename)")
    parser.add_argument("--source-type", default="catalog", help="catalog|manual|unknown")
    parser.add_argument("--chunk-size", type=int, default=900)
    parser.add_argument("--overlap", type=int, default=120)
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    source_id = args.source_id or pdf_path.name
    source_type = args.source_type

    text = extract_text_from_pdf(pdf_path)
    chunks = simple_chunk_text(text, chunk_size=args.chunk_size, overlap=args.overlap)

    embedder = get_embeddings_provider()

    inserted = 0
    for idx, ch in enumerate(chunks):
        emb = await embedder.embed(ch.text)
        insert_chunk(
            source_id=source_id,
            source_type=source_type,
            chunk_text=ch.text,
            embedding=emb,
            metadata={"pdf": str(pdf_path), "chunk_index": idx, "start": ch.start, "end": ch.end},
        )
        inserted += 1

    print(f"Inserted {inserted} chunks from {pdf_path} (source_id={source_id})")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

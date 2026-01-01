from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from app.chunking import simple_chunk_text
from app.embeddings import get_embeddings_provider
from app.db import insert_chunk


def row_to_text(row: dict) -> str:
    # You can customize: keep only columns you care about.
    # MVP: stringify key/value pairs
    parts = []
    for k, v in row.items():
        if pd.isna(v):
            continue
        s = str(v).strip()
        if not s:
            continue
        parts.append(f"{k}: {s}")
    return " | ".join(parts)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to CSV/XLSX")
    parser.add_argument("--source-id", required=False, help="Logical source id (default=filename)")
    parser.add_argument("--source-type", default="catalog", help="catalog|manual|unknown")
    parser.add_argument("--limit", type=int, default=0, help="Limit rows for MVP tests (0=all)")
    args = parser.parse_args()

    path = Path(args.csv)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    source_id = args.source_id or path.name
    source_type = args.source_type

    if path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    if args.limit and args.limit > 0:
        df = df.head(args.limit)

    embedder = get_embeddings_provider()

    inserted = 0
    for idx, rec in enumerate(df.to_dict(orient="records")):
        text = row_to_text(rec)
        if not text.strip():
            continue

        # optionally chunk long rows
        for sub_idx, ch in enumerate(simple_chunk_text(text, chunk_size=900, overlap=80)):
            emb = await embedder.embed(ch.text)
            insert_chunk(
                source_id=source_id,
                source_type=source_type,
                chunk_text=ch.text,
                embedding=emb,
                metadata={"file": str(path), "row_index": idx, "sub_chunk": sub_idx},
            )
            inserted += 1

    print(f"Inserted {inserted} chunks from {path} (source_id={source_id})")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

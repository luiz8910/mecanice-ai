"""Admin endpoints for parts-catalog PDF upload and RAG query.

Routes (all require admin auth):
  POST   /admin/catalogs          — upload a PDF catalog (async ingestion)
                                    accepts: brand (optional), manufacturer_id, description
  GET    /admin/catalogs          — list catalog documents
                                    filters: brand, manufacturer_id, status, include_inactive
  GET    /admin/catalogs/{id}     — get one catalog document
  DELETE /admin/catalogs/{id}     — soft-delete catalog (mark inactive, keep data)
                                    ?hard=true for physical deletion
  POST   /admin/catalogs/query    — RAG query against ingested catalogs
                                    filters: brand, manufacturer_id, catalog_id
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
)

from src.bot.adapters.driven.db.repositories.catalog_repo_sa import CatalogRepoSqlAlchemy
from src.bot.adapters.driven.db.repositories.rag_chunk_repo_sa import RagChunkRepoSqlAlchemy
from src.bot.adapters.driven.db.session import SessionLocal
from src.bot.adapters.driven.llm.embeddings_adapter import EmbeddingsAdapter
from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_catalog_repo,
    get_rag_chunk_repo,
)
from src.bot.adapters.driver.fastapi.schemas.catalogs import (
    CatalogDocumentResponse,
    RagQueryRequest,
    RagQueryResponse,
    RagQuerySource,
)
from src.bot.application.services.pdf_ingestion_service import PdfIngestionService
from src.bot.application.services.rag_query_service import RagQueryService
from src.bot.infrastructure.config.settings import settings
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/catalogs", tags=["admin-catalogs"])

_ALLOWED_MIME = {"application/pdf", "application/octet-stream"}


def _upload_dir() -> Path:
    path = Path(settings.CATALOG_UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ── Background ingestion ──────────────────────────────────────────────

def _ingest_background(catalog_id: int, pdf_path: str) -> None:
    """Run async ingestion in a new event loop (for threading)."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_ingest_background_async(catalog_id, pdf_path))
    finally:
        loop.close()


async def _ingest_background_async(catalog_id: int, pdf_path: str) -> None:
    """Creates its own DB session so the request session can be closed."""
    session = SessionLocal()
    try:
        service = PdfIngestionService(
            catalog_repo=CatalogRepoSqlAlchemy(session),
            chunk_repo=RagChunkRepoSqlAlchemy(session),
            embeddings=EmbeddingsAdapter(settings),
        )
        await service.ingest(catalog_id, pdf_path)
    except Exception as exc:
        logger.error("Background ingestion failed for catalog %d: %s", catalog_id, exc)
    finally:
        session.close()


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=CatalogDocumentResponse,
    status_code=202,
    summary="Upload a PDF parts catalog",
    dependencies=[Depends(require_admin)],
)
async def upload_catalog(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="PDF catalog file")],
    manufacturer_id: Annotated[int | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    brand: Annotated[str | None, Form()] = None,
    catalog_repo: CatalogRepoSqlAlchemy = Depends(get_catalog_repo),
) -> CatalogDocumentResponse:
    if (file.content_type not in _ALLOWED_MIME and
            not (file.filename or "").lower().endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Somente arquivos PDF são aceitos.")

    content = await file.read()
    stored_filename = f"{uuid.uuid4().hex}.pdf"
    stored_path = _upload_dir() / stored_filename
    stored_path.write_bytes(content)

    catalog = catalog_repo.create(
        {
            "manufacturer_id": manufacturer_id,
            "original_filename": file.filename or stored_filename,
            "stored_filename": stored_filename,
            "file_size_bytes": len(content),
            "description": description,
            "brand": brand,
        }
    )

    # Schedule background ingestion in a separate thread
    thread = threading.Thread(
        target=_ingest_background,
        args=(catalog["id"], str(stored_path)),
        daemon=True,
    )
    thread.start()

    return CatalogDocumentResponse(**catalog)


@router.get(
    "",
    response_model=list[CatalogDocumentResponse],
    summary="List catalog documents",
    dependencies=[Depends(require_admin)],
)
async def list_catalogs(
    manufacturer_id: int | None = None,
    status: str | None = None,
    brand: str | None = None,
    include_inactive: bool = False,
    limit: int = 100,
    offset: int = 0,
    catalog_repo: CatalogRepoSqlAlchemy = Depends(get_catalog_repo),
) -> list[CatalogDocumentResponse]:
    rows = catalog_repo.list_catalogs(
        manufacturer_id=manufacturer_id,
        status=status,
        brand=brand,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    return [CatalogDocumentResponse(**r) for r in rows]


# NOTE: /query must be declared BEFORE /{catalog_id} so FastAPI
# doesn't try to parse "query" as an integer path parameter.
@router.post(
    "/query",
    response_model=RagQueryResponse,
    summary="RAG query against ingested catalogs",
    dependencies=[Depends(require_admin)],
)
async def query_catalogs(
    body: RagQueryRequest,
    chunk_repo: RagChunkRepoSqlAlchemy = Depends(get_rag_chunk_repo),
) -> RagQueryResponse:
    service = RagQueryService(
        chunk_repo=chunk_repo,
        embeddings=EmbeddingsAdapter(settings),
        settings=settings,
    )
    result = await service.query(
        body.query,
        manufacturer_id=body.manufacturer_id,
        catalog_id=body.catalog_id,
        brand=body.brand,
        top_k=body.top_k,
    )
    return RagQueryResponse(
        answer=result["answer"],
        sources=[RagQuerySource(**s) for s in result["sources"]],
    )


@router.get(
    "/{catalog_id}",
    response_model=CatalogDocumentResponse,
    summary="Get a catalog document",
    dependencies=[Depends(require_admin)],
)
async def get_catalog(
    catalog_id: int,
    catalog_repo: CatalogRepoSqlAlchemy = Depends(get_catalog_repo),
) -> CatalogDocumentResponse:
    return CatalogDocumentResponse(**catalog_repo.get_by_id(catalog_id))


@router.delete(
    "/{catalog_id}",
    status_code=204,
    summary="Delete a catalog (soft-delete by default, or hard-delete with hard=true)",
    dependencies=[Depends(require_admin)],
)
async def delete_catalog(
    catalog_id: int,
    hard: bool = False,
    catalog_repo: CatalogRepoSqlAlchemy = Depends(get_catalog_repo),
    chunk_repo: RagChunkRepoSqlAlchemy = Depends(get_rag_chunk_repo),
) -> Response:
    # Fetch first so we get the stored filename (raises 404 if missing)
    catalog = catalog_repo.get_by_id(catalog_id)

    if hard:
        # Hard delete: remove chunks and file
        chunk_repo.delete_by_catalog_id(catalog_id)
        stored_path = Path(settings.CATALOG_UPLOAD_DIR) / catalog["stored_filename"]
        if stored_path.exists():
            stored_path.unlink()
        catalog_repo.delete(catalog_id)
    else:
        # Soft delete: mark as inactive
        catalog_repo.deactivate(catalog_id)

    return Response(status_code=204)

"""Repository dependencies for FastAPI (driver adapter)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from src.bot.adapters.driven.db.session import get_session
from src.bot.adapters.driven.db.repositories.mechanic_repo_sa import (
	MechanicRepoSqlAlchemy,
)
from src.bot.adapters.driven.db.repositories.browser_auth_repo_sa import (
    BrowserAuthRepoSqlAlchemy,
)
from src.bot.adapters.driven.db.repositories.browser_thread_repo_sa import (
    BrowserThreadRepoSqlAlchemy,
)
from src.bot.adapters.driven.db.repositories.llm_call_log_repo_sa import (
    LlmCallLogRepoSqlAlchemy,
)
from src.bot.adapters.driven.db.repositories.quote_workflow_repo_sa import (
	QuoteWorkflowRepoSqlAlchemy,
)
from src.bot.adapters.driven.db.repositories.quotation_repo_sa import QuotationRepoSqlAlchemy
from src.bot.adapters.driven.db.repositories.seller_credential_repo_sa import SellerCredentialRepoSqlAlchemy
from src.bot.adapters.driven.db.repositories.quotation_item_repo_sa import QuotationItemRepoSqlAlchemy
from src.bot.adapters.driven.db.repositories.vendor_repo_sa import VendorRepoSqlAlchemy
from src.bot.adapters.driven.db.repositories.workshop_repo_sa import WorkshopRepoSqlAlchemy
from src.bot.adapters.driven.db.repositories.manufacturer_repo_sa import ManufacturerRepoSqlAlchemy
from src.bot.adapters.driven.db.repositories.vehicle_repo_sa import VehicleRepoSqlAlchemy
from src.bot.adapters.driven.db.repositories.catalog_repo_sa import CatalogRepoSqlAlchemy
from src.bot.adapters.driven.db.repositories.rag_chunk_repo_sa import RagChunkRepoSqlAlchemy


def get_mechanic_repo(
	session: Session = Depends(get_session),
) -> MechanicRepoSqlAlchemy:
	return MechanicRepoSqlAlchemy(session)


def get_browser_auth_repo(
    session: Session = Depends(get_session),
) -> BrowserAuthRepoSqlAlchemy:
    return BrowserAuthRepoSqlAlchemy(session)


def get_browser_thread_repo(
    session: Session = Depends(get_session),
) -> BrowserThreadRepoSqlAlchemy:
    return BrowserThreadRepoSqlAlchemy(session)


def get_llm_call_log_repo(
    session: Session = Depends(get_session),
) -> LlmCallLogRepoSqlAlchemy:
    return LlmCallLogRepoSqlAlchemy(session)


def get_workshop_repo(
	session: Session = Depends(get_session),
) -> WorkshopRepoSqlAlchemy:
	return WorkshopRepoSqlAlchemy(session)


def get_quote_workflow_repo(
	session: Session = Depends(get_session),
) -> QuoteWorkflowRepoSqlAlchemy:
	return QuoteWorkflowRepoSqlAlchemy(session)


def get_quotation_repo(
	session: Session = Depends(get_session),
) -> QuotationRepoSqlAlchemy:
	return QuotationRepoSqlAlchemy(session)


def get_seller_credential_repo(
	session: Session = Depends(get_session),
) -> SellerCredentialRepoSqlAlchemy:
	return SellerCredentialRepoSqlAlchemy(session)


def get_quotation_item_repo(
	session: Session = Depends(get_session),
) -> QuotationItemRepoSqlAlchemy:
	return QuotationItemRepoSqlAlchemy(session)


def get_vendor_repo(
	session: Session = Depends(get_session),
) -> VendorRepoSqlAlchemy:
	return VendorRepoSqlAlchemy(session)


def get_manufacturer_repo(
    session: Session = Depends(get_session),
) -> ManufacturerRepoSqlAlchemy:
    return ManufacturerRepoSqlAlchemy(session)


def get_vehicle_repo(
    session: Session = Depends(get_session),
) -> VehicleRepoSqlAlchemy:
    return VehicleRepoSqlAlchemy(session)


def get_catalog_repo(
    session: Session = Depends(get_session),
) -> CatalogRepoSqlAlchemy:
    return CatalogRepoSqlAlchemy(session)


def get_rag_chunk_repo(
    session: Session = Depends(get_session),
) -> RagChunkRepoSqlAlchemy:
    return RagChunkRepoSqlAlchemy(session)

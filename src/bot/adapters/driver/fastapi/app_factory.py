"""FastAPI application factory for the bot package.

Run with:
    uvicorn src.bot.adapters.driver.fastapi.app_factory:app --reload --port 8001
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.bot.adapters.driver.fastapi.routers.health import (
    router as health_router,
)
from src.bot.adapters.driver.fastapi.routers.mechanics import (
    router as mechanics_router,
)
from src.bot.adapters.driver.fastapi.routers.workshops import (
    router as workshops_router,
)
from src.bot.adapters.driver.fastapi.routers.quotes import (
    router as quotes_router,
)
from src.bot.adapters.driver.fastapi.routers.seller_quotes import (
    router as seller_quotes_router,
)
from src.bot.adapters.driver.fastapi.routers.seller_auth import (
    router as seller_auth_router,
)
from src.bot.adapters.driver.fastapi.routers.seller_inbox import (
    router as seller_inbox_router,
)
from src.bot.adapters.driver.fastapi.routers.whatsapp_webhook import (
    router as whatsapp_router,
)
from src.bot.adapters.driver.fastapi.routers.quotations import (
    router as quotations_router,
)
from src.bot.adapters.driver.fastapi.routers.quotation_items import (
    router as quotation_items_router,
)
from src.bot.adapters.driver.fastapi.routers.quote_confirmation import (
    router as quote_confirmation_router,
)
from src.bot.adapters.driver.fastapi.routers.vendors import (
    router as vendors_router,
)
from src.bot.infrastructure.errors.http_exceptions import (
    register_exception_handlers,
)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Mecanice Bot — Hexagonal",
        version="0.1.0",
        description="Cotação de peças automotivas via IA (arquitetura hexagonal).",
    )

    # ── CORS ────────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── exception handlers ────────────────────────────────────────────
    register_exception_handlers(application)

    # ── routers ───────────────────────────────────────────────────────
    application.include_router(health_router)
    application.include_router(workshops_router)
    application.include_router(mechanics_router)
    application.include_router(quotes_router)
    application.include_router(whatsapp_router)
    application.include_router(seller_quotes_router)
    application.include_router(seller_auth_router)
    application.include_router(seller_inbox_router)
    application.include_router(vendors_router)
    application.include_router(quotations_router)
    application.include_router(quotation_items_router)
    application.include_router(quote_confirmation_router)

    return application


# Module-level instance used by uvicorn
app = create_app()

"""FastAPI application factory for the bot package.

Run with:
    uvicorn src.bot.adapters.driver.fastapi.app_factory:app --reload --port 8001
"""

from __future__ import annotations

from fastapi import FastAPI

from src.bot.adapters.driver.fastapi.routers.health import (
    router as health_router,
)
from src.bot.adapters.driver.fastapi.routers.quotes import (
    router as quotes_router,
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

    # ── exception handlers ────────────────────────────────────────────
    register_exception_handlers(application)

    # ── routers ───────────────────────────────────────────────────────
    application.include_router(health_router)
    application.include_router(quotes_router)

    return application


# Module-level instance used by uvicorn
app = create_app()

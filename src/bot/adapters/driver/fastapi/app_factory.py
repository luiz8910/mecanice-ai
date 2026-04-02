"""FastAPI application factory for the bot package.

Run with:
    uvicorn src.bot.adapters.driver.fastapi.app_factory:app --reload --port 9000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.bot.adapters.driver.fastapi.routers.health import (
    router as health_router,
)
from src.bot.adapters.driver.fastapi.routers.auth import (
    router as auth_router,
)
from src.bot.adapters.driver.fastapi.routers.mechanics import (
    router as mechanics_router,
)
from src.bot.adapters.driver.fastapi.routers.mechanic_service_orders import (
    router as mechanic_service_orders_router,
)
from src.bot.adapters.driver.fastapi.routers.llm_logs import (
    router as llm_logs_router,
)
from src.bot.adapters.driver.fastapi.routers.offers import (
    router as offers_router,
)
from src.bot.adapters.driver.fastapi.routers.seller_inbox import (
    router as seller_inbox_router,
)
from src.bot.adapters.driver.fastapi.routers.threads import (
    router as threads_router,
)
from src.bot.adapters.driver.fastapi.routers.workshops import (
    router as workshops_router,
)
from src.bot.adapters.driver.fastapi.routers.vendors import (
    router as vendors_router,
)
from src.bot.adapters.driver.fastapi.routers.manufacturers import (
    router as manufacturers_router,
)
from src.bot.adapters.driver.fastapi.routers.vehicles import (
    router as vehicles_router,
)
from src.bot.adapters.driver.fastapi.routers.admin_catalogs import (
    router as admin_catalogs_router,
)
from src.bot.infrastructure.config.settings import (
    LOCAL_CORS_ORIGIN_REGEX,
    get_cors_origins,
)
from src.bot.infrastructure.errors.http_exceptions import (
    register_exception_handlers,
)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Mecanice Browser Quotation Backend",
        version="0.1.0",
        description="API do fluxo interno de cotação entre mecânicos e autopeças.",
    )

    # ── CORS ────────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_origin_regex=LOCAL_CORS_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── exception handlers ────────────────────────────────────────────
    register_exception_handlers(application)

    # ── routers ───────────────────────────────────────────────────────
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(workshops_router)
    application.include_router(mechanics_router)
    application.include_router(mechanic_service_orders_router)
    application.include_router(llm_logs_router)
    application.include_router(threads_router)
    application.include_router(offers_router)
    application.include_router(seller_inbox_router)
    application.include_router(vendors_router)
    application.include_router(manufacturers_router)
    application.include_router(vehicles_router)
    application.include_router(admin_catalogs_router)

    return application


# Module-level instance used by uvicorn
app = create_app()

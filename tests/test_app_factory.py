from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware

from src.bot.adapters.driver.fastapi.app_factory import create_app
from src.bot.infrastructure.config.settings import (
    DEFAULT_CORS_ORIGINS,
    parse_cors_origins,
)


def test_parse_cors_origins_uses_defaults_when_env_is_missing():
    assert parse_cors_origins(None) == list(DEFAULT_CORS_ORIGINS)


def test_parse_cors_origins_accepts_csv_values():
    origins = parse_cors_origins(
        "https://front-end-mecanice.vercel.app,http://localhost:5173/"
    )

    assert origins == [
        "https://front-end-mecanice.vercel.app",
        "http://localhost:5173",
    ]


def test_create_app_uses_cors_origins_from_env(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://front-end-mecanice.vercel.app,http://localhost:5173",
    )

    app = create_app()
    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    )

    assert cors_middleware.options["allow_origins"] == [
        "https://front-end-mecanice.vercel.app",
        "http://localhost:5173",
    ]
    assert cors_middleware.options["allow_credentials"] is True

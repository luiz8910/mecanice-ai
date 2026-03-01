from __future__ import annotations

from celery import Celery

from src.bot.infrastructure.config.settings import settings


celery_app = Celery(
    "mecanice",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.bot.tasks.whatsapp"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

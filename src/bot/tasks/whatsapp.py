from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

from src.bot.adapters.driven.db.session import SessionLocal
from src.bot.adapters.driven.whatsapp.service import WhatsAppService
from src.bot.celery_app import celery_app
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)
TRACE_FILE_PATH = Path("runtime/quote_worker_test_trace.txt")


def _append_trace(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    TRACE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_FILE_PATH.open("a", encoding="utf-8") as trace_file:
        trace_file.write(f"{timestamp} | {message}\n")


def _short_error(error: Exception) -> str:
    message = str(error).strip() or error.__class__.__name__
    return message[:255]


@celery_app.task(bind=True, max_retries=5)
def send_quote_whatsapp(self, quote_id: str) -> dict[str, object]:
    _append_trace(
        f"received quote_id={quote_id} retry={int(self.request.retries)}"
    )
    logger.info(
        "Worker received quote response for WhatsApp processing quote_id=%s retry=%s",
        quote_id,
        int(self.request.retries),
    )

    try:
        parsed_quote_id = int(quote_id)
    except (TypeError, ValueError):
        _append_trace(f"invalid_quote_id quote_id={quote_id}")
        return {"ok": False, "reason": "invalid_quote_id"}

    session = SessionLocal()
    try:
        quote = session.execute(
            text(
                """
                SELECT
                    q.id,
                    q.code,
                    q.whatsapp_sent_at,
                    w.whatsapp_phone_e164 AS workshop_phone,
                    COALESCE(SUM(qi.price), 0) AS total
                FROM quotations q
                JOIN workshops w ON w.id = q.workshop_id
                LEFT JOIN quotation_items qi
                    ON qi.quotation_id = q.id
                   AND qi.selected = true
                WHERE q.id = :id
                  AND q.soft_delete = false
                GROUP BY q.id, q.code, q.whatsapp_sent_at, w.whatsapp_phone_e164
                """
            ),
            {"id": parsed_quote_id},
        ).mappings().one_or_none()

        if quote is None:
            _append_trace(f"quote_not_found quote_id={parsed_quote_id}")
            return {"ok": True, "queued": False, "reason": "quote_not_found"}

        if quote["whatsapp_sent_at"] is not None:
            _append_trace(f"already_sent quote_id={parsed_quote_id}")
            return {"ok": True, "queued": False, "reason": "already_sent"}

        phone = quote.get("workshop_phone")
        if not phone:
            session.execute(
                text(
                    """
                    UPDATE quotations
                    SET whatsapp_send_error = :error,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {
                    "id": parsed_quote_id,
                    "error": "workshop phone missing",
                },
            )
            session.commit()
            _append_trace(f"missing_workshop_phone quote_id={parsed_quote_id}")
            return {"ok": False, "queued": False, "reason": "missing_workshop_phone"}

        total_raw = quote.get("total")
        total = float(total_raw) if isinstance(total_raw, Decimal) else float(total_raw or 0)
        message = f"Cotação {quote['code']} confirmada. Total: R$ {total:.2f}"

        whatsapp_service = WhatsAppService()
        whatsapp_service.send_text(to=str(phone), text=message)

        session.execute(
            text(
                """
                UPDATE quotations
                SET whatsapp_sent_at = now(),
                    whatsapp_send_error = NULL,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": parsed_quote_id},
        )
        session.commit()
        _append_trace(f"sent_success quote_id={parsed_quote_id} total={total:.2f}")

        return {"ok": True, "queued": True, "sent": True}

    except Exception as exc:
        session.rollback()

        error_message = _short_error(exc)
        try:
            session.execute(
                text(
                    """
                    UPDATE quotations
                    SET whatsapp_send_error = :error,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {
                    "id": parsed_quote_id,
                    "error": error_message,
                },
            )
            session.commit()
        except Exception:
            session.rollback()

        current_retry = int(self.request.retries)
        if current_retry >= int(self.max_retries):
            _append_trace(
                f"sent_failed_max_retries quote_id={parsed_quote_id} error={error_message}"
            )
            logger.exception(
                "Failed to send WhatsApp after max retries quote_id=%s",
                parsed_quote_id,
            )
            return {
                "ok": False,
                "queued": False,
                "sent": False,
                "error": error_message,
            }

        _append_trace(
            f"retry_scheduled quote_id={parsed_quote_id} retry={current_retry + 1} error={error_message}"
        )
        raise self.retry(exc=exc, countdown=2 ** current_retry)
    finally:
        session.close()

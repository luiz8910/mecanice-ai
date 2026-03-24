"""Persistence helpers for LLM call observability."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.bot.adapters.driven.db.session import SessionLocal
from src.bot.domain.errors import NotFoundError


def _json_dump(payload: Any) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, default=str)


class LlmCallLogRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_log(self, payload: dict[str, Any]) -> str:
        row = self._session.execute(
            text(
                """
                INSERT INTO llm_call_logs (
                    requester_id,
                    thread_id,
                    request_id,
                    provider,
                    endpoint,
                    model,
                    status,
                    vehicle_json,
                    context_json,
                    request_payload_json,
                    metadata_json
                )
                VALUES (
                    :requester_id,
                    :thread_id,
                    :request_id,
                    :provider,
                    :endpoint,
                    :model,
                    COALESCE(:status, 'started'),
                    CAST(:vehicle_json AS jsonb),
                    CAST(:context_json AS jsonb),
                    CAST(:request_payload_json AS jsonb),
                    CAST(:metadata_json AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                "requester_id": payload.get("requester_id"),
                "thread_id": payload.get("thread_id"),
                "request_id": payload.get("request_id"),
                "provider": payload["provider"],
                "endpoint": payload["endpoint"],
                "model": payload["model"],
                "status": payload.get("status", "started"),
                "vehicle_json": _json_dump(payload.get("vehicle_json")),
                "context_json": _json_dump(payload.get("context_json")),
                "request_payload_json": _json_dump(payload.get("request_payload_json")),
                "metadata_json": _json_dump(payload.get("metadata_json")),
            },
        ).mappings().one()
        log_id = str(row["id"])

        for position, message in enumerate(payload.get("messages") or []):
            self._session.execute(
                text(
                    """
                    INSERT INTO llm_call_log_messages (
                        log_id,
                        position,
                        role,
                        content
                    )
                    VALUES (
                        CAST(:log_id AS uuid),
                        :position,
                        :role,
                        :content
                    )
                    """
                ),
                {
                    "log_id": log_id,
                    "position": int(position),
                    "role": str(message.get("role") or "unknown"),
                    "content": str(message.get("content") or ""),
                },
            )
        self._session.commit()
        return log_id

    def mark_success(self, log_id: str, payload: dict[str, Any]) -> None:
        self._session.execute(
            text(
                """
                UPDATE llm_call_logs
                SET status = 'succeeded',
                    http_status = :http_status,
                    duration_ms = :duration_ms,
                    response_candidate_count = :response_candidate_count,
                    parsed_response_json = CAST(:parsed_response_json AS jsonb),
                    raw_response_text = :raw_response_text,
                    updated_at = now()
                WHERE id = CAST(:log_id AS uuid)
                """
            ),
            {
                "log_id": log_id,
                "http_status": payload.get("http_status"),
                "duration_ms": payload.get("duration_ms"),
                "response_candidate_count": payload.get("response_candidate_count"),
                "parsed_response_json": (
                    None
                    if payload.get("parsed_response_json") is None
                    else _json_dump(payload.get("parsed_response_json"))
                ),
                "raw_response_text": payload.get("raw_response_text"),
            },
        )
        self._session.commit()

    def mark_failure(self, log_id: str, payload: dict[str, Any]) -> None:
        self._session.execute(
            text(
                """
                UPDATE llm_call_logs
                SET status = 'failed',
                    http_status = :http_status,
                    duration_ms = :duration_ms,
                    error_message = :error_message,
                    raw_response_text = :raw_response_text,
                    updated_at = now()
                WHERE id = CAST(:log_id AS uuid)
                """
            ),
            {
                "log_id": log_id,
                "http_status": payload.get("http_status"),
                "duration_ms": payload.get("duration_ms"),
                "error_message": payload.get("error_message"),
                "raw_response_text": payload.get("raw_response_text"),
            },
        )
        self._session.commit()

    def list_logs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        model: str | None = None,
        requester_id: str | None = None,
        thread_id: str | None = None,
    ) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: dict[str, Any] = {"limit": int(limit), "offset": int(offset)}

        if status:
            where.append("status = :status")
            params["status"] = status
        if model:
            where.append("model = :model")
            params["model"] = model
        if requester_id:
            where.append("requester_id = :requester_id")
            params["requester_id"] = requester_id
        if thread_id:
            where.append("thread_id = :thread_id")
            params["thread_id"] = thread_id

        rows = self._session.execute(
            text(
                f"""
                SELECT
                    id,
                    requester_id,
                    thread_id,
                    request_id,
                    provider,
                    endpoint,
                    model,
                    status,
                    http_status,
                    duration_ms,
                    response_candidate_count,
                    error_message,
                    created_at,
                    updated_at
                FROM llm_call_logs
                WHERE {' AND '.join(where)}
                ORDER BY created_at DESC
                LIMIT :limit
                OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_log(self, log_id: str) -> dict[str, Any]:
        row = self._session.execute(
            text(
                """
                SELECT
                    id,
                    requester_id,
                    thread_id,
                    request_id,
                    provider,
                    endpoint,
                    model,
                    status,
                    http_status,
                    duration_ms,
                    response_candidate_count,
                    error_message,
                    vehicle_json,
                    context_json,
                    request_payload_json,
                    parsed_response_json,
                    raw_response_text,
                    metadata_json,
                    created_at,
                    updated_at
                FROM llm_call_logs
                WHERE id = CAST(:log_id AS uuid)
                """
            ),
            {"log_id": log_id},
        ).mappings().one_or_none()
        if row is None:
            raise NotFoundError("llm log not found")

        messages = self._session.execute(
            text(
                """
                SELECT
                    id,
                    log_id,
                    position,
                    role,
                    content,
                    created_at
                FROM llm_call_log_messages
                WHERE log_id = CAST(:log_id AS uuid)
                ORDER BY position ASC, created_at ASC
                """
            ),
            {"log_id": log_id},
        ).mappings().all()

        payload = dict(row)
        payload["messages"] = [dict(message) for message in messages]
        return payload


class LlmCallLogStore:
    """Write-oriented store used by the LLM adapter outside request scope."""

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def create_log(self, payload: dict[str, Any]) -> str:
        session = self._session_factory()
        try:
            repo = LlmCallLogRepoSqlAlchemy(session)
            return repo.create_log(payload)
        finally:
            session.close()

    def mark_success(self, log_id: str, payload: dict[str, Any]) -> None:
        session = self._session_factory()
        try:
            repo = LlmCallLogRepoSqlAlchemy(session)
            repo.mark_success(log_id, payload)
        finally:
            session.close()

    def mark_failure(self, log_id: str, payload: dict[str, Any]) -> None:
        session = self._session_factory()
        try:
            repo = LlmCallLogRepoSqlAlchemy(session)
            repo.mark_failure(log_id, payload)
        finally:
            session.close()

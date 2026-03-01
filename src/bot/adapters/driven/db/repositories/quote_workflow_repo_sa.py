from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.bot.domain.errors import ValidationError
from src.bot.adapters.driven.db.repositories.vendor_repo_sa import VendorRepoSqlAlchemy


@dataclass
class AssignedConversation:
    conversation_id: str
    request_id: str
    workshop_id: int
    autopart_id: int
    autopart_name: str
    vendor_id: int
    vendor_name: str
    mechanic_phone_e164: str
    created: bool


@dataclass
class ConversationContext:
    conversation_id: str
    request_id: str
    workshop_id: int
    autopart_id: int
    autopart_name: str
    vendor_id: int
    vendor_name: str
    mechanic_phone_e164: str
    last_mechanic_message: str


class QuoteWorkflowRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._vendor_repo = VendorRepoSqlAlchemy(session)

    def assign_conversations_for_mechanic_message(
        self,
        *,
        source_event_id: str,
        mechanic_phone_e164: str,
        message_text: str,
    ) -> list[AssignedConversation]:
        mechanic = self._session.execute(
            text(
                """
                SELECT id, workshop_id
                FROM mechanics
                WHERE whatsapp_phone_e164 = :phone
                  AND soft_delete = false
                  AND status = 'active'
                ORDER BY id
                LIMIT 1
                """
            ),
            {"phone": mechanic_phone_e164},
        ).mappings().one_or_none()

        if mechanic is None:
            raise ValidationError("mechanic not found for whatsapp phone")

        workshop_id = int(mechanic["workshop_id"])
        autoparts = self._session.execute(
            text(
                """
                SELECT id, name
                FROM autoparts
                WHERE status = 'active'
                ORDER BY id
                """
            )
        ).mappings().all()

        conversations: list[AssignedConversation] = []
        for autopart in autoparts:
            autopart_id = int(autopart["id"])
            autopart_name = str(autopart["name"])
            vendor = self._get_or_assign_vendor(
                workshop_id=workshop_id,
                autopart_id=autopart_id,
            )
            conversation = self._create_or_get_conversation(
                source_event_id=source_event_id,
                request_id=source_event_id,
                mechanic_phone_e164=mechanic_phone_e164,
                workshop_id=workshop_id,
                autopart_id=autopart_id,
                vendor_id=vendor["vendor_id"],
                last_mechanic_message=message_text,
            )

            conversations.append(
                AssignedConversation(
                    conversation_id=conversation["conversation_id"],
                    request_id=conversation["request_id"],
                    workshop_id=workshop_id,
                    autopart_id=autopart_id,
                    autopart_name=autopart_name,
                    vendor_id=vendor["vendor_id"],
                    vendor_name=vendor["vendor_name"],
                    mechanic_phone_e164=mechanic_phone_e164,
                    created=conversation["created"],
                )
            )

        self._session.commit()
        return conversations

    def get_conversation_context(self, conversation_id: str) -> ConversationContext | None:
        row = self._session.execute(
            text(
                """
                SELECT
                    qc.conversation_id,
                    qc.request_id,
                    qc.workshop_id,
                    qc.autopart_id,
                    ap.name AS autopart_name,
                    qc.vendor_id,
                    v.name AS vendor_name,
                    qc.mechanic_phone_e164,
                    qc.last_mechanic_message
                FROM quote_conversations qc
                JOIN autoparts ap ON ap.id = qc.autopart_id
                JOIN vendors v ON v.id = qc.vendor_id
                WHERE qc.conversation_id = :conversation_id
                """
            ),
            {"conversation_id": conversation_id},
        ).mappings().one_or_none()
        if row is None:
            return None
        return ConversationContext(
            conversation_id=row["conversation_id"],
            request_id=row["request_id"],
            workshop_id=int(row["workshop_id"]),
            autopart_id=int(row["autopart_id"]),
            autopart_name=str(row["autopart_name"]),
            vendor_id=int(row["vendor_id"]),
            vendor_name=str(row["vendor_name"]),
            mechanic_phone_e164=str(row["mechanic_phone_e164"]),
            last_mechanic_message=str(row["last_mechanic_message"] or ""),
        )

    def touch_conversation(self, conversation_id: str) -> None:
        self._session.execute(
            text(
                """
                UPDATE quote_conversations
                SET updated_at = now()
                WHERE conversation_id = :conversation_id
                """
            ),
            {"conversation_id": conversation_id},
        )
        self._session.commit()

    def _get_or_assign_vendor(self, *, workshop_id: int, autopart_id: int) -> dict[str, Any]:
        existing = self._session.execute(
            text(
                """
                SELECT va.vendor_id, v.name AS vendor_name
                FROM vendor_assignments va
                JOIN vendors v ON v.id = va.vendor_id
                WHERE va.workshop_id = :workshop_id
                  AND va.autopart_id = :autopart_id
                  AND v.active = true
                LIMIT 1
                """
            ),
            {"workshop_id": workshop_id, "autopart_id": autopart_id},
        ).mappings().one_or_none()
        if existing is not None:
            return {
                "vendor_id": int(existing["vendor_id"]),
                "vendor_name": str(existing["vendor_name"]),
            }

        candidate = self._session.execute(
            text(
                """
                SELECT
                    v.id AS vendor_id,
                    v.name AS vendor_name,
                    COUNT(va.workshop_id) AS assigned_workshops
                FROM vendors v
                LEFT JOIN vendor_assignments va ON va.vendor_id = v.id
                WHERE v.autopart_id = :autopart_id
                  AND v.active = true
                GROUP BY v.id, v.name
                ORDER BY assigned_workshops ASC, v.id ASC
                LIMIT 1
                """
            ),
            {"autopart_id": autopart_id},
        ).mappings().one_or_none()

        if candidate is None:
            raise ValidationError(
                f"no active vendor configured for autopart_id={autopart_id}"
            )

        inserted = self._session.execute(
            text(
                """
                INSERT INTO vendor_assignments (workshop_id, autopart_id, vendor_id)
                VALUES (:workshop_id, :autopart_id, :vendor_id)
                ON CONFLICT (workshop_id, autopart_id)
                DO NOTHING
                RETURNING vendor_id
                """
            ),
            {
                "workshop_id": workshop_id,
                "autopart_id": autopart_id,
                "vendor_id": int(candidate["vendor_id"]),
            },
        ).mappings().one_or_none()

        if inserted is not None:
            self._vendor_repo.refresh_vendor_served_workshops_count(int(candidate["vendor_id"]))
            self._vendor_repo.record_workshop_assigned(
                vendor_id=int(candidate["vendor_id"]),
                autopart_id=autopart_id,
                workshop_id=workshop_id,
            )
            return {
                "vendor_id": int(inserted["vendor_id"]),
                "vendor_name": str(candidate["vendor_name"]),
            }

        conflict_row = self._session.execute(
            text(
                """
                SELECT va.vendor_id, v.name AS vendor_name
                FROM vendor_assignments va
                JOIN vendors v ON v.id = va.vendor_id
                WHERE va.workshop_id = :workshop_id
                  AND va.autopart_id = :autopart_id
                LIMIT 1
                """
            ),
            {"workshop_id": workshop_id, "autopart_id": autopart_id},
        ).mappings().one()

        return {
            "vendor_id": int(conflict_row["vendor_id"]),
            "vendor_name": str(conflict_row["vendor_name"]),
        }

    def _create_or_get_conversation(
        self,
        *,
        source_event_id: str,
        request_id: str,
        mechanic_phone_e164: str,
        workshop_id: int,
        autopart_id: int,
        vendor_id: int,
        last_mechanic_message: str,
    ) -> dict[str, Any]:
        from uuid import uuid4

        conversation_id = str(uuid4())
        inserted = self._session.execute(
            text(
                """
                INSERT INTO quote_conversations (
                    conversation_id,
                    source_event_id,
                    request_id,
                    mechanic_phone_e164,
                    workshop_id,
                    autopart_id,
                    vendor_id,
                    last_mechanic_message
                )
                VALUES (
                    :conversation_id,
                    :source_event_id,
                    :request_id,
                    :mechanic_phone_e164,
                    :workshop_id,
                    :autopart_id,
                    :vendor_id,
                    :last_mechanic_message
                )
                ON CONFLICT (source_event_id, autopart_id)
                DO NOTHING
                RETURNING conversation_id, request_id
                """
            ),
            {
                "conversation_id": conversation_id,
                "source_event_id": source_event_id,
                "request_id": request_id,
                "mechanic_phone_e164": mechanic_phone_e164,
                "workshop_id": workshop_id,
                "autopart_id": autopart_id,
                "vendor_id": vendor_id,
                "last_mechanic_message": last_mechanic_message,
            },
        ).mappings().one_or_none()

        if inserted is not None:
            return {
                "conversation_id": inserted["conversation_id"],
                "request_id": inserted["request_id"],
                "created": True,
            }

        existing = self._session.execute(
            text(
                """
                SELECT conversation_id, request_id
                FROM quote_conversations
                WHERE source_event_id = :source_event_id
                  AND autopart_id = :autopart_id
                LIMIT 1
                """
            ),
            {"source_event_id": source_event_id, "autopart_id": autopart_id},
        ).mappings().one()

        return {
            "conversation_id": existing["conversation_id"],
            "request_id": existing["request_id"],
            "created": False,
        }
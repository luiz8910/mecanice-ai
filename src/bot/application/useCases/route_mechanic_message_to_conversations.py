from __future__ import annotations

from src.bot.adapters.driven.db.repositories.quote_workflow_repo_sa import (
    AssignedConversation,
    QuoteWorkflowRepoSqlAlchemy,
)


class RouteMechanicMessageToConversationsUseCase:
    def __init__(self, repo: QuoteWorkflowRepoSqlAlchemy) -> None:
        self._repo = repo

    def execute(
        self,
        *,
        source_event_id: str,
        mechanic_phone_e164: str,
        message_text: str,
    ) -> list[AssignedConversation]:
        return self._repo.assign_conversations_for_mechanic_message(
            source_event_id=source_event_id,
            mechanic_phone_e164=mechanic_phone_e164,
            message_text=message_text,
        )
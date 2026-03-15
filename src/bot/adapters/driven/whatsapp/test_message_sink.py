"""In-memory sink for outbound WhatsApp messages in local tests.

This module allows test UIs (like /test/whatsapp) to inspect messages sent by
application use-cases without depending on external providers.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Lock
from uuid import uuid4

from src.bot.application.dtos.messaging import OutgoingMessageDTO

_lock = Lock()
_SINK_FILE_PATH = Path(
    os.getenv("TEST_WHATSAPP_SINK_FILE", "/tmp/mecanice_py/test_whatsapp_outbound_messages.jsonl")
)


def _ensure_sink_file() -> None:
    _SINK_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _SINK_FILE_PATH.exists():
        _SINK_FILE_PATH.write_text("", encoding="utf-8")


def record_outbound_message(message: OutgoingMessageDTO) -> dict:
    item = {
        "id": str(uuid4()),
        "direction": "incoming",
        "text": message.text or "",
        "recipient": message.recipient,
        "metadata": message.metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with _lock:
        _ensure_sink_file()
        with _SINK_FILE_PATH.open("a", encoding="utf-8") as sink_file:
            sink_file.write(json.dumps(item, ensure_ascii=True) + "\n")

    return item


def list_outbound_messages(limit: int = 250) -> list[dict]:
    if limit <= 0:
        return []

    with _lock:
        _ensure_sink_file()
        content = _SINK_FILE_PATH.read_text(encoding="utf-8")

    lines = [line for line in content.splitlines() if line.strip()]
    selected = lines[-limit:]

    items: list[dict] = []
    for line in selected:
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                items.append(parsed)
        except json.JSONDecodeError:
            continue
    return items


def clear_outbound_messages() -> None:
    with _lock:
        _ensure_sink_file()
        _SINK_FILE_PATH.write_text("", encoding="utf-8")

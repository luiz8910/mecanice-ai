"""Supplier reply extraction adapter.

MVP-friendly implementation: return a normalized text payload.
Later iterations can add regex parsing + LLM fallback.
"""

from __future__ import annotations

from src.bot.application.ports.driven.supplier_reply_extraction import (
	SupplierReplyExtractionPort,
)


class SimpleSupplierReplyExtractor(SupplierReplyExtractionPort):
	def extract_text(self, raw: str) -> str:
		return (raw or "").strip()


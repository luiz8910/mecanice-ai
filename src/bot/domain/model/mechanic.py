
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .workshop import Workshop


@dataclass
class Mechanic:
	id: Optional[int] = None
	name: str = ""
	whatsapp_phone_e164: Optional[str] = None
	city: Optional[str] = None
	state_uf: Optional[str] = None
	status: Optional[str] = "active"
	address: Optional[str] = None
	email: Optional[str] = None
	categories: List[str] = field(default_factory=list)
	notes: Optional[str] = None
	workshop_id: Optional[int] = None
	workshop: Optional[Workshop] = None

	@property
	def phone(self) -> Optional[str]:
		"""Compatibility alias for older code (maps to WhatsApp phone)."""
		return self.whatsapp_phone_e164

	@phone.setter
	def phone(self, value: Optional[str]) -> None:
		self.whatsapp_phone_e164 = value

	def assign_to_workshop(self, workshop: Workshop) -> None:
		"""Associate this mechanic with a Workshop instance."""
		self.workshop = workshop
		self.workshop_id = workshop.id

	def display_name(self) -> str:
		suffix = str(self.id) if self.id is not None else "?"
		return f"{self.name} ({suffix})"

	def contact_info(self) -> str:
		parts = [self.display_name()]
		if self.whatsapp_phone_e164:
			parts.append(self.whatsapp_phone_e164)
		if self.workshop:
			parts.append(self.workshop.name)
		if self.city:
			parts.append(self.city)
		if self.state_uf:
			parts.append(self.state_uf)
		return " | ".join(parts)


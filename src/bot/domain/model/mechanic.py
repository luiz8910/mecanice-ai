
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .workshop import Workshop


@dataclass
class Mechanic:
	id: str
	name: str
	phone: Optional[str] = None
	specializations: List[str] = field(default_factory=list)
	workshop_id: Optional[str] = None
	workshop: Optional[Workshop] = None

	def assign_to_workshop(self, workshop: Workshop) -> None:
		"""Associate this mechanic with a Workshop instance."""
		self.workshop = workshop
		self.workshop_id = workshop.id

	def display_name(self) -> str:
		return f"{self.name} ({self.id})"

	def contact_info(self) -> str:
		parts = [self.display_name()]
		if self.phone:
			parts.append(self.phone)
		if self.workshop:
			parts.append(self.workshop.name)
		return " - ".join(parts)


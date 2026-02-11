from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .mechanic import Mechanic


@dataclass
class Workshop:
    id: str
    name: str
    location: Optional[str] = None
    phone: Optional[str] = None
    mechanics: List["Mechanic"] = field(default_factory=list)

    def contact_info(self) -> str:
        parts = [self.name]
        if self.phone:
            parts.append(self.phone)
        if self.location:
            parts.append(self.location)
        return " - ".join(parts)

    def add_mechanic(self, mechanic: "Mechanic") -> None:
        """Associate a Mechanic with this Workshop (bidirectional).

        If the mechanic is already associated with another workshop, it will be reassigned.
        """
        if mechanic in self.mechanics:
            return
        # remove mechanic from previous workshop if present
        if mechanic.workshop is not None and mechanic.workshop is not self:
            try:
                mechanic.workshop.remove_mechanic(mechanic)
            except Exception:
                pass

        self.mechanics.append(mechanic)
        mechanic.assign_to_workshop(self)

    def remove_mechanic(self, mechanic: "Mechanic") -> None:
        """Disassociate a Mechanic from this Workshop (bidirectional)."""
        if mechanic in self.mechanics:
            self.mechanics.remove(mechanic)
            # clear mechanic's workshop link
            mechanic.workshop = None
            mechanic.workshop_id = None

    def get_mechanics(self) -> List["Mechanic"]:
        return list(self.mechanics)

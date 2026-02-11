from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from .supplier import Supplier
from .value_objects import Money, Description


@dataclass
class QuoteItem:
    description: Description
    unit_price: Money
    quantity: int = 1


@dataclass
class Quote:
    id: str
    supplier: Supplier
    items: List[QuoteItem] = field(default_factory=list)
    total: Optional[Money] = None
    valid_until: Optional[date] = None

    def compute_total(self) -> Money:
        total_amount = sum((item.unit_price.amount * item.quantity) for item in self.items)
        money = Money(total_amount, self.items[0].unit_price.currency if self.items else "BRL")
        self.total = money
        return money

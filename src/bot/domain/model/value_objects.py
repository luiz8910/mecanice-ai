from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self):
        # normalize to 2 decimal places
        quantized = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", quantized)


@dataclass(frozen=True)
class Quantity:
    value: Decimal


@dataclass(frozen=True)
class Identifier:
    value: str


@dataclass(frozen=True)
class Description:
    text: str

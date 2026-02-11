from pydantic import BaseModel
from typing import Optional, List


class QuoteUpdateDTO(BaseModel):
    quote_id: Optional[str]
    supplier_id: Optional[str]
    prices: Optional[List[float]] = None


class QuoteComparisonDTO(BaseModel):
    quote_ids: Optional[List[str]] = None
    winner_quote_id: Optional[str]

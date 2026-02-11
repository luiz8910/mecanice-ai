from pydantic import BaseModel
from typing import Optional, Dict


class IncomingMessageDTO(BaseModel):
    id: Optional[str]
    sender: Optional[str]
    text: Optional[str]
    metadata: Optional[Dict[str, str]] = None


class OutgoingMessageDTO(BaseModel):
    id: Optional[str]
    recipient: Optional[str]
    text: Optional[str]
    metadata: Optional[Dict[str, str]] = None

from pydantic import BaseModel
from typing import Optional, Dict


class IncomingMessageDTO(BaseModel):
    id: Optional[str] = None
    sender: Optional[str] = None
    text: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class OutgoingMessageDTO(BaseModel):
    id: Optional[str] = None
    recipient: Optional[str] = None
    text: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

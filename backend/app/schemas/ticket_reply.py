from pydantic import BaseModel, Field
from datetime import datetime

class ReplyCreate(BaseModel):
    content: str = Field(..., min_length=1)
    is_internal: bool = False

class ReplyResponse(BaseModel):
    id: int
    ticket_id: int
    author_id: int
    content: str
    is_internal: bool
    created_at: datetime
    class Config:
        from_attributes = True

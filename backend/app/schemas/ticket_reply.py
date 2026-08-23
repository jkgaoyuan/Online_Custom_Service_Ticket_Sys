from pydantic import BaseModel, Field
from datetime import datetime

class ReplyCreate(BaseModel):
    content: str = Field(..., min_length=1)
    is_internal: bool = False

class AuthorInfo(BaseModel):
    id: int
    username: str
    role: str
    class Config:
        from_attributes = True

class ReplyResponse(BaseModel):
    id: int
    ticket_id: int
    author_id: int
    content: str
    is_internal: bool
    created_at: datetime
    author: AuthorInfo | None = None
    class Config:
        from_attributes = True

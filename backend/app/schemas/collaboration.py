from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserResponse


class CollaborationCreate(BaseModel):
    to_user_id: int = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=2000)


class CollaborationResponse(BaseModel):
    id: int
    ticket_id: int
    type: str
    from_user_id: int
    to_user_id: int
    reason: Optional[str] = None
    created_at: datetime
    from_user: Optional[UserResponse] = None
    to_user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)

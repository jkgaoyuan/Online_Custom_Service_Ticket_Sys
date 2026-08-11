from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TransferRequest(BaseModel):
    to_user_id: int = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=500)


class AssistRequest(BaseModel):
    to_user_id: int = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=500)


class UserBrief(BaseModel):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


class CollaborationResponse(BaseModel):
    id: int
    type: str
    from_user: Optional[UserBrief] = None
    to_user: UserBrief
    reason: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

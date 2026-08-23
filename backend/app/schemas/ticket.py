from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


from app.schemas.collaboration import CollaborationResponse
from app.schemas.sla import SLASummary
from app.schemas.user import UserResponse


class TicketBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = Field(...)
    category_id: int = Field(..., gt=0)
    priority: str = Field(default="P2", pattern="^(P0|P1|P2|P3)$")
    source: str = Field(default="web", pattern="^(web|email|api)$")


class TicketCreate(TicketBase):
    assignee_id: Optional[int] = None
    auto_dispatch: bool = False


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = Field(None, gt=0)
    priority: Optional[str] = Field(None, pattern="^(P0|P1|P2|P3)$")
    assignee_id: Optional[int] = None


class TicketResponse(BaseModel):
    id: int
    ticket_no: str
    title: str
    description: str
    status: str
    priority: str
    category_id: int
    requester_id: int
    assignee_id: Optional[int] = None
    source: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    satisfaction: Optional[str] = None
    satisfaction_note: Optional[str] = None
    satisfaction_at: Optional[datetime] = None
    sla: Optional[SLASummary] = None

    model_config = ConfigDict(from_attributes=True)


class TicketDetailResponse(TicketResponse):
    collaborations: Optional[list[CollaborationResponse]] = None
    requester: Optional[UserResponse] = None


class StatusUpdateRequest(BaseModel):
    status: str


class AssignRequest(BaseModel):
    assignee_id: int


class SatisfactionSubmit(BaseModel):
    rating: str = Field(..., pattern="^(satisfied|neutral|dissatisfied)$")
    note: Optional[str] = Field(None)


class SatisfactionInfo(BaseModel):
    rating: str
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

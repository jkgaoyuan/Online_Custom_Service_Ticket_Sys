from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SLAResponse(BaseModel):
    ticket_id: int
    priority: str
    first_resp_hours: int
    resolution_hours: int
    first_resp_due: datetime
    resolution_due: datetime
    first_resp_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    first_resp_breached: bool
    resolution_breached: bool

    model_config = ConfigDict(from_attributes=True)


class SLASummary(BaseModel):
    first_resp_due: datetime
    resolution_due: datetime
    first_resp_breached: bool
    resolution_breached: bool

    model_config = ConfigDict(from_attributes=True)


class SLAOverdueTicketResponse(BaseModel):
    ticket_no: str
    title: str
    assignee_name: str
    due_time: datetime
    breach_type: str

    model_config = ConfigDict(from_attributes=True)

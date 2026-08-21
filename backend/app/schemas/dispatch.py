from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class AssignSuggestion(BaseModel):
    agent_id: int
    agent_name: str
    score: float
    current_load: int
    max_concurrent_tickets: int
    is_available: bool
    proficiency: int | None = None
    reason: str


class DispatchLogResponse(BaseModel):
    id: int
    ticket_id: int
    agent_id: int
    dispatch_type: str
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

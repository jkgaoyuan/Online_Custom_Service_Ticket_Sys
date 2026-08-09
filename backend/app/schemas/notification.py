from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    data: dict
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

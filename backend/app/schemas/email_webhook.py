from pydantic import BaseModel, EmailStr, Field


class InboundEmail(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=100)
    from_address: EmailStr
    from_name: str | None = Field(None, max_length=100)
    to_address: EmailStr
    subject: str = Field(..., max_length=200)
    text_body: str | None = Field(None, max_length=50000)
    html_body: str | None = Field(None, max_length=200000)
    in_reply_to: str | None = Field(None, max_length=100)
    references: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)

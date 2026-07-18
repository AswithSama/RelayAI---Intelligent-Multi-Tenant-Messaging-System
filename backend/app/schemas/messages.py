from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


MessageSender = Literal["customer", "company", "ai"]


class MessageCreate(BaseModel):
    sender: MessageSender
    body: str = Field(
        min_length=1,
        max_length=5000,
    )

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        trimmed_value = value.strip()

        if not trimmed_value:
            raise ValueError("Message body cannot be empty.")

        return trimmed_value


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender: MessageSender
    body: str
    created_at: datetime
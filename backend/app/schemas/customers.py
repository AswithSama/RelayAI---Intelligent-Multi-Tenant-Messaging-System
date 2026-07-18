from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CustomerResponse(BaseModel):
    id: int
    company_id: int
    name: str
    phone: str | None
    queue_status: Literal["review", "completed"]
    last_message: str | None
    review_reason: str | None
    created_at: datetime
    updated_at: datetime
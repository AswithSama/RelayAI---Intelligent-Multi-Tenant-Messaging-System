from datetime import datetime

from pydantic import BaseModel


class ConversationResponse(BaseModel):
    id: int
    customer_id: int
    created_at: datetime
    updated_at: datetime
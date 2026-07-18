from fastapi import APIRouter

from app.schemas.conversations import ConversationResponse
from app.services.conversations import get_conversations_by_customer


router = APIRouter(
    prefix="/customers",
    tags=["Conversations"],
)


@router.get(
    "/{customer_id}/conversations",
    response_model=list[ConversationResponse],
)
def list_customer_conversations(
    customer_id: int,
):
    return get_conversations_by_customer(
        customer_id=customer_id,
    )
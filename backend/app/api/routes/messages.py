from fastapi import APIRouter, HTTPException, status

from ai.shared.pending_runs import enqueue_ai_pending_run
from app.schemas.messages import MessageCreate, MessageResponse
from app.services.messages import (
    create_message,
    get_messages_by_conversation,
)


router = APIRouter()


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
def list_messages(conversation_id: int) -> list[dict]:
    return get_messages_by_conversation(conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_message(
    conversation_id: int,
    message: MessageCreate,
) -> dict:
    created_message = create_message(
        conversation_id=conversation_id,
        sender=message.sender,
        body=message.body,
    )

    if created_message is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create message.",
        )

    if message.sender == "customer":
        enqueue_ai_pending_run(
            conversation_id=conversation_id,
            message_id=created_message["id"],
        )

    return created_message
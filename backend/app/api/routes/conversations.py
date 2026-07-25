#routes/conversations.py
from fastapi import APIRouter, HTTPException

from app.schemas.conversations import ConversationResponse
from app.services.conversations import get_conversations_by_customer, get_conversation_context
from app.services.messages import get_messages_by_conversation

router = APIRouter(prefix="/customers",tags=["Conversations"],)


@router.get("/{customer_id}/conversations",response_model=list[ConversationResponse],)
def list_customer_conversations(customer_id: int):
    return get_conversations_by_customer(customer_id=customer_id,)

@router.post("/{conversation_id}/run-ai")
async def run_ai(conversation_id: int):

    context = get_conversation_context(conversation_id)

    if context is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    messages = get_messages_by_conversation(conversation_id)

    return {
        "conversation": context,
        "messages": messages,
    }
#routes/conversations.py
from fastapi import APIRouter, HTTPException
from app.services.ai_runner import prepare_ai_input, run_ai
from app.schemas.conversations import ConversationResponse
from app.services.conversations import get_conversations_by_customer, get_conversation_context
from app.services.messages import (
    get_messages_by_conversation,
    create_ai_message,
)
router = APIRouter(prefix="/customers",tags=["Conversations"],)


@router.get("/{customer_id}/conversations",response_model=list[ConversationResponse],)
def list_customer_conversations(customer_id: int):
    return get_conversations_by_customer(customer_id=customer_id,)

@router.post("/{conversation_id}/run-ai")
async def run_ai_route(conversation_id: int):

    context = get_conversation_context(conversation_id)

    if context is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    messages = get_messages_by_conversation(conversation_id)

    try:
        ai_input = prepare_ai_input(
            context=context,
            messages=messages,
        )
        ai_result = run_ai(ai_input)
        ai_answer = ai_result.get("answer")
        ai_message = None
        if ai_answer:
            ai_message = create_ai_message(
                conversation_id=conversation_id,
                body=ai_answer,
            )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return {
        "conversation": context,
        "messages": messages,
        "ai_input": ai_input,
        "ai_result": ai_result,
        "ai_message": ai_message,
    }
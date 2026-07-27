# ai/tools/additional_support.py

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from ai.agent.state import AgentState
import logging

from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)
from app.database.connection import get_db_connection


@tool
def handle_additional_support(
    state: Annotated[AgentState, InjectedState],
    issue: str,
    reason: str,
):
    """
    Flag the customer's inbound message as requiring human attention so the
    Message Center routes the conversation into the "Account manager" tab.

    Use this when:
    - the customer's request is unclear even after reviewing conversation history,
    - the intent is clear but available tools/context cannot answer safely,
    - the customer indicates the AI misunderstood them,
    - the request is unsupported,
    - or the message is off-topic and needs human review.

    Sets ``messages.requires_human_attention = TRUE`` on the inbound message that
    triggered this turn. The flag is sticky — the conversation stays in Account
    manager until an operator clicks "Move to Catapult managed", which stamps
    ``account_manager_dismissed_at`` on that same row. (Replaces the legacy
    ``human_handoffs`` table; ``message_summary`` and ``reason`` are no longer
    persisted — they remain useful as in-context reasoning that the agent gives
    itself before deferring.)
    """

    company_id = state.get("company_id")
    customer_id = state.get("customer_id")
    source_message_id = (
        state.get("message_id") or state.get("source_message_id") or state.get("latest_message_id")
    )

    if not company_id or not customer_id or not source_message_id:
        return {
            "status": "failed",
            "message": (
                "Cannot flag for human attention — company_id, customer_id, or "
                "source message id is missing from agent state."
            ),
        }

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE messages
                    SET requires_human_attention = TRUE,
                        updated_at = NOW()
                    WHERE id = %(message_id)s
                      AND company_id = %(company_id)s
                    """,
                    {
                        "message_id": int(source_message_id),
                        "company_id": int(company_id),
                    },
                )
                affected = cur.rowcount
            conn.commit()
    except Exception as e:
        logger.warning(
            "handle_additional_support: failed to flag message_id=%s for human attention: %s",
            source_message_id,
            e,
        )
        return {"status": "failed", "message": str(e)}

    logger.info(
        "🚩 handle_additional_support flagged message_id=%s company_id=%s customer_id=%s (reason=%r)",
        source_message_id,
        company_id,
        customer_id,
        reason,
    )

    return {
        "status": "flagged" if affected else "no_op",
        "source_message_id": int(source_message_id),
        "message": (
            "Conversation flagged for human attention — operator will see it in "
            "the Message Center Account manager tab."
        ),
    }

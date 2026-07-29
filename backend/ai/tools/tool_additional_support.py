# ai/tools/additional_support.py

import logging

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from ai.agent.state import AgentState
from app.database.connection import get_db_connection


logger = logging.getLogger(__name__)


@tool
def handle_additional_support(
    state: Annotated[AgentState, InjectedState],
    issue: str,
    reason: str,
) -> dict:
    """
    Flag the customer conversation as requiring human attention.

    Use this tool when:
    - the customer's request is unclear,
    - the available tools cannot safely answer the request,
    - the customer says the AI misunderstood them,
    - the request is unsupported,
    - or a human representative needs to review the conversation.

    The triggering customer message is marked with
    ``requires_human_attention = TRUE``.

    The associated customer is moved into the ``review`` queue, and the reason
    for the escalation is stored in ``customers.review_reason``.
    """

    company_id = state.get("company_id")
    customer_id = state.get("customer_id")

    source_message_id = (
        state.get("message_id")
        or state.get("source_message_id")
        or state.get("latest_message_id")
    )

    if not company_id or not customer_id or not source_message_id:
        return {
            "status": "failed",
            "message": (
                "Cannot flag the conversation for human attention because "
                "company_id, customer_id, or source_message_id is missing."
            ),
        }

    normalized_issue = (issue or "").strip()
    normalized_reason = (reason or "").strip()

    review_reason = " — ".join(
        value
        for value in [normalized_issue, normalized_reason]
        if value
    )

    if not review_reason:
        review_reason = "AI requested additional human support."

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Mark the triggering customer message for human attention.
                #
                # The joins ensure that the message belongs to the expected
                # customer and company.
                cur.execute(
                    """
                    UPDATE messages
                    SET requires_human_attention = TRUE
                    WHERE id = %(message_id)s
                      AND sender = 'customer'
                      AND conversation_id IN (
                          SELECT conversations.id
                          FROM conversations
                          JOIN customers
                            ON customers.id = conversations.customer_id
                          WHERE customers.id = %(customer_id)s
                            AND customers.company_id = %(company_id)s
                      )
                    RETURNING conversation_id
                    """,
                    {
                        "message_id": int(source_message_id),
                        "customer_id": int(customer_id),
                        "company_id": int(company_id),
                    },
                )

                message_row = cur.fetchone()

                if not message_row:
                    conn.rollback()

                    return {
                        "status": "no_op",
                        "source_message_id": int(source_message_id),
                        "message": (
                            "The source customer message was not found or "
                            "does not belong to the specified customer."
                        ),
                    }

                conversation_id = message_row["conversation_id"]

                # Keep the customer in the human-review queue.
                cur.execute(
                    """
                    UPDATE customers
                    SET
                        queue_status = 'review',
                        review_reason = %(review_reason)s,
                        updated_at = NOW()
                    WHERE id = %(customer_id)s
                      AND company_id = %(company_id)s
                    """,
                    {
                        "customer_id": int(customer_id),
                        "company_id": int(company_id),
                        "review_reason": review_reason,
                    },
                )

            conn.commit()

    except Exception as exc:
        logger.exception(
            "handle_additional_support failed for message_id=%s",
            source_message_id,
        )

        return {
            "status": "failed",
            "message": str(exc),
        }

    logger.info(
        "handle_additional_support flagged message_id=%s "
        "conversation_id=%s company_id=%s customer_id=%s reason=%r",
        source_message_id,
        conversation_id,
        company_id,
        customer_id,
        review_reason,
    )

    return {
        "status": "flagged",
        "source_message_id": int(source_message_id),
        "conversation_id": int(conversation_id),
        "issue": normalized_issue,
        "reason": normalized_reason,
        "message": (
            "Conversation flagged for human attention and moved to the "
            "review queue."
        ),
    }
# ai/tools/forward_message.py

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from ai.agent.state import AgentState
from app.database.connection import get_db_connection


def move_to_completed(
    *,
    company_id: int,
    customer_id: int,
    triggering_message_id: int,
) -> None:
    """
    When the AI forwards or escalates a customer issue to the company, mark the
    relevant customer messages as no longer requiring human attention and move
    the customer to the completed queue.

    This handles multi-message customer replies by clearing the human-attention
    flag for all customer messages in that customer's conversations up to and
    including the message that triggered the escalation.
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE messages
                SET requires_human_attention = FALSE
                WHERE sender = 'customer'
                  AND id <= %(triggering_message_id)s
                  AND conversation_id IN (
                      SELECT conversations.id
                      FROM conversations
                      JOIN customers
                        ON customers.id = conversations.customer_id
                      WHERE customers.id = %(customer_id)s
                        AND customers.company_id = %(company_id)s
                  )
                """,
                {
                    "company_id": int(company_id),
                    "customer_id": int(customer_id),
                    "triggering_message_id": int(triggering_message_id),
                },
            )

            cur.execute(
                """
                UPDATE customers
                SET
                    queue_status = 'completed',
                    review_reason = NULL,
                    updated_at = NOW()
                WHERE id = %(customer_id)s
                  AND company_id = %(company_id)s
                """,
                {
                    "company_id": int(company_id),
                    "customer_id": int(customer_id),
                },
            )

        conn.commit()


def _get_customer_name(
    *,
    company_id: int,
    customer_id: int,
) -> str:
    """
    Retrieve the customer's full name from the playground database.
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name
                FROM customers
                WHERE id = %(customer_id)s
                  AND company_id = %(company_id)s
                LIMIT 1
                """,
                {
                    "customer_id": int(customer_id),
                    "company_id": int(company_id),
                },
            )

            row = cur.fetchone()

    return (row["name"] or "").strip() if row else ""


@tool
def forward_message_to_company(
    query_type: str,
    notes: str,
    context: str,
    state: Annotated[AgentState, InjectedState],
) -> str:
    """
    Prepare a customer escalation for the pest control company's office.

    This playground version never sends an SMS. It generates the escalation
    details and returns them so the frontend can display them in a popup.

    Use this tool when a customer message requires company follow-up,
    internal review, scheduling assistance, service clarification,
    complaint handling, billing support, or another action that should
    not be handled fully by the AI assistant.
    """

    allowed_query_types = {
        "complaint",
        "billing",
        "scheduling",
        "overdue_service",
        "service_info",
        "upsell",
    }

    normalized_query_type = (query_type or "").strip().lower()

    if normalized_query_type not in allowed_query_types:
        normalized_query_type = "service_info"

    company_id = state.get("company_id")
    customer_id = state.get("customer_id")
    triggering_message_id = state.get("message_id")

    if not company_id:
        return (
            "Failed to prepare escalation: "
            "company_id is missing from AI workflow state."
        )

    if not customer_id:
        return (
            "Failed to prepare escalation: "
            "customer_id is missing from AI workflow state."
        )

    customer_name = _get_customer_name(
        company_id=int(company_id),
        customer_id=int(customer_id),
    )

    if not customer_name:
        customer_name = "Unknown Customer"

    result = {
        "company_name": (
            state.get("company_name")
            or "Pest Control Company"
        ),
        "customer_name": customer_name,
        "query_type": normalized_query_type,
        "notes": (notes or "").strip(),
        "context": (context or "").strip(),
        "message_body": (
            f"Customer: {customer_name}\n"
            f"Inquiry Type: {normalized_query_type}\n\n"
            f"Notes:\n{(notes or '').strip()}\n\n"
            f"Context:\n{(context or '').strip()}"
        ),
    }

    if triggering_message_id:
        move_to_completed(
            company_id=int(company_id),
            customer_id=int(customer_id),
            triggering_message_id=int(triggering_message_id),
        )

    return (
        "Escalation prepared successfully.\n"
        f"Company: {result['company_name']}\n"
        f"Customer: {result['customer_name']}\n"
        f"Type: {result['query_type']}\n\n"
        f"{result['message_body']}"
    )
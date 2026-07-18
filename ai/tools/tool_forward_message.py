# ai/tools/forward_message.py

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from ai.agent.state import AgentState
from config import ENVIRONMENT
from database import get_db_connection
from services.messaging import forward_message_core


def _move_conversation_to_catapult_managed(
    *,
    company_id: int,
    customer_id: str,
    triggering_message_id: int,
) -> None:
    """
    When AI forwards/escalates a customer issue, move the currently-open inbound
    messages for that customer conversation to Catapult Managed.

    This handles multi-message customer replies where the escalation is based on
    more than just the latest inbound message.
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE messages
                SET account_manager_dismissed_at = NOW(),
                    requires_human_attention = FALSE,
                    updated_at = NOW()
                WHERE company_id = %(company_id)s
                  AND customer_id = %(customer_id)s
                  AND direction = 'inbound'
                  AND id <= %(triggering_message_id)s
                  AND account_manager_dismissed_at IS NULL
                """,
                {
                    "company_id": int(company_id),
                    "customer_id": str(customer_id),
                    "triggering_message_id": int(triggering_message_id),
                },
            )
        conn.commit()


def _get_customer_last_name(
    *,
    company_id: int,
    customer_id: str,
) -> str:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT crm
                FROM companies
                WHERE id = %(company_id)s
                LIMIT 1
                """,
                {"company_id": int(company_id)},
            )

            company_row = cur.fetchone()
            crm = (company_row[0] or "").strip().lower() if company_row else ""

            if crm == "gorilladesk":
                cur.execute(
                    """
                    SELECT last_name
                    FROM gorilladesk_customers
                    WHERE company_id = %(company_id)s
                      AND TRIM(REGEXP_REPLACE(COALESCE(account_number::text, ''), '\\.0+$', '')) = %(customer_id)s
                    LIMIT 1
                    """,
                    {
                        "company_id": int(company_id),
                        "customer_id": str(customer_id),
                    },
                )

            elif crm == "pestpac":
                cur.execute(
                    """
                    SELECT lname
                    FROM pestpac_customers
                    WHERE company_id = %(company_id)s
                      AND bill_to::text = %(customer_id)s
                    LIMIT 1
                    """,
                    {
                        "company_id": int(company_id),
                        "customer_id": str(customer_id),
                    },
                )

            else:
                cur.execute(
                    """
                    SELECT lname
                    FROM fieldroutes_customers
                    WHERE company_id = %(company_id)s
                      AND fieldroutes_customer_id::text = %(customer_id)s
                    LIMIT 1
                    """,
                    {
                        "company_id": int(company_id),
                        "customer_id": str(customer_id),
                    },
                )

            row = cur.fetchone()

    return (row[0] or "").strip() if row else ""


@tool
def forward_message_to_company(
    query_type: str,
    notes: str,
    context: str,
    state: Annotated[AgentState, InjectedState],
) -> str:
    """
    Forwards or preview-forwards a customer escalation to the pest control company's office.

    Use this tool when a customer message requires company representative follow-up,
    internal review, scheduling assistance, service clarification, complaint handling,
    or additional action that should not be handled fully by the AI assistant.
    """

    allowed_query_types = {
        "complaint",
        "billing",
        "scheduling",
        "overdue_service",
        "service_info",
        # Accepted upsell/add-on escalations should be recorded under one generic
        # inquiry type so the office and dev tracking both see them as "upsell".
        "upsell",
    }

    normalized_query_type = (query_type or "").strip().lower()

    if normalized_query_type not in allowed_query_types:
        normalized_query_type = "service_info"

    company_id = state.get("company_id")
    customer_id = state.get("customer_id")

    triggering_message_id = state.get("message_id")

    state_context = state.get("context") or {}
    counterparty_phone = (
        state_context.get("counterparty_phone")
        or state_context.get("from_phone")
        or state_context.get("customer_phone")
    )

    if not company_id:
        return "Failed to forward message: company_id is missing from AI workflow state."

    if not customer_id:
        return "Failed to forward message: customer_id is missing from AI workflow state."

    customer_first_name = (state.get("customer_first_name") or "").strip()
    customer_last_name = _get_customer_last_name(
        company_id=int(company_id),
        customer_id=str(customer_id),
    )

    customer_name = " ".join(
        part for part in [customer_first_name, customer_last_name] if part
    )

    dry_run = ENVIRONMENT != "prod"

    try:
        result = forward_message_core(
            company_id=int(company_id),
            customer_id=str(customer_id),
            customer_name=customer_name or "",
            inquiry_type=normalized_query_type,
            counterparty_phone=counterparty_phone,
            notes=notes,
            context=context,
            triggering_message_id=int(triggering_message_id) if triggering_message_id else None,
            triggered_by_user_id=None,
            dry_run=dry_run,
        )
        if triggering_message_id:
            _move_conversation_to_catapult_managed(
                company_id=int(company_id),
                customer_id=str(customer_id),
                triggering_message_id=int(triggering_message_id),
            )
    except ValueError as e:
        return f"Failed to forward message: {str(e)}"

    if dry_run:
        return (
            "[DRY RUN] Escalation saved but SMS not sent to pest control office.\n"
            f"Would send to: {result['would_send_to_company']} at {result['would_send_to_phone']}\n"
            f"Message:\n{result['message_body']}"
        )

    return (
        f"Message successfully forwarded to {result.get('company_name') or 'pest control office'} "
        f"at {result['to_phone']}.\n"
        f"Message:\n{result['message_body']}"
    )

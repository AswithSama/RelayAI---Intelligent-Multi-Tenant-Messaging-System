"""ai/tools/tool_billing_info.py — Retrieves customer account information from the playground database."""

from typing import Any

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from ai.agent.state import AgentState
from app.database.connection import get_db_connection


@tool
def get_customer_account_info(
    state: Annotated[AgentState, InjectedState],
) -> dict[str, Any]:
    """
    Retrieve customer account and contact information from the playground.

    Use this tool when the customer asks for:
    - their account number,
    - the name associated with the account,
    - the phone number associated with the account,
    - the company associated with the account,
    - or basic account verification.

    The current playground schema does not store payment methods, balances,
    billing status, autopay status, or payment history.
    """

    # Reuse account information if it has already been loaded into state.
    cached_account_info = state.get("account_info")

    if cached_account_info:
        return cached_account_info

    company_id = state.get("company_id")
    customer_id = state.get("customer_id")

    if not company_id or not customer_id:
        return {
            "found": False,
            "provider": "playground",
            "message": (
                "Cannot retrieve customer account information because "
                "company_id or customer_id is missing from the AI workflow state."
            ),
        }

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        customers.id AS customer_id,
                        customers.name AS customer_name,
                        customers.phone AS customer_phone,
                        customers.account_number,
                        customers.queue_status,
                        customers.review_reason,

                        companies.id AS company_id,
                        companies.name AS company_name,
                        companies.phone_number AS company_phone,
                        companies.google_review_link,
                        companies.crm

                    FROM customers

                    JOIN companies
                        ON companies.id = customers.company_id

                    WHERE customers.id = %(customer_id)s
                      AND companies.id = %(company_id)s

                    LIMIT 1
                    """,
                    {
                        "customer_id": int(customer_id),
                        "company_id": int(company_id),
                    },
                )

                row = cur.fetchone()

    except Exception as exc:
        return {
            "found": False,
            "provider": "playground",
            "customer_id": customer_id,
            "company_id": company_id,
            "message": (
                "Failed to retrieve customer account information: "
                f"{str(exc)}"
            ),
        }

    if not row:
        return {
            "found": False,
            "provider": "playground",
            "customer_id": int(customer_id),
            "company_id": int(company_id),
            "account_number": None,
            "message": (
                "Customer account information was not found for the "
                "specified customer and company."
            ),
        }

    return {
        "found": True,
        "provider": "playground",

        "customer_id": row["customer_id"],
        "customer_name": row["customer_name"],
        "customer_phone": row["customer_phone"],
        "account_number": row["account_number"],

        "company_id": row["company_id"],
        "company_name": row["company_name"],
        "company_phone": row["company_phone"],
        "google_review_link": row["google_review_link"],
        "crm": row["crm"],

        "queue_status": row["queue_status"],
        "review_reason": row["review_reason"],

        # Not available in the current playground schema.
        "account_status": None,
        "past_due_balance": None,
        "payment_method_type": None,
        "card_last_four": None,
        "billing_status": None,
        "autopay_enabled": None,
    }
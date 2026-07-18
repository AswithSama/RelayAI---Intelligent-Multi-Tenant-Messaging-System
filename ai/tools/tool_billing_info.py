"""ai/tools/tool_billing_info.py — Retrieves normalized customer billing, payment, and account information from CRM systems."""
import re
from typing import Dict, Optional

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from ai.agent.state import AgentState
from database import get_db_connection


def parse_gorilladesk_payment_method(method: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Parses GorillaDesk payment method text.

    Examples:
    - "stripe ****9999" -> {"payment_method": "credit card", "last_4": "9999"}
    - "check #9999, $999" -> {"payment_method": "check", "last_4": "9999"}
    """

    if not method:
        return {
            "payment_method": None,
            "last_4": None,
        }

    method_lower = method.lower()

    if "check" in method_lower:
        payment_method = "check"

        match = re.search(r"#\s*(\d+)", method)
        last_4 = match.group(1) if match else None

    elif "stripe" in method_lower or "card" in method_lower or "****" in method:
        payment_method = "credit card"

        match = re.search(r"\*{2,}\s*(\d{4})", method)
        if not match:
            match = re.search(r"(\d{4})\b", method)

        last_4 = match.group(1) if match else None

    else:
        payment_method = method
        last_4 = None

    return {
        "payment_method": payment_method,
        "last_4": last_4,
    }

@tool
def get_customer_account_info(
    state: Annotated[AgentState, InjectedState],):

    """
    Retrieves normalized customer account, billing, and payment information
    from either the FieldRoutes or GorillaDesk CRM systems.

    Use this tool when account-specific customer information is required,
    such as:
    - account number lookup
    - billing status
    - payment method details
    - autopay/account questions
    - overdue balance information
    - customer contact/account verification

    Returns:
    A normalized dictionary containing customer account, billing,
    payment, and contact information regardless of CRM provider.
    """
    if state.get("account_info"):
        print("HITTING CACHE FOR ACCOUNT INFO")
        return state["account_info"]


    customer_id = state['customer_id']
    company_id = state["company_id"]
    customer_id = str(customer_id)

    #conn = get_db_connection()
    print("HITTING DATABASE FOR ACCOUNT INFO")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Try FieldRoutes
            cur.execute(
                """
                SELECT
                    c.fieldroutes_customer_id AS customer_id,
                    c.fname AS first_name,
                    c.lname AS last_name,
                    c.phone1 AS phone_number,
                    c.email AS email_address,
                    c.company_id AS company_id,
                    c.bill_to_account_id AS account_number,
                    c.status AS account_status,
                    c.balance AS past_due_balance,
                    p.payment_method AS payment_method_type,
                    p.last_four AS card_last_four,
                    p.status AS billing_status
                FROM fieldroutes_customers c
                LEFT JOIN LATERAL (
                    SELECT
                        payment_method,
                        last_four,
                        status
                    FROM fieldroutes_payments fp
                    WHERE fp.company_id = c.company_id
                    AND fp.fieldroutes_customer_id::text = c.fieldroutes_customer_id::text
                    ORDER BY fp.created_at DESC NULLS LAST
                    LIMIT 1
                ) p ON TRUE
                WHERE c.fieldroutes_customer_id::text = %s
                AND c.company_id = %s
                LIMIT 1;
                """,
                (customer_id, company_id),
            )

            row = cur.fetchone()

            if row:
                columns = [desc[0] for desc in cur.description]
                data = dict(zip(columns, row))
                data["provider"] = "fieldroutes"
                data["found"] = True
                return data

            # 2. Try GorillaDesk
            cur.execute(
                """
                SELECT
                    c.account_number AS customer_id,
                    c.first_name AS first_name,
                    c.last_name AS last_name,
                    c.phone AS phone_number,
                    c.emails AS email_address,
                    c.company_id AS company_id,
                    c.account_number AS account_number,
                    c.status AS account_status,
                    c.balance AS past_due_balance,
                    p.method AS raw_payment_method,
                    p.status AS billing_status
                FROM gorilladesk_customers c
                LEFT JOIN LATERAL (
                    SELECT
                        method,
                        status
                    FROM gorilladesk_payments gp
                    WHERE gp.company_id = c.company_id
                    AND gp.account_number::text = c.account_number::text
                    ORDER BY gp.created_at DESC NULLS LAST
                    LIMIT 1
                ) p ON TRUE
                WHERE c.account_number::text = %s
                AND c.company_id = %s
                LIMIT 1;
                """,
                (customer_id, company_id),
            )

            row = cur.fetchone()

            if row:
                columns = [desc[0] for desc in cur.description]
                data = dict(zip(columns, row))

                data["provider"] = "gorilladesk"
                data["found"] = True

                parsed_payment = parse_gorilladesk_payment_method(data.get("raw_payment_method"))

                data["payment_method_type"] = parsed_payment["payment_method"]
                data["card_last_four"] = parsed_payment["last_4"]
                data.pop("raw_payment_method", None)

                return data

    return {
        "provider": None,
        "found": False,
        "customer_id": customer_id,
        "account_number": None,
        "company_id": company_id,
        "message": "Customer not found in FieldRoutes or GorillaDesk tables.",
}

# ai/shared/conversation_history.py

from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage

from ai.agent.state import AgentState
from app.database.connection import get_db_connection

INBOUND_DIRECTIONS = {"inbound", "incoming", "received"}


def load_conversation_history_node(state: AgentState):

    playground_context = state.get("playground_context")

    if playground_context:
        raw_history = playground_context.get(
            "conversation_history",
            []
        )

        current_message_id = playground_context.get("message_id")

        conversation_history = []

        for message in raw_history:

            # Current customer message is already passed separately
            # as state["customer_message"]
            if (
                message.get("id") == current_message_id
                and message.get("sender") == "customer"
            ):
                continue

            sender = message.get("sender")
            body = message.get("body", "")

            if sender == "customer":
                conversation_history.append(
                    HumanMessage(content=body)
                )
            else:
                conversation_history.append(
                    AIMessage(content=body)
                )

        return {
            "conversation_history": conversation_history,
            "customer_first_name": playground_context.get(
                "customer_first_name",
                ""
            ),
            "google_review_link": playground_context.get(
                "google_review_link",
                ""
            ),
            "company_phone_number": playground_context.get(
                "company_phone",
                ""
            ),
        }

    # EXISTING production database logic stays below here
    
    customer_id = str(state["customer_id"]).strip()
    company_id = state["company_id"]

    customer_first_name = ""
    google_review_link = ""
    phone_number = ""

    history_rows = []

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # -------------------------
            # Company-level variables
            # -------------------------
            cur.execute(
                """
                SELECT
                    crm,
                    google_review_link,
                    phone_number,
                    active_review_type,
                    other_review_link
                FROM companies
                WHERE id = %s
                LIMIT 1
                """,
                (company_id,),
            )

            company_row = cur.fetchone()

            crm = ""
            if company_row:
                crm = (company_row[0] or "").strip().lower()
                google_review_link = (company_row[1] or "").strip()
                phone_number = (company_row[2] or "").strip()
                active_review_type = (company_row[3] or "").strip().lower()
                other_review_link = (company_row[4] or "").strip()

                if active_review_type == "other":
                    google_review_link = other_review_link

            # -------------------------
            # Customer first name by CRM
            # -------------------------
            if crm == "gorilladesk":
                cur.execute(
                    """
                    SELECT first_name
                    FROM gorilladesk_customers
                    WHERE company_id = %s
                      AND TRIM(REGEXP_REPLACE(COALESCE(account_number::text, ''), '\\.0+$', '')) = %s
                    LIMIT 1
                    """,
                    (company_id, customer_id),
                )

                row = cur.fetchone()
                customer_first_name = (row[0] or "").strip() if row else ""

            elif crm == "pestpac":
                cur.execute(
                    """
                    SELECT fname
                    FROM pestpac_customers
                    WHERE company_id = %s
                      AND bill_to::text = %s
                    LIMIT 1
                    """,
                    (company_id, customer_id),
                )

                row = cur.fetchone()
                customer_first_name = (row[0] or "").strip() if row else ""

            else:
                cur.execute(
                    """
                    SELECT fname
                    FROM fieldroutes_customers
                    WHERE company_id = %s
                      AND fieldroutes_customer_id::text = %s
                    LIMIT 1
                    """,
                    (company_id, customer_id),
                )

                row = cur.fetchone()
                customer_first_name = (row[0] or "").strip() if row else ""

            # -------------------------
            # Conversation history:
            # Up to and including latest outbound/company message
            # -------------------------
            cur.execute(
                """
                WITH last_outbound AS (
                    SELECT
                        created_at,
                        id
                    FROM messages
                    WHERE company_id = %s
                      AND customer_id::text = %s
                      AND COALESCE(LOWER(direction), '') NOT IN ('inbound', 'incoming', 'received')
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                )
                SELECT
                    body,
                    direction,
                    created_at,
                    id
                FROM messages
                WHERE company_id = %s
                  AND customer_id::text = %s
                  AND created_at >= NOW() - INTERVAL '24 hours'
                  AND EXISTS (SELECT 1 FROM last_outbound)
                  AND (created_at, id) <= (
                      SELECT created_at, id
                      FROM last_outbound
                  )
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (company_id, customer_id, company_id, customer_id, 10),
            )

            history_rows = cur.fetchall()
            history_rows = list(reversed(history_rows))

    conversation_history: List[Any] = []

    for body, direction, _, _ in history_rows:
        normalized_direction = (direction or "").lower()

        if normalized_direction in INBOUND_DIRECTIONS:
            conversation_history.append(HumanMessage(content=body or ""))
        else:
            conversation_history.append(AIMessage(content=body or ""))


    return {
        "conversation_history": conversation_history,
        "customer_first_name": customer_first_name,
        "google_review_link": google_review_link,
        "company_phone_number": phone_number,
    }

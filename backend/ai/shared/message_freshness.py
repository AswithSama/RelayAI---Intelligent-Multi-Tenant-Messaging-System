# ai/shared/message_freshness.py

import logging

logger = logging.getLogger(__name__)
from app.database.connection import execute_query


def is_still_latest_inbound(
    *,
    company_id: int,
    customer_id: str,
    message_id: int,
) -> bool:
    rows = execute_query(
        """
        SELECT id, body
        FROM messages
        WHERE company_id = %(company_id)s
          AND customer_id::text = %(customer_id)s
          AND COALESCE(LOWER(direction), '') IN ('inbound', 'incoming', 'received')
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        {
            "company_id": int(company_id),
            "customer_id": str(customer_id),
        },
    )

    latest_id = int(rows[0]["id"]) if rows else None

    logger.info(
        "AI latest inbound check. company_id=%s customer_id=%s processed_message_id=%s latest_inbound_id=%s latest_body=%s",
        company_id,
        customer_id,
        message_id,
        latest_id,
        rows[0].get("body") if rows else None,
    )

    return bool(rows) and latest_id == int(message_id)

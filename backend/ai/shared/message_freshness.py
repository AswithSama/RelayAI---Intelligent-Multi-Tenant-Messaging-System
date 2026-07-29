# ai/shared/message_freshness.py

import logging

from app.database.connection import execute_query

logger = logging.getLogger(__name__)


def is_still_latest_inbound(
    *,
    conversation_id: int,
    message_id: int,
) -> bool:
    """
    Check whether the message being processed is still the latest
    customer message in the playground conversation.
    """

    rows = execute_query(
        """
        SELECT id, body
        FROM messages
        WHERE conversation_id = %(conversation_id)s
          AND sender = 'customer'
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        {
            "conversation_id": int(conversation_id),
        },
    )

    latest_id = int(rows[0]["id"]) if rows else None

    logger.info(
        "AI latest inbound check. "
        "conversation_id=%s processed_message_id=%s "
        "latest_inbound_id=%s latest_body=%s",
        conversation_id,
        message_id,
        latest_id,
        rows[0].get("body") if rows else None,
    )

    return bool(rows) and latest_id == int(message_id)
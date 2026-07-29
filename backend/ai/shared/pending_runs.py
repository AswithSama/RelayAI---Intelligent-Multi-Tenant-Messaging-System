# ai/shared/pending_runs.py
from app.database.connection import get_db_connection

import logging
logger = logging.getLogger(__name__)

AI_DEBOUNCE_SECONDS = 5 


def enqueue_ai_pending_run(
    *,
    conversation_id: int,
    message_id: int,
) -> None:
    """
    Create or refresh the pending AI run for one playground conversation.

    When a customer sends multiple messages quickly, the existing pending row
    is updated with the newest message and the debounce timer starts again.
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_pending_runs (
                    conversation_id,
                    latest_message_id,
                    run_after,
                    status,
                    locked_at,
                    created_at,
                    updated_at
                )
                VALUES (
                    %(conversation_id)s,
                    %(message_id)s,
                    NOW() + (%(delay_seconds)s || ' seconds')::interval,
                    'pending',
                    NULL,
                    NOW(),
                    NOW()
                )
                ON CONFLICT (conversation_id)
                DO UPDATE SET
                    latest_message_id = EXCLUDED.latest_message_id,

                    run_after =
                        NOW() + (%(delay_seconds)s || ' seconds')::interval,

                    status = CASE
                        WHEN ai_pending_runs.status = 'running'
                            THEN 'running'
                        ELSE 'pending'
                    END,

                    locked_at = CASE
                        WHEN ai_pending_runs.status = 'running'
                            THEN ai_pending_runs.locked_at
                        ELSE NULL
                    END,

                    updated_at = NOW()

                WHERE EXCLUDED.latest_message_id >
                    ai_pending_runs.latest_message_id
                """,
                {
                    "conversation_id": int(conversation_id),
                    "message_id": int(message_id),
                    "delay_seconds": AI_DEBOUNCE_SECONDS,
                },
            )
            rows_changed = cur.rowcount

        conn.commit()

    if rows_changed == 0:
        logger.info(
            "AI pending run ignored because the message was not newer. "
            "conversation_id=%s message_id=%s",
            conversation_id,
            message_id,
        )
    else:
        logger.info(
            "AI pending run enqueued or refreshed. "
            "conversation_id=%s latest_message_id=%s delay_seconds=%s",
            conversation_id,
            message_id,
            AI_DEBOUNCE_SECONDS,
        )
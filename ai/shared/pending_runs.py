# ai/shared/pending_runs.py

from config import ENVIRONMENT, logger
from database import get_db_connection

AI_DEBOUNCE_SECONDS = 30 if ENVIRONMENT == "prod" else 5


def enqueue_ai_pending_run(
    *,
    company_id: int,
    customer_id: str,
    message_id: int,
) -> None:
    """
    Creates or refreshes the pending AI debounce run for one customer conversation.

    Every inbound customer SMS should call this after the inbound message is saved.
    If the customer sends multiple messages quickly, this keeps updating the same
    row and pushes run_after forward.
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_pending_runs (
                    company_id,
                    customer_id,
                    latest_message_id,
                    run_after,
                    status,
                    locked_at,
                    created_at,
                    updated_at
                )
                VALUES (
                    %(company_id)s,
                    %(customer_id)s,
                    %(message_id)s,
                    NOW() + (%(delay_seconds)s || ' seconds')::interval,
                    'pending',
                    NULL,
                    NOW(),
                    NOW()
                )
                ON CONFLICT (company_id, customer_id)
                DO UPDATE SET
                    latest_message_id = EXCLUDED.latest_message_id,
                    run_after = NOW() + (%(delay_seconds)s || ' seconds')::interval,
                    status = 'pending',
                    locked_at = NULL,
                    updated_at = NOW()
                WHERE EXCLUDED.latest_message_id > ai_pending_runs.latest_message_id
                """,
                {
                    "company_id": int(company_id),
                    "customer_id": str(customer_id),
                    "message_id": int(message_id),
                    "delay_seconds": AI_DEBOUNCE_SECONDS,
                },
            )
            rows_changed = cur.rowcount

        conn.commit()

    if rows_changed == 0:
        logger.info(
            "AI pending run enqueue ignored because incoming message was not newer. "
            "company_id=%s customer_id=%s message_id=%s delay_seconds=%s",
            company_id,
            customer_id,
            message_id,
            AI_DEBOUNCE_SECONDS,
        )
    else:
        logger.info(
            "AI pending run enqueued/refreshed. company_id=%s customer_id=%s latest_message_id=%s delay_seconds=%s",
            company_id,
            customer_id,
            message_id,
            AI_DEBOUNCE_SECONDS,
        )
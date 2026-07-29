# ai/shared/pending_run_worker.py

from ai.run_ai_workflow import ai_workflow_with_meta
from ai.shared.message_freshness import is_still_latest_inbound
from ai.shared.pending_runs import AI_DEBOUNCE_SECONDS
from app.database.connection import execute_query, get_db_connection

import logging
logger = logging.getLogger(__name__)
AI_STALE_LOCK_MINUTES = 5

def claim_ready_ai_run():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH ready AS (
                    SELECT id
                    FROM ai_pending_runs
                    WHERE (
                        status = 'pending'
                        AND run_after <= NOW()
                    )
                    OR (
                        status = 'running'
                        AND locked_at IS NOT NULL
                        AND locked_at <=
                            NOW() - (
                                %(stale_lock_minutes)s || ' minutes'
                            )::interval
                    )
                    ORDER BY run_after ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE ai_pending_runs AS pending_run
                SET
                    status = 'running',
                    locked_at = NOW(),
                    updated_at = NOW()
                FROM ready
                WHERE pending_run.id = ready.id
                RETURNING
                    pending_run.id,
                    pending_run.conversation_id,
                    pending_run.latest_message_id
                """,
                {
                    "stale_lock_minutes": AI_STALE_LOCK_MINUTES,
                },
            )

            row = cur.fetchone()

        conn.commit()

    return row


def finish_ai_run(
    *,
    run_id: int,
    processed_message_id: int,
) -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ai_pending_runs
                SET
                    status = CASE
                        WHEN latest_message_id = %(processed_message_id)s
                            THEN 'completed'
                        ELSE 'pending'
                    END,
                    locked_at = NULL,
                    updated_at = NOW()
                WHERE id = %(run_id)s
                """,
                {
                    "run_id": int(run_id),
                    "processed_message_id": int(processed_message_id),
                },
            )

        conn.commit()

def mark_ai_run_pending_again(
    *,
    run_id: int,
    delay_seconds: int = AI_DEBOUNCE_SECONDS,
) -> None:
    """
    Return a run to pending status and restart its debounce timer.
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ai_pending_runs
                SET status = 'pending',
                    run_after =
                        NOW() + (%(delay_seconds)s || ' seconds')::interval,
                    locked_at = NULL,
                    updated_at = NOW()
                WHERE id = %(run_id)s
                """,
                {
                    "run_id": int(run_id),
                    "delay_seconds": int(delay_seconds),
                },
            )

        conn.commit()


def mark_ai_run_failed(*, run_id: int) -> None:
    """
    Mark the pending run as failed if AI execution raises an exception.
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ai_pending_runs
                SET status = 'failed',
                    locked_at = NULL,
                    updated_at = NOW()
                WHERE id = %(run_id)s
                """,
                {
                    "run_id": int(run_id),
                },
            )

        conn.commit()


def get_inbound_message_for_ai(*, message_id: int) -> dict | None:
    """
    Retrieve the customer message that triggered the pending AI run.
    """

    rows = execute_query(
        """
        SELECT
            id,
            conversation_id,
            sender,
            body,
            requires_human_attention,
            created_at
        FROM messages
        WHERE id = %(message_id)s
          AND sender = 'customer'
        LIMIT 1
        """,
        {
            "message_id": int(message_id),
        },
    )

    return rows[0] if rows else None


def get_current_customer_turn(
    *,
    conversation_id: int,
    fallback_message_id: int,
) -> str:
    """
    Combine all customer messages sent after the latest AI or company
    response into one current customer turn.

    Example:

        customer: "Hello"
        customer: "I need help"
        customer: "with my account"

    Becomes:

        Hello
        -----
        I need help
        -----
        with my account
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH latest_response AS (
                    SELECT
                        created_at,
                        id
                    FROM messages
                    WHERE conversation_id = %(conversation_id)s
                      AND sender IN ('ai', 'company')
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                )
                SELECT body
                FROM messages
                WHERE conversation_id = %(conversation_id)s
                  AND sender = 'customer'
                  AND (
                      NOT EXISTS (
                          SELECT 1
                          FROM latest_response
                      )
                      OR (created_at, id) > (
                          SELECT created_at, id
                          FROM latest_response
                      )
                  )
                ORDER BY created_at ASC, id ASC
                """,
                {
                    "conversation_id": int(conversation_id),
                },
            )

            rows = cur.fetchall()

    messages = [
        (row["body"] or "").strip()
        for row in rows
        if (row["body"] or "").strip()
    ]

    if messages:
        return "\n-----\n".join(messages)

    fallback = get_inbound_message_for_ai(
        message_id=fallback_message_id,
    )

    return (fallback.get("body") or "").strip() if fallback else ""


def save_ai_message(
    *,
    conversation_id: int,
    body: str,
    requires_human_attention: bool = False,
) -> int:
    """
    Save the generated AI response in the playground messages table.
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (
                    conversation_id,
                    sender,
                    body,
                    requires_human_attention,
                    created_at
                )
                VALUES (
                    %(conversation_id)s,
                    'ai',
                    %(body)s,
                    %(requires_human_attention)s,
                    NOW()
                )
                RETURNING id
                """,
                {
                    "conversation_id": int(conversation_id),
                    "body": body,
                    "requires_human_attention": bool(
                        requires_human_attention
                    ),
                },
            )

            row = cur.fetchone()

        conn.commit()

    return int(row["id"])


def get_conversation_context(
    *,
    conversation_id: int,
) -> dict | None:
    rows = execute_query(
        """
        SELECT
            conversations.id,
            conversations.customer_id,
            customers.company_id,
            customers.name AS customer_name,
            companies.phone_number AS company_phone,
            companies.google_review_link
        FROM conversations
        JOIN customers
            ON customers.id = conversations.customer_id
        JOIN companies
            ON companies.id = customers.company_id
        WHERE conversations.id = %(conversation_id)s
        LIMIT 1
        """,
        {
            "conversation_id": int(conversation_id),
        },
    )

    return rows[0] if rows else None

def run_ai_workflow_for_pending_message(
    *,
    conversation_id: int,
    message_id: int,
) -> dict:
    """
    Build the current customer turn, execute the AI workflow, and save
    the generated response in the playground messages table.
    """

    inbound_message = get_inbound_message_for_ai(
        message_id=message_id,
    )

    if not inbound_message:
        logger.warning(
            "AI run skipped because the inbound message was not found. "
            "message_id=%s",
            message_id,
        )

        return {
            "ai_answer": None,
            "outbound_message_id": None,
        }

    customer_message = get_current_customer_turn(
        conversation_id=conversation_id,
        fallback_message_id=message_id,
    )
    conversation = get_conversation_context(conversation_id=conversation_id)

    if not conversation:
        logger.warning(
            "AI run skipped because conversation was not found. "
            "conversation_id=%s",
            conversation_id,
        )

        return {
            "ai_answer": None,
            "outbound_message_id": None,
        }

    ai_result = ai_workflow_with_meta(
        customer_id=conversation["customer_id"],
        company_id=conversation["company_id"],
        body=customer_message,
        message_id=message_id,
        playground_context={
            "conversation_id": conversation_id,
            "message_id": message_id,
            "customer_first_name": conversation.get("customer_name") or "",
            "company_phone": conversation.get("company_phone") or "",
            "google_review_link": conversation.get("google_review_link") or "",
        },
    )

    # The customer may have sent another message while the AI was running.
    if not is_still_latest_inbound(
        conversation_id=conversation_id,
        message_id=message_id,
    ):
        logger.info(
            "Skipping AI response because a newer customer message arrived. "
            "conversation_id=%s processed_message_id=%s",
            conversation_id,
            message_id,
        )

        return {
            "ai_answer": None,
            "outbound_message_id": None,
        }
    
    if not ai_result.get("should_send_message", False):
        logger.info(
            "AI workflow chose not to send a response. "
            "conversation_id=%s response_status=%s",
            conversation_id,
            ai_result.get("response_status"),
        )

        return {
            "ai_answer": None,
            "outbound_message_id": None,
        }
    
    ai_answer = ai_result.get("answer")

    if not ai_answer:
        logger.info(
            "AI workflow produced no answer. conversation_id=%s",
            conversation_id,
        )

        return {
            "ai_answer": None,
            "outbound_message_id": None,
        }

    requires_human_attention = (ai_result.get("response_status") == "human_attention_required")

    outbound_message_id = save_ai_message(
        conversation_id=conversation_id,
        body=ai_answer,
        requires_human_attention=requires_human_attention,
    )

    logger.info(
        "AI response saved. conversation_id=%s "
        "inbound_message_id=%s outbound_message_id=%s",
        conversation_id,
        message_id,
        outbound_message_id,
    )

    return {
        "ai_answer": ai_answer,
        "outbound_message_id": outbound_message_id,
    }


def process_ready_ai_run_once() -> None:
    """
    Claim and process one pending playground AI run.

    The background polling loop repeatedly calls this function.
    """

    pending_run = claim_ready_ai_run()

    if not pending_run:
        return

    run_id = pending_run["id"]
    conversation_id = pending_run["conversation_id"]
    latest_message_id = pending_run["latest_message_id"]

    try:
        if not is_still_latest_inbound(
            conversation_id=conversation_id,
            message_id=latest_message_id,
        ):
            logger.info(
                "Pending AI run is no longer for the latest message. "
                "run_id=%s conversation_id=%s",
                run_id,
                conversation_id,
            )

            mark_ai_run_pending_again(run_id=run_id)
            return

        run_ai_workflow_for_pending_message(
            conversation_id=int(conversation_id),
            message_id=int(latest_message_id),
        )

        finish_ai_run(
            run_id=run_id,
            processed_message_id=latest_message_id,
        )

    except Exception:
        logger.exception(
            "AI pending run failed. run_id=%s conversation_id=%s",
            run_id,
            conversation_id,
        )

        mark_ai_run_failed(run_id=run_id)
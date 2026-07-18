# ai/shared/pending_run_worker.py

from ai.run_ai_workflow import ai_workflow_with_meta
from ai.shared.message_freshness import is_still_latest_inbound
from ai.shared.pending_runs import AI_DEBOUNCE_SECONDS
from config import ENVIRONMENT, logger
from database import execute_query, get_db_connection
from services.messaging import send_message_core


def claim_ready_ai_run() -> dict | None:
    """
    Atomically claim one pending AI run that is ready to execute.

    This prevents two workers from processing the same pending run at the same time.
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH ready AS (
                    SELECT id
                    FROM ai_pending_runs
                    WHERE status = 'pending'
                      AND run_after <= NOW()
                    ORDER BY run_after ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE ai_pending_runs p
                SET status = 'running',
                    locked_at = NOW(),
                    updated_at = NOW()
                FROM ready
                WHERE p.id = ready.id
                RETURNING
                    p.id,
                    p.company_id,
                    p.customer_id,
                    p.latest_message_id
                """
            )
            row = cur.fetchone()

        conn.commit()

    if not row:
        return None

    return {
        "id": row[0],
        "company_id": row[1],
        "customer_id": row[2],
        "latest_message_id": row[3],
    }

def mark_ai_run_completed(
    *,
    run_id: int,
    message_id: int,
) -> None:
    """
    Mark the pending AI run as completed only if it still points
    to the message this worker actually processed.
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ai_pending_runs
                SET status = 'completed',
                    locked_at = NULL,
                    updated_at = NOW()
                WHERE id = %(run_id)s
                  AND latest_message_id = %(message_id)s
                """,
                {
                    "run_id": int(run_id),
                    "message_id": int(message_id),
                },
            )

        conn.commit()

def mark_ai_run_pending_again(
    *,
    run_id: int,
    delay_seconds: int = AI_DEBOUNCE_SECONDS,
) -> None:
    """
    Put the run back into pending state and push run_after forward again.
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ai_pending_runs
                SET status = 'pending',
                    run_after = NOW() + (%(delay_seconds)s || ' seconds')::interval,
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
    Mark the run as failed if AI execution crashes.
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
                {"run_id": int(run_id)},
            )

        conn.commit()


def get_inbound_message_for_ai(*, message_id: int) -> dict | None:
    """
    Fetch the inbound message that triggered the pending AI run.
    """

    rows = execute_query(
        """
        SELECT
            id,
            company_id,
            customer_id,
            body,
            from_phone,
            to_phone
        FROM messages
        WHERE id = %(message_id)s
          AND direction IN ('inbound', 'incoming', 'received')
        LIMIT 1
        """,
        {"message_id": int(message_id)},
    )

    return rows[0] if rows else None


def get_current_customer_turn_after_latest_outbound(
    *,
    company_id: int,
    customer_id: str,
    fallback_message_id: int,
) -> str:
    """
    Build the current customer turn by joining all inbound messages
    after the latest outbound/company message.

    This becomes state["customer_message"] when passed into ai_workflow_with_meta().
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH last_outbound AS (
                    SELECT
                        created_at,
                        id
                    FROM messages
                    WHERE company_id = %(company_id)s
                      AND customer_id::text = %(customer_id)s
                      AND COALESCE(LOWER(direction), '') NOT IN ('inbound', 'incoming', 'received')
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                )
                SELECT
                    body
                FROM messages
                WHERE company_id = %(company_id)s
                  AND customer_id::text = %(customer_id)s
                  AND COALESCE(LOWER(direction), '') IN ('inbound', 'incoming', 'received')
                  AND created_at >= NOW() - INTERVAL '24 hours'
                  AND (
                      NOT EXISTS (SELECT 1 FROM last_outbound)
                      OR (created_at, id) > (
                          SELECT created_at, id
                          FROM last_outbound
                      )
                  )
                ORDER BY created_at ASC, id ASC
                """,
                {
                    "company_id": int(company_id),
                    "customer_id": str(customer_id),
                },
            )
            rows = cur.fetchall()

    messages = [(row[0] or "").strip() for row in rows if (row[0] or "").strip()]

    if messages:
        return "\n-----\n".join(messages)

    fallback = get_inbound_message_for_ai(message_id=fallback_message_id)
    return (fallback.get("body") or "") if fallback else ""


def run_ai_workflow_for_pending_message(
    *,
    company_id: int,
    customer_id: str,
    message_id: int,
    dry_run: bool | None = None,
) -> dict:
    """
    Run the AI workflow for the latest inbound message and send the reply.

    This is the single production code path from an inbound customer text to an AI
    reply: rebuild the current customer turn, run the LangGraph workflow, and send the
    answer via send_message_core. The debounce loop calls it from
    process_ready_ai_run_once; the dev AI Playground calls it directly (synchronously)
    so what you test is exactly what production generates and sends.

    dry_run: None (default) sends for real only in prod, matching the loop. Pass
    True/False to force it — the Playground passes the operator's dry-run toggle. When
    dry-run, the reply is persisted (status='dry_run') but not sent via Twilio.

    Returns {"ai_answer", "outbound_message_id"}; either may be None when the workflow
    chooses not to reply or the inbound message is missing.
    """

    effective_dry_run = (ENVIRONMENT != "prod") if dry_run is None else dry_run

    inbound_message = get_inbound_message_for_ai(message_id=message_id)

    if not inbound_message:
        logger.warning(
            "AI pending run skipped because inbound message was not found. message_id=%s",
            message_id,
        )
        return {"ai_answer": None, "outbound_message_id": None}

    body = get_current_customer_turn_after_latest_outbound(
        company_id=int(company_id),
        customer_id=str(customer_id),
        fallback_message_id=int(message_id),
    )
    from_phone = inbound_message.get("from_phone")

    ai_result = ai_workflow_with_meta(
        customer_id=str(customer_id),
        company_id=int(company_id),
        body=body,
        message_id=str(message_id),
    )

    if not is_still_latest_inbound(company_id=int(company_id), customer_id=str(customer_id), message_id=int(message_id),):
        logger.info(
            "Skipping AI send because newer inbound arrived during processing. "
            "processed_message_id=%s company_id=%s customer_id=%s",
            message_id,
            company_id,
            customer_id,
        )
        return

    ai_answer = ai_result.get("answer")

    logger.info(
        "🤖 Debounced AI workflow completed for inbound message_id=%s, company_id=%s, customer_id=%s",
        message_id,
        company_id,
        customer_id,
    )
    logger.info("🤖 Debounced AI answer: %s", ai_answer)

    if not ai_answer:
        return {"ai_answer": None, "outbound_message_id": None}

    # Use from_phone so replies go back to the actual number that texted in,
    # not a stale or missing CRM phone number.
    outbound_msg = send_message_core(
        company_id=int(company_id),
        customer_id=str(customer_id),
        body=ai_answer,
        trigger_key=None,
        to_phone_override=from_phone,
        dry_run=effective_dry_run,
    )

    logger.info(
        "🤖 Debounced AI response sent. inbound_message_id=%s outbound_message_id=%s",
        message_id,
        outbound_msg.get("id"),
    )

    return {"ai_answer": ai_answer, "outbound_message_id": outbound_msg.get("id")}


def process_ready_ai_run_once() -> None:
    """
    Claim and process one ready pending AI run.

    This should be called repeatedly by a worker loop.
    """

    pending_run = claim_ready_ai_run()

    if not pending_run:
        return

    run_id = pending_run["id"]
    company_id = pending_run["company_id"]
    customer_id = pending_run["customer_id"]
    latest_message_id = pending_run["latest_message_id"]

    try:
        if not is_still_latest_inbound(
            company_id=company_id,
            customer_id=customer_id,
            message_id=latest_message_id,
        ):
            logger.info(
                "AI pending run_id=%s is no longer latest inbound. Re-queueing.",
                run_id,
            )
            mark_ai_run_pending_again(run_id=run_id)
            return

        run_ai_workflow_for_pending_message(
            company_id=int(company_id),
            customer_id=str(customer_id),
            message_id=int(latest_message_id),
        )

        mark_ai_run_completed(run_id=run_id, message_id=int(latest_message_id),)

    except Exception:
        logger.exception("AI pending run failed: run_id=%s", run_id)
        mark_ai_run_failed(run_id=run_id)

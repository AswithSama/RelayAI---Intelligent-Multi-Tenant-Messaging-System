# ai/shared/pending_run_loop.py
import asyncio

from ai.shared.pending_run_worker import process_ready_ai_run_once
from app.core.config import logger

AI_PENDING_RUN_POLL_SECONDS = 3


async def ai_pending_run_loop() -> None:
    """
    Background loop that continuously checks for debounced AI runs
    that are ready to execute.
    """

    logger.info("🤖 AI pending run worker loop started.")

    while True:
        try:
            # process_ready_ai_run_once is sync, so run it in a thread.
            await asyncio.to_thread(process_ready_ai_run_once)
        except Exception:
            logger.exception("AI pending run loop error")

        await asyncio.sleep(AI_PENDING_RUN_POLL_SECONDS)

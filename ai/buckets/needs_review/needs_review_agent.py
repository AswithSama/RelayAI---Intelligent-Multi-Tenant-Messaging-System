# ai/needs_review/needs_review_agent.py

from typing import Any, Dict

from ai.agent.state import AgentState


def classify_needs_review_sub_bucket(
    state: AgentState,
) -> Dict[str, Any]:
    """
    Layer 2 deterministic needs-review agent.

    This agent only normalizes the broad needs_review route into a consistent
    Layer 2 domain result.

    It does not use an LLM.
    It does not call tools.
    It does not create customer-facing replies.
    It does not decide final execution.
    """

    return {
        "domain": "needs_review",
        "sub_bucket": "needs_review_general",
        "reason": (
            "The customer message requires internal representative review and cannot be safely handled by an automated workflow."
        ),
    }

"""ai/state.py — Defines the shared AgentState schema used across all graph nodes."""

from typing import Any

from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict


class AgentState(TypedDict, total=False):

    company_id: str
    customer_id: str
    customer_first_name: str
    message_id: str
    google_review_link: str
    company_phone_number: str


    conversation_history: list
    customer_message: str
    messages: Annotated[list, add_messages]

    # Layer 1: broad classification
    broad_bucket_results: list[dict[str, Any]]
    active_broad_buckets: list[str]

    # Layer 2: domain/sub-bucket classification
    domain_results: list[dict[str, Any]]
    active_domain_buckets: list[str]

    # Layer 3: final orchestration/execution planning
    execution_plan: dict[str, Any]
    tool_results: list[dict[str, Any]]

    # Legacy/current fields — keep for now until fully migrated
    bucket_names: list[str]
    bucket_prompts: list[str]
    tools: list[Any]

    context: dict[str, Any]
    answer: str | None
    should_send_message: bool
    response_status: str

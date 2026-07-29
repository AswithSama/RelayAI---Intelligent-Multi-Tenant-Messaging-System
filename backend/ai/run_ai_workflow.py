"""
ai/run_ai_workflow.py

This is where ai_workflow is invoked.
It initializes the graph and runs the complete AI workflow for a customer message.
"""

from ai.agent.graph_builder import create_graph
from ai.buckets.all_buckets_registered import registry

graph = create_graph(registry)


def ai_workflow_with_meta(
    customer_id,
    company_id,
    body,
    message_id=None,
    playground_context=None,
):
    """
    Run the AI workflow and return the full result envelope.

    Returns a dict with:
      - answer: final customer-facing reply string, or None
      - should_send_message: whether the message should be sent to the customer
      - response_status: ready_to_send | no_response | human_attention_required
      - broad_bucket_results: Layer 1 selected broad buckets with reasons
      - active_broad_buckets: Layer 1 selected bucket names
      - domain_results: Layer 2 selected domain/sub-bucket results
      - active_domain_buckets: Layer 2 selected sub-bucket names
      - execution_plan: Layer 3 selected scenario outputs
      - tool_results: deterministic executor tool results
      - selected_template_key: final selected template key, if any
    """

    playground_context = playground_context or {}

    # Ensure the graph node can identify the current message.
    playground_context["message_id"] = message_id

    result = graph.invoke(
        {
            "company_id": str(company_id),
            "customer_id": str(customer_id),
            "customer_message": body,
            "messages": [],
            "message_id": str(message_id) if message_id is not None else None,
            "conversation_history": [],
            "playground_context": playground_context,
        }
    )

    return {
        "answer": result.get("answer"),
        "should_send_message": result.get("should_send_message", False),
        "response_status": result.get("response_status"),
        "selected_template_key": result.get("selected_template_key"),

        "broad_bucket_results": result.get("broad_bucket_results", []) or [],
        "active_broad_buckets": result.get("active_broad_buckets", []) or [],

        "domain_results": result.get("domain_results", []) or [],
        "active_domain_buckets": result.get("active_domain_buckets", []) or [],

        "execution_plan": result.get("execution_plan", {}) or {},
        "tool_results": result.get("tool_results", []) or [],

        "execution_stopped": result.get("execution_stopped", False),
        "stop_reason": result.get("stop_reason"),
    }


def ai_workflow(
    customer_id,
    company_id,
    body,
    message_id=None,
    playground_context=None,
):
    """
    Production/playground entry point.

    Returns just the customer-facing answer string.
    If should_send_message is False, returns None.
    """

    result = ai_workflow_with_meta(
        customer_id=customer_id,
        company_id=company_id,
        body=body,
        message_id=message_id,
        playground_context=playground_context,
    )

    if not result.get("should_send_message"):
        return None

    return result.get("answer")
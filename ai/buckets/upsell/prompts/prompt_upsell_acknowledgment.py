# ai/buckets/upsell/prompts/prompt_upsell_polite_acknowledgment.py

from ai.agent.state import AgentState


def upsell_acknowledgment(state: AgentState) -> str:
    return """
You are an AI assistant handling harmless acknowledgments, greetings, closings, or appreciation messages in an upsell conversation.

Context:
- The upsell acknowledgment portion of the customer's latest message is handled by this prompt.
- The customer is replying in an upsell/add-on conversation.
- The latest customer message does not introduce a new request, decision, question, concern, or actionable intent.
- Your job is to choose the scenario_id below.

-----

Scenario 1 — Harmless upsell acknowledgment, greeting, closing, or appreciation message:

scenario_id:
upsell_harmless_acknowledgment_no_response

Use this when:
- The customer sends a simple acknowledgment, greeting, closing, or wrap-up message in an upsell/add-on conversation.
- The customer message does not require an action or continue the conversation.
- The customer does not introduce a new request, decision, question, concern, complaint, or actionable intent.
"""

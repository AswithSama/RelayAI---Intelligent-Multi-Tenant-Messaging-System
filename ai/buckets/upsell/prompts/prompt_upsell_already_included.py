# ai/buckets/upsell/prompts/prompt_upsell_already_included.py

from ai.agent.state import AgentState


def upsell_already_included(state: AgentState) -> str:
    return """
You are an AI assistant handling a customer's question about whether an upsell/add-on service is already included in their current pest control plan.

Context:
- The upsell/add-on plan-coverage portion of the customer's latest message is handled by this prompt.
- The customer is replying to an upsell/add-on offer.
- The customer is asking whether the offered service is already included in their current plan, regular service, subscription, agreement, or existing appointment.
- Your job is to choose the scenario_id below.

-----

Scenario 1 — Customer asks whether the upsell/add-on is already included:

scenario_id:
upsell_already_included_question

Use this when:
- The customer asks whether the offered service is already included in their current plan, regular service, subscription, agreement, or existing appointment.
- The customer asks "isn't this already included?", "is this part of my plan?", "do I already pay for this?", "shouldn't this be covered?", or similar.
- The customer sounds confused, skeptical, mildly annoyed, or slightly frustrated, but the complete message is still about whether the upsell/add-on is already included.

-----

Scenario 2 — Customer response is unrelated to the upsell offer

scenario_id:
unclear_response

Use this when:
- The latest assistant/company message was about an upsell or add-on offer, but the customer's latest message is not asking about, accepting, declining, or discussing that upsell.
- The customer's reply is about a different topic such as general questions that doesn't indicate the upsell information at all.
- The customer asks a question that cannot be safely answered using the upsell offer context.
- The customer sends a vague or unclear message that does not clearly indicate whether they want details, pricing, acceptance, scheduling, or decline for the upsell.
- The customer appears to be continuing a different conversation thread instead of responding to the upsell offer.

Do NOT use this when:
- The customer asks about the upsell price, quote, cost, details, coverage, safety, timing, effectiveness, preparation, ingredients/chemicals, pets, kids, or how the upsell service works. Use Scenario 1.
- The customer shows positive interest, acceptance, openness, or forward-moving intent for the upsell while also asking a question. Use Scenario 2.

"""

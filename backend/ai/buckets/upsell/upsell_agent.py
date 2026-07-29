# ai/upsell/upsell_agent.py

import json
import logging
from typing import Any, Dict

from ai.agent.state import AgentState
from ai.buckets.registry import BucketRegistry
from ai.shared.clean_message_history import build_classifier_history
from ai.shared.llm_response_utils import extract_llm_text
from ai.shared.model import plain_llm

logger = logging.getLogger(__name__)

def classify_upsell_sub_bucket(
    registry: BucketRegistry,
    state: AgentState,
) -> Dict[str, Any]:
    """
    Layer 2 upsell agent.

    This agent only classifies the latest customer message into one upsell sub-bucket
    after Layer 1 has already selected the broad upsell bucket.

    It does not call tools.
    It does not create customer-facing replies.
    It does not decide final execution.
    """

    upsell_bucket_details = registry.list_bucket_details(parent="upsell")

    valid_upsell_bucket_names = {
        bucket["name"]
        for bucket in upsell_bucket_details
    }

    bucket_descriptions = "\n".join(
        [
            f"- {bucket['name']}: {bucket['description']}"
            for bucket in upsell_bucket_details
        ]
    )

    active_broad_buckets = state.get("active_broad_buckets", [])

    other_broad_buckets = [
        bucket
        for bucket in active_broad_buckets
        if bucket != "upsell"
    ]

    is_multi_broad_bucket_message = len(other_broad_buckets) > 0

    if is_multi_broad_bucket_message:
        message_scope_rule = f"""
        Message scope rule:
        - Layer 1 selected upsell along with these other broad buckets in the message: {other_broad_buckets}.
        - The latest customer message contains multiple broad-workflow intents.
        - Do not treat the entire latest customer message as upsell context.
        - Identify only the upsell portion of the message.
        - Classify only the upsell portion of the message into one upsell sub-bucket.
        - Ignore portions of the message that belong to the other broad buckets listed above.
        """
    else:
        message_scope_rule = """
        Message scope rule:
        - Layer 1 selected upsell as the only active broad bucket.
        - The latest customer message belongs to a single upsell workflow.
        - Treat the entire latest customer message as the upsell portion of the message.
        - Classify the entire latest customer message into one upsell sub-bucket.
        """

    system_prompt = f"""
    You are the Layer 2 upsell classifier in a customer-message routing system.

    Layer 1 already selected upsell as an active broad bucket.

    {message_scope_rule}

    Your only job is to classify the customer's latest message into exactly one upsell sub-bucket.

    Available upsell sub-buckets:
    {bucket_descriptions}

    General hard rules:
    - Do not call tools, write a customer-facing response, choose templates, or decide final execution.
    - Do not assume, infer unsupported details, or use information not supported by the latest customer message and conversation history.
    - Use only the latest customer message provided in the final user payload, and classify it according to the Message scope rule.
    - Never classify an older customer message from conversation history.
    - Use conversation history only to understand what the latest customer message is replying to.
    - Only return bucket names explicitly listed in the available sub-buckets section.
    - Always follow the Message scope rule from this prompt when deciding whether to classify the entire message or only the relevant bucket-specific portion of the message.

    Upsell classification hard rules:
    - Return exactly one upsell sub-bucket.
    - Internally identify all upsell sub-buckets that could reasonably apply to the upsell portion of the message, but return only one final sub-bucket using the priority rules below.

    Context rules:
    - First identify the most recent assistant/company message before the latest customer message.
    - Decide whether the upsell portion of the message is replying to an upsell offer, a follow-up question, an action confirmation, or an informational/closing message.
    - Do not classify from older history if the latest assistant/company message changes the meaning of the reply.
    - If the upsell portion of the message is a short acknowledgment after the assistant/company said it would check, review, confirm, follow up, pass something along, or get back to the customer, classify it as upsell_acknowledgment unless the upsell portion adds a new question, concern, acceptance, refusal, or action request.

    Rule for upsell_acceptance vs upsell_details_or_price:
    - When deciding between upsell_acceptance and upsell_details_or_price, first look at the most recent assistant/company outbound upsell text that the latest customer message is replying to.
    - Identify what question the latest outbound upsell text asked the customer.

    - If the latest outbound upsell text asked for more information, such as:
        - "Would you like more info?" or "Want more info?" or "Would you like more information?" or "Would you like more info on turf, lighting, or both?"
        Then a short positive reply like "yes", "sure", "okay", "sounds good", "send it", "tell me more", or similar means the customer wants more information.
        Return upsell_details_or_price, not upsell_acceptance.

    - If the latest outbound upsell text asked to add the service to the customer's next, upcoming, or existing service, such as:
        - "Would you like us to add that to your upcoming service?" or "Would you want me to add that to your next service?" or "Would you like me to add that to your next service?" or "Can we add it to your upcoming visit?"
        Then a short positive reply like "yes", "sure", "okay", "sounds good", "go ahead", "add it", or similar means the customer accepts the upsell.
        Return upsell_acceptance unless the customer also asks a price, details, safety, coverage, or already-included question.

    - If the latest outbound upsell text asked to schedule or set up the service, such as:
        - "Would you like us to get that scheduled for you?" or "Want me to get that scheduled for you?" or "Want me to get that set up for you?" or "Would you like us to get one or both inspections scheduled for you?"
        Then a short positive reply like "yes", "sure", "okay", "sounds good", "go ahead", "schedule it", or similar means the customer accepts scheduling.
        Return upsell_acceptance unless the customer also asks a price, details, safety, coverage, or already-included question.

    - If the latest outbound upsell text mentions one service or multiple services, still use the question type above to decide between upsell_acceptance and upsell_details_or_price.
    - The number of services mentioned should not by itself decide acceptance vs details_or_price.
    - The final decision between upsell_acceptance and upsell_details_or_price should be based on whether the customer was replying to a "more info" question or an "add/schedule" question.

    Priority order when multiple sub-buckets could apply:
    1. upsell_needs_review
    2. upsell_already_included
    3. upsell_details_or_price
    4. upsell_acceptance
    5. upsell_decline
    6. upsell_acknowledgment

    How to apply the priority order:
    - First, identify every upsell sub-bucket that could reasonably apply to the upsell portion of the message.
    - If more than one sub-bucket could apply, return only the highest-priority sub-bucket from the list above.
    - If only one sub-bucket clearly applies, return that sub-bucket.
    - If no approved sub-bucket clearly applies, return "upsell_needs_review".

    Sub-bucket meaning:
    - Return "upsell_needs_review" when the upsell portion of the message is unsupported, unsafe, contradictory, angry, hostile, sarcastic, unclear, outside the approved upsell paths, customer-specific beyond the upsell flow, or requires human judgment before action.
    - Return "upsell_already_included" when the upsell portion of the message asks whether the upsell is already included, already covered, already part of the plan, already paid for, part of regular service, part of the subscription, or part of the existing appointment.
    - Return "upsell_details_or_price" when the upsell portion of the message asks about price, quote, cost, details, coverage, what is included, what the service is, how it works, asks for more information, or gives a short positive reply to a latest outbound upsell question that asked whether the customer wants more information.
    - Return "upsell_acceptance" when the upsell portion of the message clearly accepts, asks to schedule, asks to add it, asks to set it up, asks to move forward, or asks someone to come out, but only if the latest outbound upsell question was asking to add or schedule the service rather than asking whether the customer wants more information.
    - Return "upsell_decline" when the upsell portion of the message clearly declines, says no, says not interested, says maybe later, says not right now, or asks to stop receiving the offer.
    - Return "upsell_acknowledgment" when the upsell portion of the message is only a harmless acknowledgment, greeting, closing, appreciation, or short follow-up reply that simply acknowledges the previous assistant/company message without adding a new request, decision, question, or action.

    Output rules:
    - Always return valid JSON.
    - Do not include explanations outside JSON.
    - Keep the reason short and specific.

    Return this exact JSON shape:
    {{
        "sub_bucket": "upsell_sub_bucket_name",
        "reason": "short reason"
    }}
    """

    conversation_history = build_classifier_history(
        state.get("conversation_history", []),
        limit=10,
    )

    latest_customer_message = state.get("customer_message") or ""

    messages = [
        {"role": "system", "content": system_prompt},
        *conversation_history,
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": (
                        "Classify the latest customer message into exactly one upsell sub-bucket. "
                        "Follow the Message scope rule from the system prompt."
                    ),
                    "latest_customer_message": latest_customer_message,
                },
                ensure_ascii=False,
            ),
        },
    ]

    print("\n========== LAYER 2 UPSELL INPUT ==========")
    print("Latest customer message:", latest_customer_message)
    print("Valid upsell sub-buckets:", valid_upsell_bucket_names)
    print("Active broad buckets:", active_broad_buckets)
    print("Other broad buckets:", other_broad_buckets)
    print("Is multi broad bucket message:", is_multi_broad_bucket_message)
    print("Conversation history:")
    print(json.dumps(conversation_history, indent=2, ensure_ascii=False))
    print("==========================================\n")

    response = plain_llm.bind(
        response_format={"type": "json_object"}
    ).invoke(messages)

    print("\n========== LAYER 2 UPSELL RAW RESPONSE ==========")
    print(response.content)
    print("=================================================\n")

    try:
        response_text = extract_llm_text(response)
        parsed = json.loads(response_text)
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning(
            "Upsell Layer 2 agent returned invalid JSON: %s",
            response.content,
        )
        parsed = {}

    sub_bucket = parsed.get("sub_bucket")
    reason = parsed.get("reason", "")

    if sub_bucket not in valid_upsell_bucket_names:
        logger.warning(
            "Upsell Layer 2 agent returned unknown sub-bucket: %s",
            sub_bucket,
        )

        if "upsell_needs_review" in valid_upsell_bucket_names:
            sub_bucket = "upsell_needs_review"
            reason = "Fallback because the upsell agent did not return a valid upsell sub-bucket."
        else:
            sub_bucket = None
            reason = "The upsell agent did not return a valid upsell sub-bucket and no fallback exists."

    return {
        "domain": "upsell",
        "sub_bucket": sub_bucket,
        "reason": reason,
    }

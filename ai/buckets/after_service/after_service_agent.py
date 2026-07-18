# ai/after_service/after_service_agent.py

import json
import logging
from typing import Any, Dict

from ai.agent.state import AgentState
from ai.buckets.registry import BucketRegistry
from ai.shared.clean_message_history import build_classifier_history
from ai.shared.llm_response_utils import extract_llm_text
from ai.shared.model import plain_llm

logger = logging.getLogger(__name__)


def classify_after_service_sub_bucket(
    registry: BucketRegistry,
    state: AgentState,
) -> Dict[str, Any]:
    """
    Layer 2 after-service agent.

    This agent only classifies the latest customer message into one after-service sub-bucket
    after Layer 1 has already selected the broad after_service bucket.

    It does not call tools.
    It does not create customer-facing replies.
    It does not decide final execution.
    """

    after_service_bucket_details = registry.list_bucket_details(parent="after_service")

    valid_after_service_bucket_names = {
        bucket["name"]
        for bucket in after_service_bucket_details
    }

    bucket_descriptions = "\n".join(
        [
            f"- {bucket['name']}: {bucket['description']}"
            for bucket in after_service_bucket_details
        ]
    )

    active_broad_buckets = state.get("active_broad_buckets", [])

    other_broad_buckets = [
        bucket
        for bucket in active_broad_buckets
        if bucket != "after_service"
    ]

    is_multi_broad_bucket_message = len(other_broad_buckets) > 0

    if is_multi_broad_bucket_message:
        message_scope_rule = f"""
        Message scope rule:
        - Layer 1 selected after_service along with these other broad buckets in the message: {other_broad_buckets}.
        - The latest customer message contains multiple broad-workflow intents.
        - Do not treat the entire latest customer message as after-service context.
        - Consider only the after-service portion of the message.
        - Classify only the after-service portion of the message into one after-service sub-bucket.
        - Ignore portions of the message that belong to the other broad buckets listed above.
        """
    else:
        message_scope_rule = """
        Message scope rule:
        - Layer 1 selected after_service as the only active broad bucket.
        - The latest customer message belongs to a single after-service workflow.
        - Treat the entire latest customer message as the after-service portion of the message.
        - Classify the entire latest customer message into one after-service sub-bucket.
        """

    system_prompt = f"""
    You are the Layer 2 after-service classifier in a customer-message routing system.

    Layer 1 already selected after_service as an active broad bucket.

    {message_scope_rule}

    Available after-service sub-buckets:
    {bucket_descriptions}

     General hard rules:
    - Do not call tools, write a customer-facing response, choose templates, or decide final execution.
    - Do not assume, infer unsupported details, or use information not supported by the latest customer message and conversation history.
    - Use only the latest customer message provided in the final user payload, and classify it according to the Message scope rule.
    - Never classify an older customer message from conversation history.
    - Use conversation history only to understand what the latest customer message is replying to.
    - Only return bucket names explicitly listed in the available sub-buckets section.
    - Always follow the Message scope rule from this prompt when deciding whether to classify the entire message or only the relevant bucket-specific portion of the message.

    After-service classification hard rules:
    - Return exactly one after-service sub-bucket.
    - Internally identify all after-service sub-buckets that could reasonably apply to the after-service portion of the message, but return only one final sub-bucket using the priority rules below.

    Context rules:
    - First identify the most recent assistant/company message before the latest customer message.
    - Decide whether the after-service portion of the message is replying to an after-service follow-up, service feedback request, Google review request, post-treatment explanation, action confirmation, or closing message.
    - Use the previous assistant/company message to resolve vague replies like "yes", "sure", "okay", "ok", "sounds good", "done", "thanks", "no", "fine", "all good", "still seeing bugs", "what was used?", "is it safe?", or "when will it work?".
    - Do not classify from older history if the latest assistant/company message changes the meaning of the reply.

    Priority order when multiple sub-buckets could apply:
    1. after_service_complaints
    2. after_service_review
    3. after_service_feedback

    How to apply the priority order:
    - First, identify every after-service sub-bucket that could reasonably apply to the after-service portion of the message.
    - If more than one sub-bucket could apply, return only the highest-priority sub-bucket from the list above.
    - If only one sub-bucket clearly applies, return that sub-bucket.
    - If no approved sub-bucket clearly applies, return "after_service_review".

    Sub-bucket meaning:
    - Return "after_service_complaints" when the after-service portion of the message complains, expresses dissatisfaction, says the service did not work, reports an unresolved issue, asks for a refund because of the service, or says they are unhappy.
    - Return "after_service_review" when the after-service portion of the message asks a service question, treatment question, product/chemical question, safety question, warranty question, coverage question, scheduling question, appointment question, billing/account/payment/invoice/charge question, customer-specific question, or says they are still seeing bugs fewer than 7 days after the last service.
    - Return "after_service_feedback" when the after-service portion of the message gives clean positive feedback, clean neutral feedback, or replies to a Google review request/link with agreement, completion, decline, or inability to leave a review.

    Output rules:
    - Always return valid JSON.
    - Do not include explanations outside JSON.
    - Keep the reason short and specific.

    Return this exact JSON shape:
    {{
        "sub_bucket": "after_service_sub_bucket_name",
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
                        "Classify the latest customer message into exactly one after-service sub-bucket. "
                        "Follow the Message scope rule from the system prompt."
                    ),
                    "latest_customer_message": latest_customer_message,
                },
                ensure_ascii=False,
            ),
        },
    ]

    print("\n========== LAYER 2 AFTER_SERVICE INPUT ==========")
    print("Latest customer message:", latest_customer_message)
    print("Valid after-service sub-buckets:", valid_after_service_bucket_names)
    print("Active broad buckets:", active_broad_buckets)
    print("Other broad buckets:", other_broad_buckets)
    print("Is multi broad bucket message:", is_multi_broad_bucket_message)
    print("Conversation history:")
    print(json.dumps(conversation_history, indent=2, ensure_ascii=False))
    print("=================================================\n")

    response = plain_llm.bind(
        response_format={"type": "json_object"}
    ).invoke(messages)

    print("\n========== LAYER 2 AFTER_SERVICE RAW RESPONSE ==========")
    print(response.content)
    print("========================================================\n")

    try:
        response_text = extract_llm_text(response)
        parsed = json.loads(response_text)
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning(
            "After-service Layer 2 agent returned invalid JSON: %s",
            response.content,
        )
        parsed = {}

    sub_bucket = parsed.get("sub_bucket")
    reason = parsed.get("reason", "")

    if sub_bucket not in valid_after_service_bucket_names:
        logger.warning(
            "After-service Layer 2 agent returned unknown sub-bucket: %s",
            sub_bucket,
        )

        if "after_service_review" in valid_after_service_bucket_names:
            sub_bucket = "after_service_review"
            reason = "Fallback because the after-service agent did not return a valid after-service sub-bucket."
        else:
            sub_bucket = None
            reason = "The after-service agent did not return a valid after-service sub-bucket and no fallback exists."

    return {
        "domain": "after_service",
        "sub_bucket": sub_bucket,
        "reason": reason,
    }

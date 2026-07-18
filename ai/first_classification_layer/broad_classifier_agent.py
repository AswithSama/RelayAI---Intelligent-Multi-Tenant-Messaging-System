import json
import logging
from typing import Any, Dict

from ai.agent.state import AgentState
from ai.buckets.registry import BucketRegistry
from ai.shared.clean_message_history import build_classifier_history
from ai.shared.llm_response_utils import extract_llm_text
from ai.shared.model import plain_llm

logger = logging.getLogger(__name__)


def classify_broad_buckets_node(registry: BucketRegistry):
    """
    Layer 1 broad classifier.

    This node only decides which broad workflow(s) are activated.
    It does not choose sub-buckets of any broad bucket.
    It does not call tools.
    It does not create customer-facing replies.

    Important:
    - This layer does NOT create or pass intent_text.
    - Downstream layers should use state["customer_message"] as the actual latest customer message.
    """

    def node(state: AgentState) -> Dict[str, Any]:
        broad_bucket_details = registry.list_bucket_details(level="broad")

        valid_broad_bucket_names = {
            bucket["name"]
            for bucket in broad_bucket_details
        }

        bucket_descriptions = "\n".join(
            [
                f"- {bucket['name']}: {bucket['description']}"
                for bucket in broad_bucket_details
            ]
        )

        system_prompt = f"""
        You are Layer 1 of a customer-message routing system.

        Your only job is to classify the customer's latest message into one or more broad buckets.

        Available broad buckets:
        {bucket_descriptions}

        Core rules:
        - Only return bucket names explicitly listed above.
        - Do not call tools.
        - Do not write a customer-facing response.
        - Do not choose templates or final actions.
        - Classify only the latest customer message.
        - Do not extract, rewrite, summarize, or create intent_text.
        - Use conversation history to understand what the latest customer message is replying to.

        Context rules:
        - First identify the most recent assistant/company message.
        - Determine whether the latest customer message is replying to that message or introducing a new topic.
        - Use converstaion history to resolve short or vague replies such as "yes", "sure", "okay", "sounds good", "no", "how much?", "what does that include?", "when?", "done", or "thank you".
        - Do not classify an older customer message from conversation history.
        - Do not add buckets only because older history mentioned other topics.

        Bucket selection rules:
        - Default to exactly one bucket.
        - Return multiple buckets only when the latest customer message clearly contains separate intents that require different broad workflows.
        - Do not return multiple buckets for one contextual intent.
        - Do not use "needs_review" just because the message has multiple intents.

        Broad bucket guidance:
        - Use "upsell" when the customer is replying to an upsell, add-on, upgrade, optional treatment, or extra-service offer. This includes accepting, declining, hesitating, asking price, asking what it includes, asking if it is included, asking to schedule it, or asking to add it.
        - Use "after_service" when the customer is replying to a completed service follow-up, review request, satisfaction check, service feedback message, treatment-result question, still-seeing-bugs message, or post-service complaint.
        - Use "billing_info" when the customer asks about account access, account number, login, billing, payment, autopay, card update, overdue payment, account status, or payment-related account information.
        - Also use "billing_info" when the customer replies to an overdue-service, missed-service, or service-back-on-schedule message, because overdue-service handling is currently grouped under billing_info.
        - Use "needs_review" when the latest message is unsupported, unrelated, unclear, hostile, sarcastic, profane, unsafe to answer, or does not need an AI response.

        Priority rule:
        - If the latest message is a harmless acknowledgment (e.g. thanks, awesome, sounds good) and the most recent assistant message was part of an active  upsell or add-on offer, classify it as upsell , not after_service.
        - Only use after_service for acknowledgments when the most recent assistant message was a completed-service follow-up, review request, or post-service feedback prompt.
        - Use "needs_review" for harmless acknowledgments only when they are not connected to a supported business workflow.

        Reason rule:
        - Keep reason short and specific.
        - The reason should explain why the latest customer message belongs to the selected bucket.

        Output rules:
        - Always return valid JSON.
        - Do not include explanations outside JSON.
        - Do not include intent_text in the output.

        Return this exact JSON shape:
        {{
            "broad_bucket_results": [
                {{
                    "bucket": "bucket_name",
                    "reason": "short reason"
                }}
            ]
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
        ]

        if latest_customer_message:
            messages.append(
                {
                    "role": "user",
                    "content": latest_customer_message,
                }
            )

        print("\n========== LAYER 1 BROAD CLASSIFIER INPUT ==========")
        print("Latest customer message:", latest_customer_message)
        print("Valid broad buckets:", valid_broad_bucket_names)
        print("Conversation history:")
        print(json.dumps(conversation_history, indent=2, ensure_ascii=False))
        print("====================================================\n")

        response = plain_llm.bind(
            response_format={"type": "json_object"}
        ).invoke(messages)

        print("\n========== LAYER 1 BROAD CLASSIFIER RAW RESPONSE ==========")
        print(response.content)
        print("===========================================================\n")

        try:
            response_text = extract_llm_text(response)
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning(
                "Layer 1 classifier returned invalid JSON: %s",
                response.content,
            )
            parsed = {"broad_bucket_results": []}

        raw_broad_bucket_results = parsed.get("broad_bucket_results", [])

        broad_bucket_results = []
        active_broad_buckets = []

        for item in raw_broad_bucket_results:
            bucket_name = item.get("bucket")

            if not bucket_name:
                continue

            if bucket_name not in valid_broad_bucket_names:
                logger.warning(
                    "Layer 1 classifier returned non-broad or unknown bucket: %s",
                    bucket_name,
                )
                continue

            broad_bucket_results.append(
                {
                    "bucket": bucket_name,
                    "reason": item.get("reason", ""),
                }
            )

            if bucket_name not in active_broad_buckets:
                active_broad_buckets.append(bucket_name)

        if not broad_bucket_results and "needs_review" in valid_broad_bucket_names:
            broad_bucket_results = [
                {
                    "bucket": "needs_review",
                    "reason": "Fallback because Layer 1 did not return any valid broad bucket.",
                }
            ]
            active_broad_buckets = ["needs_review"]

        return {
            "broad_bucket_results": broad_bucket_results,
            "active_broad_buckets": active_broad_buckets,
        }

    return node

# ai/billing_info/billing_agent.py

import json
import logging
from typing import Any, Dict, List

from ai.agent.state import AgentState
from ai.buckets.registry import BucketRegistry
from ai.shared.clean_message_history import build_classifier_history
from ai.shared.llm_response_utils import extract_llm_text
from ai.shared.model import plain_llm

logger = logging.getLogger(__name__)


def classify_billing_sub_buckets(
    registry: BucketRegistry,
    state: AgentState,
) -> Dict[str, Any]:
    """
    Layer 2 billing_info agent.

    This agent classifies the latest customer message into one or more billing_info
    sub-buckets after Layer 1 has already selected the broad billing_info bucket.

    It does not call tools.
    It does not create customer-facing replies.
    It does not decide final execution.
    """

    billing_bucket_details = registry.list_bucket_details(parent="billing_info")

    valid_billing_bucket_names = {
        bucket["name"]
        for bucket in billing_bucket_details
    }

    bucket_descriptions = "\n".join(
        [
            f"- {bucket['name']}: {bucket['description']}"
            for bucket in billing_bucket_details
        ]
    )

    active_broad_buckets = state.get("active_broad_buckets", [])

    other_broad_buckets = [
        bucket
        for bucket in active_broad_buckets
        if bucket != "billing_info"
    ]

    is_multi_broad_bucket_message = len(other_broad_buckets) > 0

    if is_multi_broad_bucket_message:
        system_prompt = f"""
        You are the Layer 2 billing_info classifier in a customer-message routing system.

        Layer 1 already selected billing_info as one of multiple active broad buckets.

        Message scope rule:
        - Layer 1 selected billing_info along with these other broad buckets in the message: {other_broad_buckets}.
        - The latest customer message contains multiple broad-bucket intents.
        - Do not treat the entire latest customer message as billing_info context.
        - Identify only the billing_info portion of the message.
        - Classify only the billing_info portion of the message into one or more billing_info sub-buckets.
        - Ignore portions of the message that belong to the other broad buckets listed above.

        Your only job is to classify the customer's latest message into one or more billing_info sub-buckets and return a JSON of the format provided.

        Available billing_info sub-buckets:
        {bucket_descriptions}

        General hard rules:
        - Do not call tools, write a customer-facing response, choose templates, or decide final execution.
        - Do not assume, infer unsupported details, or use information not supported by the latest customer message and conversation history.
        - Use only the latest customer message provided in the user payload, and classify it according to the Message scope rule.
        - Never classify an older customer message from conversation history.
        - Use conversation history to understand what the latest customer message is replying to.
        - Only return bucket names explicitly listed in the available sub-buckets section.
        - Always follow the Message scope rule from this prompt when deciding whether to classify the entire message or only the relevant bucket-specific portion of the message.

        Context rules:
        - The latest customer message may contain multiple broad-bucket intents because Layer 1 selected billing_info along with these other broad buckets: {other_broad_buckets}.
        - For this billing_info classifier, evaluate only the meaning of the latest customer message that is related to billing_info.
        - Do not split, rewrite, or extract the customer message. Simply ignore any non-billing meaning when choosing the billing_info sub-bucket.
        - Billing_info-related content includes AR/overdue payment reminders, autopay/card-update replies, account login/account number/password help, and overdue-service handling.
        - Do not classify the non-billing portion of the message into a billing_info sub-bucket.
        - Use conversation history only to understand what the billing-related meaning of the latest customer message is replying to.
        - Give highest priority to the most recent assistant/company message when interpreting short or vague billing-related replies.
        - If the billing-related meaning asks about anything outside the supported billing paths, such as charges, invoices, refunds, balances, payment history, failed payments, disputed billing, or payment processing, classify it as billing_needs_review.

        Billing classification hard rules:
        - Default to one sub-bucket
        - Return one or more billing_info sub-buckets.
        - Internally identify all billing_info sub-buckets that could reasonably apply to the billing_info portion of the message, but return the final sub-bucket list using the priority and safety rules below.
        - Return multiple sub-buckets only when multiple independent billing-related intents are clearly present in the billing_info portion of the message.

        Acknowledgement Rules:
        - If the billing_info-related portion of the latest customer message is a first-time vague acknowledgment directly replying to a supported billing request, classify it into the matching supported sub-bucket based on the most recent assistant/company message.
        - Example: If the assistant/company asked the customer to update an expiring card and the customer replies "sure", classify it as billing_autopay_info because it is the first acknowledgment to the card-update request.
        - If the billing_info-related portion of the latest customer message is a repeated vague acknowledgment after the assistant/company already responded to that same billing issue, do not carry forward the old intent again. Classify it as billing_needs_review unless the customer clearly adds a new supported billing intent.
        - Example: If the assistant/company already replied "Thanks !" and the customer then replies "okay" or "sure", classify it as billing_needs_review because it is only a repeated acknowledgment and should not trigger the same autopay/card-update scenario again.

        Sub-bucket meaning:
        - Return "billing_account_info" when the billing_info-related portion of the latest customer message is asking or replying about login help, portal access, account number, password reset, forgotten password.
        - Return "billing_autopay_info" only when the billing_info-related portion of the latest customer message is replying to a previous autopay setup request or expiring-card/card-update request, and only when the reply is about one of these: asking why autopay or the expiring-card update is needed, declining autopay or the card update, saying they cannot do it yet, agreeing to do it, or confirming it was already done; do not use this bucket for any other billing, payment, card, invoice, charge, balance, account-specific, how-to, instruction, or payment-processing question.
        - Return "billing_overdue_ar" only when the billing_info-related portion of the latest customer message is replying to a previous AR/overdue payment-reminder message or overdue-service message, and only when the reply is about one of these: saying they will pay now, saying they will pay later, saying they no longer use the company, saying they do not understand why they owe, saying they already paid, saying they thought they were on autodraft, declining overdue service, or providing scheduling availability for overdue service; do not use this bucket for general AR questions, detailed invoice/charge/payment questions, payment instructions, disputes, refunds, failed payments, payment history, discounts, or anything outside these approved AR/overdue-service reply types.
        - Return "billing_needs_review" when the billing-related meaning is a general billing/account/payment question, unclear billing issue, unsupported billing request, or does not confidently fit billing_account_info, billing_autopay_info, or billing_overdue_ar.

        Multiple sub-bucket rules:
        - Default to one bucket.
        - Return multiple sub-buckets only when billing_info-related portion of the latest customer message clearly contains multiple separate billing intents.
        - If the previous company message asked the customer to set up autopay and the customer says "why and what is my account number and password", return ["billing_autopay_info", "billing_account_info"].
        - If the previous company message asked the customer to update an expiring card and the customer says "why and how do I log in", return ["billing_autopay_info", "billing_account_info"].
        - If the customer says "why autopay and what's my account number", return ["billing_autopay_info", "billing_account_info"].

        Output rules:
        - Always return valid JSON.
        - Do not include explanations outside JSON.
        - Keep the reason short and specific.

        Return this exact JSON shape.

        For a single selected sub-bucket:
        {{
            "sub_buckets": ["billing_sub_bucket_name"],
            "reason": "short reason"
        }}

        For multiple selected sub-buckets:
        {{
            "sub_buckets": ["billing_sub_bucket_name_1", "billing_sub_bucket_name_2"],
            "reason": "short reason"
        }}
        """
    else:
        system_prompt = f"""
        You are the Layer 2 billing_info classifier in a customer-message routing system.

        Message scope rule:
        - Layer 1 selected billing_info as the only active broad bucket.
        - The latest customer message belongs to a single billing_info bucket.
        - Treat the entire latest customer message as the billing_info portion of the message.
        - Classify the entire latest customer message into one or more billing_info sub-buckets.

        Your only job is to classify the entire customers latest message into one or more billing_info sub-buckets and return a JSON of the format provided.

        Available billing_info sub-buckets:
        {bucket_descriptions}

        General hard rules:
        - Do not call tools, write a customer-facing response, choose templates, or decide final execution.
        - Do not assume, infer unsupported details, or use information not supported by the latest customer message and conversation history.
        - Use conversation history to understand what the latest customer message is replying to.
        - Only return bucket names explicitly listed in the available sub-buckets section.
        - Always follow the Message scope rule from this prompt.

        Billing classification hard rules:
        - Default to one sub-bucket
        - Only return one or more billing_info sub-buckets when applicable
        - Return multiple sub-buckets only when the billing_info portion of the latest customer message contains multiple clearly separate billing-related intents, and each intent can be strictly classified into a different billing sub-bucket.

        Context rules:
        - Treat the entire latest customer message as belonging to the billing_info bucket.
        - Billing_info sub-buckets are limited to AR/overdue payment reminder replies, overdue-service handling, autopay/expired card-update replies, account login/account number/password help.
        - Use conversation history to understand what the entire latest customer message is replying to.
        - Give highest priority to the most recent assistant/company message when interpreting the entire latest customer message.
        - The most recent assistant/company message controls the meaning of short or vague replies such as "yes", "sure", "okay", "done", "why", or "no".
        - Do not use older conversation history to create or continue a billing intent if the latest customer message does not clearly support it.
        - When unsure about any billing_info sub-bucket chose billing_needs_review sub-bucket.

        Acknowledgement Rules:
        - If the latest customer message is a first-time vague acknowledgment directly replying to a billing request, classify it into the matching supported sub-bucket based on the most recent assistant/company message.
        - Example: If the assistant/company asked the customer to update an expiring card and the customer replies "sure", classify it as billing_autopay_info because it is the first acknowledgment to the card-update request.
        - If the latest customer message is a repeated vague acknowledgment after the assistant/company already responded to that same billing issue, do not carry forward the old intent again. Classify it as billing_needs_review unless the customer clearly adds a new supported billing intent.
        - Example: If the assistant/company already replied "Thanks !" and the customer then replies "okay" or "sure", classify it as billing_needs_review because it is only a repeated acknowledgment and should not trigger the same autopay/card-update scenario again.

        Sub-bucket meaning:
        - Return "billing_account_info" only when the latest customer message is asking or replying about login help, portal access, account number, password reset, forgotten password.
        - Return "billing_autopay_info" only when the latest customer message is replying to a previous autopay setup request or expiring-card/card-update request, and only when the entire reply is about one of these: asking why autopay or the expiring-card update is needed, declining autopay or the card update, saying they cannot do it yet, agreeing to do it, or confirming it was already done.
        - Return "billing_overdue_ar" only when the latest customer message is replying to a previous AR/overdue payment-reminder message or overdue-service message, and only when the entire reply is about one of these: saying they will pay now, saying they will pay later, saying they no longer use the company, saying they do not understand why they owe, saying they already paid, saying they thought they were on autodraft, declining overdue service, or providing scheduling availability for overdue service.
        - Return "billing_needs_review" for any billing-related question, request, unclear issue, unsupported issue, account-specific issue, or payment-related message that does not strictly fall within the explicitly mentioned meanings of billing_account_info, billing_autopay_info, or billing_overdue_ar. Even if the surrounding context is related to one of those sub-buckets, the customers actual question/request must strictly match that sub-buckets allowed meaning; otherwise, return "billing_needs_review".

        Multiple sub-bucket rules:
        - Default to one bucket.
        - Return multiple sub-buckets only when the latest customer message clearly contains multiple separate billing intents.
        - If the previous company message asked the customer to set up autopay and the customer says "why and what is my account number and password", return ["billing_autopay_info", "billing_account_info"].
        - If the previous company message asked the customer to update an expiring card and the customer says "why and how do I log in", return ["billing_autopay_info", "billing_account_info"].
        - If the customer says "why autopay and what's my account number", return ["billing_autopay_info", "billing_account_info"].

        Output rules:
        - Always return valid JSON.
        - Do not include explanations outside JSON.
        - Keep the reason short and specific.

        Return this exact JSON shape.

        For a single selected sub-bucket:
        {{
            "sub_buckets": ["billing_sub_bucket_name"],
            "reason": "short reason"
        }}

        For multiple selected sub-buckets:
        {{
            "sub_buckets": ["billing_sub_bucket_name_1", "billing_sub_bucket_name_2"],
            "reason": "short reason"
        }}
        """


    conversation_history = build_classifier_history(
        state.get("conversation_history", []),
        limit=10,
    )

    latest_customer_message = state.get("customer_message") or ""

    broad_bucket_results = state.get("broad_bucket_results", [])

    billing_broad_reason = next(
        (
            item.get("reason", "")
            for item in broad_bucket_results
            if item.get("bucket") == "billing_info"
        ),
        "",
    )

    user_payload = {
        "task": (
            "Classify the latest customer message into one or more billing_info sub-buckets. "
            "Use the provided latest customer message, conversation history, selected Layer 1 broad buckets, "
            "Layer 1 billing_info classification reason, and the billing_info scope rule. "
            "Return only the approved billing_info sub-bucket JSON shape."
        ),
        "layer_1_context": {
            "selected_broad_buckets": active_broad_buckets,
            "billing_info_classification_reason": billing_broad_reason,
        },
        "message_context": {
            "latest_customer_message": latest_customer_message,
        },
    }

    messages = [
        {"role": "system", "content": system_prompt},
        *conversation_history,
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False),
        },
    ]

    print("\n========== LAYER 2 BILLING INPUT ==========")
    print("Latest customer message:", latest_customer_message)
    print("Valid billing sub-buckets:", valid_billing_bucket_names)
    print("Active broad buckets:", active_broad_buckets)
    print("Other broad buckets:", other_broad_buckets)
    print("Is multi broad bucket message:", is_multi_broad_bucket_message)
    print("Layer 1 billing reason:", billing_broad_reason)
    print("Conversation history:")
    print(json.dumps(conversation_history, indent=2, ensure_ascii=False))
    print("===========================================\n")

    response = plain_llm.bind(
        response_format={"type": "json_object"}
    ).invoke(messages)

    #print("\n========== LAYER 2 BILLING RAW RESPONSE ==========")
    #print(response.content)
    #print("==================================================\n")

    try:
        response_text = extract_llm_text(response)
        parsed = json.loads(response_text)
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning(
            "Billing Layer 2 agent returned invalid JSON: %s",
            response.content,
        )
        parsed = {}

    raw_sub_buckets = parsed.get("sub_buckets", [])
    reason = parsed.get("reason", "")

    if isinstance(raw_sub_buckets, str):
        raw_sub_buckets = [raw_sub_buckets]

    if not isinstance(raw_sub_buckets, list):
        raw_sub_buckets = []

    sub_buckets: List[str] = []

    for sub_bucket in raw_sub_buckets:
        if sub_bucket in valid_billing_bucket_names and sub_bucket not in sub_buckets:
            sub_buckets.append(sub_bucket)

    if "billing_needs_review" in sub_buckets and len(sub_buckets) > 1:
        sub_buckets = ["billing_needs_review"]
        reason = (
            "billing_needs_review was selected with another billing sub-bucket, "
            "so only billing_needs_review was kept."
        )

    if not sub_buckets:
        logger.warning(
            "Billing Layer 2 agent returned no valid sub-buckets: %s",
            raw_sub_buckets,
        )

        if "billing_needs_review" in valid_billing_bucket_names:
            sub_buckets = ["billing_needs_review"]
            reason = "Fallback because the billing agent did not return a valid billing sub-bucket."
        else:
            reason = "The billing agent did not return a valid billing sub-bucket and no fallback exists."

    domain_results = []

    for sub_bucket in sub_buckets:
        domain_results.append(
            {
                "domain": "billing_info",
                "sub_bucket": sub_bucket,
                "reason": reason,
            }
        )

    return {
        "domain_results": domain_results,
        "active_domain_buckets": sub_buckets,
    }

# ai/execution_layer/scenario_outputs.py

from typing import Any

SCENARIO_OUTPUTS: dict[str, dict[str, Any]] = {
    # =========================================================
    # action: handle_additional_support
    # =========================================================
    "service_question_internal_review": {
        "action": "handle_additional_support",
        "template_key": None,
        "parameters": {
            "issue": "Customer's after-service message asks a question that requires internal review.",
            "reason": "The message requires customer-specific information or human review outside the approved after-service templates.",
        },
    },
    "unclear_response":{
        "action": "handle_additional_support",
        "template_key": None,
        "parameters": {
            "issue": "Customer's message asks a question that requires internal review.",
            "reason": "The message requires customer-specific information or human review outside the approved templates.",
        },
    },
    "general_internal_review_fallback": {
        "action": "handle_additional_support",
        "template_key": None,
        "parameters": {
            "issue": "Customer's after-service message requires internal representative review.",
            "reason": "The message cannot be safely answered using only the approved after-service templates and available context.",
        },
    },
    "neutral_or_mildly_satisfied_feedback": {
        "action": "handle_additional_support",
        "template_key": None,
        "parameters": {
            "issue": "Customer gave neutral or ambiguous after-service feedback.",
            "reason": "The feedback does not clearly match the approved positive review request template and should not receive a customer-facing response.",
        },
    },
    "billing_account_internal_review": {
        "action": "handle_additional_support",
        "template_key": None,
        "parameters": {
            "issue": "Customer's billing/account message requires internal representative review.",
            "reason": "The message asks for billing, account, payment, charge, invoice, refund, balance, card, login, password, or overdue-service information that cannot be safely answered using the approved templates.",
        },
    },
    "ar_already_paid_or_autodraft_correction": {
        "action": "handle_additional_support",
        "template_key": None,
        "parameters": {
            "issue": "Customer says they already paid or thought they were on autodraft.",
            "reason": "The message requires internal review because payment status or autodraft status cannot be confirmed using approved templates.",
        },
    },
    "upsell_internal_review": {
        "action": "handle_additional_support",
        "template_key": None,
        "parameters": {
            "issue": "Customer's upsell-related message requires internal representative review.",
            "reason": "The message cannot be safely handled using the approved upsell templates, tools, or sub-bucket prompts.",
        },
    },
    # =========================================================
    # action: forward_message_to_company
    # =========================================================

    "after_service_complaint": {
        "action": "forward_message_to_company",
        "template_key": None,
        "parameters": {
            "query_type": "complaint",
            "notes": "Customer expressed frustration or concern that requires company follow-up.",
        },
    },
    "after_service_scheduling": {
        "action": "forward_message_to_company",
        "template_key": None,
        "parameters": {
            "query_type": "scheduling",
            "notes": "Customer wants to reschedule an after-service follow-up.",
        },
    },
    "ar_delayed_payment_timeline": {
        "action": "forward_message_to_company",
        "template_key": "billing_ar_customer_will_pay",
        "parameters": {
            "query_type": "billing",
            "notes": "Customer claims to be waiting until a later date to make payment.",
        },
    },
    "ar_no_longer_customer_or_cancelled": {
        "action": "forward_message_to_company",
        "template_key": None,
        "parameters": {
            "query_type": "billing",
            "notes": "Customer mentioned cancellation or no longer using the service.",
        },
    },
    "ar_balance_explanation_question": {
        "action": "forward_message_to_company",
        "template_key": None,
        "parameters": {
            "query_type": "billing",
            "notes": "Customer is confused about what they owe.",
        },
    },
    "overdue_service_availability_provided": {
        "action": "forward_message_to_company",
        "template_key": "billing_overdue_provides_times",
        "parameters": {
            "query_type": "scheduling",
            "notes": "Customer responded with availability for service.",
        },
    },
    "upsell_acceptance_schedule_new": {
        "action": "forward_message_to_company",
        "template_key": "upsell_acceptance_schedule_new",
        "parameters": {
            "query_type": "upsell",
            "notes": "Customer Opted in to {upsell_service_name}. Customer responded with his availability.",
        },
    },
    "upsell_acceptance_existing_appointment": {
        "action": "forward_message_to_company",
        "template_key": "upsell_acceptance_existing_appointment",
        "parameters": {
            "query_type": "upsell",
            "notes": "Customer Opted in to {upsell_service_name}. Customer wants the upsell added to an upcoming appointment",
        },
    },
    "upsell_already_included_question": {
        "action": "forward_message_to_company",
        "template_key": "upsell_already_included",
        "parameters": {
            "query_type": "upsell",
            "notes": "Customer Opted in for more information about the {upsell_service_name}. Please reach out to schedule",
        },
    },
    "upsell_details_or_price_quote": {
        "action": "forward_message_to_company",
        "template_key": "upsell_details_or_price_quote",
        "parameters": {
            "query_type": "upsell",
            "notes": "Customer Opted in for more information about the {upsell_service_name}. Please reach out to schedule",
        },
    },
    "upsell_positive_interest_with_question": {
        "action": "forward_message_to_company",
        "template_key": "upsell_details_or_price_schedule",
        "parameters": {
            "query_type": "upsell",
            "notes": "Customer Opted in for more information about the {upsell_service_name}. Please reach out to schedule",
        },
    },

    # =========================================================
    # action: billing_info
    # =========================================================

    "account_login_or_access_help": {
        "action": "billing_info",
        "template_key": "billing_login_help",
        "parameters": None,
    },
    "account_number_only_request": {
        "action": "billing_info",
        "template_key": "billing_account_number",
        "parameters": None,
    },
    # =========================================================
    # action: none
    # =========================================================

    "first_time_still_seeing_bugs_under_7_days": {
        "action": "none",
        "template_key": "after_service_still_seeing_bugs_under_7_days",
        "parameters": None,
    },
    "positive_after_service_feedback": {
        "action": "none",
        "template_key": "after_service_positive_review_request",
        "parameters": None,
    },
    "review_request_agreed_or_completed": {
        "action": "none",
        "template_key": "after_service_review_agreed",
        "parameters": None,
    },
    "review_request_declined_or_unable": {
        "action": "none",
        "template_key": "after_service_review_declined",
        "parameters": None,
    },
    "feedback_unclear_or_vague_acknowledgment": {
        "action": "none",
        "template_key": None,
        "parameters": {
            "issue": "Customer message did not clearly match any approved response scenario.",
            "reason": "The message appears to be a normal acknowledgment or vague conversational reply, but there is not enough context to safely infer intent or send an approved customer-facing template.",
        },
    },
    "autopay_why_needed": {
        "action": "none",
        "template_key": "billing_why_autopay",
        "parameters": None,
    },
    "expiring_card_why_update_needed": {
        "action": "none",
        "template_key": "billing_why_expiring_card",
        "parameters": None,
    },
    "autopay_or_card_update_declined_or_delayed": {
        "action": "none",
        "template_key": "billing_customer_declines",
        "parameters": None,
    },
    "autopay_or_card_update_will_do_or_completed": {
        "action": "none",
        "template_key": "billing_customer_will_do_it",
        "parameters": None,
    },
    "autopay_or_expiring_card_unclear_no_response": {
        "action": "handle_additional_support",
        "template_key": None,
        "parameters": {
            "issue": "Customer message did not clearly match any approved autopay or expiring-card response scenario.",
            "reason": "The message appears to be a vague acknowledgment or conversational reply, but there is not enough context to safely infer intent or send an approved customer-facing template.",
        },
    },
    "password_reset_only_request": {
        "action": "none",
        "template_key": "billing_password_reset",
        "parameters": None,
    },
    "account_info_unclear_no_response": {
        "action": "none",
        "template_key": None,
        "parameters": {
            "issue": "Customer message did not clearly match any approved account-information response scenario.",
            "reason": "The message appears to be a vague acknowledgment or conversational reply, but there is not enough context to safely infer intent or send an approved customer-facing template.",
        },
    },
    "ar_immediate_payment_promise": {
        "action": "none",
        "template_key": "billing_ar_customer_will_pay",
        "parameters": None,
    },
    "overdue_service_declined": {
        "action": "none",
        "template_key": "billing_overdue_declines",
        "parameters": None,
    },
    "ar_or_overdue_service_unclear_no_response": {
        "action": "none",
        "template_key": None,
        "parameters": {
            "issue": "Customer message did not clearly match any approved AR or overdue-service response scenario.",
            "reason": "The message appears to be a repetitive acknowledgment or vague conversational reply, but there is not enough context to safely infer intent or send an approved customer-facing template.",
        },
    },
    "upsell_harmless_acknowledgment_no_response": {
        "action": "none",
        "template_key": None,
        "parameters": None,
    },
    "upsell_declined_or_opted_out": {
        "action": "none",
        "template_key": "upsell_decline",
        "parameters": None,
    },
    "billing_account_acknowledgement_only": {
        "action": None,
        "template_key": None,
        "parameters": None,
    },
}


DEFAULT_SCENARIO_OUTPUT: dict[str, Any] = {
    "action": "handle_additional_support",
    "template_key": None,
    "parameters": {
        "issue": "Customer message requires internal representative review.",
        "reason": "Layer 3 returned an unknown or invalid scenario_id.",
    },
}


def get_scenario_output(scenario_id: str | None) -> dict[str, Any]:
    if not scenario_id:
        return DEFAULT_SCENARIO_OUTPUT

    return SCENARIO_OUTPUTS.get(scenario_id, DEFAULT_SCENARIO_OUTPUT)

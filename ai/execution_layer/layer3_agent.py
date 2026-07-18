# ai/execution_layer/layer3_agent.py

import json
import logging
from typing import Any, Dict, List

from ai.agent.state import AgentState
from ai.buckets.registry import BucketRegistry
from ai.execution_layer.deterministic_executor_node import deterministic_executor_node
from ai.execution_layer.scenario_outputs import get_scenario_output
from ai.shared.clean_message_history import build_classifier_history
from ai.shared.llm_response_utils import extract_llm_text
from ai.shared.model import plain_llm

logger = logging.getLogger(__name__)


def extract_scenario_ids(parsed: Dict[str, Any]) -> List[str]:
    """
    Extracts selected scenario_ids from the Layer 3 LLM response.

    Supported single-scenario shape:
    {
        "scenario_id": "approved_scenario_id"
    }

    Supported multi-scenario billing shape:
    {
        "scenario_ids": [
            "approved_scenario_id_1",
            "approved_scenario_id_2"
        ]
    }

    Also supports:
    {
        "scenarios": [
            {"scenario_id": "approved_scenario_id_1"},
            {"scenario_id": "approved_scenario_id_2"}
        ]
    }
    """

    scenario_id = parsed.get("scenario_id")

    if isinstance(scenario_id, str) and scenario_id.strip():
        return [scenario_id.strip()]

    scenario_ids = parsed.get("scenario_ids")

    if isinstance(scenario_ids, list):
        return [
            item.strip()
            for item in scenario_ids
            if isinstance(item, str) and item.strip()
        ]

    scenarios = parsed.get("scenarios")

    if isinstance(scenarios, list):
        extracted_ids: List[str] = []

        for item in scenarios:
            if not isinstance(item, dict):
                continue

            item_scenario_id = item.get("scenario_id")

            if isinstance(item_scenario_id, str) and item_scenario_id.strip():
                extracted_ids.append(item_scenario_id.strip())

        return extracted_ids

    return []


def build_domain_specific_rules(domain: str | None) -> str:
    """
    Builds Layer 3 rules that apply only to the current selected domain.
    Keep global rules in the system prompt and keep domain-specific behavior here.
    """

    if domain == "upsell":
        return """
        Domain-specific rules for upsell:
        - The current selected domain is upsell.
        - Choose exactly one approved scenario_id from the selected upsell sub-bucket prompt.
        - Do not return multiple scenario_ids for upsell.
        - Use the upsell service name only if it is provided in the current selection context.

        Upsell inspection scheduling rule:
        - Apply this rule only when the upsell offer is for an inspection and only when the current selected sub-bucket is upsell_acceptance.
        - Treat termite inspections, rodent inspections, pest inspections, property inspections, or any upsell message that says inspect/inspection as inspection upsells.
        - Inspection upsells must be scheduled as a separate/new service or appointment.
        - Inspection upsells must not be added to the customer's existing service, next service, upcoming service, or already scheduled appointment.
        - If the latest assistant/company upsell message offered to schedule an inspection, choose the approved scenario_id for scheduling a new appointment.
        - If the customer asks to add the inspection to their next service or existing appointment, still choose the approved scenario_id for scheduling a new appointment.
        - Do not choose an existing/upcoming appointment scenario for inspection upsells.

        General upsell rule:
        - If the upsell is not an inspection, choose the closest approved upsell scenario from the selected prompt based on the latest customer message and conversation history.
        """

    if domain == "billing_info":
        return """
        Domain-specific rules for billing_info:
        - The current selected domain is billing_info.
        - Billing_info may return one scenario_id or multiple scenario_ids.
        - Return multiple scenario_ids only when the latest customer message clearly contains multiple distinct billing intents, and each intent is explicitly handled by an approved scenario in selected_sub_bucket_prompt.
        - If only one approved billing intent is present, return exactly one scenario_id.
        - Do not return multiple scenario_ids just because the message contains extra context, explanation, or follow-up wording.

        Billing full-coverage rule:
        - The selected billing scenario_id or scenario_ids must safely cover the full meaningful latest customer message.
        - Do not choose a normal billing scenario just because one part of the message matches.
        - If the customer message contains one approved part and one unsupported billing/payment/account question, choose Scenario X from the selected billing prompt.
        - Payment-processing questions such as "can you run the payment?", "do I need to pay now?", "will you charge it?", or "should I do anything else?" are not handled by autopay/card-update completion scenarios unless explicitly listed in the selected prompt.
        - Account number, password, login info, or access-detail questions may be handled with an autopay/card-update completion scenario only when the selected prompt explicitly allows that exception and the question is only needed to complete the autopay/card-update request.
        - If the selected billing prompt does not explicitly handle the extra question/request, choose Scenario X.
        - Do not apply upsell or after_service behavior to billing_info.
        """

    if domain == "after_service":
        return """
        Domain-specific rules for after_service:
        - The current selected domain is after_service.
        - Choose exactly one approved scenario_id from the selected after-service sub-bucket prompt.
        - Do not return multiple scenario_ids for after_service.
        - Use conversation history to understand what the latest customer message is replying to.
        """

    if domain == "needs_review":
        return """
        Domain-specific rules for needs_review:
        - The current selected domain is needs_review.
        - Choose exactly one approved scenario_id from the selected needs-review sub-bucket prompt.
        - Use this domain when the message requires internal review, is unclear, unsupported, risky, or cannot be safely handled by the automated workflow.
        - Do not force the message into upsell, billing_info, or after_service behavior.
        - Do not return multiple scenario_ids for needs_review.
        """

    return """
    Domain-specific rules for unknown or fallback domain:
    - Choose exactly one approved scenario_id from the selected sub-bucket prompt.
    - Do not return multiple scenario_ids unless the current domain is billing_info.
    - If no approved scenario can be safely selected, return no scenario_id so the Python fallback can route the message to internal support.
    """


def layer3_scenario_selector_node(registry: BucketRegistry):
    """
    Layer 3 scenario selector.

    This node:
    - reads selected Layer 2 sub-buckets from state["domain_results"]
    - retrieves each selected sub-bucket prompt from the registry
    - asks the LLM to choose the best matching scenario_id inside each prompt
    - allows multiple scenario_ids only for billing-style domains
    - maps each selected scenario_id to a deterministic scenario_output
    - stores the mapped scenario outputs in state["execution_plan"]
    - calls the deterministic executor as the final step

    This node does not directly execute tools itself.
    """

    def node(state: AgentState) -> Dict[str, Any]:
        latest_customer_message = state.get("customer_message") or ""
        domain_results = state.get("domain_results", [])

        selected_sub_bucket_context: List[Dict[str, Any]] = []

        for domain_result in domain_results:
            sub_bucket = domain_result.get("sub_bucket")

            if not sub_bucket:
                continue

            if not registry.exists(sub_bucket):
                logger.warning(
                    "Layer 3 received unknown selected sub-bucket: %s",
                    sub_bucket,
                )
                continue

            bucket_config = registry.get(sub_bucket)
            bucket_prompt = bucket_config.get_prompt(state)

            domain = domain_result.get("domain")

            selected_context = {
                "domain": domain,
                "sub_bucket": sub_bucket,
                "classification_reason": domain_result.get("reason", ""),
                "bucket_prompt": bucket_prompt,
            }

            selected_context["upsell_service_name"] = domain_result.get(
                "upsell_service_name",
            ) or ["none"]

            selected_sub_bucket_context.append(selected_context)

        if not selected_sub_bucket_context:
            execution_plan = {
                "scenario_results": [
                    {
                        "domain": "unknown",
                        "sub_bucket": "unknown",
                        "customer_message": latest_customer_message,
                        "classification_reason": "",
                        "selected_scenario_id": None,
                        "scenario_output": {
                            "action": "handle_additional_support",
                            "template_key": None,
                            "parameters": {
                                "issue": "No valid selected sub-bucket was available for Layer 3.",
                                "reason": "Layer 3 could not retrieve any selected sub-bucket prompt from the registry.",
                            },
                        },
                        "reason": "No valid selected sub-bucket context was available.",
                    }
                ]
            }

            return deterministic_executor_node(
                registry=registry,
                state={
                    **state,
                    "execution_plan": execution_plan,
                },
            )

        selected_sub_bucket_names = list(
            dict.fromkeys(
                context["sub_bucket"]
                for context in selected_sub_bucket_context
                if context.get("sub_bucket")
            )
        )

        is_multi_sub_bucket_message = len(selected_sub_bucket_names) > 1

        if is_multi_sub_bucket_message:
            message_scope_rule = f"""
            Message scope rule:
            - Layer 2 selected multiple sub-buckets for this message: {selected_sub_bucket_names}.
            - The latest customer message contains multiple workflow-specific intents.
            - Do not treat the entire latest customer message as belonging to the current sub-bucket.
            - For the current selected sub-bucket, consider only the portion of the message that belongs to this sub-bucket.
            - Ignore portions of the message that belong to the other selected sub-buckets.
            - Choose the best approved scenario_id from the current selected sub-bucket prompt for only that sub-bucket-specific portion.
            """
        else:
            message_scope_rule = f"""
            Message scope rule:
            - Layer 2 selected exactly one sub-bucket for this message: {selected_sub_bucket_names}.
            - The latest customer message belongs to a single selected sub-bucket workflow.
            - Treat the latest customer message according to this selected sub-bucket prompt.
            """

        conversation_history = build_classifier_history(
            state.get("conversation_history", []),
            limit=10,
        )

        scenario_results: List[Dict[str, Any]] = []
        seen_sub_buckets = set()

        for selected_context in selected_sub_bucket_context:
            sub_bucket = selected_context.get("sub_bucket")
            domain = selected_context.get("domain")
            upsell_service_name = selected_context.get("upsell_service_name") or ["none"]
            domain_specific_rules = build_domain_specific_rules(domain)
            if domain == "billing_info":
                output_shape_rules = """
                Return this exact JSON shape for normal single-scenario selection:
                {
                    "scenario_id": "approved_scenario_id"
                }

                When multiple supported billing/account intents are present, return:
                {
                    "scenario_ids": [
                        "approved_scenario_id_1",
                        "approved_scenario_id_2"
                    ]
                }
                """
            else:
                output_shape_rules = """
                Return this exact JSON shape:
                {
                    "scenario_id": "approved_scenario_id"
                }
                """

            if not sub_bucket:
                continue

            if sub_bucket in seen_sub_buckets:
                continue

            system_prompt = f"""
            You are Layer 3 of a customer-message workflow.

            Layer 1 selected broad buckets.
            Layer 2 selected specific domain/sub-buckets.

            Current selected domain:
            {domain}

            Current selected sub-bucket:
            {sub_bucket}

            {message_scope_rule}

            Your job is to read the selected sub-bucket prompt and choose the best matching approved scenario_id for the latest_customer_message.

            Hard rules:
            - Do not invent service details, treatment results, appointment details, pricing, refund details, or company policies.
            - Do not assume missing context, customer intent, service outcome, product used, safety information, appointment status, billing status, refund eligibility, or company policy.
            - Do not answer customer-specific questions yourself.
            - Do not answer service, treatment, safety, scheduling, warranty, billing, account, payment, invoice, refund, or appointment questions yourself.
            - Do not create, rewrite, or modify templates.
            - You must only choose scenario_ids that are explicitly listed in the selected sub-bucket prompt.
            - Process the current selected sub-bucket.
            - Return only one response object for the current selected sub-bucket.

            Domain-specific rules:
            {domain_specific_rules}

            For the current selected sub-bucket:
            - Read message_context.latest_customer_message as the latest customer message to evaluate.
            - Use conversation_history to understand context.
            - Read the selected_sub_bucket_prompt from user payload.
            - Choose the best matching approved scenario_id listed in selected_sub_bucket_prompt.

            Output rules:
            - Always return valid JSON.
            - Do not include explanations outside JSON.
            - Do not include markdown.
            - Do not include customer-facing text.
            - Do not return action.
            - Do not return template_key.
            - Do not return parameters.

            {output_shape_rules}
            """

            user_payload = {
                "task": (
                    "Choose the best matching approved scenario_id for the current selected sub-bucket. "
                    "Use provided latest customer message, conversation history, classification reason, "
                    "and selected sub-bucket prompt to evaluate. Do not return action, template_key, or parameters."
                ),
                "current_selection": {
                    "domain": domain,
                    "sub_bucket": sub_bucket,
                },
                "message_context": {
                    "latest_customer_message": latest_customer_message,
                },
                "selected_sub_bucket_prompt": selected_context.get("bucket_prompt", ""),
            }

            if domain == "upsell":
                user_payload["current_selection"]["upsell_service_name"] = (
                    upsell_service_name
                )

            messages = [
                {"role": "system", "content": system_prompt},
                *conversation_history,
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ]
            print("\n========== LAYER 3 SINGLE SUB-BUCKET INPUT ==========")
            print("Latest customer message:", latest_customer_message)
            print("Selected sub-bucket:", sub_bucket)
            print("Domain:", domain)
            print(
                "Classification reason:",
                selected_context.get("classification_reason", ""),
            )
            print("=====================================================\n")

            response = plain_llm.bind(response_format={"type": "json_object"}).invoke(messages)

            print("\n========== LAYER 3 SINGLE SUB-BUCKET RAW RESPONSE ==========")
            print(response.content)
            print("============================================================\n")

            try:
                response_text = extract_llm_text(response)
                parsed = json.loads(response_text)
            except (json.JSONDecodeError, ValueError, TypeError):
                logger.warning(
                    "Layer 3 scenario selector returned invalid JSON for sub-bucket %s: %s",
                    sub_bucket,
                    response.content,
                )

                scenario_results.append(
                    {
                        "domain": domain,
                        "sub_bucket": sub_bucket,
                        "customer_message": latest_customer_message,
                        "classification_reason": selected_context.get(
                            "classification_reason",
                            "",
                        ),
                        "upsell_service_name": upsell_service_name,
                        "selected_scenario_id": None,
                        "scenario_output": {
                            "action": "handle_additional_support",
                            "template_key": None,
                            "parameters": {
                                "issue": f"Layer 3 returned invalid JSON for {sub_bucket}.",
                                "reason": "The scenario selector failed to return parseable JSON, so internal review is required.",
                            },
                        },
                        "reason": "Layer 3 returned invalid JSON.",
                    }
                )

                seen_sub_buckets.add(sub_bucket)
                continue

            reason = parsed.get("reason", "")

            parsed_domain = domain
            parsed_sub_bucket = sub_bucket

            selected_scenario_ids = extract_scenario_ids(parsed)
            allows_multiple_outputs = parsed_domain in {"billing_info"}

            if not allows_multiple_outputs and len(selected_scenario_ids) > 1:
                logger.warning(
                    "Layer 3 returned multiple scenario_ids for non-billing domain %s / sub-bucket %s. Keeping only the first scenario_id.",
                    parsed_domain,
                    sub_bucket,
                )
                selected_scenario_ids = selected_scenario_ids[:1]

            if not selected_scenario_ids:
                scenario_results.append(
                    {
                        "domain": parsed_domain,
                        "sub_bucket": parsed_sub_bucket,
                        "customer_message": latest_customer_message,
                        "classification_reason": selected_context.get(
                            "classification_reason",
                            "",
                        ),
                        "upsell_service_name": upsell_service_name,
                        "selected_scenario_id": None,
                        "scenario_output": {
                            "action": "handle_additional_support",
                            "template_key": None,
                            "parameters": {
                                "issue": f"Layer 3 did not return a scenario_id for {sub_bucket}.",
                                "reason": "The scenario selector returned no approved scenario_id, so internal review is required.",
                            },
                        },
                        "reason": "Layer 3 returned no scenario_id.",
                    }
                )

                seen_sub_buckets.add(sub_bucket)
                continue

            for index, selected_scenario_id in enumerate(
                selected_scenario_ids,
                start=1,
            ):
                scenario_output = get_scenario_output(selected_scenario_id)

                scenario_results.append(
                    {
                        "domain": parsed_domain,
                        "sub_bucket": parsed_sub_bucket,
                        "customer_message": latest_customer_message,
                        "classification_reason": selected_context.get(
                            "classification_reason",
                            "",
                        ),
                        "upsell_service_name": upsell_service_name,
                        "selected_scenario_id": selected_scenario_id,
                        "scenario_output": scenario_output,
                        "reason": reason or f"Matched selected scenario_id {index}.",
                    }
                )
            seen_sub_buckets.add(sub_bucket)

        if not scenario_results:
            scenario_results.append(
                {
                    "domain": "unknown",
                    "sub_bucket": "unknown",
                    "customer_message": latest_customer_message,
                    "classification_reason": "",
                    "selected_scenario_id": None,
                    "scenario_output": {
                        "action": "handle_additional_support",
                        "template_key": None,
                        "parameters": {
                            "issue": "Layer 3 did not produce any scenario results.",
                            "reason": "No selected sub-bucket produced a valid scenario output, so internal review is required.",
                        },
                    },
                    "reason": "Layer 3 produced no valid scenario results.",
                }
            )

        execution_plan = {
            "scenario_results": scenario_results,
        }

        return deterministic_executor_node(
            registry=registry,
            state={
                **state,
                "execution_plan": execution_plan,
            },
        )

    return node

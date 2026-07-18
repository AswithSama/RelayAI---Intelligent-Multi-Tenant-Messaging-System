# ai/execution_layer/deterministic_executor_node.py

import logging
import string
from typing import Any, Dict, List

from ai.agent.state import AgentState
from ai.buckets.registry import BucketRegistry
from ai.shared.message_freshness import is_still_latest_inbound
from ai.tools.tool_additional_support import handle_additional_support
from ai.tools.tool_billing_info import get_customer_account_info
from ai.tools.tool_forward_message import forward_message_to_company
from ai.utils.template_helpers import get_current_day
from database import get_db_connection

logger = logging.getLogger(__name__)


APPROVED_RESPONSE_TEMPLATES = {
    # -------------------------
    # Upsell templates
    # -------------------------
    "upsell_acceptance_schedule_new": (
        "Perfect, I'll have someone reach out to get that scheduled for you! "
        "Have a great day, {first_name}!"
    ),
    "upsell_acceptance_existing_appointment": (
        "Perfect, I'll get that added to your next service, {first_name}. "
        "Let me know if you have any other questions."
    ),
    "upsell_details_or_price_quote": (
        "I'll have someone reach out and break the details down for you and give you a custom quote. "
        "Thanks {first_name}, have a great day!"
    ),
    "upsell_details_or_price_schedule": (
        "I'll have someone reach out to break the details down for you and get that scheduled! "
        "Have a great day, {first_name}!"
    ),
    "upsell_already_included": "Let me check into that for you!",
    "upsell_decline": "No worries {first_name}, have a great {day_of_week}!",
    # -------------------------
    # After-service templates
    # -------------------------

    "after_service_positive_review_request": (
        "That's great to hear {first_name}! If you have a minute, would you mind sharing your experience "
        "in a quick review? It would really help our team!\n\n{review_link}"
    ),
    "after_service_review_agreed": (
        "Thanks {first_name}! Have a great {day_of_week}!"
    ),
    "after_service_review_declined": (
        "No worries {first_name}, have a great {day_of_week}!"
    ),
    "after_service_still_seeing_bugs_under_7_days": (
        "Thanks for the update, {first_name}. It's normal to still see some activity right after treatment. "
        "Give it about 10 days to fully take effect, and if you're still seeing activity after that, "
        "just let us know and we'll take care of it."
    ),
    # -------------------------
    # Billing/account templates
    # -------------------------
    "billing_login_help": (
        "Your account number is {account_number}, but if you forgot your password you should be able to "
        "reset that with the phone number we have on file. If that's not working you can call "
        "{company_phone} and we would love to help you out!"
    ),
    "billing_account_number": (
        "Your account number is {account_number}, let me know if you need any other help!"
    ),
    "billing_password_reset": (
        "You should be able to reset your password with the phone number we have on file, but if that's "
        "not working you can call {company_phone} and we would love to help you out!"
    ),
    "billing_why_autopay": (
        "No worries, this would only be if you didn't want to make payment manually, {first_name}. "
        "Have a great {day_of_week}!"
    ),
    "billing_why_expiring_card": (
        "No worries, this is just to help make sure there's no interruption in your service once the "
        "card expires, {first_name}. Have a great {day_of_week}!"
    ),
    "billing_customer_declines": ("No worries {first_name}! Have a great {day_of_week}!"),
    "billing_customer_will_do_it": ("Thanks {first_name}!"),
    "billing_no_card_yet": ("No worries {first_name}! Have a great {day_of_week}!"),
    # -------------------------
    # Billing overdue / AR templates
    # -------------------------
    "billing_ar_customer_will_pay": ("Thanks {first_name}!"),
    "billing_overdue_declines": ("No worries {first_name}! Have a great {day_of_week}!"),
    "billing_overdue_provides_times": (
        "Perfect, I'll get someone to schedule this for you, {first_name}! "
        "Have a great {day_of_week}!"
    ),
}


def _is_stale_ai_run(*, state: AgentState, tool_name: str) -> bool:
    company_id = state.get("company_id")
    customer_id = state.get("customer_id")
    message_id = state.get("message_id")

    if not company_id or not customer_id or not message_id:
        logger.warning(
            "Cannot run stale AI check before tool=%s because company_id/customer_id/message_id is missing. "
            "company_id=%s customer_id=%s message_id=%s",
            tool_name,
            company_id,
            customer_id,
            message_id,
        )
        return False

    is_fresh = is_still_latest_inbound(
        company_id=int(company_id),
        customer_id=str(customer_id),
        message_id=int(message_id),
    )

    if is_fresh:
        return False

    logger.info(
        "Skipping stale AI side-effect tool. tool=%s processed_message_id=%s company_id=%s customer_id=%s",
        tool_name,
        message_id,
        company_id,
        customer_id,
    )

    return True


def _get_template_variables(template: str) -> List[str]:
    formatter = string.Formatter()
    return [field_name for _, field_name, _, _ in formatter.parse(template) if field_name]


def _get_missing_template_variables(
    *,
    template: str,
    values: Dict[str, Any],
) -> List[str]:
    required_variables = _get_template_variables(template)

    missing_variables = []

    for variable in required_variables:
        value = values.get(variable)

        if value is None:
            missing_variables.append(variable)
            continue

        if isinstance(value, str) and not value.strip():
            missing_variables.append(variable)
            continue

    return missing_variables


def _safe_get_nested(data: Dict[str, Any], *keys: str) -> Any:
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current


def _build_template_values(
    *,
    state: AgentState,
    account_info: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    account_info = account_info or {}

    google_review_link = state.get("google_review_link") or ""

    phone_number = state.get("company_phone_number") or ""

    return {
        "first_name": state.get("customer_first_name") or "",
        "day_of_week": get_current_day(),
        # Preferred new names
        "google_review_link": google_review_link,
        "company_phone_number": phone_number,
        # Backward-compatible template aliases
        "review_link": google_review_link,
        "company_phone": phone_number,
        "account_number": (
            account_info.get("account_number")
            or account_info.get("accountNumber")
            or _safe_get_nested(account_info, "customer", "account_number")
            or ""
        ),
    }


def _format_template(
    *,
    template_key: str,
    state: AgentState,
    account_info: Dict[str, Any] | None = None,
) -> tuple[str | None, List[str]]:
    template = APPROVED_RESPONSE_TEMPLATES.get(template_key)

    if not template:
        logger.warning("Unknown template_key selected: %s", template_key)
        return None, []

    values = _build_template_values(
        state=state,
        account_info=account_info,
    )

    missing_variables = _get_missing_template_variables(
        template=template,
        values=values,
    )

    if missing_variables:
        logger.warning(
            "Missing required template variables %s for template_key %s",
            missing_variables,
            template_key,
        )
        return None, missing_variables

    try:
        return template.format(**values), []
    except KeyError as exc:
        logger.exception(
            "Missing template variable %s for template_key %s",
            exc,
            template_key,
        )
        return None, [str(exc)]


def _is_forwarded_complaint(
    scenario_result: Dict[str, Any],
) -> bool:
    scenario_output = scenario_result.get("scenario_output", {}) or {}
    parameters = scenario_output.get("parameters", {}) or {}

    return (
        scenario_output.get("action") == "forward_message_to_company"
        and parameters.get("query_type") == "complaint"
    )


SERVICE_OPT_IN_SCENARIO_IDS = {
    "upsell_positive_interest_with_question",
    "upsell_acceptance_schedule_new",
    "upsell_acceptance_existing_appointment",
    "upsell_details_or_price_quote"
}

UPSELL_SERVICE_DISPLAY_NAMES = {
    "mosquito": "Mosquito treatment",
    "tick": "Tick treatment",
    "flea": "Flea treatment",
    "rodent": "Rodent control",
    "rodent_exclusion": "Rodent exclusion inspection",
    "rodent_protection_boxes": "Rodent protection boxes",
    "termite": "Termite inspection",
    "moisture": "Moisture inspection",
    "weed_prevention": "Weed prevention treatment",
    "weed_control": "Weed control treatment",
    "wildlife": "Wildlife inspection",
    "synthetic_turf": "Synthetic turf",
    "outdoor_lighting": "Outdoor lighting",
    "fertilizer": "Fertilizer treatment",
    "grub": "Grub treatment",
    "pigeon_control": "Pigeon control",
    "none": "Upsell service",
}


def _get_upsell_display_name(
    *,
    scenario_result: Dict[str, Any],
) -> str:
    upsell_service_name = scenario_result.get("upsell_service_name", ["none"])

    if isinstance(upsell_service_name, str):
        upsell_service_name = [upsell_service_name]

    if not isinstance(upsell_service_name, list):
        upsell_service_name = ["none"]

    display_names = [
        UPSELL_SERVICE_DISPLAY_NAMES.get(service_name, "Upsell service")
        for service_name in upsell_service_name
        if service_name and service_name != "none"
    ]

    if not display_names:
        return "Upsell service"

    if len(display_names) == 1:
        return display_names[0]

    return ", ".join(display_names[:-1]) + " and " + display_names[-1]


def _record_customer_service_opt_in(
    *,
    state: AgentState,
    scenario_result: Dict[str, Any],
) -> None:
    if _is_stale_ai_run(state=state, tool_name="record_customer_service_opt_in"):
        return

    selected_scenario_id = scenario_result.get("selected_scenario_id")

    company_id = state.get("company_id")
    customer_id = state.get("customer_id")

    if not company_id or not customer_id:
        logger.warning(
            "Skipping service opt-in DB update because company_id or customer_id is missing. "
            "company_id=%s customer_id=%s scenario_id=%s",
            company_id,
            customer_id,
            selected_scenario_id,
        )
        return

    if selected_scenario_id == "upsell_acceptance_existing_appointment":
        event_type = "add_on_added"
        lead_type = "add-on"
    else:
        event_type = "lead_attained"
        lead_type = "lead"

    add_on_name = _get_upsell_display_name(
        scenario_result=scenario_result,
    )

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Dollar value of the upsell this customer was actually offered: the
            # potential_revenue of the iteration on their most recent outbound
            # upsell_2d message. Mirrors how the manual "Record Upsell" flow resolves
            # the amount (relies on messages.iteration_id, added 2026-05-14).
            cursor.execute(
                """
                SELECT tmi.potential_revenue
                FROM messages m
                JOIN trigger_message_iterations tmi ON tmi.id = m.iteration_id
                WHERE m.company_id = %(company_id)s
                  AND m.customer_id = %(customer_id)s
                  AND m.trigger_key = 'upsell_2d'
                  AND m.direction = 'outbound'
                  AND m.iteration_id IS NOT NULL
                ORDER BY COALESCE(m.sent_at, m.created_at) DESC
                LIMIT 1
                """,
                {"company_id": int(company_id), "customer_id": str(customer_id)},
            )
            revenue_row = cursor.fetchone()
            projected_revenue = revenue_row[0] if revenue_row else None

            cursor.execute(
                """
                INSERT INTO recent_activity_events (
                    company_id,
                    event_type,
                    customer_id,
                    lead_type,
                    add_on_name,
                    projected_annual_revenue,
                    event_date,
                    created_at
                )
                VALUES (
                    %(company_id)s,
                    %(event_type)s,
                    %(customer_id)s,
                    %(lead_type)s,
                    %(add_on_name)s,
                    %(projected_revenue)s,
                    CURRENT_DATE,
                    NOW()
                )
                """,
                {
                    "company_id": int(company_id),
                    "event_type": event_type,
                    "customer_id": str(customer_id),
                    "lead_type": lead_type,
                    "add_on_name": add_on_name,
                    "projected_revenue": projected_revenue,
                },
            )
            conn.commit()


def _call_handle_additional_support(
    *,
    state: AgentState,
    scenario_result: Dict[str, Any],
) -> Dict[str, Any]:

    if _is_stale_ai_run(state=state, tool_name="handle_additional_support"):
        return {
            "tool_name": "handle_additional_support",
            "selected_scenario_id": scenario_result.get("selected_scenario_id"),
            "skipped": True,
            "reason": "stale_ai_run_newer_inbound_exists",
        }
    scenario_output = scenario_result.get("scenario_output", {}) or {}
    parameters = scenario_output.get("parameters", {}) or {}

    tool_args = {
        "issue": (
            parameters.get("issue") or "Customer message requires internal representative review."
        ),
        "reason": (
            parameters.get("reason")
            or scenario_result.get("reason")
            or "A selected scenario requires internal representative review."
        ),
        "state": state,
    }

    result = handle_additional_support.invoke(tool_args)

    return {
        "tool_name": "handle_additional_support",
        "domain": scenario_result.get("domain"),
        "sub_bucket": scenario_result.get("sub_bucket"),
        "selected_scenario_id": scenario_result.get("selected_scenario_id"),
        "args": tool_args,
        "result": result,
    }


def _call_forward_message_to_company(
    *,
    state: AgentState,
    scenario_result: Dict[str, Any],
) -> Dict[str, Any]:
    if _is_stale_ai_run(state=state, tool_name="forward_message_to_company"):
        return {
            "tool_name": "forward_message_to_company",
            "selected_scenario_id": scenario_result.get("selected_scenario_id"),
            "skipped": True,
            "reason": "stale_ai_run_newer_inbound_exists",
        }
    scenario_output = scenario_result.get("scenario_output", {}) or {}
    parameters = scenario_output.get("parameters", {}) or {}

    sub_bucket = scenario_result.get("sub_bucket") or "unknown"

    notes_template = parameters.get("notes")
    upsell_display_name = _get_upsell_display_name(
        scenario_result=scenario_result,
    )

    notes = (
        notes_template.format(
            upsell_service_name=upsell_display_name.lower(),
        )
        if notes_template
        else None
    )

    tool_args = {
        "query_type": parameters.get("query_type"),
        "notes": notes,
        "context": state.get("customer_message"),
        "state": state,
    }

    result = forward_message_to_company.invoke(tool_args)

    return {
        "tool_name": "forward_message_to_company",
        "domain": scenario_result.get("domain"),
        "sub_bucket": sub_bucket,
        "selected_scenario_id": scenario_result.get("selected_scenario_id"),
        "args": tool_args,
        "result": result,
    }


def _call_get_customer_account_info(
    *,
    state: AgentState,
    scenario_result: Dict[str, Any],
    ) -> Dict[str, Any]:
    tool_args = {
        "state": state,
    }

    result = get_customer_account_info.invoke(tool_args)

    return {
        "tool_name": "get_customer_account_info",
        "domain": scenario_result.get("domain"),
        "sub_bucket": scenario_result.get("sub_bucket"),
        "selected_scenario_id": scenario_result.get("selected_scenario_id"),
        "args": tool_args,
        "result": result,
    }


def deterministic_executor_node(
    *,
    registry: BucketRegistry,
    state: AgentState,
) -> Dict[str, Any]:
    """
    Final deterministic execution layer.

    This function consumes:
    state["execution_plan"]["scenario_results"]

    It executes required tools, applies stop rules, formats the final approved
    templates, and returns the final response fields.

    Supports multiple scenario_results producing multiple templates.
    """

    execution_plan = state.get("execution_plan", {}) or {}
    scenario_results = execution_plan.get("scenario_results", [])

    if not isinstance(scenario_results, list):
        scenario_results = []

    tool_results: List[Dict[str, Any]] = []
    complaint_forward_result = next(
        (item for item in scenario_results if _is_forwarded_complaint(item)),
        None,
    )

    if complaint_forward_result:
        try:
            tool_results.append(
                _call_forward_message_to_company(
                    state=state,
                    scenario_result=complaint_forward_result,
                )
            )
        except Exception as exc:
            logger.exception("forward_message_to_company execution failed for complaint.")
            tool_results.append(
                {
                    "tool_name": "forward_message_to_company",
                    "domain": complaint_forward_result.get("domain"),
                    "sub_bucket": complaint_forward_result.get("sub_bucket"),
                    "selected_scenario_id": complaint_forward_result.get("selected_scenario_id"),
                    "result": {
                        "error": str(exc),
                    },
                }
            )

        return {
            "tool_results": tool_results,
            "answer": None,
            "should_send_message": False,
            "response_status": "human_attention_required",
            "selected_template_key": None,
            "selected_template_keys": [],
            "execution_stopped": True,
            "stop_reason": (
                "Complaint forward selected; skipped all customer-facing templates "
                "and all other actions."
            ),
        }

    handle_support_result = next(
        (
            item
            for item in scenario_results
            if (item.get("scenario_output", {}) or {}).get("action") == "handle_additional_support"
        ),
        None,
    )

    if handle_support_result:
        try:
            tool_result = _call_handle_additional_support(
                state=state,
                scenario_result=handle_support_result,
            )
            tool_results.append(tool_result)
        except Exception as exc:
            logger.exception("handle_additional_support execution failed.")
            tool_results.append(
                {
                    "tool_name": "handle_additional_support",
                    "domain": handle_support_result.get("domain"),
                    "sub_bucket": handle_support_result.get("sub_bucket"),
                    "result": {
                        "error": str(exc),
                    },
                }
            )

        return {
            "tool_results": tool_results,
            "answer": None,
            "should_send_message": False,
            "response_status": "human_attention_required",
            "selected_template_key": None,
            "selected_template_keys": [],
            "execution_stopped": True,
            "stop_reason": "handle_additional_support selected; skipped all other actions.",
        }

    account_info: Dict[str, Any] | None = None

    for scenario_result in scenario_results:
        scenario_output = scenario_result.get("scenario_output", {}) or {}
        action = scenario_output.get("action")

        if action == "billing_info":
            try:
                tool_result = _call_get_customer_account_info(
                    state=state,
                    scenario_result=scenario_result,
                )
                tool_results.append(tool_result)

                if isinstance(tool_result.get("result"), dict):
                    account_info = tool_result["result"]

            except Exception as exc:
                logger.exception("get_customer_account_info execution failed.")
                tool_results.append(
                    {
                        "tool_name": "get_customer_account_info",
                        "domain": scenario_result.get("domain"),
                        "sub_bucket": scenario_result.get("sub_bucket"),
                        "result": {
                            "error": str(exc),
                        },
                    }
                )

    for scenario_result in scenario_results:
        scenario_output = scenario_result.get("scenario_output", {}) or {}
        action = scenario_output.get("action")

        if action == "forward_message_to_company":
            try:
                tool_results.append(
                    _call_forward_message_to_company(
                        state=state,
                        scenario_result=scenario_result,
                    )
                )
            except Exception as exc:
                logger.exception("forward_message_to_company execution failed.")
                tool_results.append(
                    {
                        "tool_name": "forward_message_to_company",
                        "domain": scenario_result.get("domain"),
                        "sub_bucket": scenario_result.get("sub_bucket"),
                        "result": {
                            "error": str(exc),
                        },
                    }
                )

    selected_template_keys: List[str] = []

    for scenario_result in scenario_results:
        scenario_output = scenario_result.get("scenario_output", {}) or {}
        template_key = scenario_output.get("template_key")

        if template_key and template_key not in selected_template_keys:
            selected_template_keys.append(template_key)

    if not selected_template_keys:
        return {
            "tool_results": tool_results,
            "answer": None,
            "should_send_message": False,
            "response_status": "no_response",
            "selected_template_key": None,
            "selected_template_keys": [],
            "execution_stopped": False,
        }

    formatted_answers: List[str] = []
    failed_template_keys: List[str] = []
    missing_template_variables: Dict[str, List[str]] = {}

    for template_key in selected_template_keys:
        formatted_answer, missing_variables = _format_template(
            template_key=template_key,
            state=state,
            account_info=account_info,
        )

        if formatted_answer:
            formatted_answers.append(formatted_answer)
        else:
            failed_template_keys.append(template_key)
            missing_template_variables[template_key] = missing_variables

    if failed_template_keys:
        missing_variables_result = {
            "domain": "template_execution",
            "sub_bucket": "missing_template_variables",
            "selected_scenario_id": "missing_template_variables",
            "reason": "A selected customer-facing template could not be safely sent because required variables were missing.",
            "scenario_output": {
                "action": "handle_additional_support",
                "template_key": None,
                "parameters": {
                    "issue": "Customer-facing template could not be sent because required variables were missing.",
                    "reason": (
                        "Missing template variables detected before sending customer response: "
                        f"{missing_template_variables}"
                    ),
                },
            },
        }

        try:
            tool_results.append(
                _call_handle_additional_support(
                    state=state,
                    scenario_result=missing_variables_result,
                )
            )
        except Exception as exc:
            logger.exception(
                "handle_additional_support execution failed for missing template variables."
            )
            tool_results.append(
                {
                    "tool_name": "handle_additional_support",
                    "domain": "template_execution",
                    "sub_bucket": "missing_template_variables",
                    "result": {"error": str(exc)},
                }
            )

        return {
            "tool_results": tool_results,
            "answer": None,
            "should_send_message": False,
            "response_status": "human_attention_required",
            "selected_template_key": selected_template_keys[0],
            "selected_template_keys": selected_template_keys,
            "execution_stopped": True,
            "stop_reason": (
                "One or more templates were blocked because required variables were missing: "
                + str(missing_template_variables)
            ),
        }

    for scenario_result in scenario_results:
        selected_scenario_id = scenario_result.get("selected_scenario_id")

        if selected_scenario_id in SERVICE_OPT_IN_SCENARIO_IDS:
            try:
                _record_customer_service_opt_in(
                    state=state,
                    scenario_result=scenario_result,
                )
            except Exception:
                logger.exception("Failed to record customer service opt-in.")

    answer = "\n-----\n".join(formatted_answers)

    return {
        "tool_results": tool_results,
        "answer": answer,
        "should_send_message": True,
        "response_status": "ready_to_send",
        "selected_template_key": selected_template_keys[0],
        "selected_template_keys": selected_template_keys,
        "execution_stopped": False,
    }

from ai.run_ai_workflow import ai_workflow_with_meta

def prepare_ai_input(
    context: dict,
    messages: list[dict],
) -> dict:

    customer_messages = [
        message
        for message in messages
        if message.get("sender") == "customer"
    ]

    if not customer_messages:
        raise ValueError("No customer message found in conversation")

    latest_customer_message = customer_messages[-1]

    customer_name = context.get("customer_name") or ""

    customer_first_name = (
        customer_name.split()[0]
        if customer_name
        else ""
    )

    return {
        "conversation_id": context["conversation_id"],

        "customer_id": context["customer_id"],
        "customer_name": customer_name,
        "customer_first_name": customer_first_name,
        "customer_phone": context.get("customer_phone"),
        "account_number": context.get("account_number"),

        "company_id": context["company_id"],
        "company_name": context.get("company_name"),
        "company_phone": context.get("company_phone_number"),
        "google_review_link": context.get("google_review_link"),
        "crm": context.get("crm"),

        "body": latest_customer_message["body"],
        "message_id": latest_customer_message["id"],

        "conversation_history": messages,
    }

def run_ai(ai_input: dict) -> dict:
    result = ai_workflow_with_meta(
        customer_id=ai_input["customer_id"],
        company_id=ai_input["company_id"],
        body=ai_input["body"],
        message_id=ai_input["message_id"],
        playground_context=ai_input,
    )

    return result
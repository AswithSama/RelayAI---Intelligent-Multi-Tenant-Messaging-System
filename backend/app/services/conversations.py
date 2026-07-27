from app.database.connection import execute_query

def get_conversations_by_customer(
    customer_id: int,
) -> list[dict]:
    query = """
        SELECT
            id,
            customer_id,
            created_at,
            updated_at
        FROM conversations
        WHERE customer_id = %(customer_id)s
        ORDER BY updated_at DESC, id DESC
    """

    parameters = {
        "customer_id": customer_id,
    }

    return execute_query(query, parameters)

def get_conversation_context(
    conversation_id: int,
) -> dict | None:

    query = """
        SELECT
            conversations.id AS conversation_id,

            customers.id AS customer_id,
            customers.name AS customer_name,
            customers.phone AS customer_phone,
            customers.account_number,
            customers.queue_status,
            customers.review_reason,

            companies.id AS company_id,
            companies.name AS company_name,
            companies.phone_number AS company_phone_number,
            companies.google_review_link,
            companies.crm

        FROM conversations

        JOIN customers
            ON conversations.customer_id = customers.id

        JOIN companies
            ON customers.company_id = companies.id

        WHERE conversations.id = %(conversation_id)s
    """

    parameters = {
        "conversation_id": conversation_id,
    }

    rows = execute_query(query, parameters)

    if not rows:
        return None

    return rows[0]
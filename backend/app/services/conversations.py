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
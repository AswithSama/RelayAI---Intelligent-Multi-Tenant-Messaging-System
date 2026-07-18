from app.database.connection import execute_query


def get_customers_by_company(
    company_id: int,
    queue_status: str | None = None,
) -> list[dict]:
    query = """
        SELECT
            id,
            company_id,
            name,
            phone,
            queue_status,
            last_message,
            review_reason,
            created_at,
            updated_at
        FROM customers
        WHERE company_id = %(company_id)s
    """

    parameters = {
        "company_id": company_id,
    }

    if queue_status is not None:
        query += """
            AND queue_status = %(queue_status)s
        """
        parameters["queue_status"] = queue_status

    query += """
        ORDER BY updated_at DESC
    """

    return execute_query(query, parameters)
from app.database.connection import execute_query, execute_write
from fastapi import HTTPException

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

def mark_completed(customer_id: int) -> dict:
    query = """
        UPDATE customers
        SET
            queue_status = 'completed',
            review_reason = NULL,
            updated_at = NOW()
        WHERE id = %(customer_id)s
        RETURNING
            id,
            company_id,
            name,
            phone,
            queue_status,
            last_message,
            review_reason,
            created_at,
            updated_at;
    """

    result = execute_write(
        query,
        {
            "customer_id": customer_id,
        },
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    return result
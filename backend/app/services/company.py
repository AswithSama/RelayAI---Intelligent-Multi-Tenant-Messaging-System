from app.database.connection import execute_query


def get_all_companies() -> list[dict]:
    return execute_query(
        """
        SELECT
            id,
            name,
            created_at,
            updated_at
        FROM companies
        ORDER BY name
        """
    )
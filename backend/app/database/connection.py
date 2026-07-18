from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from app.core.config import settings


@contextmanager
def get_db_connection() -> Generator[Connection, None, None]:
    connection = psycopg.connect(
        settings.database_url,
        row_factory=dict_row,
    )

    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def execute_query(
    query: str,
    parameters: dict | None = None,
) -> list[dict]:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters or {})

            if cursor.description is None:
                connection.commit()
                return []

            rows = cursor.fetchall()
            return list(rows)
        
def execute_write(
    query: str,
    parameters: dict | None = None,
) -> dict | None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters or {})

            row = cursor.fetchone() if cursor.description is not None else None

            connection.commit()

            return row
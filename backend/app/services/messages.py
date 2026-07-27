from app.database.connection import execute_query, execute_write


def get_messages_by_conversation(
    conversation_id: int,
) -> list[dict]:
    query = """
        SELECT
            id,
            conversation_id,
            sender,
            body,
            created_at
        FROM messages
        WHERE conversation_id = %(conversation_id)s
        ORDER BY created_at ASC, id ASC
    """

    parameters = {
        "conversation_id": conversation_id,
    }

    return execute_query(query, parameters)


def create_message(
    conversation_id: int,
    sender: str,
    body: str,
) -> dict | None:
    query = """
        INSERT INTO messages (
            conversation_id,
            sender,
            body
        )
        VALUES (
            %(conversation_id)s,
            %(sender)s,
            %(body)s
        )
        RETURNING
            id,
            conversation_id,
            sender,
            body,
            created_at
    """

    parameters = {
        "conversation_id": conversation_id,
        "sender": sender,
        "body": body,
    }

    return execute_write(query, parameters)


def create_ai_message(
    conversation_id: int,
    body: str,
) -> dict:
    query = """
        INSERT INTO messages (
            conversation_id,
            sender,
            body
        )
        VALUES (
            %(conversation_id)s,
            'ai',
            %(body)s
        )
        RETURNING
            id,
            conversation_id,
            sender,
            body,
            created_at
    """

    parameters = {
        "conversation_id": conversation_id,
        "body": body,
    }

    return execute_write(query,parameters,)


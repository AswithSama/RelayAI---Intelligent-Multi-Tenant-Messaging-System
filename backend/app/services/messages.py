from app.database.connection import execute_query, execute_write


def get_messages_by_conversation(conversation_id: int) -> list[dict]:
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

## merge create_message and create_ai_message into 1

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


def delete_messages_by_conversation(
    conversation_id: int,
) -> bool:
    delete_pending_run_query = """
        DELETE FROM ai_pending_runs
        WHERE conversation_id = %(conversation_id)s
    """

    delete_messages_query = """
        DELETE FROM messages
        WHERE conversation_id = %(conversation_id)s
    """

    parameters = {
        "conversation_id": conversation_id,
    }

    execute_query(delete_pending_run_query, parameters)
    execute_query(delete_messages_query, parameters)

    return True
# ai/shared/clean_message_history.py

from typing import Dict, List

from langchain_core.messages import AIMessage, HumanMessage


def build_classifier_history(messages, limit: int = 10) -> List[Dict[str, str]]:
    """
    Build a clean conversation-history payload for classifier agents.

    Keeps only user/assistant content and removes tool messages,
    metadata, empty messages, and internal objects.
    """

    clean_messages = []

    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("role")
            content = msg.get("content", "")

            if role in {"user", "assistant", "human", "ai"} and content:
                clean_messages.append(
                    {
                        "role": "user" if role in {"user", "human"} else "assistant",
                        "content": content.strip(),
                    }
                )

        elif isinstance(msg, HumanMessage):
            if msg.content:
                clean_messages.append(
                    {
                        "role": "user",
                        "content": msg.content.strip(),
                    }
                )

        elif isinstance(msg, AIMessage):
            if msg.content and not getattr(msg, "tool_calls", None):
                clean_messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content.strip(),
                    }
                )

    return clean_messages[-limit:]

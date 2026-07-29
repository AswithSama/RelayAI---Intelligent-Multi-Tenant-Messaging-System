# ai/agent/graph_nodes.py

from typing import Any, Dict, List
from langchain_core.messages import AIMessage, HumanMessage
from ai.agent.state import AgentState

def load_conversation_history_node(state: AgentState):

    playground_context = state.get("playground_context")
    raw_history = playground_context.get("conversation_history",[])

    current_message_id = playground_context.get("message_id")
    conversation_history = []

    for message in raw_history:
        # Skip the current customer message since it's passed separately.
        if (message.get("id") == current_message_id and message.get("sender") == "customer"):
            continue

        sender = message.get("sender")
        body = message.get("body", "")
        if sender == "customer": 
            conversation_history.append(HumanMessage(content=body)) 
        else: 
            conversation_history.append(AIMessage(content=body))

    return {
        "conversation_history": conversation_history,
        "customer_first_name": playground_context.get("customer_first_name", ""),
        "google_review_link": playground_context.get("google_review_link", ""),
        "company_phone_number": playground_context.get("company_phone", ""),
    }
            
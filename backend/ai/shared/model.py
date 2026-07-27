# ai/shared/model.py

from langchain_openai import ChatOpenAI
from app.core.config import settings

# `timeout` caps a single OpenAI call so a hung request can't pin a worker (and,
# before the queue migration, a held DB connection) indefinitely. `max_retries`
# lets the SDK ride out transient 429/5xx within one workflow run; the Cloud Tasks
# `ai-inbound-replies` queue retries the whole message on top of that.
plain_llm = ChatOpenAI(
    model="gpt-5-mini",
    api_key=settings.openai_api_key,
    temperature=0,
    timeout=30,
    max_retries=2,
    model_kwargs={
        "reasoning": {
            "effort": "medium"
        }
    },
)

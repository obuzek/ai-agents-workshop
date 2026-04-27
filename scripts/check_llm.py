"""Quick check that your LLM provider is configured and reachable."""

from app.llm import get_chat_model

llm = get_chat_model()
reply = llm.invoke("Say hello in exactly three words.")
print(reply.content)

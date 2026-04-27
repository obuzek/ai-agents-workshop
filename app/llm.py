"""
Provider-swappable LLM factory for the workshop.

All labs call get_chat_model() instead of importing a provider-specific class
directly. Switching providers is a one-line .env change:

    LLM_PROVIDER=gemini   # default — free tier, no credit card
    LLM_PROVIDER=openai
    LLM_PROVIDER=anthropic

Each provider reads its own API key from the environment automatically
(GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY). Set LLM_MODEL to
override the default model for any provider.
"""

import logging
import os
import sys

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

load_dotenv()

_DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash-lite",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
}


def check_llm_config():
    """Verify the LLM provider package is installed. Call at agent startup."""
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    try:
        get_chat_model()
    except ImportError:
        logger.error(
            "LLM_PROVIDER='%s' but the required package is not installed.\n"
            "  Run:  uv sync --all-extras",
            provider,
        )
        sys.exit(1)


def get_chat_model(**kwargs) -> BaseChatModel:
    """Return a LangChain chat model for the configured provider.

    Keyword arguments are forwarded to the underlying chat model constructor
    (e.g. max_retries=3).
    """
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    model = os.environ.get("LLM_MODEL", "") or _DEFAULT_MODELS.get(provider)

    if model is None:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. "
            f"Supported: {', '.join(_DEFAULT_MODELS)}"
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, **kwargs)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, **kwargs)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, **kwargs)

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. "
        f"Supported: {', '.join(_DEFAULT_MODELS)}"
    )

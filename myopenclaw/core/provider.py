import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel


load_dotenv()

COMPATIBLE_BASE_URLS = {
    "openai": None,
    "other": None,
}


def get_provider(
    provider_name: str = "openai",
    model_name: str = "gpt-4o-mini",
    temperature: float = 0.0,
    base_url: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    provider_name = provider_name.lower()

    if provider_name in ["openai", "other"]:
        from langchain_openai import ChatOpenAI

        current_api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not current_api_key:
            raise ValueError("Missing OPENAI_API_KEY.")

        final_base_url = base_url or os.environ.get("OPENAI_API_BASE")
        if not final_base_url:
            final_base_url = COMPATIBLE_BASE_URLS.get(provider_name)

        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=current_api_key,
            base_url=final_base_url,
            **kwargs,
        )

    if provider_name == "anthropic":
        from langchain_anthropic import ChatAnthropic

        current_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not current_api_key:
            raise ValueError("Missing ANTHROPIC_API_KEY.")

        final_base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")
        return ChatAnthropic(
            model_name=model_name,
            temperature=temperature,
            api_key=current_api_key,
            base_url=final_base_url,
            **kwargs,
        )

    if provider_name == "ollama":
        from langchain_community.chat_models import ChatOllama

        final_base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=final_base_url,
            **kwargs,
        )

    raise ValueError(f"Unsupported provider: {provider_name}")

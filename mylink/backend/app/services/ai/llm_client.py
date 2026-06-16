from typing import Optional
from langchain_openai import ChatOpenAI
from app.config import settings


def get_llm(model: Optional[str] = None, temperature: float = 0.2) -> ChatOpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return ChatOpenAI(
        model=model or settings.OPENAI_MODEL,
        temperature=temperature,
        timeout=60,
        max_retries=2,
        api_key=settings.OPENAI_API_KEY,
    )

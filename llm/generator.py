"""Abstract LLM connector hierarchy and QazCode Hub implementation.

``BaseLLMConnector`` defines the interface; ``QazCodeHubConnector`` wraps the
AsyncOpenAI client pointed at hub.qazcode.ai (or any OpenAI-compatible endpoint).
"""

import logging
from abc import ABC, abstractmethod

from openai import AsyncOpenAI

from backend import config
from llm.retriever import ChunkResult

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Ты — эксперт-диагност. Твоя задача — проанализировать симптомы и найти \
соответствия в предоставленных выдержках из клинических протоколов Казахстана. \
Ответ давай строго в формате JSON.

Формат ответа (валидный JSON, без дополнительного текста):
{
  "diagnoses": [
    {
      "rank": 1,
      "diagnosis": "Точное название диагноза",
      "icd10_code": "X00.0",
      "explanation": "Краткое обоснование: какие симптомы соответствуют протоколу"
    }
  ]
}

Требования:
- Ранжируй диагнозы по убыванию клинической вероятности (rank 1 — наиболее вероятный).
- Включай только диагнозы, прямо подкреплённые выдержками из протоколов.
- Коды МКБ-10 бери только из текста протоколов, не выдумывай.
- Если в выдержках нет достаточных данных — верни пустой список diagnoses: [].
- Не добавляй markdown, комментарии или текст вне JSON-объекта.\
"""


# ── Helper ────────────────────────────────────────────────────────────────────

def _build_context(chunks: list[ChunkResult]) -> str:
    """Format retrieved chunks into a readable block for the user prompt."""
    parts = [
        f"[Протокол: {chunk.protocol_id} | чанк #{chunk.chunk_index}]\n{chunk.text}"
        for chunk in chunks
    ]
    return "\n\n---\n\n".join(parts)


def build_messages(symptoms: str, chunks: list[ChunkResult]) -> list[dict]:
    """Build the messages list for the LLM chat completion call."""
    if chunks:
        context_block = _build_context(chunks)
        user_content = (
            f"Симптомы пациента:\n{symptoms}\n\n"
            f"Выдержки из клинических протоколов:\n{context_block}"
        )
    else:
        user_content = (
            f"Симптомы пациента:\n{symptoms}\n\n"
            "Выдержки из клинических протоколов: не найдены."
        )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


# ── Abstract base ─────────────────────────────────────────────────────────────

class BaseLLMConnector(ABC):
    """Interface for LLM backends used by RAGService."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        """Send *messages* to the LLM and return the raw text response."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release underlying HTTP / connection resources."""
        ...


# ── QazCode Hub implementation ────────────────────────────────────────────────

class QazCodeHubConnector(BaseLLMConnector):
    """AsyncOpenAI-backed connector for the QazCode Hub (or any compatible endpoint)."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=config.LLM_BASE_URL,
            api_key=config.LLM_API_KEY,
        )

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        effective_model = model or config.LLM_MODEL
        logger.debug("LLM request: model=%s, messages=%d", effective_model, len(messages))

        response = await self._client.chat.completions.create(
            model=effective_model,
            temperature=temperature,
            messages=messages,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        logger.debug("LLM response (first 200 chars): %s", raw[:200])
        return raw

    async def close(self) -> None:
        await self._client.close()

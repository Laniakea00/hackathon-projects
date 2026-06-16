"""Abstract LLM connector hierarchy and QazCode Hub implementation.

``BaseLLMConnector`` defines the interface; ``QazCodeHubConnector`` wraps the
AsyncOpenAI client pointed at hub.qazcode.ai (or any OpenAI-compatible endpoint).
"""

import json
import logging
from abc import ABC, abstractmethod

from openai import AsyncOpenAI

from backend import config
from llm.retriever import ChunkResult

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Ты — система поддержки принятия врачебных решений. \
Используй предоставленные протоколы как клинический справочник.

Формат ответа (строго валидный JSON, без дополнительного текста):
{
  "diagnoses": [
    {
      "rank": 1,
      "diagnosis": "Точное название диагноза",
      "icd10_code": "X00.0",
      "explanation": "Краткое клиническое обоснование: какие симптомы соответствуют протоколу"
    }
  ]
}

Требования:
- Проанализируй симптомы пациента, опираясь на протоколы. Не просто копируй из списка, а сопоставь клиническую картину.
- Ранжируй три диагноза по убыванию клинической вероятности (rank 1 — наиболее вероятный).
- Коды МКБ-10 бери ТОЧНО из заголовка протокола (поле МКБ). Используй полный код с точкой и подклассом: \
если в протоколе написано "A39.0", выводи "A39.0", а не "A39". НИКОГДА не обрезай подкод — "N41" недопустим, нужно "N41.1" или "N41.9".
- Если в одном протоколе перечислено несколько кодов (например, "N41.0, N41.1, N41.9"), \
используй наиболее специфичный подкод ТОЛЬКО если симптоматика пациента ЯВНО соответствует именно ему. \
При типичной или неоднозначной клинической картине — используй подкод ".9" (неуточнённый).
- icd10_code ОБЯЗАТЕЛЬНО должен соответствовать формату "X00.0" или "X00" — никаких тире, вопросительных знаков или прочерков.
- Не добавляй markdown, комментарии или текст вне JSON-объекта.\
"""

_REWRITE_SYSTEM = """\
Ты — медицинский аналитик. Извлеки из жалобы пациента только клинические сущности: \
симптомы, их характеристики, возраст, пол, длительность. \
Убери приветствия, эмоции и нерелевантный текст. \
ВАЖНО: пиши clinical_query строго на русском языке, медицинской терминологией. \
Верни JSON: {"clinical_query": "симптом1, симптом2, длительность, ..."}\
"""


# ── Query rewrite ─────────────────────────────────────────────────────────────

async def rewrite_query(symptoms: str, connector: "BaseLLMConnector") -> str:
    """Extract clinical entities from a raw patient complaint.

    Returns the rewritten query, or the original *symptoms* on any failure.
    """
    messages = [
        {"role": "system", "content": _REWRITE_SYSTEM},
        {"role": "user", "content": symptoms},
    ]
    try:
        raw = await connector.complete(messages, temperature=0.0)
        data = json.loads(raw)
        rewritten = (data.get("clinical_query") or "").strip()
        if rewritten:
            logger.info("Query rewrite: %r → %r", symptoms[:80], rewritten[:80])
            return rewritten
    except Exception as exc:
        logger.warning("Query rewrite failed (%s) — using original query.", exc)
    return symptoms


# ── Context builder ───────────────────────────────────────────────────────────

def _build_context(chunks: list[ChunkResult]) -> str:
    """Format top-k chunks into a readable protocol context block."""
    parts = []
    for chunk in chunks:
        codes = ", ".join(chunk.icd_codes) if chunk.icd_codes else "—"
        header = f"[Протокол: {chunk.title} | МКБ: {codes}]"
        parts.append(f"{header}\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


def build_messages(symptoms: str, chunks: list[ChunkResult]) -> list[dict]:
    """Build the final messages list for the LLM diagnostic generation call."""
    if chunks:
        context_block = _build_context(chunks)
        user_content = (
            f"Выдержки из клинических протоколов:\n{context_block}\n\n"
            f"Симптомы пациента:\n{symptoms}\n\n"
            "Проанализируй симптомы пациента, опираясь на протоколы. "
            "Верни строго JSON: три диагноза с рангом, кодом МКБ-10 и кратким обоснованием."
        )
    else:
        user_content = (
            f"Симптомы пациента:\n{symptoms}\n\n"
            "Выдержки из клинических протоколов: не найдены. "
            "Верни строго JSON: три наиболее вероятных диагноза с рангом, кодом МКБ-10 и обоснованием."
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
    """AsyncOpenAI-backed connector for the QazCode Hub."""

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

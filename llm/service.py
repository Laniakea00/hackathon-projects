"""RAG service – orchestrates retrieve → generate → format pipeline."""

import logging

from llm.formatter import FALLBACK, parse_llm_response
from llm.generator import BaseLLMConnector, build_messages
from llm.retriever import MedicalRetriever
from backend.schemas.diagnose import DiagnosisItem

logger = logging.getLogger(__name__)


class RAGService:
    """Thin orchestration layer over MedicalRetriever + BaseLLMConnector.

    Usage
    -----
    Create once at application startup and inject into endpoint handlers:

        retriever = MedicalRetriever()
        connector = QazCodeHubConnector()
        service   = RAGService(retriever, connector)
    """

    def __init__(
        self,
        retriever: MedicalRetriever,
        connector: BaseLLMConnector,
    ) -> None:
        self.retriever = retriever
        self.connector = connector

    async def diagnose(
        self,
        symptoms: str,
        top_k: int = 5,
        icd_filter: list[str] | None = None,
    ) -> list[DiagnosisItem]:
        """Full RAG pipeline for a symptom query.

        Parameters
        ----------
        symptoms:
            Free-text symptom description from the user.
        top_k:
            Maximum number of protocol chunks to retrieve.
        icd_filter:
            Optional list of ICD-10 code prefixes to restrict retrieval to
            protocols tagged with those codes (hybrid search).

        Returns
        -------
        Validated list of DiagnosisItem objects, never empty (falls back to
        the canonical fallback item when nothing useful can be produced).
        """
        # ── Step 1: hybrid retrieval ──────────────────────────────────────────
        chunks = await self.retriever.get_relevant_chunks(
            symptoms, top_k=top_k, icd_codes=icd_filter
        )
        logger.info(
            "Retrieved %d chunks for query %r (icd_filter=%s)",
            len(chunks),
            symptoms[:80],
            icd_filter,
        )

        if not chunks:
            logger.warning("No relevant chunks found – returning fallback.")
            return FALLBACK

        # ── Step 2: LLM generation ────────────────────────────────────────────
        messages = build_messages(symptoms, chunks)
        raw = await self.connector.complete(messages)

        # ── Step 3: parse & validate ──────────────────────────────────────────
        diagnoses = parse_llm_response(raw)

        if not diagnoses:
            logger.warning("LLM returned empty diagnoses – returning fallback.")
            return FALLBACK

        return diagnoses

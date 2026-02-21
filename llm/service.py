"""RAG service – orchestrates retrieve → generate → format pipeline.

Retrieval priority
------------------
1. pgvector (neural, high quality) — used when the DB has embeddings.
2. BM25 (lexical, no embeddings needed) — automatic fallback so the API
   works immediately, even before ``bootstrap.py`` has finished ingesting.
"""

import asyncio
import logging

from llm.bm25_retriever import bm25_search
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
        # ── Step 1: pgvector retrieval ────────────────────────────────────────
        chunks = await self.retriever.get_relevant_chunks(
            symptoms, top_k=top_k, icd_codes=icd_filter
        )
        logger.info(
            "pgvector: %d chunks for %r (icd_filter=%s)",
            len(chunks), symptoms[:80], icd_filter,
        )

        # ── Step 1b: BM25 fallback (DB empty / bootstrap not done yet) ────────
        if not chunks:
            logger.info("pgvector empty — falling back to BM25 retriever")
            chunks = await asyncio.to_thread(bm25_search, symptoms, top_k)
            logger.info("BM25: %d chunks retrieved", len(chunks))

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

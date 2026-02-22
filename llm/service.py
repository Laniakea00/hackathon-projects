"""RAG service — Query Rewrite → Vector Search → Rerank → Generation.

Pipeline
--------
1. Query Rewrite  : LLM extracts clinical entities from the raw complaint.
2. Vector Search  : top-12 chunks retrieved via pgvector (or BM25 fallback).
3. Heuristic Rerank: ICD-frequency + keyword boost, keep top-5.
4. Generation     : LLM produces 3 ranked diagnoses from the top-5 context.

Every stage is wrapped in try/except so that failures degrade gracefully:
  - Rewrite failure → use original query.
  - Search failure or empty → BM25 fallback → FALLBACK response.
  - Generation failure → FALLBACK response.
"""

import asyncio
import logging
from collections import Counter

from llm.bm25_retriever import bm25_search
from llm.formatter import FALLBACK, parse_llm_response
from llm.generator import BaseLLMConnector, build_messages, rewrite_query
from llm.retriever import ChunkResult, MedicalRetriever
from backend.schemas.diagnose import DiagnosisItem

logger = logging.getLogger(__name__)

_RERANK_TOP_K = 5
_SEARCH_TOP_K = 12


# ── Heuristic reranker ────────────────────────────────────────────────────────

def _heuristic_rerank(
    chunks: list[ChunkResult],
    query: str,
    top_k: int = _RERANK_TOP_K,
) -> list[ChunkResult]:
    """Re-score chunks by combining vector distance with ICD frequency.

    Scoring:
    - Base   : 1 - distance  (higher = closer match)
    - ICD    : codes frequent in top-12 get a boost (weight 0.3)
    - Title  : small bonus when a title word appears in the query (0.1)
    """
    if not chunks:
        return chunks

    icd_freq: Counter = Counter()
    for chunk in chunks:
        for code in chunk.icd_codes:
            icd_freq[code] += 1
    max_freq = max(icd_freq.values()) if icd_freq else 1

    query_lower = query.lower()
    scored: list[tuple[float, ChunkResult]] = []

    for chunk in chunks:
        base = 1.0 - min(chunk.distance, 1.0)

        icd_boost = (
            sum(icd_freq[c] / max_freq for c in chunk.icd_codes) * 0.3
            if chunk.icd_codes else 0.0
        )

        title_words = [w for w in (chunk.title or "").lower().split() if len(w) > 4]
        title_boost = 0.1 if any(w in query_lower for w in title_words) else 0.0

        scored.append((base + icd_boost + title_boost, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [chunk for _, chunk in scored[:top_k]]

    logger.info(
        "Rerank: %d → %d chunks | top icd_codes: %s",
        len(chunks), len(top),
        [c for c, _ in icd_freq.most_common(3)],
    )
    return top


# ── RAG service ───────────────────────────────────────────────────────────────

class RAGService:
    """Orchestrates the full Query Rewrite → Search → Rerank → Generate pipeline."""

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
        top_k: int = _SEARCH_TOP_K,
        icd_filter: list[str] | None = None,
    ) -> list[DiagnosisItem]:
        """Full RAG pipeline for a symptom query.

        Returns a validated list of DiagnosisItem objects, never empty.
        """
        # ── Stage 1: Query Rewrite ─────────────────────────────────────────────
        try:
            clinical_query = await rewrite_query(symptoms, self.connector)
        except Exception as exc:
            logger.warning("Stage 1 (rewrite) failed: %s — using original query.", exc)
            clinical_query = symptoms

        # ── Stage 2: Vector retrieval (top-12) ────────────────────────────────
        chunks: list[ChunkResult] = []
        try:
            chunks = await self.retriever.get_relevant_chunks(
                clinical_query, top_k=top_k, icd_codes=icd_filter
            )
            logger.info(
                "Stage 2 (pgvector): %d chunks for %r",
                len(chunks), clinical_query[:80],
            )
        except Exception as exc:
            logger.warning("Stage 2 (pgvector) failed: %s", exc)

        # ── Stage 2b: BM25 fallback ────────────────────────────────────────────
        if not chunks:
            logger.info("pgvector empty — falling back to BM25.")
            try:
                chunks = await asyncio.to_thread(bm25_search, clinical_query, top_k)
                logger.info("Stage 2b (BM25): %d chunks retrieved.", len(chunks))
            except Exception as exc:
                logger.warning("Stage 2b (BM25) failed: %s", exc)

        if not chunks:
            logger.warning("No chunks found — returning FALLBACK.")
            return FALLBACK

        # ── Stage 3: Heuristic Rerank → top-5 ────────────────────────────────
        try:
            top_chunks = _heuristic_rerank(chunks, symptoms, top_k=_RERANK_TOP_K)
        except Exception as exc:
            logger.warning("Stage 3 (rerank) failed: %s — using raw top-5.", exc)
            top_chunks = chunks[:_RERANK_TOP_K]

        # ── Stage 4: LLM Generation ───────────────────────────────────────────
        try:
            messages = build_messages(symptoms, top_chunks)
            raw = await self.connector.complete(messages)
            diagnoses = parse_llm_response(raw)
        except Exception as exc:
            logger.warning("Stage 4 (generation) failed: %s — returning FALLBACK.", exc)
            return FALLBACK

        if not diagnoses:
            logger.warning("LLM returned empty diagnoses — returning FALLBACK.")
            return FALLBACK

        return diagnoses

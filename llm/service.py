"""RAG service — Query Rewrite → Vector Search → Rerank → Generation.

Pipeline
--------
1. Query Rewrite  : LLM extracts clinical entities from the raw complaint.
2. Vector Search  : top-12 chunks via pgvector (or BM25 fallback).
3. Diversity      : keep best chunk per protocol, then heuristic rerank → top-5.
4. Generation     : LLM produces ranked diagnoses from context.
   Post-filter    : soft — logs mismatches but does NOT remove LLM predictions.

Every stage is wrapped in try/except so failures degrade gracefully.
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


# ── Diversity filter ───────────────────────────────────────────────────────────

def _dedupe_by_protocol(chunks: list[ChunkResult]) -> list[ChunkResult]:
    """Keep only the closest chunk per protocol to ensure diverse context."""
    seen: set[str] = set()
    result: list[ChunkResult] = []
    for chunk in sorted(chunks, key=lambda c: c.distance):
        if chunk.protocol_id not in seen:
            seen.add(chunk.protocol_id)
            result.append(chunk)
    return result


# ── Heuristic reranker ────────────────────────────────────────────────────────

def _heuristic_rerank(
    chunks: list[ChunkResult],
    query: str,
    top_k: int = _RERANK_TOP_K,
) -> list[ChunkResult]:
    """Re-score chunks combining vector distance + ICD frequency + title match.

    Scoring:
    - Base  : 1 - distance         (higher = closer)
    - ICD   : codes frequent in top chunks get boost (weight 0.2, reduced from 0.3)
    - Title : bonus when title word appears in query (weight 0.1)
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

        icd_boost = 0.0
        if chunk.icd_codes:
            icd_boost = max(icd_freq.get(c, 0) / max_freq for c in chunk.icd_codes) * 0.20

        title_words = [w for w in (chunk.title or "").lower().split() if len(w) > 4]
        title_boost = 0.10 if any(w in query_lower for w in title_words) else 0.0

        scored.append((base + icd_boost + title_boost, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


# ── RAG service ───────────────────────────────────────────────────────────────

class RAGService:
    """Orchestrates Query Rewrite → Search → Diversity → Rerank → Generate."""

    def __init__(self, retriever: MedicalRetriever, connector: BaseLLMConnector) -> None:
        self.retriever = retriever
        self.connector = connector

    async def diagnose(
        self,
        symptoms: str,
        top_k: int = _SEARCH_TOP_K,
        icd_filter: list[str] | None = None,
    ) -> list[DiagnosisItem]:
        """Full RAG pipeline. Returns a non-empty list of DiagnosisItem."""

        # ── Stage 1: Query Rewrite ─────────────────────────────────────────────
        try:
            clinical_query = await rewrite_query(symptoms, self.connector)
            if clinical_query != symptoms:
                logger.info("Stage 1 rewrite | original: %r → clinical: %r",
                            symptoms[:120], clinical_query[:120])
        except Exception as exc:
            logger.warning("Stage 1 (rewrite) failed: %s — using original.", exc)
            clinical_query = symptoms

        # ── Stage 2: Vector retrieval ──────────────────────────────────────────
        chunks: list[ChunkResult] = []
        try:
            chunks = await self.retriever.get_relevant_chunks(
                clinical_query, top_k=top_k, icd_codes=icd_filter
            )
            logger.info("Stage 2 (pgvector): %d chunks retrieved.", len(chunks))
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

        # ── Stage 3: Diversity + Heuristic Rerank ─────────────────────────────
        try:
            diverse = _dedupe_by_protocol(chunks)
            top_chunks = _heuristic_rerank(diverse, clinical_query, top_k=_RERANK_TOP_K)
        except Exception as exc:
            logger.warning("Stage 3 (rerank) failed: %s — using raw top-5.", exc)
            top_chunks = chunks[:_RERANK_TOP_K]

        # Log top chunks for debugging
        context_icds: set[str] = set()
        for c in top_chunks:
            for code in (c.icd_codes or []):
                context_icds.add((code or "").strip().upper())
            logger.info(
                "  ctx | pid=%-14s dist=%.3f icd=%-20s title=%s",
                c.protocol_id, c.distance,
                str((c.icd_codes or [])[:3]), (c.title or "")[:50],
            )

        # ── Stage 4: LLM Generation ───────────────────────────────────────────
        try:
            messages = build_messages(symptoms, top_chunks)
            raw = await self.connector.complete(messages)
            logger.info("Stage 4 LLM raw: %s", raw[:300])

            diagnoses = parse_llm_response(raw)

            if not diagnoses:
                logger.warning("LLM returned empty list — context ICD fallback.")
                cnt = Counter(
                    (c or "").strip().upper()
                    for ch in top_chunks for c in (ch.icd_codes or [])
                )
                top_codes = [c for c, _ in cnt.most_common(3)]
                return [
                    DiagnosisItem(rank=i + 1, diagnosis="(from context)",
                                  icd10_code=top_codes[i], explanation="")
                    for i in range(min(3, len(top_codes)))
                ] or FALLBACK

            # Soft post-filter: log mismatches, do NOT remove predictions
            def _norm(code: str) -> str:
                return (code or "").strip().upper().replace(" ", "")

            for d in diagnoses:
                p = _norm(d.icd10_code)
                in_ctx = p in context_icds or any(
                    a.startswith(p) or p.startswith(a) for a in context_icds
                )
                if not in_ctx:
                    logger.info(
                        "  LLM predicted %s (%s) — NOT in context ICDs %s",
                        p, d.diagnosis[:40], sorted(context_icds)[:6],
                    )

            return diagnoses[:3]

        except Exception as exc:
            logger.warning("Stage 4 (generation) failed: %s — returning FALLBACK.", exc)
            return FALLBACK

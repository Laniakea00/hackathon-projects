"""RAG service — Query Rewrite → Vector Search → Rerank → Generation.

Pipeline
--------
1. Query Rewrite  : LLM extracts clinical entities from the raw complaint.
2. Vector Search  : pgvector + BM25 run in parallel; results fused via RRF.
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
_SEARCH_TOP_K = 30          # broader initial pool for both pgvector and BM25
_RRF_K = 60                 # standard RRF constant
# Cosine distance threshold: chunks farther than this are likely irrelevant.
# Kept as a soft filter — if too few pass, we keep at least _MIN_CHUNKS_AFTER_FILTER.
_DISTANCE_THRESHOLD = 0.45
_MIN_CHUNKS_AFTER_FILTER = 5


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


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────────

def _rrf_fuse(
    vec_chunks: list[ChunkResult],
    bm25_chunks: list[ChunkResult],
    k: int = _RRF_K,
) -> list[ChunkResult]:
    """Fuse pgvector and BM25 results via Reciprocal Rank Fusion.

    Each pgvector chunk is scored by its vector rank plus the best BM25 rank
    of its protocol.  BM25-only protocols (not retrieved by pgvector at all)
    are appended at the tail so they can still surface via the reranker.

    score = 1/(k + vec_rank) + 1/(k + bm25_proto_rank)
    """
    # Best BM25 rank per protocol_id (1-indexed)
    bm25_proto_rank: dict[str, int] = {}
    for rank, chunk in enumerate(bm25_chunks, start=1):
        if chunk.protocol_id not in bm25_proto_rank:
            bm25_proto_rank[chunk.protocol_id] = rank

    bm25_miss = len(bm25_chunks) + 1
    vec_protos: set[str] = set()

    scored: list[tuple[float, ChunkResult]] = []
    for vec_rank, chunk in enumerate(vec_chunks, start=1):
        vec_protos.add(chunk.protocol_id)
        bm25_rank = bm25_proto_rank.get(chunk.protocol_id, bm25_miss)
        rrf = 1.0 / (k + vec_rank) + 1.0 / (k + bm25_rank)
        scored.append((rrf, chunk))

    # Append BM25-only chunks (protocols absent from pgvector results)
    vec_miss = len(vec_chunks) + 1
    for bm25_rank, chunk in enumerate(bm25_chunks, start=1):
        if chunk.protocol_id not in vec_protos:
            rrf = 1.0 / (k + vec_miss) + 1.0 / (k + bm25_rank)
            scored.append((rrf, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored]


# ── Heuristic reranker ────────────────────────────────────────────────────────

def _heuristic_rerank(
    chunks: list[ChunkResult],
    query: str,
    top_k: int = _RERANK_TOP_K,
) -> list[ChunkResult]:
    """Re-score chunks by vector distance + query keyword overlap in chunk text.

    Why the old approach was removed:
    - ICD frequency boost: rewarded having many protocols with the SAME code
      (e.g. 5× C53 → each got max +0.20, filling all context slots with cancer
      protocols for a cardiac query).
    - Title boost/penalty: all corpus titles are "Одобрен"/"Рекомендовано" —
      those words never appear in medical queries → uniform -0.08 penalty with
      zero discriminative power.

    New scoring:
    - Base      : 1 - distance          (primary signal)
    - Text hit  : +up to 0.20 for query keywords found in chunk text
                  (complementary token-level signal to dense vector distance)

    After scoring, an ICD-family diversity cap limits each 3-char ICD prefix
    (e.g. "C53", "F10") to at most 2 slots in the final top-k context, so a
    cluster of same-diagnosis protocols can never monopolise the LLM context.
    """
    if not chunks:
        return chunks

    query_lower = query.lower()
    query_words = {w for w in query_lower.split() if len(w) > 4}

    scored: list[tuple[float, ChunkResult]] = []
    for chunk in chunks:
        base = 1.0 - min(chunk.distance, 1.0)

        text_boost = 0.0
        if query_words:
            chunk_text_lower = (chunk.text or "").lower()
            hits = sum(1 for w in query_words if w in chunk_text_lower)
            text_boost = (hits / len(query_words)) * 0.20

        scored.append((base + text_boost, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)

    # ICD-family diversity cap: max 2 protocols per 3-char ICD prefix
    family_count: Counter = Counter()
    result: list[ChunkResult] = []
    for _, chunk in scored:
        families = {c[:3] for c in (chunk.icd_codes or []) if len(c) >= 3}
        # Accept the chunk if at least one of its ICD families still has room,
        # or if it carries no ICD codes at all (keep it for its text value).
        if not families or any(family_count[f] < 2 for f in families):
            result.append(chunk)
            for f in families:
                family_count[f] += 1
        if len(result) >= top_k:
            break

    return result


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

        # ── Stage 2: Parallel pgvector + BM25 → RRF fusion ────────────────────
        chunks: list[ChunkResult] = []
        vec_chunks: list[ChunkResult] = []
        bm25_chunks: list[ChunkResult] = []
        try:
            _vec_task = self.retriever.get_relevant_chunks(
                clinical_query, top_k=top_k, icd_codes=icd_filter
            )
            _bm25_task = asyncio.to_thread(bm25_search, clinical_query, top_k)
            _vec_result, _bm25_result = await asyncio.gather(
                _vec_task, _bm25_task, return_exceptions=True
            )
            if isinstance(_vec_result, Exception):
                logger.warning("Stage 2 (pgvector) failed: %s", _vec_result)
            else:
                vec_chunks = _vec_result

            if isinstance(_bm25_result, Exception):
                logger.warning("Stage 2 (BM25) failed: %s", _bm25_result)
            else:
                bm25_chunks = _bm25_result

            logger.info(
                "Stage 2 | pgvector: %d  BM25: %d chunks.",
                len(vec_chunks), len(bm25_chunks),
            )
            chunks = _rrf_fuse(vec_chunks, bm25_chunks)
            logger.info("Stage 2 (RRF fused): %d chunks.", len(chunks))
        except Exception as exc:
            logger.warning("Stage 2 retrieval failed: %s", exc)

        if not chunks:
            logger.warning("No chunks found — returning FALLBACK.")
            return FALLBACK

        # ── Stage 2c: Distance threshold filter ───────────────────────────
        close_chunks = [c for c in chunks if c.distance <= _DISTANCE_THRESHOLD]
        if len(close_chunks) >= _MIN_CHUNKS_AFTER_FILTER:
            logger.info(
                "Distance filter: kept %d/%d chunks (threshold=%.2f).",
                len(close_chunks), len(chunks), _DISTANCE_THRESHOLD,
            )
            chunks = close_chunks
        else:
            logger.info(
                "Distance filter: only %d chunks below threshold — keeping all %d.",
                len(close_chunks), len(chunks),
            )

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

            # ── Subcode expansion ──────────────────────────────────────────────
            # If the LLM outputs a parent code (e.g. "A39") but the retrieved
            # context contains exactly one matching subcode (e.g. "A39.0"),
            # promote the prediction to the more specific code.
            def _norm(code: str) -> str:
                return (code or "").strip().upper().replace(" ", "")

            def _expand_subcode(code: str) -> str:
                n = _norm(code)
                if "." in n or not n:
                    return code
                candidates = [c for c in context_icds if c.startswith(n + ".")]
                if len(candidates) == 1:
                    logger.info(
                        "  Subcode expansion: %s → %s (unique match in context)",
                        n, candidates[0],
                    )
                    return candidates[0]
                return code

            expanded: list[DiagnosisItem] = []
            for d in diagnoses[:3]:
                new_code = _expand_subcode(d.icd10_code)
                if new_code != d.icd10_code:
                    d = DiagnosisItem(
                        rank=d.rank,
                        diagnosis=d.diagnosis,
                        icd10_code=new_code,
                        explanation=d.explanation,
                    )
                p = _norm(d.icd10_code)
                in_ctx = p in context_icds or any(
                    a.startswith(p) or p.startswith(a) for a in context_icds
                )
                if not in_ctx:
                    logger.info(
                        "  LLM predicted %s (%s) — NOT in context ICDs %s",
                        p, d.diagnosis[:40], sorted(context_icds)[:6],
                    )
                expanded.append(d)

            return expanded

        except Exception as exc:
            logger.warning("Stage 4 (generation) failed: %s — returning FALLBACK.", exc)
            return FALLBACK

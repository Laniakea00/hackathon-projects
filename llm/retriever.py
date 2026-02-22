"""Semantic retriever for clinical protocol chunks.

Uses SentenceTransformer to encode the user query and performs a hybrid
cosine-distance + ICD metadata search against the ``protocol_chunks`` table
via pgvector's ``<=>`` operator.

The heavy model.encode() call runs in a thread-pool executor so it never
blocks the asyncio event loop.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field

from sentence_transformers import SentenceTransformer
from sqlalchemy import text

from backend import config
from backend.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# ── ICD code sanitisation ─────────────────────────────────────────────────────

_ICD_RE = re.compile(r"^[A-Z][0-9]")


def _sanitize_icd_codes(codes: list[str]) -> list[str]:
    """Keep only strings that look like valid ICD-10 code prefixes."""
    return [c for c in codes if _ICD_RE.match(c)]


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ChunkResult:
    """A retrieved protocol chunk with its cosine distance to the query."""

    id: int
    protocol_id: str
    chunk_index: int
    text: str
    distance: float         # lower = more similar (cosine distance ∈ [0, 2])
    title: str = ""         # protocol title (from protocols table)
    icd_codes: list[str] = field(default_factory=list)  # ICD-10 codes for this protocol


# ── SQL templates ─────────────────────────────────────────────────────────────

_BASE_SQL = """
    SELECT
        pc.id,
        pc.protocol_id,
        pc.chunk_index,
        pc.text,
        (pc.embedding <=> CAST(:emb AS vector)) AS distance,
        COALESCE(p.title, pc.protocol_id)       AS title,
        (
            SELECT ARRAY_AGG(d2.icd_code)
            FROM diagnoses d2
            WHERE d2.protocol_id = pc.protocol_id
        ) AS icd_codes
    FROM protocol_chunks pc
    LEFT JOIN protocols p ON p.id = pc.protocol_id
    WHERE pc.embedding IS NOT NULL
"""

_ICD_FILTER_CLAUSE = """
      AND pc.protocol_id IN (
          SELECT DISTINCT d.protocol_id
          FROM diagnoses d
          WHERE d.icd_code IN ({placeholders})
      )
"""

_ORDER_CLAUSE = "    ORDER BY distance ASC\n    LIMIT :top_k"


def _build_search_sql(icd_codes: list[str] | None) -> tuple[text, dict]:
    """Construct the parameterised search SQL and bind parameter dict."""
    params: dict = {}
    sql = _BASE_SQL

    if icd_codes:
        safe = _sanitize_icd_codes(icd_codes)
        if safe:
            placeholders = ", ".join(f":code_{i}" for i in range(len(safe)))
            sql += _ICD_FILTER_CLAUSE.format(placeholders=placeholders)
            for i, code in enumerate(safe):
                params[f"code_{i}"] = code

    sql += _ORDER_CLAUSE
    return text(sql), params


# ── Retriever class ───────────────────────────────────────────────────────────

class MedicalRetriever:
    """Async hybrid retriever backed by pgvector."""

    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None

    async def initialize(self) -> None:
        """Load the embedding model in a thread so startup doesn't block."""
        logger.info("Loading embedding model: %s …", config.EMBEDDING_MODEL)
        loop = asyncio.get_running_loop()
        self._model = await loop.run_in_executor(
            None, lambda: SentenceTransformer(config.EMBEDDING_MODEL)
        )
        logger.info("Embedding model ready.")

    async def _encode_query(self, query_text: str) -> list[float]:
        """Encode *query_text* with the mandatory e5 'query: ' prefix."""
        if self._model is None:
            raise RuntimeError("Retriever not initialised – call initialize() first.")

        loop = asyncio.get_running_loop()
        vec = await loop.run_in_executor(
            None,
            lambda: self._model.encode(  # type: ignore[union-attr]
                f"query: {query_text}",
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
        )
        return vec.tolist()

    @staticmethod
    def _vec_to_pg_literal(vec: list[float]) -> str:
        """Serialise a float list to the pgvector text format '[x,y,…]'."""
        return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"

    async def get_relevant_chunks(
        self,
        query_text: str,
        top_k: int = 5,
        icd_codes: list[str] | None = None,
    ) -> list[ChunkResult]:
        """Return the *top_k* most semantically relevant protocol chunks."""
        embedding = await self._encode_query(query_text)
        emb_literal = self._vec_to_pg_literal(embedding)

        sql, extra_params = _build_search_sql(icd_codes)
        params = {"emb": emb_literal, "top_k": top_k, **extra_params}

        async with AsyncSessionLocal() as session:
            result = await session.execute(sql, params)
            rows = result.mappings().all()

        return [
            ChunkResult(
                id=int(row["id"]),
                protocol_id=str(row["protocol_id"]),
                chunk_index=int(row["chunk_index"]),
                text=str(row["text"]),
                distance=float(row["distance"]),
                title=str(row["title"] or ""),
                icd_codes=list(row["icd_codes"] or []),
            )
            for row in rows
        ]

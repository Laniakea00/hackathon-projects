"""BM25 lexical retriever for clinical protocol chunks.

Serves two roles:
1. Fallback when the pgvector DB is empty (bootstrap hasn't run yet) — the API
   is immediately usable with lexical search at no infrastructure cost.
2. First-stage candidate retrieval in a future BM25 + vector hybrid pipeline.

The index is built lazily in-process from the JSONL corpus and cached as a
module-level singleton — no database required.

Core BM25 implementation ported from ``src/rag.py`` (origin/main branch) and
adapted to return the same ``ChunkResult`` type used by ``MedicalRetriever``
so that ``RAGService`` needs no changes when switching between backends.
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")

# Candidate corpus locations (checked in order).
_CORPUS_CANDIDATES: list[Path] = [
    Path(__file__).resolve().parent.parent / "data" / "protocols_corpus.jsonl",
    Path(__file__).resolve().parent.parent / "data" / "raw_protocols" / "protocols_corpus.jsonl",
]


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BM25Chunk:
    """Internal chunk type — wraps a text slice with its protocol metadata."""
    id: int              # sequential index into the chunk list
    protocol_id: str
    source_file: str
    title: str
    icd_codes: list[str]
    text: str


# ── BM25 index ────────────────────────────────────────────────────────────────

class BM25Index:
    """In-memory BM25 index over protocol text chunks.

    Parameters mirror standard BM25: k1 controls term-frequency saturation,
    b controls document-length normalisation.
    """

    def __init__(
        self,
        chunks: List[BM25Chunk],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b
        self.chunks = chunks
        self.tfs: List[Dict[str, int]] = []
        self.dls: List[int] = []
        self.df: Dict[str, int] = {}
        self.avgdl: float = 0.0
        self._build_stats()

    # ── Construction ──────────────────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [w.lower() for w in _WORD_RE.findall(text)]

    @staticmethod
    def _chunk_text(text: str, max_len: int = 1200, overlap: int = 150) -> List[str]:
        text = (text or "").strip()
        if not text:
            return []
        if len(text) <= max_len:
            return [text]
        out: List[str] = []
        i = 0
        while i < len(text):
            out.append(text[i : i + max_len])
            i += max_len - overlap
        return out

    @classmethod
    def build_from_jsonl(
        cls,
        jsonl_path: Path,
        max_len: int = 1200,
        overlap: int = 150,
    ) -> "BM25Index":
        chunks: List[BM25Chunk] = []
        chunk_id = 0

        with open(jsonl_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                protocol_id = obj.get("protocol_id", "")
                source_file = obj.get("source_file", "")
                title = obj.get("title", "")
                icd_codes = obj.get("icd_codes", []) or []
                full_text = obj.get("text", "") or ""

                for part in cls._chunk_text(full_text, max_len=max_len, overlap=overlap):
                    chunks.append(
                        BM25Chunk(
                            id=chunk_id,
                            protocol_id=protocol_id,
                            source_file=source_file,
                            title=title,
                            icd_codes=icd_codes,
                            text=part,
                        )
                    )
                    chunk_id += 1

        logger.info("BM25: built index over %d chunks from %s", len(chunks), jsonl_path)
        return cls(chunks)

    def _build_stats(self) -> None:
        total_dl = 0
        for ch in self.chunks:
            toks = self._tokenize(ch.text)
            dl = len(toks)
            self.dls.append(dl)
            total_dl += dl

            tf: Dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            self.tfs.append(tf)

            for t in tf:
                self.df[t] = self.df.get(t, 0) + 1

        self.avgdl = total_dl / max(len(self.chunks), 1) if self.chunks else 0.0

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _idf(self, term: str) -> float:
        N = len(self.chunks)
        df = self.df.get(term, 0)
        if df == 0 or N == 0:
            return 0.0
        return math.log(1.0 + (N - df + 0.5) / (df + 0.5))

    def _score(self, query_tokens: List[str], idx: int) -> float:
        tf = self.tfs[idx]
        dl = self.dls[idx]
        if dl == 0:
            return 0.0
        score = 0.0
        for t in query_tokens:
            f = tf.get(t, 0)
            if not f:
                continue
            idf = self._idf(t)
            denom = f + self.k1 * (1.0 - self.b + self.b * (dl / (self.avgdl + 1e-9)))
            score += idf * (f * (self.k1 + 1.0)) / (denom + 1e-9)
        return score

    def search(
        self, query: str, top_k: int = 6
    ) -> List[Tuple[float, BM25Chunk]]:
        tokens = self._tokenize(query)
        if not tokens:
            return []

        scored: List[Tuple[float, int]] = [
            (self._score(tokens, i), i)
            for i in range(len(self.chunks))
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            (s, self.chunks[i])
            for s, i in scored[:top_k]
            if s > 0
        ]


# ── Lazy singleton ─────────────────────────────────────────────────────────────

_index: Optional[BM25Index] = None
_lock: Lock = Lock()


def _find_corpus() -> Optional[Path]:
    for path in _CORPUS_CANDIDATES:
        if path.exists():
            return path
    return None


def get_index() -> Optional[BM25Index]:
    """Return the module-level BM25 index, building it on first call."""
    global _index
    if _index is not None:
        return _index
    with _lock:
        if _index is not None:
            return _index
        corpus = _find_corpus()
        if corpus is None:
            logger.warning(
                "BM25: corpus not found at %s — BM25 retriever disabled.",
                [str(p) for p in _CORPUS_CANDIDATES],
            )
            return None
        _index = BM25Index.build_from_jsonl(corpus)
    return _index


# ── Public retriever function ─────────────────────────────────────────────────

def bm25_search(query: str, top_k: int = 5) -> list:
    """Return top-k BM25 results as ``ChunkResult``-compatible objects.

    Imports ``ChunkResult`` lazily to avoid a circular import
    (retriever → database → … → bm25_retriever).
    """
    from llm.retriever import ChunkResult  # local import avoids circular dep

    index = get_index()
    if index is None:
        return []

    hits = index.search(query, top_k=top_k)
    results: list[ChunkResult] = []
    for rank, (score, chunk) in enumerate(hits):
        # Convert BM25 score to a pseudo-distance: lower = better
        # BM25 scores are unbounded above, so we map via 1/(1+score)
        distance = 1.0 / (1.0 + score)
        results.append(
            ChunkResult(
                id=chunk.id,
                protocol_id=chunk.protocol_id,
                chunk_index=chunk.id,
                text=chunk.text,
                distance=distance,
                title=chunk.title,
                icd_codes=list(chunk.icd_codes),
            )
        )
    return results

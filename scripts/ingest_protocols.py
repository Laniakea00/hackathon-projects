#!/usr/bin/env python3
"""Ingest medical protocols from JSONL into PostgreSQL with pgvector embeddings.

Strategy
--------
1. Read protocols_corpus.jsonl line by line (streaming, no full file in RAM).
2. Clean each text with "surgical tail removal":
   - Drop everything from the first noise marker (bibliography, authors).
   - Normalise whitespace.
3. Split cleaned text into overlapping chunks (~1 000 chars with 200-char overlap).
4. Encode chunks with intfloat/multilingual-e5-large (dim=1024).
5. Persist Protocol, Diagnosis, and ProtocolChunk rows.

Idempotency: if a Protocol row already exists it is skipped entirely,
so the script can safely be re-run after a partial failure.

Usage (from project root)
-------------------------
    uv run python scripts/ingest_protocols.py
    # or inside Docker:
    docker compose run --rm backend uv run python scripts/ingest_protocols.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterator

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path so `backend.*` is importable
# when the script is called from any working directory.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sentence_transformers import SentenceTransformer  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend.database import SessionLocal, init_db  # noqa: E402
from backend.models import Diagnosis, Protocol, ProtocolChunk  # noqa: E402
from backend.utils.text import clean_text, chunk_text  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CORPUS_PATH: Path = PROJECT_ROOT / "data" / "raw_protocols" / "protocols_corpus.jsonl"

EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large"
EMBEDDING_DIM: int = 1024   # must match model output

CHUNK_SIZE: int = 1000      # target chunk length in characters
CHUNK_OVERLAP: int = 200    # overlap between consecutive chunks

# How many protocols to accumulate before a single DB commit.
# Larger batches → fewer round-trips; smaller → less RAM.
DB_BATCH_SIZE: int = 16

# How many chunk texts to embed in one SentenceTransformer call.
EMBED_BATCH_SIZE: int = 32

# clean_text / chunk_text live in backend.utils.text (shared with bootstrap.py)

# ---------------------------------------------------------------------------
# JSONL reader
# ---------------------------------------------------------------------------


def iter_protocols(path: Path) -> Iterator[dict]:
    """Yield parsed JSON objects from a JSONL file, skipping blank lines."""
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"  [WARN] Skipping malformed JSON at line {lineno}: {exc}")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _flush_batch(
    db: Session,
    model: SentenceTransformer,
    buffer: list[tuple[dict, str, str, list[str]]],
) -> int:
    """Embed all chunks in *buffer* and persist to DB in a single transaction.

    Parameters
    ----------
    db:      Active SQLAlchemy session.
    model:   Loaded SentenceTransformer.
    buffer:  List of (record, raw_text, cleaned_text, chunks).

    Returns
    -------
    Number of chunks inserted.
    """
    # Build a flat, indexed list of texts to embed
    texts_to_embed: list[str] = []
    chunk_index_map: list[tuple[int, int]] = []   # (buf_idx, chunk_idx)

    for buf_idx, (_, _, _, chunks) in enumerate(buffer):
        for chunk_idx, chunk in enumerate(chunks):
            # e5 models require "passage: " prefix for documents
            texts_to_embed.append(f"passage: {chunk}")
            chunk_index_map.append((buf_idx, chunk_idx))

    if not texts_to_embed:
        return 0

    # Encode in sub-batches to control GPU/CPU memory
    embeddings: list[list[float]] = []
    for start in range(0, len(texts_to_embed), EMBED_BATCH_SIZE):
        batch = texts_to_embed[start: start + EMBED_BATCH_SIZE]
        vecs = model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
        embeddings.extend(vecs.tolist())

    # Group embeddings back by protocol
    buf_to_chunks: dict[int, list[tuple[int, str, list[float]]]] = defaultdict(list)
    for (buf_idx, chunk_idx), emb in zip(chunk_index_map, embeddings):
        original_chunk_text = buffer[buf_idx][3][chunk_idx]
        buf_to_chunks[buf_idx].append((chunk_idx, original_chunk_text, emb))

    # Insert everything in one transaction
    total_chunks = 0
    for buf_idx, (record, raw_text, _, _) in enumerate(buffer):
        protocol = Protocol(
            id=record["protocol_id"],
            source_file=record.get("source_file", ""),
            title=record.get("title", ""),
            full_text=raw_text,                     # preserve original
        )
        db.add(protocol)
        db.flush()  # populate PK without committing

        for icd_code in record.get("icd_codes", []):
            if icd_code and icd_code.strip():
                db.add(
                    Diagnosis(protocol_id=protocol.id, icd_code=icd_code.strip())
                )

        for chunk_idx, chunk_text_val, emb in buf_to_chunks.get(buf_idx, []):
            db.add(
                ProtocolChunk(
                    protocol_id=protocol.id,
                    chunk_index=chunk_idx,
                    text=chunk_text_val,
                    embedding=emb,
                )
            )
            total_chunks += 1

    db.commit()
    return total_chunks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if not CORPUS_PATH.exists():
        sys.exit(f"ERROR: corpus file not found: {CORPUS_PATH}")

    print("=== QazCode Protocol Ingestion ===")
    print(f"Corpus : {CORPUS_PATH}")
    print(f"Model  : {EMBEDDING_MODEL}  (dim={EMBEDDING_DIM})")
    print()

    print("Step 1/3  Initialising database …")
    init_db()

    print("Step 2/3  Loading embedding model …")
    model = SentenceTransformer(EMBEDDING_MODEL)

    print("Step 3/3  Ingesting protocols …")

    db: Session = SessionLocal()
    buffer: list[tuple[dict, str, str, list[str]]] = []
    total_added = total_skipped = total_chunks = 0

    try:
        for record in iter_protocols(CORPUS_PATH):
            pid = record.get("protocol_id", "")

            # --- Idempotency check ---
            if db.get(Protocol, pid) is not None:
                total_skipped += 1
                continue

            raw_text: str = record.get("text", "")
            cleaned: str = clean_text(raw_text)
            chunks: list[str] = chunk_text(cleaned)

            buffer.append((record, raw_text, cleaned, chunks))

            if len(buffer) >= DB_BATCH_SIZE:
                total_chunks += _flush_batch(db, model, buffer)
                total_added += len(buffer)
                print(
                    f"  … {total_added:>5} protocols | "
                    f"{total_chunks:>6} chunks inserted"
                )
                buffer = []

        # Flush remaining records
        if buffer:
            total_chunks += _flush_batch(db, model, buffer)
            total_added += len(buffer)

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print()
    print("Done!")
    print(f"  Protocols inserted : {total_added}")
    print(f"  Protocols skipped  : {total_skipped}  (already in DB)")
    print(f"  Chunks inserted    : {total_chunks}")


if __name__ == "__main__":
    main()

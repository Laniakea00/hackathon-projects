#!/usr/bin/env python3
"""Fast "first-boot" ingest for QazCode clinical protocols.

Differences from ingest_protocols.py
-------------------------------------
- Guards against re-running: exits immediately if the protocols table already
  has rows (idempotent, safe for ``restart: "no"`` in Docker Compose).
- Embedding cache: per-protocol ``.npy`` + ``.json`` files in
  ``data/.embeddings/`` so subsequent runs (e.g., after schema wipe) skip
  the expensive encode step for protocols whose text hasn't changed.
- Bulk insert: uses ``session.execute(insert(Model), list_of_dicts)`` batches
  of 50 protocols instead of ORM object construction (much faster).
- Calls ``create_hnsw_index()`` once after all data is in, amortising index
  build cost over the full dataset.

Usage (from project root)
--------------------------
    uv run python scripts/bootstrap.py
    # or inside Docker (see docker-compose.yml bootstrap service):
    docker compose run --rm bootstrap
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path regardless of working directory.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402
from sqlalchemy import insert, text  # noqa: E402

from backend.database.session import SessionLocal, create_hnsw_index, init_db  # noqa: E402
from backend.models.diagnosis import Diagnosis  # noqa: E402
from backend.models.protocol import Protocol, ProtocolChunk  # noqa: E402
from backend.utils.text import chunk_text, clean_text  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CORPUS_PATH: Path = PROJECT_ROOT / "data" / "raw_protocols" / "protocols_corpus.jsonl"
CACHE_DIR: Path = PROJECT_ROOT / "data" / ".embeddings"

EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large"
EMBEDDING_DIM: int = 1024

CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 200

# How many protocols to accumulate before a single DB commit.
DB_BATCH_SIZE: int = 50

# How many chunk texts to embed in one SentenceTransformer call.
EMBED_BATCH_SIZE: int = 32


# ---------------------------------------------------------------------------
# Embedding cache helpers
# ---------------------------------------------------------------------------

def _cache_paths(protocol_id: str) -> tuple[Path, Path]:
    """Return (embeddings .npy, chunks manifest .json) paths for a protocol."""
    safe_id = protocol_id.replace("/", "_").replace("\\", "_")
    return (
        CACHE_DIR / f"{safe_id}.npy",
        CACHE_DIR / f"{safe_id}.json",
    )


def _load_cache(protocol_id: str, chunks: list[str]) -> list[list[float]] | None:
    """Return cached embeddings if the chunks manifest matches, else None."""
    emb_path, manifest_path = _cache_paths(protocol_id)
    if not emb_path.exists() or not manifest_path.exists():
        return None

    try:
        cached_chunks: list[str] = json.loads(manifest_path.read_text(encoding="utf-8"))
        if cached_chunks != chunks:
            return None
        arr = np.load(str(emb_path))
        return arr.tolist()
    except Exception:
        return None


def _save_cache(protocol_id: str, chunks: list[str], embeddings: list[list[float]]) -> None:
    """Persist embeddings and chunk manifest to the cache directory."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    emb_path, manifest_path = _cache_paths(protocol_id)
    np.save(str(emb_path), np.array(embeddings, dtype=np.float32))
    manifest_path.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# JSONL reader
# ---------------------------------------------------------------------------

def _iter_protocols(path: Path):
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
# Batch processing
# ---------------------------------------------------------------------------

def _embed_batch(
    model: SentenceTransformer,
    texts: list[str],
) -> list[list[float]]:
    """Encode a flat list of texts, returning normalised 1024-dim vectors."""
    all_vecs: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        vecs = model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
        all_vecs.extend(vecs.tolist())
    return all_vecs


def _flush_batch(
    db,
    model: SentenceTransformer,
    buffer: list[tuple[dict, str, list[str]]],
) -> int:
    """Compute or reuse embeddings, then bulk-insert all rows.

    Parameters
    ----------
    db:     Active SQLAlchemy session.
    model:  Loaded SentenceTransformer.
    buffer: List of (record, cleaned_text, chunks).

    Returns
    -------
    Number of ProtocolChunk rows inserted.
    """
    # ── Collect texts that need fresh embeddings ──────────────────────────────
    needs_embed: list[tuple[int, list[str]]] = []  # (buf_idx, chunks)
    cached_embeddings: dict[int, list[list[float]]] = {}

    for buf_idx, (record, _, chunks) in enumerate(buffer):
        pid = record["protocol_id"]
        cached = _load_cache(pid, chunks)
        if cached is not None:
            cached_embeddings[buf_idx] = cached
        else:
            needs_embed.append((buf_idx, chunks))

    # ── Embed missing protocols ───────────────────────────────────────────────
    if needs_embed:
        flat_texts: list[str] = []
        flat_index: list[tuple[int, int]] = []  # (buf_idx, chunk_idx)
        for buf_idx, chunks in needs_embed:
            for chunk_idx, chunk in enumerate(chunks):
                flat_texts.append(f"passage: {chunk}")
                flat_index.append((buf_idx, chunk_idx))

        flat_vecs = _embed_batch(model, flat_texts)

        # Group back by protocol
        by_proto: dict[int, list[list[float]]] = defaultdict(list)
        for (buf_idx, _), vec in zip(flat_index, flat_vecs):
            by_proto[buf_idx].append(vec)

        for buf_idx, vecs in by_proto.items():
            record, _, chunks = buffer[buf_idx]
            cached_embeddings[buf_idx] = vecs
            _save_cache(record["protocol_id"], chunks, vecs)

    # ── Bulk insert ───────────────────────────────────────────────────────────
    protocol_rows: list[dict] = []
    diagnosis_rows: list[dict] = []
    chunk_rows: list[dict] = []

    for buf_idx, (record, raw_text, chunks) in enumerate(buffer):
        pid = record["protocol_id"]
        protocol_rows.append(
            {
                "id": pid,
                "source_file": record.get("source_file", ""),
                "title": record.get("title", ""),
                "full_text": raw_text.replace("\x00", ""),
            }
        )

        for icd_code in record.get("icd_codes", []):
            code = (icd_code or "").strip()
            if code:
                diagnosis_rows.append({"protocol_id": pid, "icd_code": code})

        for chunk_idx, (chunk_text_val, emb) in enumerate(
            zip(chunks, cached_embeddings.get(buf_idx, []))
        ):
            chunk_rows.append(
                {
                    "protocol_id": pid,
                    "chunk_index": chunk_idx,
                    "text": chunk_text_val.replace("\x00", ""),
                    "embedding": emb,
                }
            )

    if protocol_rows:
        db.execute(insert(Protocol), protocol_rows)
    if diagnosis_rows:
        db.execute(insert(Diagnosis), diagnosis_rows)
    if chunk_rows:
        db.execute(insert(ProtocolChunk), chunk_rows)

    db.commit()
    return len(chunk_rows)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not CORPUS_PATH.exists():
        sys.exit(f"ERROR: corpus file not found: {CORPUS_PATH}")

    print("=== QazCode Bootstrap ===")
    print(f"Corpus : {CORPUS_PATH}")
    print(f"Model  : {EMBEDDING_MODEL}  (dim={EMBEDDING_DIM})")
    print()

    # ── Step 1: ensure schema ─────────────────────────────────────────────────
    print("Step 1/4  Initialising database schema …")
    init_db()

    # ── Step 2: guard against re-running ─────────────────────────────────────
    db = SessionLocal()
    try:
        count = db.execute(text("SELECT COUNT(*) FROM protocols")).scalar()
    finally:
        db.close()

    if count and count > 0:
        print(f"Database already populated ({count} protocols).  Nothing to do.")
        sys.exit(0)

    # ── Step 3: load embedding model ──────────────────────────────────────────
    print("Step 2/4  Loading embedding model …")
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            print(f"  GPU detected: {torch.cuda.get_device_name(0)} — using CUDA ⚡")
        else:
            print("  No GPU detected — using CPU (slow, ~4–6 h for full corpus)")
    except ImportError:
        device = "cpu"
        print("  torch not installed — using CPU")
    model = SentenceTransformer(EMBEDDING_MODEL, device=device)

    # ── Step 4: stream, embed, and insert ─────────────────────────────────────
    print("Step 3/4  Ingesting protocols …")

    db = SessionLocal()
    buffer: list[tuple[dict, str, list[str]]] = []
    total_added = total_chunks = 0

    try:
        for record in _iter_protocols(CORPUS_PATH):
            raw_text: str = record.get("text", "")
            cleaned: str = clean_text(raw_text)
            chunks: list[str] = chunk_text(cleaned, CHUNK_SIZE, CHUNK_OVERLAP)

            buffer.append((record, raw_text, chunks))

            if len(buffer) >= DB_BATCH_SIZE:
                total_chunks += _flush_batch(db, model, buffer)
                total_added += len(buffer)
                print(
                    f"  … {total_added:>5} protocols | "
                    f"{total_chunks:>6} chunks inserted"
                )
                buffer = []

        if buffer:
            total_chunks += _flush_batch(db, model, buffer)
            total_added += len(buffer)

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # ── Step 5: build HNSW index ──────────────────────────────────────────────
    print("Step 4/4  Building HNSW index …")
    create_hnsw_index()

    print()
    print("Done!")
    print(f"  Protocols inserted : {total_added}")
    print(f"  Chunks inserted    : {total_chunks}")


if __name__ == "__main__":
    main()

"""SQLAlchemy engine/session factory and DB initialisation for QazCode.

Provides two engines:
- ``engine``        – synchronous (used by the ingest/bootstrap scripts).
- ``async_engine``  – asyncpg-backed (used by the FastAPI RAG endpoints).

Key design decisions:
- pgvector type registered with psycopg2 via SQLAlchemy connect event so that
  Python lists are accepted as vector column values during bulk insert.
- ``init_db()`` creates the extension and all tables but does NOT build the
  HNSW index — call ``create_hnsw_index()`` separately after bulk insert.
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend import config
from backend.database.base import Base


# ── Synchronous engine (ingest / bootstrap scripts) ───────────────────────────

engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


@event.listens_for(engine, "connect")
def _register_pgvector(dbapi_conn, connection_record):  # noqa: ANN001
    """Register pgvector adapter so Python lists work as vector column values."""
    try:
        from pgvector.psycopg2 import register_vector  # type: ignore[import]
        register_vector(dbapi_conn)
    except Exception:
        # Graceful degradation: if pgvector adapter isn't available the
        # raw text-literal fallback in retriever.py still works.
        pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Async engine (FastAPI / retriever) ────────────────────────────────────────

async_engine = create_async_engine(
    config.ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── DB lifecycle helpers ───────────────────────────────────────────────────────

def init_db() -> None:
    """Enable pgvector extension and create all tables (idempotent).

    Does NOT create the HNSW index — call ``create_hnsw_index()`` after
    bulk-inserting data so that index build is amortised over all rows.

    Uses the synchronous engine so it can be called from scripts and from
    the FastAPI lifespan handler (wrapped in asyncio.to_thread if needed).
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Import models here (deferred) so their metadata is registered before
    # create_all, while avoiding circular imports at module level.
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def create_hnsw_index() -> None:
    """Create an HNSW index on protocol_chunks.embedding (idempotent).

    Call this once after all data has been inserted.  Building the index
    after bulk insert is significantly faster than maintaining it during insert.
    """
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
                ON protocol_chunks
                USING hnsw (embedding vector_cosine_ops)
                """
            )
        )
        conn.commit()


# ── Embedding cache → DB loader ───────────────────────────────────────────────

def init_vector_db() -> None:
    """Load embeddings from data/.embeddings/ into DB if tables are empty.

    Idempotent: exits immediately when protocol_chunks table already has rows.
    Also reads data/raw_protocols/protocols_corpus.jsonl (if present) to
    populate protocols.title and the diagnoses table with ICD-10 codes.
    Call from the FastAPI lifespan via asyncio.to_thread() after init_db().
    """
    import json
    import logging
    from pathlib import Path

    import numpy as np
    from sqlalchemy import text

    logger = logging.getLogger(__name__)

    # ── Guard: skip if chunks table already has data ──────────────────────────
    with engine.connect() as conn:
        chunk_count = conn.execute(text("SELECT COUNT(*) FROM protocol_chunks")).scalar()
    if chunk_count and chunk_count > 0:
        logger.info("init_vector_db: %d chunks already in DB — skipping.", chunk_count)
        return

    # ── Locate embedding cache ─────────────────────────────────────────────────
    root = Path(__file__).resolve().parent.parent.parent
    cache_dir = root / "data" / ".embeddings"
    if not cache_dir.exists():
        logger.info("init_vector_db: cache dir %s not found — skipping.", cache_dir)
        return

    npy_files = sorted(cache_dir.glob("*.npy"))
    if not npy_files:
        logger.info("init_vector_db: cache dir is empty — skipping.")
        return

    logger.info("init_vector_db: found %d cached protocols — loading …", len(npy_files))

    # ── Load metadata from corpus JSONL (title + ICD codes) ──────────────────
    # Without this, protocols.title = protocol_id and diagnoses table stays
    # empty, leaving the LLM with no ICD context to ground its answers.
    meta: dict[str, dict] = {}
    corpus_path = root / "data" / "raw_protocols" / "protocols_corpus.jsonl"
    if corpus_path.exists():
        logger.info("init_vector_db: reading metadata from %s …", corpus_path.name)
        with open(corpus_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    pid = rec.get("protocol_id", "")
                    if pid:
                        meta[pid] = {
                            "title": (rec.get("title") or "").strip(),
                            "icd_codes": [
                                c.strip() for c in rec.get("icd_codes", []) if c.strip()
                            ],
                        }
                except Exception:
                    pass
        logger.info("init_vector_db: metadata loaded for %d protocols.", len(meta))
    else:
        logger.warning(
            "init_vector_db: corpus not found at %s — titles and ICD codes will be empty.",
            corpus_path,
        )

    # ── Build row lists ────────────────────────────────────────────────────────
    from backend.models.protocol import Protocol, ProtocolChunk

    protocol_rows: list[dict] = []
    diagnosis_rows: list[dict] = []
    chunk_rows: list[dict] = []

    for npy_path in npy_files:
        safe_id = npy_path.stem
        json_path = cache_dir / f"{safe_id}.json"
        if not json_path.exists():
            logger.warning("init_vector_db: no manifest for %s — skipping.", safe_id)
            continue

        try:
            embeddings = np.load(str(npy_path))           # shape: (n_chunks, 1024)
            chunks: list[str] = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("init_vector_db: cannot read %s — %s", safe_id, exc)
            continue

        m = meta.get(safe_id, {})
        title = m.get("title") or safe_id   # fall back to id if title missing

        protocol_rows.append({
            "id": safe_id,
            "source_file": "",
            "title": title,
            "full_text": "",
        })

        for icd_code in m.get("icd_codes", []):
            diagnosis_rows.append({"protocol_id": safe_id, "icd_code": icd_code})

        for chunk_idx, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
            clean = chunk_text.replace("\x00", "")
            chunk_rows.append({
                "protocol_id": safe_id,
                "chunk_index": chunk_idx,
                "text": clean,
                "embedding": emb.tolist(),
            })

    if not protocol_rows:
        logger.warning("init_vector_db: no valid cached protocols found.")
        return

    # ── Bulk insert with ON CONFLICT DO NOTHING (truly idempotent) ────────────
    BATCH = 500
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from backend.models.diagnosis import Diagnosis

    proto_stmt = pg_insert(Protocol).on_conflict_do_nothing(index_elements=["id"])
    diag_stmt = pg_insert(Diagnosis).on_conflict_do_nothing(
        constraint="uq_diagnosis_protocol_code"
    )
    chunk_stmt = pg_insert(ProtocolChunk).on_conflict_do_nothing(
        constraint="uq_chunk_protocol_index"
    )

    db = SessionLocal()
    try:
        db.execute(proto_stmt, protocol_rows)
        for i in range(0, len(diagnosis_rows), BATCH):
            db.execute(diag_stmt, diagnosis_rows[i : i + BATCH])
        for i in range(0, len(chunk_rows), BATCH):
            db.execute(chunk_stmt, chunk_rows[i : i + BATCH])
        db.commit()
        logger.info(
            "init_vector_db: inserted %d protocols, %d diagnoses, %d chunks.",
            len(protocol_rows), len(diagnosis_rows), len(chunk_rows),
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # ── Build HNSW index after all data is in ─────────────────────────────────
    create_hnsw_index()
    logger.info("init_vector_db: HNSW index ready.")


# ── FastAPI dependency injectors ──────────────────────────────────────────────

def get_db():
    """Sync FastAPI dependency – yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Async FastAPI dependency – yields an AsyncSession."""
    async with AsyncSessionLocal() as session:
        yield session

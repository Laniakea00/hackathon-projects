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

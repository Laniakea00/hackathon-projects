"""Centralised settings for QazCode.

Reads environment variables at import time.
In local development, populate a `.env` file – it is loaded automatically
via python-dotenv before any os.getenv() call.
"""

import os

from dotenv import load_dotenv

# Load .env only when the file exists; harmless in Docker (vars already set).
load_dotenv()

# ── PostgreSQL ────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/qazcode",
)

# Async variant for SQLAlchemy asyncpg engine (swap driver only).
ASYNC_DATABASE_URL: str = DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://", 1
)

# ── LLM (OpenAI-compatible endpoint) ─────────────────────────────────────────
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://hub.qazcode.ai/v1")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "oss-120b")

# ── Embedding model ───────────────────────────────────────────────────────────
EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "intfloat/multilingual-e5-large"
)
EMBEDDING_DIM: int = 1024   # output dimension of multilingual-e5-large

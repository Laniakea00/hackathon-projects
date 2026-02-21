"""Backward-compatible re-exports for the backend.database package.

Existing code that imports from ``backend.database`` directly continues to work
unchanged:
    from backend.database import Base, engine, init_db, AsyncSessionLocal, ...
"""

from backend.database.base import Base  # noqa: F401
from backend.database.session import (  # noqa: F401
    AsyncSessionLocal,
    SessionLocal,
    async_engine,
    create_hnsw_index,
    engine,
    get_async_db,
    get_db,
    init_db,
)

__all__ = [
    "Base",
    "AsyncSessionLocal",
    "SessionLocal",
    "async_engine",
    "create_hnsw_index",
    "engine",
    "get_async_db",
    "get_db",
    "init_db",
]

# This file is intentionally shadowed by the backend/database/ package.
#
# Python resolves `backend.database` to the backend/database/ directory
# (which contains __init__.py) and ignores this file entirely.
#
# All symbols previously defined here (Base, engine, SessionLocal,
# AsyncSessionLocal, init_db, get_db, get_async_db, …) are now in:
#
#   backend/database/base.py     – DeclarativeBase
#   backend/database/session.py  – engines, sessionmakers, lifecycle helpers
#   backend/database/__init__.py – backward-compatible re-exports
#
# DO NOT add code here – it will never be executed.

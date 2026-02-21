# This file is intentionally shadowed by the backend/models/ package.
#
# Python resolves `backend.models` to the backend/models/ directory
# (which contains __init__.py) and ignores this file entirely.
#
# All ORM models previously defined here are now in:
#
#   backend/models/protocol.py  – Protocol, ProtocolChunk
#   backend/models/diagnosis.py – Diagnosis
#   backend/models/user.py      – User, UserRole
#   backend/models/chat.py      – ClinicalCase, ChatMessage, UserCard, enums
#   backend/models/__init__.py  – backward-compatible re-exports
#
# DO NOT add code here – it will never be executed.

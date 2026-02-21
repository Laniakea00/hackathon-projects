"""Declarative base for all QazCode ORM models.

Kept isolated so that session.py and models can both import it
without creating circular dependencies.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

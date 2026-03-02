"""
Database type helpers.
Uses JSONB when available (PostgreSQL), falls back to JSON for SQLite (testing).
"""
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB


class JSONBCompat(JSON):
    """
    A JSON type that uses PostgreSQL's JSONB when connected to PostgreSQL,
    and falls back to plain JSON (TEXT in SQLite) for testing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class comparator_factory(JSON.Comparator):
        pass

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(JSON())

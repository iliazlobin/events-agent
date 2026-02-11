"""Database module for SQLite connection and schema management."""

from events_agent.database.connection import DatabaseConnection
from events_agent.database.schema import SchemaManager

__all__ = ["DatabaseConnection", "SchemaManager"]

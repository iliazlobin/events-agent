"""Thread-safe SQLite database connection management."""

import sqlite3
import threading
from pathlib import Path
from typing import Optional


class DatabaseConnection:
    """Thread-safe SQLite connection manager with connection pooling.

    Uses thread-local storage to ensure each thread gets its own connection.
    Supports both file-based and in-memory databases.

    Example:
        >>> db = DatabaseConnection("data/events.db")
        >>> conn = db.get_connection()
        >>> cursor = conn.cursor()
        >>> cursor.execute("SELECT * FROM events")
    """

    def __init__(self, db_path: str = "data/events.db"):
        """Initialize database connection manager.

        Args:
            db_path: Path to SQLite database file. Use ":memory:" for in-memory database.
        """
        self.db_path = db_path
        self._local = threading.local()

        # Create data directory if using file-based database
        if db_path != ":memory:":
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection.

        Creates a new connection for each thread if one doesn't exist.
        Enables foreign keys and WAL mode for concurrent reads.

        Returns:
            SQLite connection object for the current thread.
        """
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = self._create_connection()
        return self._local.connection

    def _create_connection(self) -> sqlite3.Connection:
        """Create and configure a new SQLite connection.

        Returns:
            Configured SQLite connection.
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)

        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")

        # Enable WAL mode for concurrent reads (file-based only)
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")

        # Return rows as sqlite3.Row objects for column name access
        conn.row_factory = sqlite3.Row

        return conn

    def close(self) -> None:
        """Close the thread-local connection if it exists."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    def close_all(self) -> None:
        """Close all connections across all threads.

        Note: This only closes the connection for the current thread.
        Other threads must close their own connections.
        """
        self.close()

    def execute(self, sql: str, parameters: tuple = ()) -> sqlite3.Cursor:
        """Execute a SQL statement and return the cursor.

        Args:
            sql: SQL statement to execute.
            parameters: Optional parameters for the SQL statement.

        Returns:
            Cursor object for the executed statement.
        """
        conn = self.get_connection()
        return conn.execute(sql, parameters)

    def execute_many(self, sql: str, parameters: list[tuple]) -> sqlite3.Cursor:
        """Execute a SQL statement multiple times with different parameters.

        Args:
            sql: SQL statement to execute.
            parameters: List of parameter tuples.

        Returns:
            Cursor object for the executed statement.
        """
        conn = self.get_connection()
        return conn.executemany(sql, parameters)

    def commit(self) -> None:
        """Commit the current transaction."""
        conn = self.get_connection()
        conn.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        conn = self.get_connection()
        conn.rollback()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - commit on success, rollback on error."""
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False

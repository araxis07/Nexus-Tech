"""SQLite connection management for save files."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from nexus_tech.persistence.schema import initialize_schema


class DatabaseManager:
    """Manage SQLite connections and schema initialization."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def exists(self) -> bool:
        """Return whether the database file already exists."""

        return self.db_path.exists()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a transactional SQLite connection and always close it."""

        connection = sqlite3.connect(self.db_path)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the database file and schema if needed."""

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            initialize_schema(connection)

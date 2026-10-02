"""Database access layer.

There is no real database behind this project. `Database` builds the same DSN a
PostgreSQL driver would use, but `connect()` returns a `MockConnection` that
records every statement and serves canned rows for SELECTs. Swap
`connection_factory` for `psycopg.connect` to talk to a real server.
"""

from __future__ import annotations

import logging
from collections import deque
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Sequence

from clinic.config import DatabaseConfig

logger = logging.getLogger(__name__)

Row = tuple[Any, ...]


class MockCursor:
    def __init__(self, connection: MockConnection) -> None:
        self._connection = connection
        self._rows: list[Row] = []
        self.rowcount = -1

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        statement = " ".join(sql.split())
        self._connection.executed.append((statement, tuple(params)))
        if statement.upper().startswith("SELECT"):
            self._rows = self._connection.next_result()
            self.rowcount = len(self._rows)
        else:
            self._rows = []
            self.rowcount = 1

    def fetchone(self) -> Row | None:
        return self._rows.pop(0) if self._rows else None

    def fetchall(self) -> list[Row]:
        rows, self._rows = self._rows, []
        return rows

    def close(self) -> None:
        self._rows = []


class MockConnection:
    """Stands in for a DB-API connection. Records statements; never touches a network."""

    def __init__(self, dsn: str, password: str | None = None) -> None:
        self.dsn = dsn
        self.executed: list[tuple[str, tuple[Any, ...]]] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self._results: deque[list[Row]] = deque()

    def queue_result(self, rows: list[Row]) -> None:
        """Queue the rows the next SELECT will return."""
        self._results.append(list(rows))

    def next_result(self) -> list[Row]:
        return self._results.popleft() if self._results else []

    def cursor(self) -> MockCursor:
        return MockCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


ConnectionFactory = Callable[..., Any]


class Database:
    def __init__(
        self,
        config: DatabaseConfig,
        connection_factory: ConnectionFactory = MockConnection,
    ) -> None:
        self.config = config
        self._connection_factory = connection_factory
        self._connection: Any = None

    @property
    def connection(self) -> Any:
        if self._connection is None:
            logger.info(
                "connecting to postgres host=%s port=%s dbname=%s",
                self.config.host,
                self.config.port,
                self.config.name,
            )
            self._connection = self._connection_factory(
                self.config.dsn(), password=self.config.password
            )
        return self._connection

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        conn = self.connection
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as exc:
            conn.rollback()
            # Driver errors can echo row values (e.g. unique-violation details), so
            # only the exception type is logged.
            logger.error("transaction rolled back error_type=%s", type(exc).__name__)
            raise
        finally:
            cursor.close()

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

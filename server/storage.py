"""Storage adapters for the run engine.

One narrow SQL store interface with two implementations:

- SQLiteStore — the local-first default (WAL journal, zero setup).
- PostgresStore — hosted mode via DATABASE_URL (psycopg2), pointed at a
  managed PostgreSQL such as Supabase. Imported lazily so the local app
  keeps working without the driver installed.

Both dialects share the same DDL and column names; only the parameter
placeholder differs. Rows cross the boundary as plain dicts, so the
engine never sees a driver type.
"""

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS runs (
      id TEXT PRIMARY KEY, goal TEXT NOT NULL, dataset_name TEXT NOT NULL,
      dataset_text TEXT NOT NULL, state TEXT NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL, error TEXT)""",
    """CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      idx INTEGER NOT NULL, role TEXT NOT NULL, title TEXT NOT NULL,
      state TEXT NOT NULL, summary TEXT, result_json TEXT, updated_at TEXT)""",
    """CREATE TABLE IF NOT EXISTS approvals (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      action TEXT NOT NULL, target TEXT NOT NULL, risk TEXT NOT NULL,
      impact TEXT NOT NULL, reversibility TEXT NOT NULL,
      content_hash TEXT NOT NULL, state TEXT NOT NULL,
      created_at TEXT NOT NULL, decided_at TEXT)""",
    """CREATE TABLE IF NOT EXISTS artifacts (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      name TEXT NOT NULL, kind TEXT NOT NULL, version INTEGER NOT NULL,
      content TEXT NOT NULL, published_path TEXT, created_at TEXT NOT NULL)""",
]


class SqlStore:
    """Dialect-neutral SQL access. Subclasses provide the connection and
    the parameter placeholder."""

    placeholder = "?"

    def _rows(self, cursor):
        if cursor.description is None:
            return []
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _exec(self, sql, params=()):
        cursor = self._conn.cursor()
        cursor.execute(sql.replace("?", self.placeholder), params)
        rows = self._rows(cursor)
        self._commit()
        return rows

    def _create_schema(self):
        for statement in SCHEMA_STATEMENTS:
            self._exec(statement)

    # -- generic helpers --------------------------------------------------
    def insert(self, table, row):
        columns = ", ".join(row)
        marks = ", ".join(["?"] * len(row))
        self._exec(f"INSERT INTO {table} ({columns}) VALUES ({marks})",
                   tuple(row.values()))

    def update(self, table, key, fields):
        assignments = ", ".join(f"{column} = ?" for column in fields)
        self._exec(f"UPDATE {table} SET {assignments} WHERE id = ?",
                   tuple(fields.values()) + (key,))

    # -- domain queries ---------------------------------------------------
    def get_run(self, run_id):
        rows = self._exec("SELECT * FROM runs WHERE id = ?", (run_id,))
        return rows[0] if rows else None

    def list_runs(self, limit=50):
        return self._exec(
            "SELECT id, goal, dataset_name, state, created_at, updated_at "
            "FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))

    def get_tasks(self, run_id):
        return self._exec(
            "SELECT * FROM tasks WHERE run_id = ? ORDER BY idx", (run_id,))

    def latest_artifact(self, run_id):
        rows = self._exec(
            "SELECT * FROM artifacts WHERE run_id = ? "
            "ORDER BY version DESC LIMIT 1", (run_id,))
        return rows[0] if rows else None

    def approvals_for_run(self, run_id):
        return self._exec(
            "SELECT * FROM approvals WHERE run_id = ?", (run_id,))

    def pending_approval(self, run_id):
        rows = self._exec(
            "SELECT * FROM approvals WHERE run_id = ? AND state = 'pending'",
            (run_id,))
        return rows[0] if rows else None

    def get_approval(self, approval_id, run_id):
        rows = self._exec(
            "SELECT * FROM approvals WHERE id = ? AND run_id = ?",
            (approval_id, run_id))
        return rows[0] if rows else None


class SQLiteStore(SqlStore):
    placeholder = "?"

    def __init__(self, path):
        import sqlite3
        from pathlib import Path

        Path(str(path)).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _commit(self):
        self._conn.commit()


class PostgresStore(SqlStore):
    placeholder = "%s"

    def __init__(self, database_url):
        import psycopg2  # lazy: only hosted mode needs the driver

        self._conn = psycopg2.connect(database_url)
        self._conn.autocommit = True
        self._create_schema()

    def _commit(self):
        pass  # autocommit


def open_store(database_url=None, sqlite_path=None):
    """Hosted PostgreSQL when DATABASE_URL is configured; SQLite otherwise."""
    if database_url and str(database_url).startswith(("postgres://", "postgresql://")):
        return PostgresStore(str(database_url))
    return SQLiteStore(sqlite_path)

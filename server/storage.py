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
    """CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      ended INTEGER NOT NULL, preferences_json TEXT NOT NULL,
      history_json TEXT NOT NULL, transcript_json TEXT NOT NULL,
      next_entry_id INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS memory_kv (
      key TEXT PRIMARY KEY, text TEXT NOT NULL,
      category TEXT NOT NULL, updated TEXT)""",
    """CREATE TABLE IF NOT EXISTS vault_notes (
      path TEXT PRIMARY KEY, run_id TEXT NOT NULL,
      content TEXT NOT NULL, created_at TEXT NOT NULL)""",
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
        self._migrate()

    def _migrate(self):
        """Additive migrations for databases created by earlier versions.

        ADD COLUMN errors when the column already exists in both dialects,
        which makes this safely repeatable on every startup."""
        for table in ("runs", "sessions"):
            try:
                self._exec(f"ALTER TABLE {table} ADD COLUMN owner TEXT")
            except Exception:
                self._rollback()
            else:
                # Rows written before ownership existed belong to the
                # local owner, matching pre-auth behavior.
                self._exec(
                    f"UPDATE {table} SET owner = 'local-owner' WHERE owner IS NULL")

    def _rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

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

    def list_runs(self, owner=None, limit=50):
        if owner is None:
            return self._exec(
                "SELECT id, goal, dataset_name, state, created_at, updated_at "
                "FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))
        return self._exec(
            "SELECT id, goal, dataset_name, state, created_at, updated_at "
            "FROM runs WHERE owner = ? ORDER BY created_at DESC LIMIT ?",
            (owner, limit))

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

    # -- sessions ---------------------------------------------------------
    def get_session(self, session_id):
        rows = self._exec("SELECT * FROM sessions WHERE id = ?", (session_id,))
        return rows[0] if rows else None

    def upsert_session(self, row):
        fields = {k: v for k, v in row.items() if k != "id"}
        assignments = ", ".join(f"{column} = ?" for column in fields)
        cursor = self._conn.cursor()
        cursor.execute(
            f"UPDATE sessions SET {assignments} WHERE id = ?".replace(
                "?", self.placeholder),
            tuple(fields.values()) + (row["id"],))
        if cursor.rowcount == 0:
            self.insert("sessions", row)
        else:
            self._commit()

    def trim_sessions(self, keep):
        self._exec(
            "DELETE FROM sessions WHERE id NOT IN "
            "(SELECT id FROM sessions ORDER BY updated_at DESC LIMIT ?)",
            (keep,))

    # -- shared memory ----------------------------------------------------
    def memory_load(self):
        return {
            row["key"]: {"text": row["text"], "category": row["category"],
                         "updated": row["updated"]}
            for row in self._exec("SELECT * FROM memory_kv")
        }

    def memory_save(self, payload):
        self._exec("DELETE FROM memory_kv")
        for key, entry in payload.items():
            self.insert("memory_kv", {
                "key": key, "text": entry["text"],
                "category": entry["category"], "updated": entry["updated"]})

    # -- vault notes ------------------------------------------------------
    def upsert_note(self, path, run_id, content, created_at):
        self._exec("DELETE FROM vault_notes WHERE path = ?", (path,))
        self.insert("vault_notes", {"path": path, "run_id": run_id,
                                    "content": content,
                                    "created_at": created_at})

    def list_notes(self):
        return self._exec(
            "SELECT path, run_id, created_at FROM vault_notes "
            "ORDER BY created_at DESC")

    def get_note(self, path):
        rows = self._exec("SELECT * FROM vault_notes WHERE path = ?", (path,))
        return rows[0] if rows else None


class DbMemoryBackend:
    """Agent memory persisted in the store's memory_kv table (hosted mode)."""

    persistent = True

    def __init__(self, store):
        self._store = store

    def load(self):
        try:
            return self._store.memory_load()
        except Exception:
            return {}

    def save(self, payload):
        try:
            self._store.memory_save(payload)
            return True
        except Exception:
            return False


class SQLiteStore(SqlStore):
    placeholder = "?"

    def __init__(self, path):
        import os
        import sqlite3
        import tempfile
        from pathlib import Path

        path = Path(str(path))
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Read-only deployment (e.g. a serverless bundle): fall back to
            # the writable temp directory. State is then per-instance and
            # ephemeral — configure DATABASE_URL for durable hosting.
            path = Path(tempfile.gettempdir()) / "agentic-os" / path.name
            path.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(path.parent, os.W_OK):
            path = Path(tempfile.gettempdir()) / "agentic-os" / path.name
            path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _commit(self):
        self._conn.commit()


class PostgresStore(SqlStore):
    placeholder = "%s"

    def __init__(self, database_url):
        import psycopg2  # lazy: only hosted mode needs the driver

        self._psycopg2 = psycopg2
        self._database_url = database_url
        self._conn = self._connect()
        self._create_schema()

    def _connect(self):
        conn = self._psycopg2.connect(self._database_url, connect_timeout=10)
        conn.autocommit = True
        return conn

    def _exec(self, sql, params=()):
        try:
            return super()._exec(sql, params)
        except self._psycopg2.OperationalError:
            # Serverless invocations and poolers drop idle connections;
            # reconnect once rather than failing a user's request.
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = self._connect()
            return super()._exec(sql, params)

    def _commit(self):
        pass  # autocommit


def open_store(database_url=None, sqlite_path=None):
    """Hosted PostgreSQL when DATABASE_URL is configured; SQLite otherwise."""
    if database_url and str(database_url).startswith(("postgres://", "postgresql://")):
        return PostgresStore(str(database_url))
    return SQLiteStore(sqlite_path)

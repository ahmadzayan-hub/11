"""Durable run engine: goal -> plan -> tasks -> approval -> artifact.

State is persisted to SQLite (WAL) after every transition, so runs survive
an application restart and can be resumed, cancelled, or approved later.
Execution is client-stepped: each `advance()` call executes exactly one
bounded task under a lock, which gives honest pause (stop advancing),
cancel, and recovery semantics without a background worker.

The publish step writes the approved report into an Obsidian-compatible
vault folder (markdown + provenance frontmatter + [[wikilinks]]) and is
gated by a server-enforced approval bound to the exact artifact hash —
a manipulated client cannot publish unapproved or altered content.
"""

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from server import analytics

RUN_STATES = {"queued", "running", "awaiting_approval", "verifying",
              "completed", "partially_completed", "failed", "cancelled"}
TASK_STATES = {"pending", "running", "succeeded", "failed", "skipped",
               "awaiting_approval", "cancelled"}

RUN_TRANSITIONS = {
    "queued": {"running", "cancelled"},
    "running": {"running", "awaiting_approval", "completed",
                "partially_completed", "failed", "cancelled"},
    "awaiting_approval": {"running", "completed", "partially_completed",
                          "cancelled"},
    "completed": set(), "partially_completed": set(), "failed": set(),
    "cancelled": set(),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, goal TEXT NOT NULL, dataset_name TEXT NOT NULL,
  dataset_text TEXT NOT NULL, state TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, error TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
  idx INTEGER NOT NULL, role TEXT NOT NULL, title TEXT NOT NULL,
  state TEXT NOT NULL, summary TEXT, result_json TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS approvals (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
  action TEXT NOT NULL, target TEXT NOT NULL, risk TEXT NOT NULL,
  impact TEXT NOT NULL, reversibility TEXT NOT NULL,
  content_hash TEXT NOT NULL, state TEXT NOT NULL,
  created_at TEXT NOT NULL, decided_at TEXT
);
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
  name TEXT NOT NULL, kind TEXT NOT NULL, version INTEGER NOT NULL,
  content TEXT NOT NULL, published_path TEXT, created_at TEXT NOT NULL
);
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


class RunEngine:
    def __init__(self, db_path, vault_dir, gateway):
        self.db_path = str(db_path)
        self.vault_dir = Path(vault_dir)
        self.gateway = gateway
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.db_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(SCHEMA)

    # -- state helpers ----------------------------------------------------
    def _set_run_state(self, run_id, new_state, error=None):
        row = self._db.execute("SELECT state FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        current = row["state"]
        if new_state != current and new_state not in RUN_TRANSITIONS[current]:
            raise ValueError(f"Illegal run transition {current} -> {new_state}")
        self._db.execute(
            "UPDATE runs SET state=?, error=?, updated_at=? WHERE id=?",
            (new_state, error, _now(), run_id))
        self._db.commit()

    def _set_task(self, task_id, state, summary=None, result=None):
        self._db.execute(
            "UPDATE tasks SET state=?, summary=COALESCE(?, summary), "
            "result_json=COALESCE(?, result_json), updated_at=? WHERE id=?",
            (state, summary, json.dumps(result) if result is not None else None,
             _now(), task_id))
        self._db.commit()

    # -- API --------------------------------------------------------------
    def create_run(self, goal, dataset_text=None, dataset_name=None):
        run_id = uuid.uuid4().hex[:12]
        text = dataset_text or analytics.sample_dataset()
        name = dataset_name or ("uploaded dataset" if dataset_text else "sample sales dataset")
        now = _now()
        self._db.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?,NULL)",
            (run_id, goal.strip(), name, text, "queued", now, now))
        roles = [role for role, _ in analytics.PIPELINE] + ["publish"]
        for idx, role in enumerate(roles):
            self._db.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,NULL,NULL,?)",
                (uuid.uuid4().hex[:12], run_id, idx, role,
                 analytics.ROLE_TITLES[role], "pending", now))
        self._db.commit()
        return self.get_run(run_id)

    def _context(self, run, tasks):
        ctx = {"goal": run["goal"], "dataset_text": run["dataset_text"],
               "dataset_name": run["dataset_name"], "run_id": run["id"]}
        for task in tasks:
            if task["state"] == "succeeded" and task["result_json"]:
                result = json.loads(task["result_json"])
                ctx[task["role"]] = result.get("output", {})
                ctx[task["role"] + "_result"] = result
        return ctx

    def advance(self, run_id):
        """Execute exactly one bounded task; every transition is durable."""
        run = self._row(run_id)
        if run["state"] in ("completed", "partially_completed", "failed", "cancelled"):
            raise ValueError(f"Run is {run['state']} and cannot advance.")
        if run["state"] == "awaiting_approval":
            raise ValueError("Run is awaiting approval — decide the approval first.")
        tasks = self._tasks(run_id)
        task = next((t for t in tasks if t["state"] == "pending"), None)
        if task is None:
            return self.get_run(run_id)
        self._set_run_state(run_id, "running")

        if task["role"] == "publish":
            return self._request_publish_approval(run_id, task, tasks)

        self._set_task(task["id"], "running")
        ctx = self._context(run, tasks)
        stage = dict(analytics.PIPELINE)[task["role"]]
        try:
            result = (stage(ctx, gateway=self.gateway)
                      if task["role"] == "business" else stage(ctx))
        except Exception as error:  # defensive: a stage bug must not hang the run
            self._set_task(task["id"], "failed", summary=f"Stage error: {error}")
            self._set_run_state(run_id, "failed", error=str(error))
            return self.get_run(run_id)

        if result["status"] == "failed" and task["role"] != "validator":
            self._set_task(task["id"], "failed", summary=result["summary"], result=result)
            self._set_run_state(run_id, "failed", error=result["summary"])
            return self.get_run(run_id)

        self._set_task(task["id"], "succeeded", summary=result["summary"], result=result)

        if task["role"] == "validator" and not result["output"]["passed"]:
            # Rejected work: skip publishing, finish as partially completed.
            for t in self._tasks(run_id):
                if t["state"] == "pending":
                    self._set_task(t["id"], "skipped",
                                   summary="Skipped: validation rejected the work.")
            self._set_run_state(run_id, "partially_completed",
                                error="Validation checks failed.")
            return self.get_run(run_id)

        if task["role"] == "reporter":
            self._db.execute(
                "INSERT INTO artifacts VALUES (?,?,?,?,?,?,NULL,?)",
                (uuid.uuid4().hex[:12], run_id, "analytics-report", "markdown", 1,
                 result["output"]["report_markdown"], _now()))
            self._db.commit()
        return self.get_run(run_id)

    def _request_publish_approval(self, run_id, task, tasks):
        artifact = self._db.execute(
            "SELECT * FROM artifacts WHERE run_id=? ORDER BY version DESC",
            (run_id,)).fetchone()
        if artifact is None:
            self._set_task(task["id"], "skipped", summary="No artifact to publish.")
            self._set_run_state(run_id, "completed")
            return self.get_run(run_id)
        existing = self._db.execute(
            "SELECT id FROM approvals WHERE run_id=? AND state='pending'",
            (run_id,)).fetchone()
        if existing is None:
            content_hash = hashlib.sha256(artifact["content"].encode()).hexdigest()
            self._db.execute(
                "INSERT INTO approvals VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
                (uuid.uuid4().hex[:12], run_id,
                 "Publish the analytics report to the Obsidian vault",
                 str(self.vault_dir / "Reports"), "high",
                 "Writes two markdown notes (report + run log) to the local vault.",
                 "Reversible: delete the created notes.",
                 content_hash, "pending", _now()))
            self._db.commit()
        self._set_task(task["id"], "awaiting_approval",
                       summary="Waiting for human approval to publish.")
        self._set_run_state(run_id, "awaiting_approval")
        return self.get_run(run_id)

    def decide_approval(self, run_id, approval_id, decision):
        approval = self._db.execute(
            "SELECT * FROM approvals WHERE id=? AND run_id=?",
            (approval_id, run_id)).fetchone()
        if approval is None:
            raise KeyError(approval_id)
        if approval["state"] != "pending":
            raise ValueError(f"Approval already {approval['state']}.")
        task = next(t for t in self._tasks(run_id) if t["role"] == "publish")
        artifact = self._db.execute(
            "SELECT * FROM artifacts WHERE run_id=? ORDER BY version DESC",
            (run_id,)).fetchone()
        # Approval binds to the exact content hash: altered content invalidates it.
        current_hash = hashlib.sha256(artifact["content"].encode()).hexdigest()
        if current_hash != approval["content_hash"]:
            raise ValueError("Artifact changed after approval was requested.")
        if decision == "approve":
            path = self._publish(run_id, artifact)
            self._db.execute("UPDATE approvals SET state='approved_once', decided_at=? WHERE id=?",
                             (_now(), approval_id))
            self._db.execute("UPDATE artifacts SET published_path=? WHERE id=?",
                             (str(path), artifact["id"]))
            self._db.commit()
            self._set_task(task["id"], "succeeded",
                           summary=f"Published to {path}.")
            self._set_run_state(run_id, "completed")
        else:
            self._db.execute("UPDATE approvals SET state='rejected', decided_at=? WHERE id=?",
                             (_now(), approval_id))
            self._db.commit()
            self._set_task(task["id"], "skipped",
                           summary="Publishing rejected by the user; no note was written.")
            self._set_run_state(run_id, "completed")
        return self.get_run(run_id)

    def _publish(self, run_id, artifact):
        run = self._row(run_id)
        reports = self.vault_dir / "Reports"
        logs = self.vault_dir / "Runs"
        reports.mkdir(parents=True, exist_ok=True)
        logs.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", run["goal"].lower()).strip("-")[:48] or "report"
        note = reports / f"{slug}-{run_id}.md"
        frontmatter = (
            "---\n"
            f"type: analytics-report\nrun: {run_id}\n"
            f"generated: {_now()}\nstatus: approved\n"
            f"dataset: \"{run['dataset_name']}\"\n---\n\n"
        )
        note.write_text(frontmatter + artifact["content"]
                        + f"\n\nRun log: [[{run_id}]]\n", encoding="utf-8")
        log_lines = [f"---\ntype: run-log\nrun: {run_id}\ngenerated: {_now()}\n---",
                     f"# Run {run_id}", "", f"**Goal:** {run['goal']}", "",
                     "| Stage | Outcome |", "| --- | --- |"]
        for t in self._tasks(run_id):
            log_lines.append(f"| {t['title']} | {t['state']}: {t['summary'] or ''} |")
        log_lines.append(f"\nReport: [[{note.stem}]]\n")
        (logs / f"{run_id}.md").write_text("\n".join(log_lines), encoding="utf-8")
        return note

    def cancel(self, run_id):
        self._set_run_state(run_id, "cancelled")
        for t in self._tasks(run_id):
            if t["state"] in ("pending", "awaiting_approval"):
                self._set_task(t["id"], "cancelled")
        self._db.execute(
            "UPDATE approvals SET state='cancelled', decided_at=? "
            "WHERE run_id=? AND state='pending'", (_now(), run_id))
        self._db.commit()
        return self.get_run(run_id)

    # -- reads ------------------------------------------------------------
    def _row(self, run_id):
        row = self._db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return row

    def _tasks(self, run_id):
        return self._db.execute(
            "SELECT * FROM tasks WHERE run_id=? ORDER BY idx", (run_id,)).fetchall()

    def list_runs(self):
        rows = self._db.execute(
            "SELECT id, goal, dataset_name, state, created_at, updated_at "
            "FROM runs ORDER BY created_at DESC LIMIT 50").fetchall()
        return [dict(r) for r in rows]

    def get_run(self, run_id):
        run = self._row(run_id)
        tasks = []
        charts, report = [], None
        for t in self._tasks(run_id):
            result = json.loads(t["result_json"]) if t["result_json"] else None
            tasks.append({"id": t["id"], "role": t["role"], "title": t["title"],
                          "state": t["state"], "summary": t["summary"],
                          "quality_checks": (result or {}).get("quality_checks", []),
                          "claims": (result or {}).get("claims", [])})
            if result and t["role"] == "visuals":
                charts = result["output"].get("charts", [])
        artifact = self._db.execute(
            "SELECT * FROM artifacts WHERE run_id=? ORDER BY version DESC",
            (run_id,)).fetchone()
        if artifact:
            report = {"id": artifact["id"], "name": artifact["name"],
                      "version": artifact["version"], "content": artifact["content"],
                      "published_path": artifact["published_path"]}
        approvals = [dict(a) for a in self._db.execute(
            "SELECT id, action, target, risk, impact, reversibility, state, "
            "created_at, decided_at FROM approvals WHERE run_id=?",
            (run_id,)).fetchall()]
        return {"id": run["id"], "goal": run["goal"],
                "dataset_name": run["dataset_name"], "state": run["state"],
                "error": run["error"], "created_at": run["created_at"],
                "updated_at": run["updated_at"], "tasks": tasks,
                "approvals": approvals, "charts": charts, "report": report}

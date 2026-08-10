"""FastAPI adapter that exposes the existing Agent class as a web API.

This layer contains no business logic. Every operation is mapped onto the
Agent's already-tested command surface (/remember, /forget, /set, /clear)
or reads the Agent's public state, and responses return fresh state
snapshots so the frontend never has to parse reply strings.

The command-line application (python main.py) is unaffected by this module.
"""

import os
import re
import threading
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import Agent
from server.model_gateway import ModelGateway
from server.runs import RunEngine
from utils import load_config

MAX_SESSIONS = 32
MAX_TEXT_LENGTH = 4000
PREFERENCE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,39}$")

# Presentation metadata for the Agent's command surface, used by the UI for
# quick actions and the command palette. Behaviour lives in agent.py only.
COMMANDS = [
    {"command": "/help", "usage": "/help", "description": "Show available commands"},
    {"command": "/remember", "usage": "/remember <information>", "description": "Save information to memory"},
    {"command": "/recall", "usage": "/recall", "description": "Show saved memory"},
    {"command": "/forget", "usage": "/forget <key> | all", "description": "Remove saved memory"},
    {"command": "/set", "usage": "/set <setting> <value>", "description": "Update a preference"},
    {"command": "/preferences", "usage": "/preferences", "description": "Show current preferences"},
    {"command": "/history", "usage": "/history", "description": "Show conversation history"},
    {"command": "/clear", "usage": "/clear", "description": "Clear conversation history"},
    {"command": "/exit", "usage": "/exit", "description": "End the session"},
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class Session:
    """One conversation: an Agent instance plus its visible transcript."""

    def __init__(self, config):
        self.id = uuid.uuid4().hex
        self.agent = Agent(config)
        self.transcript = []
        self.ended = False
        self.created_at = now_iso()
        self._next_entry_id = 1

    def add_entry(self, role, text):
        entry = {
            "id": self._next_entry_id,
            "role": role,
            "text": text,
            "time": now_iso(),
        }
        self._next_entry_id += 1
        self.transcript.append(entry)
        return entry

    def snapshot(self):
        return {
            "session_id": self.id,
            "agent_name": self.agent.name,
            "version": self.agent.version,
            "welcome": self.agent.get_welcome_message(),
            "ended": self.ended,
            "created_at": self.created_at,
            "transcript": self.transcript,
            "preferences": dict(self.agent.preferences),
            "memory": dict(self.agent.memory),
            "memory_entries": self.agent.memory_entries(),
            "history": list(self.agent.history),
            "memory_persisted": bool(self.agent.memory_file),
            "commands": COMMANDS,
        }


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


class MemoryIn(BaseModel):
    information: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    category: str | None = Field(default=None, max_length=24)


class PreferenceIn(BaseModel):
    key: str = Field(min_length=1, max_length=40)
    value: str = Field(min_length=1, max_length=200)


class RunIn(BaseModel):
    goal: str = Field(min_length=3, max_length=500)
    dataset_text: str | None = Field(default=None, max_length=300_000)
    dataset_name: str | None = Field(default=None, max_length=100)


class ApprovalIn(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(config_path=None):
    config = load_config(config_path or PROJECT_ROOT / "config.json")
    app = FastAPI(
        title=config.get("agent_name", "Agentic OS"),
        version=str(config.get("version", "1.0.0")),
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    sessions = OrderedDict()
    lock = threading.Lock()
    app.state.sessions = sessions

    gateway = ModelGateway()
    engine = RunEngine(
        config.get("database_file") or PROJECT_ROOT / "data" / "agentic.db",
        config.get("vault_dir") or PROJECT_ROOT / "vault",
        gateway,
    )
    app.state.engine = engine

    allowed_origins = [
        origin.strip()
        for origin in os.environ.get(
            "AGENTIC_OS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if request.url.path.startswith("/api/"):
            # Session, memory, and export payloads are private.
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        # Never leak stack traces or internal details to the browser.
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong on the server. Please try again."},
        )

    def get_session(session_id):
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found. It may have expired — start a new session.",
            )
        return session

    def clean_single_line(value, field_name):
        value = value.strip()
        if not value or "\n" in value or "\r" in value:
            raise HTTPException(
                status_code=422,
                detail=f"{field_name} must be a single non-empty line.",
            )
        return value

    # ------------------------------------------------------------------
    # Health and sessions
    # ------------------------------------------------------------------
    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "agent_name": config.get("agent_name", "Agentic OS"),
            "version": str(config.get("version", "1.0.0")),
            "model_provider": gateway.status(),
        }

    @app.post("/api/sessions", status_code=201)
    def create_session():
        with lock:
            while len(sessions) >= MAX_SESSIONS:
                sessions.popitem(last=False)
            session = Session(config)
            sessions[session.id] = session
            return session.snapshot()

    @app.get("/api/sessions/{session_id}")
    def read_session(session_id: str):
        with lock:
            return get_session(session_id).snapshot()

    @app.delete("/api/sessions/{session_id}")
    def end_session(session_id: str):
        with lock:
            session = get_session(session_id)
            session.ended = True
            reply = session.agent.process_input("/exit")
            session.add_entry("agent", reply)
            return session.snapshot()

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------
    @app.post("/api/sessions/{session_id}/messages")
    def send_message(session_id: str, message: MessageIn):
        text = message.text.strip()
        if not text:
            raise HTTPException(status_code=422, detail="Message text is empty.")
        with lock:
            session = get_session(session_id)
            if session.ended:
                raise HTTPException(
                    status_code=409,
                    detail="This session has ended. Start a new session to continue.",
                )
            session.add_entry("user", text)
            reply = session.agent.process_input(text)
            entry = session.add_entry("agent", reply)
            if text.split()[0].lower() == "/exit":
                session.ended = True
            return {"reply": entry, "state": session.snapshot()}

    @app.delete("/api/sessions/{session_id}/history")
    def clear_history(session_id: str):
        with lock:
            session = get_session(session_id)
            session.agent.history.clear()
            return {
                "reply_text": "Conversation history cleared.",
                "state": session.snapshot(),
            }

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    @app.put("/api/sessions/{session_id}/preferences")
    def update_preference(session_id: str, preference: PreferenceIn):
        key = preference.key.strip().lower()
        if not PREFERENCE_KEY_PATTERN.match(key):
            raise HTTPException(
                status_code=422,
                detail="Preference names may use lowercase letters, digits, and underscores.",
            )
        value = clean_single_line(preference.value, "Preference value")
        with lock:
            session = get_session(session_id)
            reply = session.agent.set_preference(key, value)
            return {"reply_text": reply, "state": session.snapshot()}

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------
    @app.post("/api/sessions/{session_id}/memory", status_code=201)
    def add_memory(session_id: str, memory: MemoryIn):
        information = clean_single_line(memory.information, "Memory text")
        with lock:
            session = get_session(session_id)
            # Reload the shared file first so a concurrent session's saves
            # are never overwritten (lost-update prevention).
            session.agent.reload_memory()
            reply = session.agent.add_memory(information, memory.category)
            return {"reply_text": reply, "state": session.snapshot()}

    @app.put("/api/sessions/{session_id}/memory/{key}")
    def update_memory(session_id: str, key: str, memory: MemoryIn):
        information = clean_single_line(memory.information, "Memory text")
        with lock:
            session = get_session(session_id)
            session.agent.reload_memory()
            if key not in session.agent.memory:
                raise HTTPException(status_code=404, detail=f"No memory named {key}.")
            reply = session.agent.update_memory(key, information, memory.category)
            return {"reply_text": reply, "state": session.snapshot()}

    @app.get("/api/sessions/{session_id}/export")
    def export_data(session_id: str):
        with lock:
            session = get_session(session_id)
            return JSONResponse(
                content={
                    "exported_at": now_iso(),
                    "agent_name": session.agent.name,
                    "preferences": dict(session.agent.preferences),
                    "memory": dict(session.agent.memory),
                    "memory_entries": session.agent.memory_entries(),
                    "history": list(session.agent.history),
                    "transcript": session.transcript,
                },
                headers={
                    "Content-Disposition": 'attachment; filename="agentic-os-export.json"'
                },
            )

    @app.delete("/api/sessions/{session_id}/memory/{key}")
    def delete_memory(session_id: str, key: str):
        with lock:
            session = get_session(session_id)
            session.agent.reload_memory()
            if key not in session.agent.memory:
                raise HTTPException(status_code=404, detail=f"No memory named {key}.")
            reply = session.agent.remove_memory(key)
            return {"reply_text": reply, "state": session.snapshot()}

    @app.delete("/api/sessions/{session_id}/memory")
    def clear_memory(session_id: str):
        with lock:
            session = get_session(session_id)
            session.agent.reload_memory()
            reply = session.agent.clear_all_memory()
            return {"reply_text": reply, "state": session.snapshot()}

    # ------------------------------------------------------------------
    # Runs: goal -> plan -> tasks -> approval -> artifact
    # ------------------------------------------------------------------
    def _run_or_404(action):
        try:
            return action()
        except KeyError:
            raise HTTPException(status_code=404, detail="Run not found.")
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error))

    @app.post("/api/runs", status_code=201)
    def create_run(run: RunIn):
        with lock:
            return engine.create_run(run.goal, run.dataset_text, run.dataset_name)

    @app.get("/api/runs")
    def list_runs():
        with lock:
            return {"runs": engine.list_runs()}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        with lock:
            return _run_or_404(lambda: engine.get_run(run_id))

    @app.post("/api/runs/{run_id}/advance")
    def advance_run(run_id: str):
        with lock:
            return _run_or_404(lambda: engine.advance(run_id))

    @app.post("/api/runs/{run_id}/cancel")
    def cancel_run(run_id: str):
        with lock:
            return _run_or_404(lambda: engine.cancel(run_id))

    @app.post("/api/runs/{run_id}/approvals/{approval_id}")
    def decide_approval(run_id: str, approval_id: str, decision: ApprovalIn):
        with lock:
            return _run_or_404(
                lambda: engine.decide_approval(run_id, approval_id, decision.decision)
            )

    # ------------------------------------------------------------------
    # Static frontend (production build), if present
    # ------------------------------------------------------------------
    dist = PROJECT_ROOT / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            candidate = (dist / full_path).resolve()
            # Serve real files inside dist; anything else falls back to the
            # SPA entry point. Path-aware containment (is_relative_to on the
            # resolved path) blocks traversal — a string prefix check would
            # not, e.g. a sibling directory named "dist-evil".
            if (
                full_path
                and candidate.is_relative_to(dist.resolve())
                and candidate.is_file()
            ):
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


# AGENTIC_OS_CONFIG lets tests and tools point the server at an alternative
# configuration file (and therefore an alternative memory file).
app = create_app(os.environ.get("AGENTIC_OS_CONFIG"))

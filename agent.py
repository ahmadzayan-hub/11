"""The Agent class: the central brain of the Agentic OS application.

The Agent receives every user request, keeps the conversation history,
stores memory (optionally persisted to disk), applies user preferences,
and produces a response for each recognized command.
"""

import re
from datetime import datetime, timezone

from utils import load_memory, save_json, validate_input

DEFAULT_MEMORY_CATEGORY = "general"
CATEGORY_PATTERN = re.compile(r"^[a-z][a-z0-9 _-]{0,23}$")


class FileMemoryBackend:
    """Default memory persistence: a JSON file on this computer."""

    def __init__(self, path):
        self.path = path

    @property
    def persistent(self):
        return bool(self.path)

    def load(self):
        return load_memory(self.path) if self.path else {}

    def save(self, payload):
        if not self.path:
            return True
        try:
            save_json(self.path, payload)
            return True
        except OSError:
            return False

DEFAULT_PREFERENCES = {
    "tone": "friendly",
    "language": "English",
    "save_history": True,
}

TONE_STYLES = {
    "friendly": "Happy to help! I received your request: \"{request}\". "
    "Enter /help to see everything I can do.",
    "concise": "Received: \"{request}\". See /help for commands.",
    "formal": "Your request \"{request}\" has been received. "
    "Please consult /help for the list of supported commands.",
}


class Agent:
    """Manages preferences, history, memory, and command handling."""

    def __init__(self, config, memory_backend=None):
        self.name = config.get("agent_name", "Agentic OS")
        self.version = config.get("version", "1.0.0")

        self.preferences = dict(DEFAULT_PREFERENCES)
        configured = config.get("preferences", {})
        if isinstance(configured, dict):
            self.preferences.update(configured)

        self.max_history_items = self._read_positive_int(
            config.get("maximum_history_items"), default=50
        )

        self.history = []
        self.memory_file = config.get("memory_file")
        self._memory_backend = memory_backend or FileMemoryBackend(self.memory_file)
        self.reload_memory()

    @property
    def memory_persistent(self):
        return self._memory_backend.persistent

    def reload_memory(self):
        """(Re)load memory from the backend, replacing the in-memory copy.

        Called at startup and again before shared-store mutations so that
        two concurrent sessions cannot overwrite each other's saves.
        self.memory keeps the simple key -> text contract; categories and
        timestamps live in self.memory_meta. Both plain-string files (the
        original format) and rich entries load transparently.
        """
        self.memory = {}
        self.memory_meta = {}
        raw = self._memory_backend.load()
        for key, value in raw.items():
            if isinstance(value, dict):
                text = str(value.get("text", "")).strip()
                if not text:
                    continue
                self.memory[key] = text
                updated = value.get("updated")
                self.memory_meta[key] = {
                    "category": self._clean_category(value.get("category")),
                    "updated": updated if isinstance(updated, str) else None,
                }
            elif isinstance(value, str) and value.strip():
                self.memory[key] = value
                self.memory_meta[key] = {
                    "category": DEFAULT_MEMORY_CATEGORY,
                    "updated": None,
                }

    @staticmethod
    def _read_positive_int(value, default):
        """Return value as a positive int, or the default when invalid."""
        if isinstance(value, bool):
            return default
        if isinstance(value, int) and value > 0:
            return value
        return default

    @staticmethod
    def _clean_category(value):
        """Normalize a category label, falling back to the default."""
        if isinstance(value, str):
            value = value.strip().lower()
            if CATEGORY_PATTERN.match(value):
                return value
        return DEFAULT_MEMORY_CATEGORY

    @staticmethod
    def _now_iso():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _key_order(key):
        """Sort memory keys numerically (memory_2 before memory_10)."""
        prefix, _, suffix = key.rpartition("_")
        if prefix == "memory" and suffix.isdecimal():
            return (0, int(suffix), key)
        return (1, 0, key)

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------
    def get_welcome_message(self):
        return (
            f"Welcome to {self.name} (version {self.version}). "
            "Enter /help to view available commands."
        )

    def process_input(self, user_input):
        """Route a single user request to the matching handler."""
        if not validate_input(user_input):
            return "Please enter a command or question."

        user_input = user_input.strip()
        command = user_input.split(maxsplit=1)[0].lower()
        # The /history command itself is not recorded, so its output shows
        # only the requests that came before it.
        if command != "/history":
            self._record_history(user_input)

        if command == "/help":
            return self.get_help()
        if command == "/history":
            return self.get_history()
        if command == "/clear":
            self.history.clear()
            return "Conversation history cleared."
        if command == "/remember":
            return self.remember(user_input)
        if command == "/recall":
            return self.recall()
        if command == "/forget":
            return self.forget(user_input)
        if command == "/set":
            return self.update_preference(user_input)
        if command == "/preferences":
            return self.get_preferences()
        if command == "/exit":
            return "Session closed. Goodbye."
        if user_input.startswith("/"):
            return (
                f"Unknown command: {command}. "
                "Enter /help to view available commands."
            )
        return self.generate_response(user_input)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    def _record_history(self, user_input):
        """Append the request to history, respecting user preferences."""
        if not self.preferences.get("save_history", True):
            return
        self.history.append(user_input)
        if len(self.history) > self.max_history_items:
            del self.history[: len(self.history) - self.max_history_items]

    def get_history(self):
        if not self.history:
            return "No conversation history is available."
        return "\n".join(self.history)

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------
    def remember(self, command):
        information = command[len("/remember"):].strip()
        return self.add_memory(information)

    def add_memory(self, information, category=None):
        """Save a new memory entry with a category and timestamp."""
        information = information.strip() if isinstance(information, str) else ""
        if not information:
            return "Please provide information to remember."
        key = self._next_memory_key()
        self.memory[key] = information
        self.memory_meta[key] = {
            "category": self._clean_category(category),
            "updated": self._now_iso(),
        }
        return self._saved_message("Information saved.")

    def recall(self):
        if not self.memory:
            return "No information has been saved yet."
        lines = [
            f"{key}: {self.memory[key]}"
            for key in sorted(self.memory, key=self._key_order)
        ]
        return "Saved information:\n" + "\n".join(lines)

    def forget(self, command):
        target = command[len("/forget"):].strip()
        if not target:
            return (
                "Please specify what to forget: "
                "/forget <key> or /forget all."
            )
        if target.lower() == "all":
            return self.clear_all_memory()
        return self.remove_memory(target)

    def remove_memory(self, key):
        """Delete one memory entry by key."""
        if key in self.memory:
            del self.memory[key]
            self.memory_meta.pop(key, None)
            return self._saved_message(f"Removed {key}.")
        return f"No saved information found for {key}. Enter /recall to list keys."

    def clear_all_memory(self):
        """Delete every memory entry."""
        self.memory.clear()
        self.memory_meta.clear()
        return self._saved_message("All saved information has been removed.")

    def memory_entries(self):
        """Memory as a list of rich entries in stable numeric key order."""
        entries = []
        for key in sorted(self.memory, key=self._key_order):
            meta = self.memory_meta.get(
                key, {"category": DEFAULT_MEMORY_CATEGORY, "updated": None}
            )
            entries.append(
                {
                    "key": key,
                    "text": self.memory[key],
                    "category": meta["category"],
                    "updated": meta["updated"],
                }
            )
        return entries

    def update_memory(self, key, information, category=None):
        """Replace the text (and optionally category) of an existing entry.

        Used by the web interface's edit control; returns a user-facing
        message either way so callers never need to raise.
        """
        information = information.strip() if isinstance(information, str) else ""
        if not information:
            return "Please provide information to remember."
        if key not in self.memory:
            return f"No saved information found for {key}. Enter /recall to list keys."
        self.memory[key] = information
        previous = self.memory_meta.get(
            key, {"category": DEFAULT_MEMORY_CATEGORY, "updated": None}
        )
        self.memory_meta[key] = {
            "category": self._clean_category(category)
            if category is not None
            else previous["category"],
            "updated": self._now_iso(),
        }
        return self._saved_message("Information updated.")

    def _next_memory_key(self):
        """Build a unique key even after entries have been deleted."""
        highest = 0
        for key in self.memory:
            prefix, _, suffix = key.rpartition("_")
            if prefix == "memory" and suffix.isdecimal():
                highest = max(highest, int(suffix))
        return f"memory_{highest + 1}"

    def _save_memory(self):
        """Persist memory via the backend. True on success, False on failure."""
        payload = {
            entry["key"]: {
                "text": entry["text"],
                "category": entry["category"],
                "updated": entry["updated"],
            }
            for entry in self.memory_entries()
        }
        return self._memory_backend.save(payload)

    def _saved_message(self, base):
        """Report the outcome honestly: a failed disk write is never
        presented as a successful save."""
        if self._save_memory():
            return base
        return (
            base.rstrip(".")
            + ", but the change could not be written to disk and may not "
            + "survive a restart. Check permissions for the memory file."
        )

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    def update_preference(self, command):
        parts = command.split(maxsplit=2)
        if len(parts) < 3:
            return "Usage: /set <setting> <value>. Example: /set tone concise"
        _, key, value = parts
        return self.set_preference(key, value)

    def set_preference(self, key, value):
        """Store one preference, converting true/false strings to booleans."""
        key = key.strip().lower()
        if isinstance(value, str) and value.lower() in ("true", "false"):
            value = value.lower() == "true"
        self.preferences[key] = value
        shown = str(value).lower() if isinstance(value, bool) else value
        return f"Preference updated: {key} = {shown}."

    def get_preferences(self):
        lines = []
        for key, value in sorted(self.preferences.items()):
            shown = str(value).lower() if isinstance(value, bool) else value
            lines.append(f"{key}: {shown}")
        return "Current preferences:\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # Responses
    # ------------------------------------------------------------------
    def generate_response(self, user_input):
        tone = self.preferences.get("tone", "friendly")
        template = TONE_STYLES.get(tone, TONE_STYLES["friendly"])
        return template.format(request=user_input)

    def get_help(self):
        return (
            "Available commands:\n"
            "/help: Display available commands\n"
            "/remember <information>: Save information\n"
            "/recall: Display saved information\n"
            "/forget <key>: Remove one saved item (/forget all removes everything)\n"
            "/set <setting> <value>: Update a preference (e.g. /set tone concise)\n"
            "/preferences: Display current preferences\n"
            "/history: Display conversation history\n"
            "/clear: Clear conversation history\n"
            "/exit: Close the application"
        )

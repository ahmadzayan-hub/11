"""The Agent class: the central brain of the Agentic OS application.

The Agent receives every user request, keeps the conversation history,
stores memory (optionally persisted to disk), applies user preferences,
and produces a response for each recognized command.
"""

from utils import load_memory, save_json, validate_input

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

    def __init__(self, config):
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
        self.memory = load_memory(self.memory_file) if self.memory_file else {}

    @staticmethod
    def _read_positive_int(value, default):
        """Return value as a positive int, or the default when invalid."""
        if isinstance(value, bool):
            return default
        if isinstance(value, int) and value > 0:
            return value
        return default

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
        if not information:
            return "Please provide information to remember."
        self.memory[self._next_memory_key()] = information
        self._save_memory()
        return "Information saved."

    def recall(self):
        if not self.memory:
            return "No information has been saved yet."
        lines = [
            f"{key}: {value}" for key, value in sorted(self.memory.items())
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
            self.memory.clear()
            self._save_memory()
            return "All saved information has been removed."
        if target in self.memory:
            del self.memory[target]
            self._save_memory()
            return f"Removed {target}."
        return f"No saved information found for {target}. Enter /recall to list keys."

    def update_memory(self, key, information):
        """Replace the text stored under an existing memory key in place.

        Used by the web interface's edit control; returns a user-facing
        message either way so callers never need to raise.
        """
        information = information.strip() if isinstance(information, str) else ""
        if not information:
            return "Please provide information to remember."
        if key not in self.memory:
            return f"No saved information found for {key}. Enter /recall to list keys."
        self.memory[key] = information
        self._save_memory()
        return "Information updated."

    def _next_memory_key(self):
        """Build a unique key even after entries have been deleted."""
        highest = 0
        for key in self.memory:
            prefix, _, suffix = key.rpartition("_")
            if prefix == "memory" and suffix.isdecimal():
                highest = max(highest, int(suffix))
        return f"memory_{highest + 1}"

    def _save_memory(self):
        if not self.memory_file:
            return
        try:
            save_json(self.memory_file, self.memory)
        except OSError:
            # Memory stays available for this session even if the disk
            # write fails; persistence resumes on the next successful save.
            pass

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    def update_preference(self, command):
        parts = command.split(maxsplit=2)
        if len(parts) < 3:
            return "Usage: /set <setting> <value>. Example: /set tone concise"
        _, key, value = parts
        key = key.lower()
        if value.lower() in ("true", "false"):
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

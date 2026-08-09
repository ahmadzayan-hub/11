"""Reusable helper functions for the Agentic OS application.

These utilities handle configuration loading, JSON persistence, and
input validation so that the Agent class and the entry point stay small.
"""

import json
from pathlib import Path


def load_config(file_path):
    """Load application settings from a JSON configuration file.

    Raises FileNotFoundError when the file is missing and ValueError
    when the file exists but does not contain valid JSON, so callers
    can show a clear message instead of a raw traceback.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    try:
        with path.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Configuration file is not valid JSON: {file_path} ({error})"
        ) from error
    if not isinstance(config, dict):
        raise ValueError(
            f"Configuration file must contain a JSON object: {file_path}"
        )
    return config


def save_json(file_path, data):
    """Write data to a JSON file, creating parent directories if needed."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def load_memory(file_path):
    """Load persistent memory from a JSON file.

    A missing file is normal on first run and returns an empty dict.
    A corrupt file also returns an empty dict rather than crashing the
    application, because memory is a convenience, not critical state.
    """
    path = Path(file_path)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def validate_input(user_input):
    """Return True when the input is a non-empty, non-whitespace string."""
    return isinstance(user_input, str) and bool(user_input.strip())

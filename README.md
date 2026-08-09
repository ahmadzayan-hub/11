# Agentic OS

## Project Purpose

Agentic OS is an interactive Python application that behaves like a simple
intelligent assistant. It runs in the terminal, receives user requests,
remembers selected information between sessions, applies user preferences,
and responds to a set of recognized commands.

In this project, "operating system" means an intelligent assistant
environment — not a replacement for Windows, macOS, or Linux.

## Main Features

- Command-line interaction through a simple `You:` / `Agent:` loop
- A central `Agent` class that manages all behaviour
- User preferences (tone, language, history saving) changeable at runtime
- Conversation history with a configurable maximum size
- Persistent memory stored in `data/memory.json` that survives restarts
- Configuration through an external `config.json` file
- Error handling for invalid input, unknown commands, and missing or
  corrupt files
- A unit-test suite built with Python's `unittest` framework

## Directory Structure

```text
agentic-os/
│
├── main.py            # Entry point and interaction loop
├── agent.py           # The Agent class (commands, memory, preferences)
├── utils.py           # Configuration loading, JSON persistence, validation
├── config.json        # User-editable settings
├── README.md          # This file
├── user_guide.md      # Detailed usage guide
├── requirements.txt   # Dependencies (standard library only)
├── .gitignore
│
├── data/
│   └── memory.json    # Persistent memory (starts empty)
│
└── tests/
    ├── __init__.py
    ├── test_agent.py  # Tests for the Agent class
    └── test_utils.py  # Tests for helpers and persistence
```

## System Requirements

- Python 3.8 or newer
- No external packages — the project uses only the Python standard library,
  so `requirements.txt` is intentionally empty apart from a comment.

## Installation

```bash
git clone <repository-url>
cd 11
```

No further installation steps are needed.

## Running the Program

Run from the project's root directory (the folder containing `config.json`):

```bash
python main.py
```

Enter `/exit` (or press Ctrl+C) to close the application.

## Running the Tests

From the project's root directory:

```bash
python -m unittest discover tests
```

All tests pass on the submitted version:

```text
............................................
----------------------------------------------------------------------
Ran 44 tests

OK
```

## Basic Usage Example

```text
Welcome to Agentic OS (version 1.0.0). Enter /help to view available commands.
You: /set tone concise
Agent: Preference updated: tone = concise.
You: /remember My preferred language is English.
Agent: Information saved.
You: /recall
Agent: Saved information:
       memory_1: My preferred language is English.
You: /history
Agent: /set tone concise
       /remember My preferred language is English.
       /recall
You: /exit
Agent: Session closed. Goodbye.
```

See `user_guide.md` for the full command reference and more examples.

## Known Limitations

- The agent recognizes commands and produces tone-styled acknowledgements
  for free text; it does not use an AI language model and does not learn
  autonomously.
- Preference changes made with `/set` apply to the current session only.
  Permanent defaults are set by editing `config.json`.
- Conversation history is kept in memory for the session only; it is not
  written to disk.
- Memory persistence stores plain text in `data/memory.json` without
  encryption, so avoid saving confidential information.

## Future Improvements

- Persist preference changes back to `config.json` on request
- Optional saving of conversation history between sessions
- Named memory keys (e.g. `/remember birthday = 1 May`)
- Integration with an AI model for free-text conversation

## Author and Course Information

- Author: Ahmad Zayan
- Course: Agentic OS Final Project
- Version: 1.0.0

# Agentic OS — User Guide

This guide explains how to use the Agentic OS assistant in day-to-day
sessions. For installation and testing instructions, see `README.md`.

## Starting and Stopping the Application

Start the application from the project's root directory:

```bash
python main.py
```

The assistant greets you and waits for input:

```text
Welcome to Agentic OS (version 1.0.0). Enter /help to view available commands.
You:
```

To stop, enter `/exit` — anything typed after it on the same line is
ignored, so `/exit now` also closes the application. Pressing Ctrl+C
(or Ctrl+D) closes it safely as well.

## The Input Prompt

Every line you type after `You:` is sent to the agent.

- Lines starting with `/` are treated as **commands**.
- Anything else is treated as a **free-text request**, which the agent
  acknowledges using your preferred tone.
- Empty input is rejected with a gentle reminder — the application never
  crashes on blank lines.

## Supported Commands

| Command        | Purpose                                   | Example                        |
| -------------- | ----------------------------------------- | ------------------------------ |
| `/help`        | Displays available commands               | `/help`                        |
| `/remember`    | Saves information                         | `/remember My name is Ahmad`   |
| `/recall`      | Displays all saved information            | `/recall`                      |
| `/forget`      | Removes one saved item, or everything     | `/forget memory_1`, `/forget all` |
| `/set`         | Updates a preference                      | `/set tone concise`            |
| `/preferences` | Displays current preferences              | `/preferences`                 |
| `/history`     | Displays session history                  | `/history`                     |
| `/clear`       | Clears conversation history               | `/clear`                       |
| `/exit`        | Closes the application                    | `/exit`                        |

Command names are case-insensitive (`/HELP` works), but saved information
and preference values keep the exact text you typed. The `/history`
command itself is not added to the history it displays — it shows only
the requests that came before it.

## How Preferences Work

Preferences control how the agent behaves. Defaults live in `config.json`:

| Preference     | Default    | Effect                                                  |
| -------------- | ---------- | ------------------------------------------------------- |
| `tone`         | `friendly` | Response style: `friendly`, `concise`, or `formal`      |
| `language`     | `English`  | Recorded for reference; responses are in English        |
| `save_history` | `true`     | When `false`, requests are not recorded in the history  |

Change a preference for the current session with `/set`:

```text
You: /set tone formal
Agent: Preference updated: tone = formal.
You: Good morning
Agent: Your request "Good morning" has been received. Please consult /help
       for the list of supported commands.
```

Values `true` and `false` are stored as real booleans, so
`/set save_history false` switches history recording off immediately.
An unrecognized `tone` value falls back to the friendly style.

`/set` changes apply **only to the current session**. To change a default
permanently, edit the `preferences` section of `config.json`.

## How Memory Works

`/remember` stores a piece of information under an automatic key
(`memory_1`, `memory_2`, ...):

```text
You: /remember The metro opens at 5am
Agent: Information saved.
You: /recall
Agent: Saved information:
       memory_1: The metro opens at 5am
```

Memory is written to `data/memory.json`, so it **remains available after
you close and restart the application**. Keys stay unique even after
deletions, so removing `memory_1` never causes a new entry to overwrite
an existing one.

## Clearing Stored Information

- `/forget memory_1` removes a single item (use `/recall` to see the keys).
- `/forget all` removes everything the agent has remembered.
- `/clear` clears the **conversation history** of the current session; it
  does not touch saved memory.

You can also delete `data/memory.json` while the application is closed —
it is recreated automatically on the next `/remember`.

## Common Errors and Solutions

| Message                                                | Cause and solution                                                       |
| ------------------------------------------------------ | ------------------------------------------------------------------------ |
| `Configuration file not found: config.json`            | Run the app from the project root folder, where `config.json` lives.     |
| `Configuration file is not valid JSON: ...`            | Fix the JSON syntax in `config.json` (a missing comma or quote).         |
| `Unknown command: /... Enter /help ...`                | The command is misspelled or unsupported — check `/help`.                |
| `Please provide information to remember.`              | `/remember` was used without any text after it.                          |
| `Usage: /set <setting> <value>.`                       | `/set` needs both a setting name and a value.                            |
| `No saved information found for ...`                   | The key does not exist — enter `/recall` to list valid keys.             |

Invalid or unexpected input never crashes the application; the agent
always answers with an explanation of what to do instead.

## Privacy and Data Storage

- Saved memory is stored as **plain, unencrypted text** in
  `data/memory.json` on your own computer. Nothing is sent over the
  internet.
- Do not store passwords, API keys, or confidential personal information
  with `/remember`.
- To erase all stored data, enter `/forget all` or delete
  `data/memory.json`.
- Conversation history exists only in memory for the current session and
  disappears when the application closes.

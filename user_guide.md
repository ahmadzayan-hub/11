# Agentic OS — User Guide

This guide covers day-to-day use of Agentic OS in both interfaces: the web
workspace and the command line. For installation and testing, see
`README.md`.

---

## Part 1 — The Web Workspace

### Starting and stopping

```bash
python -m uvicorn server.app:app --port 8000
```

Open <http://localhost:8000>. A session starts automatically, and
**refreshing the page reconnects to the same conversation** (a new session
begins only when you ask for one, end the current one, or restart the
server). Stop the server with Ctrl+C; use **End session** in the sidebar
to close a session gracefully first (the agent says goodbye and the
composer locks).

On your first visit a short onboarding dialog explains the basics — it
appears once and can be dismissed permanently.

### The workspace at a glance

- **Header** — product identity, a centered command search (opens the
  palette), live session status (Ready, Working, Offline, Error, or
  Session ended), theme toggle, and help.
- **Sidebar** (desktop) — switches between Workspace, Memory, Activity,
  and Preferences, plus New session and End session. On phones and
  tablets the four views live in a **bottom tab bar**, and the session
  actions open in a drawer from the menu button.
- **Workspace** — a greeting hero with suggested actions when the
  conversation is empty, then your messages and the agent's replies with
  timestamps, a copy button on agent replies, and auto-scroll that pauses
  while you read older messages (a **Latest** button jumps back down).
- **Context panel** (large screens) — session facts and recent activity.

### Sending messages and commands

Type in the composer and press <kbd>Enter</kbd> to send;
<kbd>Shift</kbd>+<kbd>Enter</kbd> adds a line break. Anything starting
with `/` is a command; everything else gets a tone-styled acknowledgement.

You never need to memorize commands:

- Press <kbd>Ctrl</kbd>+<kbd>K</kbd> (or <kbd>⌘</kbd>+<kbd>K</kbd>) to
  open the searchable command palette — picking a command inserts it into
  the composer.
- The help button (?) lists every command with its usage.
- An empty conversation offers suggested starting actions.

If a message fails to send (for example, offline), it is not lost — a
retry option appears, and the status badge shows the connection state.

### Managing memory and your data

Open **Memory** to see everything the agent has saved. Each entry carries
a **category** (General, Profile, Work, Projects, or Preferences) and a
**last-updated date**. You can search entries, filter by category, add new
ones, **edit any entry in place** (text and category), delete a single
entry, or delete everything. The **Data controls** card provides:

- **Export my data** — downloads memory, preferences, history, and the
  transcript as `agentic-os-export.json`.
- **Clear conversation history** — removes this session's history only.
- **Delete all memory** — permanently removes every saved entry.

Destructive actions always require confirmation. Memory is stored in
`data/memory.json` on the machine running the server and persists between
sessions and restarts. Do not store passwords or confidential information.

### Preferences

Open **Preferences** to switch the response tone (Friendly, Concise, or
Formal — replies change immediately), set **your name** (used in the
workspace greeting), set the language label, and turn session-history
recording on or off. Changes apply to the current session; permanent
defaults are edited in `config.json`. The **Interface** card holds
browser-side settings: theme (Dark, Light, or System) and a reduced-motion
switch.

### Activity

Open **Activity** for a timestamped timeline of real events — session
started or restored, memory saved, preference changed, history cleared,
requests completed or failed, and connection changes — filterable by
**System, Memory, Preferences, or Errors**, alongside a **Session
health** card showing connection state, whether memory persistence is
active, entry counts, and the time of the last successful response.

Note: memory saved with the CLI's `/remember` command gets the *General*
category; categories are chosen in the web interface.

### Themes and accessibility

- The theme toggle switches light/dark; with no choice made, the app
  follows your system setting. The choice is remembered.
- The entire app works with a keyboard alone: <kbd>Tab</kbd> moves focus
  (a skip-link jumps straight to the composer), dialogs trap focus and
  close with <kbd>Escape</kbd>, and important changes are announced to
  screen readers.
- System reduced-motion settings are respected.

---

## Part 2 — The Command-Line Interface

### Starting and stopping

```bash
python main.py
```

To stop, enter `/exit` — anything typed after it on the same line is
ignored, so `/exit now` also closes the application. Pressing Ctrl+C
(or Ctrl+D) closes it safely as well.

Every line you type after `You:` is sent to the agent. Empty input is
rejected with a gentle reminder — the application never crashes on blank
lines.

---

## Supported Commands (both interfaces)

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
| `/exit`        | Ends the session                          | `/exit`                        |

Command names are case-insensitive (`/HELP` works), but saved information
and preference values keep the exact text you typed. The `/history`
command itself is not added to the history it displays — it shows only
the requests that came before it.

## How Preferences Work

| Preference     | Default    | Effect                                                  |
| -------------- | ---------- | ------------------------------------------------------- |
| `tone`         | `friendly` | Response style: `friendly`, `concise`, or `formal`      |
| `language`     | `English`  | Recorded for reference; responses are in English        |
| `save_history` | `true`     | When `false`, requests are not recorded in the history  |

Values `true` and `false` are stored as real booleans, so
`/set save_history false` switches history recording off immediately.
An unrecognized `tone` value falls back to the friendly style.

## How Memory Works

`/remember` (or the Memory panel) stores information under an automatic
key (`memory_1`, `memory_2`, ...). Memory is written to
`data/memory.json`, so it **remains available after restarts**. Keys stay
unique even after deletions, so removing one entry never overwrites
another.

## Clearing Stored Information

- Delete a single entry in the Memory panel, or `/forget memory_1`.
- Clear everything with the panel's **Clear all** button (asks for
  confirmation) or `/forget all`.
- **Clear history** in the sidebar (asks for confirmation) or `/clear`
  clears the conversation history only; it does not touch saved memory.
- You can also delete `data/memory.json` while the server is stopped — it
  is recreated automatically.

## Common Errors and Solutions

| Message                                                | Cause and solution                                                       |
| ------------------------------------------------------ | ------------------------------------------------------------------------ |
| `Configuration file not found: ...`                    | Run from the project root folder, where `config.json` lives.             |
| `Configuration file is not valid JSON: ...`            | Fix the JSON syntax in `config.json` (a missing comma or quote).         |
| `Unknown command: /... Enter /help ...`                | The command is misspelled or unsupported — check `/help`.                |
| `Please provide information to remember.`              | `/remember` was used without any text after it.                          |
| `Usage: /set <setting> <value>.`                       | `/set` needs both a setting name and a value.                            |
| `No saved information found for ...`                   | The key does not exist — check `/recall` or the Memory panel.            |
| `Cannot reach the Agentic OS server.` (web)            | The server is not running or the connection dropped — a retry is offered.|
| `This session has ended.` (web)                        | Start a new session from the sidebar.                                    |

Invalid or unexpected input never crashes the application; the agent
always answers with an explanation of what to do instead.

## Privacy and Data Storage

- Saved memory is **plain, unencrypted text** in `data/memory.json` on the
  machine running Agentic OS. Nothing is sent over the internet.
- Conversation history and activity exist in memory for the current
  session only and disappear when the session or server closes.
- The web app stores only two things in your browser: the theme choice and
  whether onboarding was dismissed.
- Do not store passwords, API keys, or confidential personal information
  with `/remember`.

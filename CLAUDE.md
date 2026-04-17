# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AI-powered meeting scheduler. A Flask web app where users chat naturally to book Google Calendar events. An LLM extracts the attendee name and time from conversation, then calls a `book_meeting` tool that creates the calendar event via the Google Calendar API.

All application code lives under `ai-meeting-scheduler/`.

## Commands

All commands run from `ai-meeting-scheduler/`:

```bash
# Run the web app
python app.py

# Run the CLI agent (no web server, interactive terminal)
python smart_agent.py

# Run all tests
python -m unittest test_timezone test_input_validation test_session_isolation test_session_store -v

# Run a single test module
python -m unittest test_timezone -v

# Run a single test case
python -m unittest test_timezone.TestCalendarTimezone.test_start_and_end_timezones_match -v
```

## Environment variables

Create `ai-meeting-scheduler/.env`:

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `SECRET_KEY` | No | `dev-secret-change-in-production` | Flask session cookie signing |
| `TIMEZONE` | No | `America/New_York` | Calendar event timezone (both start and end) |
| `MAX_SESSIONS` | No | `1000` | Max concurrent in-memory sessions before LRU eviction |

Google Calendar also requires `credentials.json` (OAuth2 client secrets) in the working directory. On first run it opens a browser for the OAuth flow and caches the token to `token.json`. Both files are gitignored.

## Architecture

### Request flow

```
Browser  →  POST /chat  →  input validation
                         →  session cookie → session_histories (LRU store)
                         →  llm_with_tools.invoke(history)
                         →  if tool_calls: book_meeting() → add_event_to_calendar()
                         →  JSON reply
```

### Key design decisions

**Per-session chat history** (`app.py`): `session_histories` is a `_BoundedSessionStore` (LRU-capped `OrderedDict`, default 1000 entries). Each browser session gets a UUID stored in a signed cookie; the UUID keys into this dict. This prevents cross-user contamination and bounds memory use.

**Tool-use pattern** (`app.py`): The LLM is bound to `book_meeting` via LangChain's `.bind_tools()`. When the model emits a tool call, the code executes it, wraps the result in a `ToolMessage`, appends it to history, and returns the result string directly to the user — no second LLM pass.

**System prompt per session** (`_make_system_prompt()`): The date is evaluated fresh when a session is first created (not at server start), so "next Friday" resolves correctly for long-running servers.

**Timezone** (`calendar_helper.py`): `CALENDAR_TIMEZONE` is a single constant used for both `start.timeZone` and `end.timeZone`. Previously these were different hardcoded values, which caused incorrect event durations.

### Module responsibilities

- `app.py` — Flask routes, LLM wiring, session store, `book_meeting` tool definition
- `calendar_helper.py` — Google Calendar OAuth2 + event insertion, isolated from LLM logic
- `smart_agent.py` — standalone CLI version (no Flask, simpler tool stub, useful for prompt testing)
- `chat_loop.py` — minimal LangChain chat loop, no tools (reference/demo only)

### Testing approach

Each test file stubs all external dependencies (Google libraries, LangChain, OpenAI) at the module level using `sys.modules` before importing `app`. Tests target behaviour through the Flask test client or directly against the class under test. No pytest — use `python -m unittest`.

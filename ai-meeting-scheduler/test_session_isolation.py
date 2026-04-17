"""
Tests for Gap 3: per-session chat history isolation.

Verifies that:
- Each browser session gets its own independent chat history
- Two concurrent sessions cannot see each other's messages
- A new session always starts with a fresh history (only the system prompt)
- The server-side session_histories dict is keyed by session ID
"""
import sys
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stub all external dependencies before app.py is imported
# ---------------------------------------------------------------------------
def _stub_modules():
    for name in [
        "google", "google.auth", "google.auth.transport",
        "google.auth.transport.requests", "google.oauth2",
        "google.oauth2.credentials", "google_auth_oauthlib",
        "google_auth_oauthlib.flow", "googleapiclient",
        "googleapiclient.discovery",
    ]:
        sys.modules.setdefault(name, MagicMock())

    fake_lc = MagicMock()
    for name in [
        "langchain_openai", "langchain_core", "langchain_core.messages",
        "langchain_core.tools",
    ]:
        sys.modules.setdefault(name, fake_lc)

_stub_modules()

with patch("langchain_openai.ChatOpenAI", MagicMock()), \
     patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
    import app as flask_app


def _fake_llm_response(text="OK"):
    r = MagicMock()
    r.tool_calls = []
    r.content = text
    return r


class TestSessionIsolation(unittest.TestCase):

    def setUp(self):
        flask_app.app.config["TESTING"] = True
        flask_app.app.secret_key = "test-secret"
        # Start each test with an empty session store
        flask_app.session_histories.clear()

    # ------------------------------------------------------------------
    # 1. Two different clients have separate histories
    # ------------------------------------------------------------------
    def test_two_clients_have_independent_histories(self):
        with patch.object(flask_app, "llm_with_tools") as mock_llm:
            mock_llm.invoke.return_value = _fake_llm_response("Reply A")
            client_a = flask_app.app.test_client()
            client_a.post("/chat", json={"message": "Hello from A"})

        with patch.object(flask_app, "llm_with_tools") as mock_llm:
            mock_llm.invoke.return_value = _fake_llm_response("Reply B")
            client_b = flask_app.app.test_client()
            client_b.post("/chat", json={"message": "Hello from B"})

        # Each client should have created its own session entry
        self.assertEqual(len(flask_app.session_histories), 2)

    # ------------------------------------------------------------------
    # 2. The same client reuses its own history across requests
    # ------------------------------------------------------------------
    def test_same_client_accumulates_history(self):
        client = flask_app.app.test_client()

        with patch.object(flask_app, "llm_with_tools") as mock_llm:
            mock_llm.invoke.return_value = _fake_llm_response("First reply")
            client.post("/chat", json={"message": "First message"})

        with patch.object(flask_app, "llm_with_tools") as mock_llm:
            mock_llm.invoke.return_value = _fake_llm_response("Second reply")
            client.post("/chat", json={"message": "Second message"})

        # Only one session should exist
        self.assertEqual(len(flask_app.session_histories), 1)
        history = list(flask_app.session_histories.values())[0]
        # SystemMessage + 2x (HumanMessage + AIMessage) = 5 entries
        self.assertEqual(len(history), 5)

    # ------------------------------------------------------------------
    # 3. A new session starts with exactly one message (the system prompt)
    # ------------------------------------------------------------------
    def test_new_session_starts_with_only_system_prompt(self):
        # Verify the prompt builder produces the expected text (no mocking needed)
        prompt = flask_app._make_system_prompt()
        self.assertIn("scheduling assistant", prompt)
        self.assertIn("book_meeting", prompt)

        # Verify the history is initialised with exactly that one system message
        # before any user messages arrive, by inspecting how many entries exist
        # after a fresh session's first round-trip:
        # [SystemMessage, HumanMessage, AIMessage] → length 3
        client = flask_app.app.test_client()
        with patch.object(flask_app, "llm_with_tools") as mock_llm:
            mock_llm.invoke.return_value = _fake_llm_response()
            client.post("/chat", json={"message": "Hi"})

        history = list(flask_app.session_histories.values())[0]
        self.assertEqual(len(history), 3,
                         "Expected [SystemMessage, HumanMessage, AIMessage] after first turn")

    # ------------------------------------------------------------------
    # 4. Client A's messages are not visible in client B's history
    # ------------------------------------------------------------------
    def test_client_a_messages_not_in_client_b_history(self):
        """Histories are separate list objects; appending to one must not affect the other."""
        client_a = flask_app.app.test_client()
        client_b = flask_app.app.test_client()

        with patch.object(flask_app, "llm_with_tools") as mock_llm:
            mock_llm.invoke.return_value = _fake_llm_response()
            client_a.post("/chat", json={"message": "Hello from A"})
            client_a.post("/chat", json={"message": "Second from A"})

        with patch.object(flask_app, "llm_with_tools") as mock_llm:
            mock_llm.invoke.return_value = _fake_llm_response()
            client_b.post("/chat", json={"message": "Hello from B"})

        histories = list(flask_app.session_histories.values())
        self.assertEqual(len(histories), 2)

        # A had 2 turns → 5 messages; B had 1 turn → 3 messages (or vice-versa)
        lengths = sorted(len(h) for h in histories)
        self.assertEqual(lengths, [3, 5],
                         "Histories must be independent: A=5 entries, B=3 entries")

    # ------------------------------------------------------------------
    # 5. session_histories is keyed by UUID-format session IDs
    # ------------------------------------------------------------------
    def test_session_ids_are_uuid_format(self):
        import re
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        client = flask_app.app.test_client()

        with patch.object(flask_app, "llm_with_tools") as mock_llm:
            mock_llm.invoke.return_value = _fake_llm_response()
            client.post("/chat", json={"message": "hi"})

        for sid in flask_app.session_histories:
            self.assertRegex(sid, uuid_pattern, f"'{sid}' is not a valid UUID")


if __name__ == "__main__":
    unittest.main(verbosity=2)

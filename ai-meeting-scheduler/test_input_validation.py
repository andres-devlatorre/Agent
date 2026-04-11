"""
Tests for Gap 2: input validation on the /chat endpoint.

The LLM and calendar helpers are fully mocked so no API keys are needed.
"""
import sys
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub every external dependency before app.py is imported
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

    # langchain stubs
    fake_lc = MagicMock()
    for name in [
        "langchain_openai", "langchain_core", "langchain_core.messages",
        "langchain_core.tools",
    ]:
        sys.modules.setdefault(name, fake_lc)

_stub_modules()

# Patch ChatOpenAI and the @tool decorator before the module loads
with patch("langchain_openai.ChatOpenAI", MagicMock()), \
     patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):

    # Provide real message classes so chat_history works correctly
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    sys.modules["langchain_core.messages"].HumanMessage  = HumanMessage
    sys.modules["langchain_core.messages"].SystemMessage = SystemMessage
    sys.modules["langchain_core.messages"].AIMessage     = AIMessage

    import app as flask_app


class TestChatInputValidation(unittest.TestCase):

    def setUp(self):
        flask_app.app.config["TESTING"] = True
        self.client = flask_app.app.test_client()
        # Clear shared chat_history before each test
        flask_app.chat_history[:] = [flask_app.chat_history[0]]

    # ------------------------------------------------------------------
    # Bad / missing request body
    # ------------------------------------------------------------------
    def test_no_body_returns_400(self):
        resp = self.client.post("/chat", content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    def test_plain_text_body_returns_400(self):
        resp = self.client.post("/chat", data="hello", content_type="text/plain")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    def test_malformed_json_returns_400(self):
        resp = self.client.post("/chat", data="{bad json", content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    # ------------------------------------------------------------------
    # Missing or empty message field
    # ------------------------------------------------------------------
    def test_missing_message_field_returns_400(self):
        resp = self.client.post("/chat",
                                json={"other_key": "value"},
                                content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    def test_null_message_returns_400(self):
        resp = self.client.post("/chat",
                                json={"message": None},
                                content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_empty_string_message_returns_400(self):
        resp = self.client.post("/chat",
                                json={"message": ""},
                                content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_whitespace_only_message_returns_400(self):
        resp = self.client.post("/chat",
                                json={"message": "   "},
                                content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_non_string_message_returns_400(self):
        resp = self.client.post("/chat",
                                json={"message": 42},
                                content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    # ------------------------------------------------------------------
    # Valid message reaches the LLM (happy path)
    # ------------------------------------------------------------------
    def test_valid_message_calls_llm_and_returns_200(self):
        fake_response = MagicMock()
        fake_response.tool_calls = []
        fake_response.content = "Sure, who should I schedule with?"

        with patch.object(flask_app, "llm_with_tools") as mock_llm:
            mock_llm.invoke.return_value = fake_response
            resp = self.client.post("/chat", json={"message": "Book a meeting"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["reply"], "Sure, who should I schedule with?")
        mock_llm.invoke.assert_called_once()

    def test_leading_trailing_whitespace_is_stripped(self):
        """Whitespace around a valid message should be stripped before being sent to the LLM."""
        fake_response = MagicMock()
        fake_response.tool_calls = []
        fake_response.content = "Got it!"

        def make_human_msg(**kwargs):
            m = MagicMock()
            m.content = kwargs.get("content", "")
            return m

        with patch.object(flask_app, "llm_with_tools") as mock_llm, \
             patch.object(flask_app, "HumanMessage", side_effect=make_human_msg) as mock_hm:
            mock_llm.invoke.return_value = fake_response
            resp = self.client.post("/chat", json={"message": "  hello  "})

        self.assertEqual(resp.status_code, 200)
        mock_hm.assert_called_once_with(content="hello")

    # ------------------------------------------------------------------
    # Bad inputs must NOT corrupt chat_history
    # ------------------------------------------------------------------
    def test_invalid_request_does_not_append_to_chat_history(self):
        history_len_before = len(flask_app.chat_history)
        self.client.post("/chat", json={"message": ""})
        self.assertEqual(len(flask_app.chat_history), history_len_before)


if __name__ == "__main__":
    unittest.main(verbosity=2)

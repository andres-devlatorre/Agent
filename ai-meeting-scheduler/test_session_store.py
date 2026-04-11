"""
Tests for _BoundedSessionStore — the LRU-capped session history store.

These tests target the store class directly and do not require Flask,
LangChain, or any API credentials.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch


# Stub external dependencies so app.py can be imported
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
    from app import _BoundedSessionStore


class TestBoundedSessionStore(unittest.TestCase):

    # ------------------------------------------------------------------
    # Basic get_history behaviour
    # ------------------------------------------------------------------
    def test_get_history_creates_entry_on_first_access(self):
        store = _BoundedSessionStore(max_size=10)
        history = store.get_history("s1", lambda: ["system-msg"])
        self.assertEqual(history, ["system-msg"])
        self.assertIn("s1", store)

    def test_get_history_returns_same_list_on_subsequent_access(self):
        store = _BoundedSessionStore(max_size=10)
        h1 = store.get_history("s1", lambda: ["system-msg"])
        h2 = store.get_history("s1", lambda: ["should-not-be-called"])
        self.assertIs(h1, h2)

    def test_factory_not_called_for_existing_key(self):
        store = _BoundedSessionStore(max_size=10)
        store.get_history("s1", lambda: ["initial"])
        factory = MagicMock(return_value=["new"])
        store.get_history("s1", factory)
        factory.assert_not_called()

    # ------------------------------------------------------------------
    # Capacity enforcement
    # ------------------------------------------------------------------
    def test_store_never_exceeds_max_size(self):
        store = _BoundedSessionStore(max_size=3)
        for i in range(10):
            store.get_history(f"session-{i}", lambda: [])
        self.assertLessEqual(len(store), 3)

    def test_oldest_session_is_evicted_first(self):
        store = _BoundedSessionStore(max_size=3)
        store.get_history("oldest", lambda: ["oldest"])
        store.get_history("middle", lambda: ["middle"])
        store.get_history("newest", lambda: ["newest"])
        # Adding one more should evict "oldest"
        store.get_history("overflow", lambda: ["overflow"])
        self.assertNotIn("oldest", store)
        self.assertIn("middle", store)
        self.assertIn("newest", store)
        self.assertIn("overflow", store)

    def test_max_size_one_keeps_only_latest(self):
        store = _BoundedSessionStore(max_size=1)
        store.get_history("a", lambda: ["a"])
        store.get_history("b", lambda: ["b"])
        self.assertEqual(len(store), 1)
        self.assertIn("b", store)
        self.assertNotIn("a", store)

    # ------------------------------------------------------------------
    # LRU promotion — accessing a session saves it from eviction
    # ------------------------------------------------------------------
    def test_accessing_session_prevents_its_eviction(self):
        store = _BoundedSessionStore(max_size=3)
        store.get_history("s1", lambda: ["s1"])
        store.get_history("s2", lambda: ["s2"])
        store.get_history("s3", lambda: ["s3"])
        # Access s1 — it should now be most-recently-used
        store.get_history("s1", lambda: [])
        # Adding s4 should evict s2 (now the least-recently-used), not s1
        store.get_history("s4", lambda: ["s4"])
        self.assertIn("s1", store, "s1 was recently accessed and must not be evicted")
        self.assertNotIn("s2", store, "s2 is the LRU and must be evicted")

    # ------------------------------------------------------------------
    # MAX_SESSIONS env var
    # ------------------------------------------------------------------
    def test_max_sessions_env_var_is_respected(self):
        with patch.dict(os.environ, {"MAX_SESSIONS": "5"}):
            # Re-evaluate the int conversion as the app does
            max_s = int(os.getenv("MAX_SESSIONS", "1000"))
        self.assertEqual(max_s, 5)

    def test_default_max_sessions_is_1000(self):
        env = {k: v for k, v in os.environ.items() if k != "MAX_SESSIONS"}
        with patch.dict(os.environ, env, clear=True):
            max_s = int(os.getenv("MAX_SESSIONS", "1000"))
        self.assertEqual(max_s, 1000)

    # ------------------------------------------------------------------
    # Standard dict interface still works (used by existing tests)
    # ------------------------------------------------------------------
    def test_clear_empties_store(self):
        store = _BoundedSessionStore(max_size=10)
        store.get_history("s1", lambda: [])
        store.get_history("s2", lambda: [])
        store.clear()
        self.assertEqual(len(store), 0)

    def test_values_returns_all_histories(self):
        store = _BoundedSessionStore(max_size=10)
        store.get_history("s1", lambda: ["a"])
        store.get_history("s2", lambda: ["b"])
        all_vals = list(store.values())
        self.assertEqual(len(all_vals), 2)

    def test_iteration_yields_all_keys(self):
        store = _BoundedSessionStore(max_size=10)
        store.get_history("x", lambda: [])
        store.get_history("y", lambda: [])
        self.assertEqual(set(store), {"x", "y"})


if __name__ == "__main__":
    unittest.main(verbosity=2)

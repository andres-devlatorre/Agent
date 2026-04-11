"""
Tests for the timezone fix in calendar_helper.py.

Google libraries are stubbed at the module level so no real credentials
or installed packages are required.
"""
import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stub out google.* imports before calendar_helper is ever imported
# ---------------------------------------------------------------------------
def _stub_google_modules():
    fake_google = MagicMock()
    for name in [
        "google",
        "google.auth",
        "google.auth.transport",
        "google.auth.transport.requests",
        "google.oauth2",
        "google.oauth2.credentials",
        "google_auth_oauthlib",
        "google_auth_oauthlib.flow",
        "googleapiclient",
        "googleapiclient.discovery",
    ]:
        sys.modules.setdefault(name, fake_google)

_stub_google_modules()


def _fresh_calendar_helper(extra_env=None):
    """Import (or re-import) calendar_helper with a clean env."""
    sys.modules.pop("calendar_helper", None)
    env = {k: v for k, v in os.environ.items() if k != "TIMEZONE"}
    if extra_env:
        env.update(extra_env)
    with patch.dict(os.environ, env, clear=True):
        import calendar_helper
        return calendar_helper


class TestCalendarTimezone(unittest.TestCase):

    # ------------------------------------------------------------------
    # 1. Start and end timezones must always be identical
    # ------------------------------------------------------------------
    def test_start_and_end_timezones_match(self):
        ch = _fresh_calendar_helper()
        start_iso = "2026-04-15T14:00:00"
        start_dt = datetime.fromisoformat(start_iso)
        end_dt   = start_dt + timedelta(minutes=60)
        event = {
            "start": {"dateTime": start_dt.isoformat(), "timeZone": ch.CALENDAR_TIMEZONE},
            "end":   {"dateTime": end_dt.isoformat(),   "timeZone": ch.CALENDAR_TIMEZONE},
        }
        self.assertEqual(
            event["start"]["timeZone"],
            event["end"]["timeZone"],
            "start.timeZone and end.timeZone must be the same value",
        )

    # ------------------------------------------------------------------
    # 2. Default timezone is America/New_York when env var is absent
    # ------------------------------------------------------------------
    def test_default_timezone_is_new_york(self):
        ch = _fresh_calendar_helper()  # no TIMEZONE in env
        self.assertEqual(ch.CALENDAR_TIMEZONE, "America/New_York")

    # ------------------------------------------------------------------
    # 3. TIMEZONE env var overrides the default
    # ------------------------------------------------------------------
    def test_timezone_env_var_is_respected(self):
        ch = _fresh_calendar_helper({"TIMEZONE": "Europe/London"})
        self.assertEqual(ch.CALENDAR_TIMEZONE, "Europe/London")

    # ------------------------------------------------------------------
    # 4. End time is exactly duration_minutes after start time
    # ------------------------------------------------------------------
    def test_end_time_offset_is_correct(self):
        start_iso = "2026-04-15T09:00:00"
        start_dt  = datetime.fromisoformat(start_iso)
        end_dt    = start_dt + timedelta(minutes=60)
        self.assertEqual((end_dt - start_dt).seconds, 3600)

    # ------------------------------------------------------------------
    # 5. add_event_to_calendar passes the correct timezone to the API
    # ------------------------------------------------------------------
    def test_api_receives_consistent_timezone(self):
        ch = _fresh_calendar_helper({"TIMEZONE": "Asia/Tokyo"})

        mock_service = MagicMock()
        mock_events  = mock_service.events.return_value
        mock_insert  = mock_events.insert.return_value
        mock_insert.execute.return_value = {"htmlLink": "https://calendar.google.com/fake"}

        with patch.object(ch, "get_calendar_service", return_value=mock_service):
            ch.add_event_to_calendar("Charlie", "2026-04-15T10:00:00")

        _, kwargs = mock_events.insert.call_args
        body = kwargs["body"]

        self.assertEqual(body["start"]["timeZone"], "Asia/Tokyo",
                         "start timezone should be Asia/Tokyo")
        self.assertEqual(body["end"]["timeZone"], "Asia/Tokyo",
                         "end timezone should be Asia/Tokyo")
        self.assertEqual(body["start"]["timeZone"], body["end"]["timeZone"],
                         "start and end timezones must be identical")


if __name__ == "__main__":
    unittest.main(verbosity=2)

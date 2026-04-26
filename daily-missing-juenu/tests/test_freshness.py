"""Tests for the freshness gate (check_freshness + record-sent rejection)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import store  # noqa: E402


def _tiktok_url_for(posted_at: datetime) -> str:
    """Synthesize a TikTok URL whose ID decodes to posted_at."""
    ts = int(posted_at.timestamp())
    vid = (ts << 32) | 0xDEADBEEF
    return f"https://www.tiktok.com/@synth/video/{vid}"


class TestCheckFreshness(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 4, 24, 12, 0, 0, tzinfo=timezone.utc)

    # ---- TikTok: posted_at auto-derived ----

    def test_fresh_tiktok_today(self) -> None:
        url = _tiktok_url_for(self.now - timedelta(hours=1))
        status, _, _ = store.check_freshness(url, max_age_days=3, now=self.now)
        self.assertEqual(status, store.FRESH)

    def test_fresh_tiktok_right_at_the_boundary(self) -> None:
        # Exactly 2 days ago — well inside 3-day window
        url = _tiktok_url_for(self.now - timedelta(days=2))
        status, _, _ = store.check_freshness(url, max_age_days=3, now=self.now)
        self.assertEqual(status, store.FRESH)

    def test_stale_tiktok_beyond_window(self) -> None:
        url = _tiktok_url_for(self.now - timedelta(days=5))
        status, effective, reason = store.check_freshness(url, max_age_days=3, now=self.now)
        self.assertEqual(status, store.STALE)
        self.assertIsNotNone(effective)
        self.assertIn("5.0d ago", reason)

    def test_stale_real_known_video(self) -> None:
        """Real URL from the sent-log, 38 days before our fake 'now'."""
        url = "https://www.tiktok.com/@duoayo/video/7618242851331230984"
        status, _, _ = store.check_freshness(url, max_age_days=3, now=self.now)
        self.assertEqual(status, store.STALE)

    # ---- non-TikTok: posted_at must be supplied ----

    def test_unknown_when_non_tiktok_without_posted_at(self) -> None:
        status, eff, reason = store.check_freshness(
            "https://www.youtube.com/watch?v=abc",
            max_age_days=3,
            now=self.now,
        )
        self.assertEqual(status, store.UNKNOWN)
        self.assertIsNone(eff)
        self.assertIn("posted_at", reason)

    def test_fresh_non_tiktok_with_recent_posted_at(self) -> None:
        status, _, _ = store.check_freshness(
            "https://www.instagram.com/p/abc/",
            posted_at=self.now - timedelta(hours=6),
            max_age_days=3,
            now=self.now,
        )
        self.assertEqual(status, store.FRESH)

    def test_stale_non_tiktok_with_old_posted_at(self) -> None:
        status, _, reason = store.check_freshness(
            "https://www.youtube.com/watch?v=abc",
            posted_at=self.now - timedelta(days=10),
            max_age_days=3,
            now=self.now,
        )
        self.assertEqual(status, store.STALE)
        self.assertIn("10.0d ago", reason)

    # ---- naive datetime handling ----

    def test_naive_posted_at_treated_as_utc(self) -> None:
        naive = datetime(2026, 4, 24, 0, 0, 0)  # no tzinfo
        status, effective, _ = store.check_freshness(
            "https://www.youtube.com/watch?v=abc",
            posted_at=naive,
            max_age_days=3,
            now=self.now,
        )
        self.assertEqual(status, store.FRESH)
        self.assertIsNotNone(effective.tzinfo)


class TestRecordSentGate(unittest.TestCase):
    """record_sent must refuse stale / unknown candidates."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self._orig = {k: getattr(store, k) for k in
                      ("SENT_LOG", "FAN_ACCOUNTS", "OPENERS", "STATE", "DATA_DIR")}
        store.DATA_DIR = self.tmp
        store.SENT_LOG = self.tmp / "sent-log.yaml"
        store.FAN_ACCOUNTS = self.tmp / "fan-accounts.yaml"
        store.OPENERS = self.tmp / "openers.yaml"
        store.STATE = self.tmp / "state.yaml"
        self.addCleanup(lambda: [setattr(store, k, v) for k, v in self._orig.items()])

    def test_rejects_stale_tiktok(self) -> None:
        url = "https://www.tiktok.com/@x/video/7618242851331230984"  # March 2026
        with self.assertRaises(store.FreshnessRejected) as cm:
            store.record_sent(url=url, handle="x", platform="tiktok", max_age_days=3)
        self.assertEqual(cm.exception.status, store.STALE)
        self.assertFalse(store.is_sent(url))

    def test_rejects_non_tiktok_without_posted_at(self) -> None:
        with self.assertRaises(store.FreshnessRejected) as cm:
            store.record_sent(
                url="https://www.youtube.com/watch?v=abc",
                handle="x",
                platform="youtube",
                max_age_days=3,
            )
        self.assertEqual(cm.exception.status, store.UNKNOWN)

    def test_accepts_fresh_tiktok(self) -> None:
        now = datetime.now(tz=timezone.utc)
        url = _tiktok_url_for(now - timedelta(hours=2))
        entry = store.record_sent(url=url, handle="x", platform="tiktok", max_age_days=3)
        self.assertEqual(entry["url"], url)
        self.assertTrue(store.is_sent(url))

    def test_accepts_fresh_non_tiktok_with_posted_at(self) -> None:
        now = datetime.now(tz=timezone.utc)
        entry = store.record_sent(
            url="https://www.youtube.com/watch?v=fresh1",
            handle="x",
            platform="youtube",
            posted_at=now - timedelta(hours=6),
            max_age_days=3,
        )
        self.assertEqual(entry["url"], "https://www.youtube.com/watch?v=fresh1")

    def test_skip_freshness_bypass(self) -> None:
        """Escape hatch for backfill / migration scripts."""
        old_url = "https://www.tiktok.com/@x/video/7618242851331230984"
        entry = store.record_sent(url=old_url, handle="x", platform="tiktok", skip_freshness=True)
        self.assertEqual(entry["url"], old_url)


if __name__ == "__main__":
    unittest.main()

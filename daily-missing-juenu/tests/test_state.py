"""Tests for the last_run_at / since-filter and TikTok ID decoding.

Run with:  python -m unittest discover -s tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import store  # noqa: E402


class _TempStoreBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

        self._orig = {
            "SENT_LOG": store.SENT_LOG,
            "FAN_ACCOUNTS": store.FAN_ACCOUNTS,
            "OPENERS": store.OPENERS,
            "STATE": store.STATE,
            "DATA_DIR": store.DATA_DIR,
        }
        store.DATA_DIR = self.tmp
        store.SENT_LOG = self.tmp / "sent-log.yaml"
        store.FAN_ACCOUNTS = self.tmp / "fan-accounts.yaml"
        store.OPENERS = self.tmp / "openers.yaml"
        store.STATE = self.tmp / "state.yaml"
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        for k, v in self._orig.items():
            setattr(store, k, v)


# ---------- last_run_at / state ----------

class TestLastRunAt(_TempStoreBase):
    def test_empty_returns_none(self) -> None:
        self.assertIsNone(store.last_run_at())

    def test_mark_and_read_roundtrip(self) -> None:
        fixed = datetime(2026, 4, 20, 12, 0, 0, tzinfo=timezone.utc)
        store.mark_run_complete(fixed)
        got = store.last_run_at()
        self.assertEqual(got, fixed)

    def test_malformed_value_returns_none(self) -> None:
        store.STATE.write_text("last_run_at: 'not a date'\n", encoding="utf-8")
        self.assertIsNone(store.last_run_at())

    def test_non_mapping_raises(self) -> None:
        store.STATE.write_text("- oops, list\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            store.get_state()


class TestSinceOrDefault(_TempStoreBase):
    def test_uses_last_run_at_when_present(self) -> None:
        fixed = datetime(2026, 4, 20, 12, 0, 0, tzinfo=timezone.utc)
        store.mark_run_complete(fixed)
        self.assertEqual(store.since_or_default("7d"), fixed)

    def test_falls_back_to_default_when_empty(self) -> None:
        got = store.since_or_default("7d")
        # Should be roughly 7 days before now.
        expected = datetime.now().astimezone() - timedelta(days=7)
        # Allow a loose window — we're computing date boundary, not wall-clock.
        self.assertLess(abs((got - expected).total_seconds()), 86400 * 2)

    def test_no_default_returns_epoch(self) -> None:
        got = store.since_or_default(None)
        self.assertEqual(got, datetime.fromtimestamp(0, tz=timezone.utc))


class TestRecordSentAdvancesState(_TempStoreBase):
    def test_record_sent_sets_last_run_at(self) -> None:
        self.assertIsNone(store.last_run_at())
        store.record_sent(skip_freshness=True, url="u1", handle="h", platform="tiktok", country="KR", opener="o")
        after = store.last_run_at()
        self.assertIsNotNone(after)
        # It should be very recent.
        self.assertLess((datetime.now().astimezone() - after).total_seconds(), 5)


# ---------- TikTok ID → datetime ----------

class TestTiktokCreatedAt(unittest.TestCase):
    def test_decode_known_id(self) -> None:
        # 7613638874778094869 >> 32 = 1773204579 = 2026-03-05 05:27:19 UTC
        got = store.tiktok_created_at(7613638874778094869)
        self.assertEqual(got, datetime(2026, 3, 5, 5, 27, 19, tzinfo=timezone.utc))

    def test_decode_url(self) -> None:
        url = "https://www.tiktok.com/@duoayo/video/7618242851331230984"
        got = store.tiktok_created_at(url)
        # 7618242851331230984 >> 32 = 1774102386 = 2026-03-17 15:13:06 UTC
        self.assertEqual(got, datetime(2026, 3, 17, 15, 13, 6, tzinfo=timezone.utc))

    def test_decode_numeric_string(self) -> None:
        got = store.tiktok_created_at("7613638874778094869")
        self.assertIsNotNone(got)

    def test_non_tiktok_url_returns_none(self) -> None:
        self.assertIsNone(store.tiktok_created_at("https://www.youtube.com/watch?v=abc123"))
        self.assertIsNone(store.tiktok_created_at("https://www.instagram.com/p/xyz/"))

    def test_chronological_ordering_matches_id_ordering(self) -> None:
        """The whole point of this feature — bigger ID = later timestamp."""
        older = store.tiktok_created_at(7613638874778094869)
        newer = store.tiktok_created_at(7618242851331230984)
        self.assertLess(older, newer)

    def test_parse_tiktok_video_id(self) -> None:
        self.assertEqual(
            store.parse_tiktok_video_id("https://www.tiktok.com/@x/video/7612232083817106706"),
            7612232083817106706,
        )
        self.assertIsNone(store.parse_tiktok_video_id("https://youtube.com/watch?v=abc"))


if __name__ == "__main__":
    unittest.main()

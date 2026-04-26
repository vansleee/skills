"""Tests for scripts/store.py.

Each test uses a throw-away temp directory so we never touch real data.
Run with:  python -m unittest discover -s tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import store  # noqa: E402


class _TempStoreBase(unittest.TestCase):
    """Redirect the three module-level Path constants at a temp directory.

    Each subclass gets a clean slate per test method.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

        self._orig = {
            "SENT_LOG": store.SENT_LOG,
            "FAN_ACCOUNTS": store.FAN_ACCOUNTS,
            "OPENERS": store.OPENERS,
            "DATA_DIR": store.DATA_DIR,
        }
        store.DATA_DIR = self.tmp
        store.SENT_LOG = self.tmp / "sent-log.yaml"
        store.FAN_ACCOUNTS = self.tmp / "fan-accounts.yaml"
        store.OPENERS = self.tmp / "openers.yaml"
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        for k, v in self._orig.items():
            setattr(store, k, v)

    def _write_yaml(self, path: Path, data) -> None:
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


# ---------------- parse_since ----------------

class TestParseSince(unittest.TestCase):
    def test_days(self) -> None:
        got = store.parse_since("7d")
        self.assertEqual(got, date.today() - timedelta(days=7))

    def test_weeks(self) -> None:
        self.assertEqual(store.parse_since("2w"), date.today() - timedelta(days=14))

    def test_months_thirty_day_shorthand(self) -> None:
        self.assertEqual(store.parse_since("1m"), date.today() - timedelta(days=30))

    def test_iso_date(self) -> None:
        self.assertEqual(store.parse_since("2026-03-25"), date(2026, 3, 25))

    def test_none_and_empty(self) -> None:
        self.assertIsNone(store.parse_since(None))
        self.assertIsNone(store.parse_since(""))

    def test_bad_value_raises(self) -> None:
        with self.assertRaises(ValueError):
            store.parse_since("banana")


# ---------------- sent-log ----------------

class TestSentLog(_TempStoreBase):
    def _seed(self) -> None:
        self._write_yaml(store.SENT_LOG, [
            {"date": "2026-03-20", "url": "u1", "handle": "a", "platform": "tiktok", "country": "KR", "opener": "o1"},
            {"date": "2026-03-24", "url": "u2", "handle": "b", "platform": "tiktok", "country": "KR", "opener": "o2"},
            {"date": "2026-03-25", "url": "u3", "handle": "a", "platform": "tiktok", "country": "KR", "opener": "o3"},
        ])

    def test_sent_list_empty(self) -> None:
        self.assertEqual(store.sent_list(), [])

    def test_sent_list_sorted_newest_first(self) -> None:
        self._seed()
        rows = store.sent_list()
        self.assertEqual([r["url"] for r in rows], ["u3", "u2", "u1"])

    def test_sent_list_since_filter(self) -> None:
        self._seed()
        rows = store.sent_list(since="2026-03-24")
        self.assertEqual({r["url"] for r in rows}, {"u2", "u3"})

    def test_sent_list_handle_filter(self) -> None:
        self._seed()
        rows = store.sent_list(handle="a")
        self.assertEqual({r["url"] for r in rows}, {"u1", "u3"})

    def test_sent_list_limit(self) -> None:
        self._seed()
        rows = store.sent_list(limit=2)
        self.assertEqual(len(rows), 2)

    def test_is_sent(self) -> None:
        self._seed()
        self.assertTrue(store.is_sent("u2"))
        self.assertFalse(store.is_sent("u999"))

    def test_record_sent_happy_path(self) -> None:
        entry = store.record_sent(
            skip_freshness=True,
            url="new",
            handle="h",
            platform="tiktok",
            country="KR",
            opener="opener line",
            date_str="2026-04-24",
        )
        self.assertEqual(entry["url"], "new")
        self.assertTrue(store.is_sent("new"))

    def test_record_sent_autobumps_account(self) -> None:
        """Recording a sent video should also create/bump the account row."""
        store.record_sent(skip_freshness=True, url="new", handle="fresh_handle", platform="youtube", country="TW", opener="o")
        accts = store.accounts_list()
        handles = {a["handle"] for a in accts}
        self.assertIn("fresh_handle", handles)
        new_acct = next(a for a in accts if a["handle"] == "fresh_handle")
        self.assertEqual(new_acct["platform"], "youtube")
        self.assertEqual(new_acct["country"], "TW")
        self.assertEqual(new_acct["hit_count"], 1)

    def test_record_sent_dedupe_raises(self) -> None:
        store.record_sent(skip_freshness=True, url="dup", handle="h")
        with self.assertRaises(ValueError):
            store.record_sent(skip_freshness=True, url="dup", handle="h")

    def test_last_opener_empty(self) -> None:
        self.assertIsNone(store.last_opener())

    def test_last_opener_returns_most_recent(self) -> None:
        self._seed()
        self.assertEqual(store.last_opener(), "o3")

    def test_recent_openers(self) -> None:
        self._seed()
        self.assertEqual(store.recent_openers(2), ["o3", "o2"])
        self.assertEqual(store.recent_openers(10), ["o3", "o2", "o1"])

    def test_recent_openers_skips_null(self) -> None:
        """Rows with opener=None shouldn't pollute the recent-openers list."""
        self._write_yaml(store.SENT_LOG, [
            {"date": "2026-03-25", "url": "u1", "handle": "a", "opener": None},
            {"date": "2026-03-24", "url": "u2", "handle": "a", "opener": "has opener"},
        ])
        self.assertEqual(store.recent_openers(5), ["has opener"])


# ---------------- fan accounts ----------------

class TestFanAccounts(_TempStoreBase):
    def _seed(self) -> None:
        self._write_yaml(store.FAN_ACCOUNTS, [
            {"handle": "a", "platform": "tiktok", "country": "KR", "hit_count": 5, "last_seen": "2026-03-01", "active": True, "notes": None},
            {"handle": "b", "platform": "tiktok", "country": "KR", "hit_count": 3, "last_seen": "2026-03-20", "active": True, "notes": None},
            {"handle": "c", "platform": "youtube", "country": "TW", "hit_count": 0, "last_seen": None, "active": False, "notes": None},
        ])

    def test_list_sorted_by_hit_count_then_last_seen(self) -> None:
        self._seed()
        accts = store.accounts_list()
        self.assertEqual([a["handle"] for a in accts], ["a", "b", "c"])

    def test_active_filter(self) -> None:
        self._seed()
        accts = store.accounts_list(active_only=True)
        self.assertEqual({a["handle"] for a in accts}, {"a", "b"})

    def test_platform_filter(self) -> None:
        self._seed()
        accts = store.accounts_list(platform="youtube")
        self.assertEqual({a["handle"] for a in accts}, {"c"})

    def test_limit(self) -> None:
        self._seed()
        accts = store.accounts_list(limit=1)
        self.assertEqual([a["handle"] for a in accts], ["a"])

    def test_bump_existing(self) -> None:
        self._seed()
        updated = store.bump_account("b", seen="2026-04-01")
        self.assertEqual(updated["hit_count"], 4)
        self.assertEqual(updated["last_seen"], "2026-04-01")

    def test_bump_fills_missing_fields(self) -> None:
        self._write_yaml(store.FAN_ACCOUNTS, [
            {"handle": "x", "platform": None, "country": None, "hit_count": 2, "last_seen": "2026-03-01", "active": True, "notes": None},
        ])
        updated = store.bump_account("x", platform="tiktok", country="JP", seen="2026-04-01")
        self.assertEqual(updated["platform"], "tiktok")
        self.assertEqual(updated["country"], "JP")

    def test_bump_creates_new_when_missing(self) -> None:
        updated = store.bump_account("brand_new", platform="instagram", country="US")
        self.assertEqual(updated["handle"], "brand_new")
        self.assertEqual(updated["platform"], "instagram")
        self.assertEqual(updated["hit_count"], 1)
        self.assertTrue(updated["active"])

    def test_add_account_happy(self) -> None:
        row = store.add_account("new", platform="threads", country="KR", notes="manual")
        self.assertEqual(row["handle"], "new")
        self.assertEqual(row["hit_count"], 0)
        self.assertIsNone(row["last_seen"])
        self.assertEqual(row["notes"], "manual")

    def test_add_account_dedupe_raises(self) -> None:
        store.add_account("new")
        with self.assertRaises(ValueError):
            store.add_account("new")


# ---------------- openers ----------------

class TestOpeners(_TempStoreBase):
    def _seed_pool(self, items) -> None:
        self._write_yaml(store.OPENERS, items)

    def test_openers_list_empty(self) -> None:
        self.assertEqual(store.openers_list(), [])

    def test_openers_list_returns_strings(self) -> None:
        self._seed_pool(["a", "b", "c"])
        self.assertEqual(store.openers_list(), ["a", "b", "c"])

    def test_add_opener(self) -> None:
        self._seed_pool(["a", "b"])
        pool = store.add_opener("c")
        self.assertEqual(pool, ["a", "b", "c"])
        self.assertEqual(store.openers_list(), ["a", "b", "c"])

    def test_add_opener_dedupe_raises(self) -> None:
        self._seed_pool(["a"])
        with self.assertRaises(ValueError):
            store.add_opener("a")

    def test_pick_opener_empty_raises(self) -> None:
        with self.assertRaises(ValueError):
            store.pick_opener()

    def test_pick_opener_avoids_last(self) -> None:
        """With only one history entry, pick_opener(avoid_last=1) should never
        return that opener across many tries."""
        self._seed_pool(["a", "b", "c", "d"])
        self._write_yaml(store.SENT_LOG, [
            {"date": "2026-03-25", "url": "u1", "handle": "h", "opener": "b"},
        ])
        for _ in range(50):
            picked, avoided = store.pick_opener(avoid_last=1)
            self.assertNotEqual(picked, "b")
            self.assertEqual(avoided, ["b"])

    def test_pick_opener_falls_back_when_all_avoided(self) -> None:
        """If the avoid set would leave the pool empty, we fall back to the
        full pool rather than raising (better to repeat than to fail)."""
        self._seed_pool(["a"])
        self._write_yaml(store.SENT_LOG, [
            {"date": "2026-03-25", "url": "u1", "handle": "h", "opener": "a"},
        ])
        picked, _ = store.pick_opener(avoid_last=1)
        self.assertEqual(picked, "a")


if __name__ == "__main__":
    unittest.main()

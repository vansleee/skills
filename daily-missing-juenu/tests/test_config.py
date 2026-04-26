"""Tests for scripts/config.py.

Uses stdlib unittest so there are no extra dependencies beyond pyyaml.
Run with:  python -m unittest discover -s tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import config as cfg  # noqa: E402


class TestConfig(unittest.TestCase):
    """config.load() uses lru_cache, so we have to clear it per-test when we
    swap out CONFIG_PATH. Not pretty, but local to tests."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmpdir = Path(self._tmp.name)

        # Swap CONFIG_PATH for a temp file and clear the cache.
        self._orig_path = cfg.CONFIG_PATH
        cfg.CONFIG_PATH = self.tmpdir / "config.yaml"
        cfg.load.cache_clear()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        cfg.CONFIG_PATH = self._orig_path
        cfg.load.cache_clear()

    def _write(self, obj) -> None:
        cfg.CONFIG_PATH.write_text(yaml.safe_dump(obj, allow_unicode=True), encoding="utf-8")
        cfg.load.cache_clear()

    # ---- load ----

    def test_load_returns_parsed_mapping(self) -> None:
        self._write({"a": 1, "b": {"c": "hi"}})
        data = cfg.load()
        self.assertEqual(data["a"], 1)
        self.assertEqual(data["b"]["c"], "hi")

    def test_load_missing_file_raises(self) -> None:
        # no _write → file doesn't exist
        with self.assertRaises(FileNotFoundError):
            cfg.load()

    def test_load_non_mapping_raises(self) -> None:
        cfg.CONFIG_PATH.write_text("- just a list\n", encoding="utf-8")
        cfg.load.cache_clear()
        with self.assertRaises(ValueError):
            cfg.load()

    # ---- get ----

    def test_get_dotted_path(self) -> None:
        self._write({"slack": {"sender": {"label": "Alice"}}})
        self.assertEqual(cfg.get("slack", "sender", "label"), "Alice")

    def test_get_missing_returns_default(self) -> None:
        self._write({"a": 1})
        self.assertIsNone(cfg.get("x", "y"))
        self.assertEqual(cfg.get("x", "y", default="fallback"), "fallback")

    def test_get_partial_hit_returns_default(self) -> None:
        # path runs into a non-dict before consuming all keys
        self._write({"a": "not a dict"})
        self.assertIsNone(cfg.get("a", "b"))

    # ---- convenience accessors ----

    def test_convenience_accessors(self) -> None:
        self._write({
            "message": {"video_count": 5, "intro_template": "T", "fallback_prefix": "P"},
            "slack": {
                "sender": {"label": "S", "user_id": "UX"},
                "recipient": {"label": "R", "dm_channel": "DX"},
            },
            "search": {"keywords": {"ko": ["a", "b"], "zh": ["c"]}},
        })
        self.assertEqual(cfg.video_count(), 5)
        self.assertEqual(cfg.sender_label(), "S")
        self.assertEqual(cfg.sender_user_id(), "UX")
        self.assertEqual(cfg.recipient_label(), "R")
        self.assertEqual(cfg.recipient_dm(), "DX")
        self.assertEqual(cfg.intro_template(), "T")
        self.assertEqual(cfg.fallback_prefix(), "P")
        self.assertEqual(cfg.search_keywords(), {"ko": ["a", "b"], "zh": ["c"]})

    def test_video_count_defaults_when_missing(self) -> None:
        self._write({"message": {}})
        self.assertEqual(cfg.video_count(), 3)

    def test_search_keywords_returns_empty_dict_when_missing(self) -> None:
        self._write({})
        self.assertEqual(cfg.search_keywords(), {})


if __name__ == "__main__":
    unittest.main()

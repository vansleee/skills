"""Smoke tests for scripts/tools.py — the CLI wiring.

Invokes tools.py as a subprocess and checks exit codes + stdout shape. This
catches argparse misconfiguration, missing sub-commands, and import errors
that the pure-Python tests (test_store, test_config) would miss.

We don't exhaustively re-test store.py's behavior here — just enough to
verify the CLI forwards correctly.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "scripts" / "tools.py"


def _run(args: list[str], env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(TOOLS), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


class TestCLISmoke(unittest.TestCase):
    """These tests hit the real data/ files but only via read commands."""

    def test_help_exits_zero(self) -> None:
        r = _run(["--help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("config-show", r.stdout)
        self.assertIn("is-sent", r.stdout)
        self.assertIn("pick-opener", r.stdout)

    def test_config_show_emits_json(self) -> None:
        r = _run(["config-show", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertIn("slack", data)
        self.assertIn("message", data)

    def test_config_get_dotted_path(self) -> None:
        r = _run(["config-get", "slack.sender.label"])
        self.assertEqual(r.returncode, 0, r.stderr)
        # Whatever the config says, it should be a non-empty line.
        self.assertTrue(r.stdout.strip())

    def test_config_get_missing_exits_nonzero(self) -> None:
        r = _run(["config-get", "does.not.exist"])
        self.assertNotEqual(r.returncode, 0)

    def test_list_accounts_json(self) -> None:
        r = _run(["list-accounts", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = json.loads(r.stdout)
        self.assertIsInstance(rows, list)
        if rows:
            self.assertIn("handle", rows[0])

    def test_is_sent_exit_codes(self) -> None:
        """exit 0 for a known sent URL, 1 for an obvious non-match.

        Reads the first URL out of sent-log.yaml if possible, skips otherwise.
        """
        sent_log = ROOT / "data" / "sent-log.yaml"
        if not sent_log.exists():
            self.skipTest("no sent-log.yaml present")
        rows = yaml.safe_load(sent_log.read_text(encoding="utf-8")) or []
        if not rows:
            self.skipTest("sent-log is empty")
        known = rows[0]["url"]

        r_hit = _run(["is-sent", known])
        self.assertEqual(r_hit.returncode, 0)

        r_miss = _run(["is-sent", "https://example.invalid/definitely-not-here"])
        self.assertEqual(r_miss.returncode, 1)

    def test_unknown_subcommand_fails(self) -> None:
        r = _run(["no-such-command"])
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()

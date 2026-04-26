"""Config loader for daily-missing-juenu.

`config.yaml` lives at the skill root. This module reads it once and exposes
a typed-ish view (plain nested dict). Callers should go through `load()`
rather than opening the YAML themselves so future schema changes have one
chokepoint.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

SKILL_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_ROOT / "config.yaml"


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    """Return the parsed config.yaml. Cached; safe to call repeatedly."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("config.yaml must be a YAML mapping at the top level")
    return data


def get(*path: str, default: Any = None) -> Any:
    """Dotted-path getter, e.g. get('slack', 'sender', 'label')."""
    node: Any = load()
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


# Convenience accessors used throughout the codebase. Centralizing these
# means renaming a config key only touches this file.

def video_count() -> int:
    return int(get("message", "video_count", default=3))


def max_age_days() -> int:
    return int(get("message", "max_age_days", default=3))


def sender_label() -> str:
    return str(get("slack", "sender", "label", default="sender"))


def sender_user_id() -> str:
    return str(get("slack", "sender", "user_id", default=""))


def recipient_label() -> str:
    return str(get("slack", "recipient", "label", default="recipient"))


def recipient_dm() -> str:
    return str(get("slack", "recipient", "dm_channel", default=""))


def intro_template() -> str:
    return str(get("message", "intro_template", default="{count} videos:"))


def fallback_prefix() -> str:
    return str(get("message", "fallback_prefix", default=""))


def search_keywords() -> dict[str, list[str]]:
    kws = get("search", "keywords", default={}) or {}
    return {lang: list(v or []) for lang, v in kws.items()}

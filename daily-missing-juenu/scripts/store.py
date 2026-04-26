"""YAML-backed data stores for daily-missing-juenu.

Three stores live under `data/`:
  - sent-log.yaml       List of videos already drafted/sent. Dedupe source.
  - fan-accounts.yaml   Watchlist of fan accounts ranked by hit_count.
  - openers.yaml        Opener phrase pool.

All reads/writes go through this module so schema changes touch one file.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from . import config as cfg  # type: ignore[import-not-found]

DATA_DIR = cfg.SKILL_ROOT / "data"
SENT_LOG = DATA_DIR / "sent-log.yaml"
FAN_ACCOUNTS = DATA_DIR / "fan-accounts.yaml"
OPENERS = DATA_DIR / "openers.yaml"
STATE = DATA_DIR / "state.yaml"


# ---------- low-level I/O ----------

def _load_list(path: Path) -> list:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise ValueError(f"{path} must be a YAML list, got {type(data).__name__}")
    return data


def _dump_list(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            rows,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=100,
        )


def _load_mapping(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a YAML mapping, got {type(data).__name__}")
    return data


def _dump_mapping(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _today() -> str:
    return date.today().isoformat()


def _row_date(row: dict) -> date | None:
    v = row.get("date")
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def parse_since(spec: str | None) -> date | None:
    """Accepts '30d', '6w', '3m', or ISO date 'YYYY-MM-DD'."""
    if not spec:
        return None
    import re
    m = re.fullmatch(r"(\d+)([dwm])", spec)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        days = {"d": 1, "w": 7, "m": 30}[unit] * n
        return date.today() - timedelta(days=days)
    try:
        return datetime.strptime(spec, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"bad --since value: {spec!r}")


# ---------- sent-log ----------

def sent_list(
    since: str | None = None,
    handle: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    rows = _load_list(SENT_LOG)
    cutoff = parse_since(since)
    if cutoff:
        rows = [r for r in rows if (d := _row_date(r)) and d >= cutoff]
    if handle:
        rows = [r for r in rows if r.get("handle") == handle]
    rows.sort(key=lambda r: (r.get("date", ""), r.get("url", "")), reverse=True)
    if limit:
        rows = rows[:limit]
    return rows


def is_sent(url: str) -> bool:
    return any(r.get("url") == url for r in _load_list(SENT_LOG))


class FreshnessRejected(Exception):
    """Raised by record_sent when the candidate fails the freshness gate."""

    def __init__(self, status: str, reason: str):
        super().__init__(f"{status}: {reason}")
        self.status = status
        self.reason = reason


def record_sent(
    url: str,
    handle: str,
    platform: str = "tiktok",
    country: str | None = None,
    opener: str | None = None,
    date_str: str | None = None,
    posted_at: datetime | None = None,
    max_age_days: int | None = None,
    skip_freshness: bool = False,
) -> dict:
    rows = _load_list(SENT_LOG)
    if any(r.get("url") == url for r in rows):
        raise ValueError(f"already sent: {url}")

    # Freshness gate — refuses stale or unverifiable candidates.
    if not skip_freshness:
        status, _, reason = check_freshness(url, posted_at=posted_at, max_age_days=max_age_days)
        if status != FRESH:
            raise FreshnessRejected(status, reason)

    entry = {
        "date": date_str or _today(),
        "url": url,
        "handle": handle,
        "platform": platform,
        "country": country,
        "opener": opener,
    }
    rows.append(entry)
    _dump_list(SENT_LOG, rows)
    bump_account(handle, platform=platform, country=country, seen=entry["date"])
    # Advance last_run_at so the next run's "since" filter excludes this one.
    mark_run_complete()
    return entry


def last_opener() -> str | None:
    rows = _load_list(SENT_LOG)
    rows = [r for r in rows if r.get("opener")]
    rows.sort(key=lambda r: (r.get("date", ""), r.get("url", "")), reverse=True)
    return rows[0]["opener"] if rows else None


def recent_openers(n: int) -> list[str]:
    rows = _load_list(SENT_LOG)
    rows = [r for r in rows if r.get("opener")]
    rows.sort(key=lambda r: (r.get("date", ""), r.get("url", "")), reverse=True)
    return [r["opener"] for r in rows[:n]]


# ---------- fan accounts ----------

def accounts_list(
    active_only: bool = False,
    platform: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    accts = _load_list(FAN_ACCOUNTS)
    if active_only:
        accts = [a for a in accts if a.get("active", True)]
    if platform:
        accts = [a for a in accts if a.get("platform") == platform]
    accts.sort(
        key=lambda a: (int(a.get("hit_count", 0)), str(a.get("last_seen") or "")),
        reverse=True,
    )
    if limit:
        accts = accts[:limit]
    return accts


def bump_account(
    handle: str,
    platform: str | None = None,
    country: str | None = None,
    seen: str | None = None,
) -> dict:
    accts = _load_list(FAN_ACCOUNTS)
    seen = seen or _today()
    for a in accts:
        if a.get("handle") == handle:
            a["hit_count"] = int(a.get("hit_count", 0)) + 1
            a["last_seen"] = seen
            if platform and not a.get("platform"):
                a["platform"] = platform
            if country and not a.get("country"):
                a["country"] = country
            _dump_list(FAN_ACCOUNTS, accts)
            return a
    new = {
        "handle": handle,
        "platform": platform or "tiktok",
        "country": country,
        "hit_count": 1,
        "last_seen": seen,
        "active": True,
        "notes": None,
    }
    accts.append(new)
    _dump_list(FAN_ACCOUNTS, accts)
    return new


def add_account(
    handle: str,
    platform: str | None = None,
    country: str | None = None,
    notes: str | None = None,
) -> dict:
    accts = _load_list(FAN_ACCOUNTS)
    if any(a.get("handle") == handle for a in accts):
        raise ValueError(f"already exists: {handle}")
    new = {
        "handle": handle,
        "platform": platform or "tiktok",
        "country": country,
        "hit_count": 0,
        "last_seen": None,
        "active": True,
        "notes": notes,
    }
    accts.append(new)
    _dump_list(FAN_ACCOUNTS, accts)
    return new


# ---------- openers ----------

def openers_list() -> list[str]:
    if not OPENERS.exists():
        return []
    with OPENERS.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise ValueError(f"{OPENERS} must be a YAML list of strings")
    return [str(s) for s in data if s]


def add_opener(text: str) -> list[str]:
    pool = openers_list()
    if text in pool:
        raise ValueError(f"already present: {text}")
    pool.append(text)
    OPENERS.parent.mkdir(parents=True, exist_ok=True)
    with OPENERS.open("w", encoding="utf-8") as f:
        yaml.safe_dump(pool, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return pool


def pick_opener(avoid_last: int = 1) -> tuple[str, list[str]]:
    """Return (picked_opener, openers_that_were_avoided)."""
    import random
    pool = openers_list()
    if not pool:
        raise ValueError("openers.yaml is empty")
    avoided = set(recent_openers(avoid_last))
    candidates = [o for o in pool if o not in avoided] or pool
    return random.choice(candidates), sorted(avoided)


# ---------------- state / since-filter ----------------

def get_state() -> dict:
    return _load_mapping(STATE)


def last_run_at() -> datetime | None:
    """When did the last successful draft complete? None if never run."""
    raw = get_state().get("last_run_at")
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
    return None


def mark_run_complete(when: datetime | None = None) -> datetime:
    """Set last_run_at. Call at the end of a successful draft; record_sent
    calls this for you, so manual use is rarely needed."""
    now = when or datetime.now().astimezone()
    state = get_state()
    state["last_run_at"] = now.isoformat()
    _dump_mapping(STATE, state)
    return now


def since_or_default(default_spec: str | None = "7d") -> datetime:
    """Return the cutoff for "new videos only". Uses last_run_at if set,
    otherwise falls back to now - default_spec (e.g. '7d'). Never returns
    None — callers can always compare against this."""
    lr = last_run_at()
    if lr is not None:
        return lr
    cutoff_date = parse_since(default_spec) if default_spec else None
    if cutoff_date is None:
        # Very old default — essentially "no filter".
        return datetime.fromtimestamp(0, tz=timezone.utc)
    return datetime.combine(cutoff_date, datetime.min.time()).astimezone()


# ---------------- TikTok ID timestamp decoding ----------------
#
# TikTok video IDs are 64-bit integers; the top 32 bits encode the Unix
# timestamp of creation. This is stable and well-documented. Other
# platforms don't offer a comparable trick — we rely on profile ordering
# for YouTube/IG/Threads.

_TIKTOK_ID_RE = re.compile(r"/video/(\d+)")


def parse_tiktok_video_id(url: str) -> int | None:
    m = _TIKTOK_ID_RE.search(url)
    return int(m.group(1)) if m else None


def tiktok_created_at(url_or_id: str | int) -> datetime | None:
    """Decode creation time from a TikTok video ID or URL. Returns None if
    the input isn't a TikTok URL/ID."""
    if isinstance(url_or_id, int):
        vid = url_or_id
    else:
        s = str(url_or_id)
        if s.isdigit():
            vid = int(s)
        else:
            parsed = parse_tiktok_video_id(s)
            if parsed is None:
                return None
            vid = parsed
    ts = vid >> 32
    return datetime.fromtimestamp(ts, tz=timezone.utc)


# ---------------- freshness gate ----------------
#
# The freshness check has three possible outcomes:
#   "fresh"   — posted within max_age_days, safe to include
#   "stale"   — known posted_at, but older than max_age_days — reject
#   "unknown" — we couldn't determine posted_at (caller must supply it or
#               drop the candidate)
#
# For TikTok, posted_at is derivable from the video ID. For every other
# platform, the caller must pass `posted_at` explicitly (usually parsed out
# of the post page's JSON-LD or og:published_time meta).

FRESH = "fresh"
STALE = "stale"
UNKNOWN = "unknown"


def derive_posted_at(url: str) -> datetime | None:
    """Try to derive post time from the URL alone. Only works for TikTok.
    Returns None for every other platform — callers must supply it."""
    if "tiktok.com" in url:
        return tiktok_created_at(url)
    return None


def check_freshness(
    url: str,
    posted_at: datetime | None = None,
    max_age_days: int | None = None,
    now: datetime | None = None,
) -> tuple[str, datetime | None, str]:
    """Return (status, effective_posted_at, human_reason).

    status is one of FRESH / STALE / UNKNOWN. effective_posted_at is the
    timestamp we compared against (None if unknown). reason is a short
    human-readable explanation suitable for CLI output.
    """
    max_age = max_age_days if max_age_days is not None else cfg.max_age_days()
    max_delta = timedelta(days=max_age)
    now = now or datetime.now().astimezone()

    posted = posted_at or derive_posted_at(url)
    if posted is None:
        return UNKNOWN, None, "posted_at not supplied and cannot be derived"

    # Normalize timezone so subtraction is defined.
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)

    age = now - posted
    if age > max_delta:
        days = age.total_seconds() / 86400
        return STALE, posted, f"posted {days:.1f}d ago, max allowed {max_age}d"
    return FRESH, posted, f"posted {age.total_seconds()/86400:.1f}d ago"

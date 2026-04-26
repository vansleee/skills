#!/usr/bin/env python3
"""daily-missing-juenu CLI.

Entry point for the skill's data access. Thin argparse layer on top of
scripts.store; all business logic lives in store.py and config.py.

Usage:
    python scripts/tools.py <command> [args...]

Every command supports --json for machine-readable output.

Dependencies: PyYAML. If missing:
    pip install pyyaml --break-system-packages
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make `from scripts import ...` work whether this file is invoked as
# `python scripts/tools.py` or `python -m scripts.tools`.
_THIS = Path(__file__).resolve()
_ROOT = _THIS.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import yaml  # noqa: F401  (imported for early failure if missing)
except ImportError:
    sys.stderr.write(
        "ERROR: PyYAML is required. Install with:\n"
        "  pip install pyyaml --break-system-packages\n"
    )
    sys.exit(2)

from scripts import config as cfg  # type: ignore[import-not-found]  # noqa: E402
from scripts import store  # type: ignore[import-not-found]  # noqa: E402


def _emit(obj, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, default=str, indent=2))
    else:
        if isinstance(obj, list):
            for row in obj:
                print(row)
        else:
            print(obj)


# ---------- config ----------

def cmd_config_show(args) -> int:
    _emit(cfg.load(), args.json or True)
    return 0


def cmd_config_get(args) -> int:
    val = cfg.get(*args.path.split("."))
    _emit(val, args.json)
    return 0 if val is not None else 1


# ---------- sent-log ----------

def cmd_is_sent(args) -> int:
    hit = store.is_sent(args.url)
    if args.json:
        print(json.dumps({"url": args.url, "sent": hit}, ensure_ascii=False))
    else:
        print("yes" if hit else "no")
    return 0 if hit else 1


def cmd_list_sent(args) -> int:
    rows = store.sent_list(since=args.since, handle=args.handle, limit=args.limit)
    _emit(rows, args.json)
    return 0


def cmd_record_sent(args) -> int:
    from datetime import datetime
    posted_at = datetime.fromisoformat(args.posted_at) if args.posted_at else None
    try:
        entry = store.record_sent(
            url=args.url,
            handle=args.handle,
            platform=args.platform,
            country=args.country,
            opener=args.opener,
            date_str=args.date,
            posted_at=posted_at,
            max_age_days=args.max_age_days,
            skip_freshness=args.skip_freshness,
        )
    except store.FreshnessRejected as e:
        sys.stderr.write(f"REFUSED: not fresh — {e.reason}\n")
        if e.status == store.UNKNOWN:
            sys.stderr.write(
                "  → pass --posted-at <ISO> (parse from the post page's "
                "datePublished / og:published_time), or use a TikTok URL.\n"
            )
        return 5
    except ValueError as e:
        sys.stderr.write(f"skip: {e}\n")
        return 3
    _emit(entry, args.json) if args.json else print(
        f"recorded: {entry['date']}  @{entry['handle']}  {entry['url']}"
    )
    return 0


def cmd_is_fresh(args) -> int:
    from datetime import datetime
    posted_at = datetime.fromisoformat(args.posted_at) if args.posted_at else None
    status, effective, reason = store.check_freshness(
        args.url,
        posted_at=posted_at,
        max_age_days=args.max_age_days,
    )
    if args.json:
        print(json.dumps(
            {
                "url": args.url,
                "status": status,
                "posted_at": effective.isoformat() if effective else None,
                "reason": reason,
            },
            ensure_ascii=False,
        ))
    else:
        print(f"{status}: {reason}")
    return {store.FRESH: 0, store.STALE: 1, store.UNKNOWN: 2}[status]


# ---------- openers ----------

def cmd_list_openers(args) -> int:
    _emit(store.openers_list(), args.json)
    return 0


def cmd_pick_opener(args) -> int:
    try:
        picked, avoided = store.pick_opener(avoid_last=args.avoid_last)
    except ValueError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 2
    if args.json:
        print(json.dumps(
            {"opener": picked, "avoided": avoided, "pool_size": len(store.openers_list()) - len(avoided)},
            ensure_ascii=False,
        ))
    else:
        print(picked)
    return 0


def cmd_last_opener(args) -> int:
    op = store.last_opener()
    if args.json:
        print(json.dumps({"opener": op}, ensure_ascii=False))
    else:
        print(op if op is not None else "")
    return 0 if op else 1


def cmd_add_opener(args) -> int:
    try:
        pool = store.add_opener(args.text)
    except ValueError as e:
        sys.stderr.write(f"{e}\n")
        return 3
    _emit({"added": args.text, "total": len(pool)}, args.json) if args.json else print(f"added: {args.text}")
    return 0


# ---------- fan accounts ----------

def cmd_list_accounts(args) -> int:
    rows = store.accounts_list(active_only=args.active, platform=args.platform, limit=args.limit)
    _emit(rows, args.json)
    return 0


def cmd_bump_account(args) -> int:
    row = store.bump_account(args.handle, platform=args.platform, country=args.country, seen=args.date)
    _emit(row, args.json) if args.json else print(f"{row['handle']}: hits={row['hit_count']} last_seen={row['last_seen']}")
    return 0


# ---------- state / since ----------

def cmd_get_since(args) -> int:
    if args.raw:
        lr = store.last_run_at()
        if lr is None:
            if args.json:
                print(json.dumps({"since": None}, ensure_ascii=False))
            return 1
        out = lr.isoformat()
    else:
        since_dt = store.since_or_default(args.default)
        out = since_dt.isoformat()
    if args.json:
        print(json.dumps({"since": out}, ensure_ascii=False))
    else:
        print(out)
    return 0


def cmd_mark_run_complete(args) -> int:
    from datetime import datetime
    when = None
    if args.when:
        when = datetime.fromisoformat(args.when)
    result = store.mark_run_complete(when)
    if args.json:
        print(json.dumps({"last_run_at": result.isoformat()}, ensure_ascii=False))
    else:
        print(result.isoformat())
    return 0


def cmd_tiktok_created_at(args) -> int:
    ts = store.tiktok_created_at(args.url)
    if ts is None:
        sys.stderr.write(f"not a TikTok URL/ID: {args.url}\n")
        return 2
    if args.json:
        print(json.dumps({"url": args.url, "created_at": ts.isoformat()}, ensure_ascii=False))
    else:
        print(ts.isoformat())
    return 0


def cmd_add_account(args) -> int:
    try:
        row = store.add_account(args.handle, platform=args.platform, country=args.country, notes=args.notes)
    except ValueError as e:
        sys.stderr.write(f"{e}\n")
        return 3
    _emit(row, args.json) if args.json else print(f"added: @{row['handle']} ({row['platform']})")
    return 0


# ---------- CLI wiring ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def with_json(sp):
        sp.add_argument("--json", action="store_true", help="emit JSON")
        return sp

    # config
    sp = sub.add_parser("config-show", help="dump the whole config.yaml")
    with_json(sp)
    sp.set_defaults(func=cmd_config_show)

    sp = sub.add_parser("config-get", help="get one config value by dotted path (e.g. slack.sender.label)")
    sp.add_argument("path")
    with_json(sp)
    sp.set_defaults(func=cmd_config_get)

    # sent-log
    sp = sub.add_parser("is-sent", help="exit 0 if URL is in sent-log, 1 otherwise")
    sp.add_argument("url")
    with_json(sp)
    sp.set_defaults(func=cmd_is_sent)

    sp = sub.add_parser("list-sent", help="list sent entries (newest first)")
    sp.add_argument("--since", help="30d / 6w / 3m / YYYY-MM-DD")
    sp.add_argument("--handle")
    sp.add_argument("--limit", type=int)
    with_json(sp)
    sp.set_defaults(func=cmd_list_sent)

    sp = sub.add_parser(
        "record-sent",
        help="append a sent entry (enforces freshness gate; also bumps the account)",
    )
    sp.add_argument("--url", required=True)
    sp.add_argument("--handle", required=True)
    sp.add_argument("--platform", default="tiktok")
    sp.add_argument("--country", default=None)
    sp.add_argument("--opener", default=None)
    sp.add_argument("--date", default=None, help="draft date (default: today)")
    sp.add_argument(
        "--posted-at",
        default=None,
        help="ISO datetime the video was posted; required for non-TikTok URLs",
    )
    sp.add_argument("--max-age-days", type=int, default=None, help="override config default")
    sp.add_argument(
        "--skip-freshness",
        action="store_true",
        help="bypass the freshness gate (use only for backfill / migrations)",
    )
    with_json(sp)
    sp.set_defaults(func=cmd_record_sent)

    sp = sub.add_parser(
        "is-fresh",
        help="check whether a URL is within the max_age_days window "
             "(exit 0=fresh, 1=stale, 2=unknown)",
    )
    sp.add_argument("url")
    sp.add_argument("--posted-at", default=None, help="required for non-TikTok URLs")
    sp.add_argument("--max-age-days", type=int, default=None, help="override config default")
    with_json(sp)
    sp.set_defaults(func=cmd_is_fresh)

    # openers
    sp = sub.add_parser("list-openers", help="dump the opener pool")
    with_json(sp)
    sp.set_defaults(func=cmd_list_openers)

    sp = sub.add_parser("pick-opener", help="pick a random opener, avoiding recent ones")
    sp.add_argument("--avoid-last", type=int, default=1)
    with_json(sp)
    sp.set_defaults(func=cmd_pick_opener)

    sp = sub.add_parser("last-opener", help="print the most recent opener (exit 1 if none)")
    with_json(sp)
    sp.set_defaults(func=cmd_last_opener)

    sp = sub.add_parser("add-opener", help="append a new opener to the pool")
    sp.add_argument("text")
    with_json(sp)
    sp.set_defaults(func=cmd_add_opener)

    # fan accounts
    sp = sub.add_parser("list-accounts", help="list fan accounts, ranked by hit_count")
    sp.add_argument("--active", action="store_true")
    sp.add_argument("--platform", help="tiktok / youtube / instagram / threads")
    sp.add_argument("--limit", type=int)
    with_json(sp)
    sp.set_defaults(func=cmd_list_accounts)

    sp = sub.add_parser("bump-account", help="record a hit for an account (auto-creates if new)")
    sp.add_argument("handle")
    sp.add_argument("--platform", default=None)
    sp.add_argument("--country", default=None)
    sp.add_argument("--date", default=None)
    with_json(sp)
    sp.set_defaults(func=cmd_bump_account)

    sp = sub.add_parser("add-account", help="register a new fan account on the watchlist")
    sp.add_argument("handle")
    sp.add_argument("--platform", default=None)
    sp.add_argument("--country", default=None)
    sp.add_argument("--notes", default=None)
    with_json(sp)
    sp.set_defaults(func=cmd_add_account)

    # state / since
    sp = sub.add_parser(
        "get-since",
        help="print the cutoff for 'new videos only' (last_run_at, or --default if unset)",
    )
    sp.add_argument("--default", default="7d", help="fallback when last_run_at is unset (30d/6w/ISO-date)")
    sp.add_argument("--raw", action="store_true", help="print raw last_run_at without default fallback (exit 1 if unset)")
    with_json(sp)
    sp.set_defaults(func=cmd_get_since)

    sp = sub.add_parser(
        "mark-run-complete",
        help="set last_run_at (record-sent already does this automatically)",
    )
    sp.add_argument("--when", default=None, help="ISO datetime; default: now")
    with_json(sp)
    sp.set_defaults(func=cmd_mark_run_complete)

    sp = sub.add_parser(
        "tiktok-created-at",
        help="decode a TikTok video ID or URL into its posted-at datetime",
    )
    sp.add_argument("url", help="TikTok video URL or numeric ID")
    with_json(sp)
    sp.set_defaults(func=cmd_tiktok_created_at)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

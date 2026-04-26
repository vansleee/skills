# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo purpose

Collection of personal Claude skills — each skill is a self-contained subdirectory with its own `SKILL.md` (workflow), `README.md` (setup), `scripts/`, `tests/`, `config.example.yaml`, and `data/`.

## Skills

### daily-missing-juenu

Finds Lee Ju-Eun (李珠珢) fan videos daily, composes a Slack draft digest, never auto-sends.

**Setup (first time):**
```bash
cd daily-missing-juenu
pip install pyyaml --break-system-packages
cp config.example.yaml config.yaml
cp data/fan-accounts.example.yaml data/fan-accounts.yaml
cp data/sent-log.example.yaml data/sent-log.yaml
# edit config.yaml: fill slack.sender.user_id and slack.recipient.dm_channel
```

**Run tests:**
```bash
cd daily-missing-juenu
python -m unittest discover -s tests -v
```

**Run one test module:**
```bash
python -m unittest tests.test_store -v
```

## Architecture — daily-missing-juenu

```
scripts/config.py   — YAML config loader; cached load(), dotted-path get(), convenience accessors
scripts/store.py    — YAML-backed data API: sent-log, fan-accounts, openers, state
scripts/tools.py    — CLI entry point (argparse); 20+ subcommands, all support --json
tests/              — stdlib unittest; safe to run anytime (temp files, no network)
```

**Data flow:**
1. `get-since` → time window for search
2. Browse fan accounts / WebSearch → candidate URLs
3. `is-sent <url>` → dedupe (exit 0 = already sent, skip)
4. `is-fresh <url> [--posted-at ISO]` → freshness gate (exit 0=keep, 1=stale, 2=unknown, 5=rejected)
5. Filter to exactly `message.video_count` freshest candidates
6. `pick-opener` → random Chinese/Korean phrase avoiding recent repeats
7. `slack_send_message_draft` to `slack.recipient.dm_channel` — **never call send directly**
8. `record-sent --url ... --handle ... --platform ... --opener ...` → writes sent-log, bumps fan account, advances `last_run_at`

**Exit code contract (tools.py):**
- `0` — success / positive result (is-sent=yes, is-fresh=yes)
- `1` — expected negative (is-sent=no, is-fresh=stale)
- `2` — unknown / missing data
- `3` — validation error
- `5` — freshness rejected by record-sent

**Data files (all gitignored except openers.yaml):**
- `data/sent-log.yaml` — dedup source; list of `{date, url, handle, platform, country, opener}`
- `data/fan-accounts.yaml` — watchlist; ranked by `hit_count` desc; auto-created on first bump
- `data/openers.yaml` — shipped in repo; list of Chinese/Korean phrase strings
- `data/state.yaml` — single key `last_run_at` (ISO datetime); advanced by `record-sent`

**Key conventions:**
- All dates: `YYYY-MM-DD` string in YAML
- TikTok freshness: derived from video ID (top 32 bits = Unix timestamp); no `--posted-at` needed
- Other platforms: must pass `--posted-at` parsed from page JSON-LD or `og:published_time`
- Handles: stored without leading `@`
- URLs are canonical dedupe keys

Full workflow details: `daily-missing-juenu/SKILL.md`

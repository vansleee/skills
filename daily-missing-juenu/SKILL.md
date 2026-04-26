---
name: daily-missing-juenu
description: Search for the latest fan-made videos of 李珠珢 (Lee Ju-Eun / 이주은), compose a short digest, and save it as a Slack draft — never auto-send. Who sends, who receives, and how many videos are all read from config.yaml. **Always** use when the user mentions 珠珢, 李珠珢, 이주은, Lee Ju Eun, daily jueun, daily missing juenu, 每日珠珢, 找珠珢新片, cheerleader fancam, 珠珢直拍, or 珠珢 fan edit — even casually. Also triggers when the nightly scheduled task for 李珠珢 fires.
allowed-tools:
  - Bash
  - WebFetch
  - WebSearch
  # Chrome MCP — required for reliable TikTok/IG/YouTube browsing.
  - mcp__Claude_in_Chrome__tabs_context_mcp
  - mcp__Claude_in_Chrome__tabs_create_mcp
  - mcp__Claude_in_Chrome__navigate
  - mcp__Claude_in_Chrome__read_page
  # Slack MCP tools (server prefix varies per install).
  - slack_send_message_draft
  - slack_send_message
---

# daily-missing-juenu

Compile a fancam digest for 李珠珢, save as a Slack draft. **Never auto-send.**

## Setup (once per install)

```bash
pip install pyyaml --break-system-packages
cp config.example.yaml config.yaml
cp data/fan-accounts.example.yaml data/fan-accounts.yaml
cp data/sent-log.example.yaml     data/sent-log.yaml
$EDITOR config.yaml    # fill slack.sender.user_id and slack.recipient.dm_channel
```

## Layout

```
daily-missing-juenu/
├── config.yaml         sender/receiver/video count   (gitignored, copy from .example)
├── scripts/
│   ├── config.py       config loader
│   ├── store.py        YAML-backed data API
│   └── tools.py        CLI — all data access goes through this
├── tests/              python -m unittest discover -s tests
└── data/
    ├── sent-log.yaml         dedupe source              (gitignored)
    ├── fan-accounts.yaml     watchlist by hit_count     (gitignored)
    ├── state.yaml            last_run_at for since-filter (gitignored)
    └── openers.yaml          opener phrase pool
```

Go through `scripts/tools.py` — never parse YAML under `data/` by hand.

## Config reference

Read at runtime with `python scripts/tools.py config-get <dotted.path>`.

| Key | What it's for |
| --- | ------------- |
| `message.video_count` | Videos per digest (target exactly this many) |
| `message.max_age_days` | Max age allowed; `record-sent` refuses anything older (hard gate) |
| `slack.sender.{label,user_id}` | Producer; `user_id` is the fallback-DM target |
| `slack.recipient.{label,dm_channel}` | Recipient; `dm_channel` is where drafts land |
| `message.intro_template` | Intro line with `{count}` and `{source}` placeholders |
| `message.fallback_prefix` | Prefix when the draft has to go to sender's own DM |
| `freshness.tiktok_id_anchor` | "Bigger TikTok ID = newer" mental anchor |
| `search.keywords` | Per-language keywords for search-page browsing |

---

## 1 · Find candidates

First, get the "since" cutoff — we only care about videos posted after the previous run:

```bash
python scripts/tools.py get-since --default 7d --json
# → {"since": "2026-04-17T09:00:00+08:00"}
```

`get-since` returns `last_run_at` if set, else now − `--default` (7 days by default). `record-sent` automatically advances `last_run_at`, so successive runs naturally window to just-new videos.

Priority for finding candidates (WebSearch is weak on TikTok — mostly returns `/discover/` pages):

1. **Chrome on known fan accounts' pages** — IDs and post dates visible, most reliable.
2. **Chrome on platform search pages** — for posts outside the watchlist.
3. **WebSearch fallback** — `site:tiktok.com` + config keywords; only keep results with `/video/<18-digit>/`.

```bash
python scripts/tools.py list-accounts --active --json          # ranked watchlist
python scripts/tools.py config-get search.keywords --json      # keywords
```

Don't only browse TikTok — `hit_count` is skewed by legacy (old data was TikTok-only). Hit YouTube and Instagram too; aim for 2–3 accounts per platform.

Newest-post locations: TikTok/YouTube Videos tab; IG/Threads profile grid. Stop scrolling once you reach posts older than the `since` cutoff.

## 2 · Validate each URL via oembed

HTTP 200 = live, 400/404 = drop.

- TikTok: `https://www.tiktok.com/oembed?url=<url>`
- YouTube: `https://www.youtube.com/oembed?url=<url>&format=json`
- Instagram: `https://www.instagram.com/oembed?url=<url>`
- Threads: `https://www.threads.net/oembed?url=<url>`

## 3 · Filter to exactly `message.video_count`

For **every candidate**, in this order:

1. **Dedupe** — `python scripts/tools.py is-sent <url>` (exit 0 = drop, 1 = keep).

2. **Freshness gate** — this is the hard rule. Use `is-fresh`:
   ```bash
   # TikTok: posted_at auto-derived from the video ID
   python scripts/tools.py is-fresh <url>

   # Non-TikTok: you must supply --posted-at (see below)
   python scripts/tools.py is-fresh <url> --posted-at 2026-04-24T10:00:00+00:00
   ```
   Exit codes: `0 = fresh (keep)`, `1 = stale (drop)`, `2 = unknown (drop, can't decide)`.

   `max_age_days` comes from config (default 3). Override per-call with `--max-age-days`.

3. **Getting `--posted-at` for non-TikTok** — this is on you, and is the step the gate is designed to force. Fetch the post page HTML and grep/parse one of:
   - JSON-LD `"datePublished":"..."` or `"uploadDate":"..."` (YouTube, Instagram, Threads).
   - `<meta property="og:published_time" content="..."/>` or `"article:published_time"`.

   If you can't find a timestamp, **drop the candidate** — don't guess, and don't skip the gate (`--skip-freshness` is for migrations only). Missing dates usually mean private / stale / unresolvable content anyway.

**User-pasted links** — if the user pasted a URL in the conversation, it still has to pass `is-fresh` (or they want stale videos and should override with `--max-age-days` at their own call).

**Ordering among survivors** — TikTok: larger video ID = newer. Others: top-of-grid first.

**Also drop**: AI-generated, composited, or remix clips.

If filtering leaves fewer than `message.video_count` candidates, go search more. Don't relax the freshness gate to fill the slot.

## 4 · Compose

Pick the opener (already avoids the most recent one):

```bash
python scripts/tools.py pick-opener --json
```

Build the message:

```
{opener}

{intro}

1️⃣ {summary} ({views or "最新"})
{URL}

2️⃣ ...
```

- `{intro}` is `message.intro_template` with `{count}` = `message.video_count`.
- `{source}` in the template = the country name (「韓國」) when all N videos share one country+platform; otherwise empty (so intro reads "今日精選 N 支影片：").
- Use 1️⃣ 2️⃣ 3️⃣ ... up to N.

## 5 · Draft (never auto-send to recipient)

```bash
DRAFT=$(python scripts/tools.py config-get slack.recipient.dm_channel)
FALLBACK=$(python scripts/tools.py config-get slack.sender.user_id)
```

Call `slack_send_message_draft` with `channel_id=$DRAFT`. The sender hits Send from Slack's Drafts UI.

On failure, fall back to `slack_send_message` with `channel_id=$FALLBACK` and prefix the message with `message.fallback_prefix` (fill `{recipient}` from `slack.recipient.label`).

Report back to chat: draft location, all URLs, which opener was used.

**Scheduled / unattended runs** do the same thing — **never** call `slack_schedule_message`, **never** send to the recipient. Additionally send `slack_send_message` to `slack.sender.user_id` with "Today's N are drafted; hit Send before you head out."

## 6 · Record

For each video in the draft:

```bash
# TikTok — posted_at is auto-derived from the URL
python scripts/tools.py record-sent \
  --url "<URL>" --handle <handle> --platform tiktok \
  --country <KR|TW|...> --opener "<today's opener>"

# Non-TikTok — you MUST pass --posted-at (same value you used with is-fresh)
python scripts/tools.py record-sent \
  --url "<URL>" --handle <handle> --platform <youtube|instagram|threads> \
  --country <KR|TW|...> --opener "<today's opener>" \
  --posted-at 2026-04-24T10:00:00+00:00
```

`record-sent` runs the same freshness check as `is-fresh` — it **refuses** stale or unknown candidates with exit 5. If you see `REFUSED: not fresh — ...`, drop the candidate and pick another; do not reach for `--skip-freshness` (that's for backfill/migration only).

On success it also (a) bumps the source account's `hit_count` and `last_seen`, and (b) advances `last_run_at` so the next run's `get-since` skips everything before now. Unknown handles auto-create; use `add-account` to register without a hit.

If the pipeline fails *before* any `record-sent` calls succeed, `last_run_at` stays at its previous value — the next run retries over the same window. If at least one `record-sent` succeeded before a later failure, the window has already moved forward; that's fine because `is-sent` dedupe covers it.

---

## CLI cheat sheet

All commands accept `--help` and `--json`.

| Command | Use |
| ------- | --- |
| `config-show` / `config-get <path>` | Config dump / lookup |
| `list-accounts --active [--platform X]` | Watchlist, ranked by hit_count |
| `list-sent [--since 7d] [--handle X]` | Recent drafts |
| `is-sent <url>` | Dedupe check (exit 0 = sent, 1 = new) |
| `is-fresh <url> [--posted-at ISO] [--max-age-days N]` | Freshness gate (exit 0=fresh, 1=stale, 2=unknown) |
| `get-since [--default 7d] [--raw]` | Cutoff for "new only" — uses `last_run_at` |
| `tiktok-created-at <url-or-id>` | Decode TikTok post time from ID |
| `mark-run-complete [--when ISO]` | Manually advance `last_run_at` (record-sent auto-calls this) |
| `pick-opener [--avoid-last N]` | Opener, avoiding recent |
| `list-openers` / `add-opener "..."` | Opener pool CRUD |
| `record-sent --url ... --handle ... --opener ... [--posted-at ISO]` | Record (refuses stale) + bump account + advance `last_run_at` |
| `add-account <handle> --platform X [--country Y]` | Add to watchlist |

## Tests

```bash
python -m unittest discover -s tests
```

`test_store.py` uses tempdirs (safe). `test_cli.py` shells out to `tools.py` read-only.

## Notes

- Update `freshness.tiktok_id_anchor` every few months — it's a mental anchor, doesn't gate anything, but stale values make freshness judgments harder.
- New platform or data field? Update `store.py` and its tests; SKILL.md usually doesn't need changes.

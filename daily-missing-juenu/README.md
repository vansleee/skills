# daily-missing-juenu

A Claude Code / Cowork skill that compiles a daily digest of fan videos of 李珠珢 (Lee Ju-Eun / 이주은) from TikTok, YouTube, Instagram, and Threads, composes a short message, and saves it as a Slack draft for the user to review and send.

The skill **never auto-sends** — it only drafts. The human makes the final call.

## Install

This repo IS the skill folder. Drop it into `~/.claude/skills/`:

```bash
git clone https://github.com/<owner>/daily-missing-juenu.git ~/daily-missing-juenu
ln -s ~/daily-missing-juenu ~/.claude/skills/daily-missing-juenu
```

Or copy instead of symlink if you don't plan to pull updates:

```bash
git clone https://github.com/<owner>/daily-missing-juenu.git
cp -r daily-missing-juenu ~/.claude/skills/
```

## First-time setup

After cloning:

```bash
cd ~/.claude/skills/daily-missing-juenu

# 1. Install the only Python dependency
pip install pyyaml --break-system-packages

# 2. Create your local config from the example
cp config.example.yaml config.yaml
$EDITOR config.yaml     # fill in slack.sender.user_id and slack.recipient.dm_channel

# 3. Seed the data files
cp data/fan-accounts.example.yaml data/fan-accounts.yaml
cp data/sent-log.example.yaml     data/sent-log.yaml
cp data/state.example.yaml        data/state.yaml

# 4. Sanity-check
python scripts/tools.py config-show --json
python scripts/tools.py list-accounts --active --json
python -m unittest discover -s tests
```

`config.yaml`, `data/sent-log.yaml`, and `data/fan-accounts.yaml` are gitignored so your local state never goes up to GitHub.

## What the skill does

See [`SKILL.md`](SKILL.md) for the full workflow. Short version:

1. Reads `config.yaml` for sender, receiver, and video count.
2. Calls `python scripts/tools.py list-accounts --active --json` to get the ranked watchlist.
3. Browses those accounts via Chrome MCP (falling back to WebSearch) and validates each candidate URL with the platform's oembed endpoint.
4. Filters out duplicates via `tools.py is-sent`.
5. Picks `message.video_count` freshest candidates.
6. Picks an opener (avoiding the most recent one) via `tools.py pick-opener`.
7. Composes the message and saves it as a Slack **draft** in the recipient's DM via `slack_send_message_draft`.
8. Records each video with `tools.py record-sent`, which also bumps the source account's `hit_count`.

## Layout

```
.
├── .gitignore
├── README.md                    ← this file
├── SKILL.md                     ← main skill instructions (read this)
├── config.example.yaml          ← copy → config.yaml and fill in
├── scripts/
│   ├── config.py                ← config loader
│   ├── store.py                 ← YAML-backed data access (pure Python)
│   └── tools.py                 ← CLI entry point
├── tests/
│   ├── test_config.py
│   ├── test_store.py
│   └── test_cli.py
└── data/
    ├── openers.yaml                ← opener phrase pool (ships in repo)
    ├── fan-accounts.example.yaml   ← copy → fan-accounts.yaml
    ├── sent-log.example.yaml       ← copy → sent-log.yaml
    └── state.example.yaml          ← copy → state.yaml (tracks last_run_at)
```

## Running tests

```bash
python -m unittest discover -s tests -v
```

`test_store.py` uses temp directories and never touches real data, so it's safe to run anytime. `test_cli.py` shells out to `scripts/tools.py` and makes read-only queries against whatever real data is present.

## Configuration reference

| Key | Meaning |
| --- | ------- |
| `message.video_count` | How many videos in each digest. |
| `slack.sender.{label,user_id}` | Who produces the digest. `user_id` is the Slack UID for fallback DMs. |
| `slack.recipient.{label,dm_channel}` | Who the digest is for. `dm_channel` is the DM channel ID where drafts land. |
| `message.intro_template` | The intro line format (uses `{count}`, `{source}` placeholders). |
| `message.fallback_prefix` | Used when `slack_send_message_draft` fails and we fall back to the sender's own DM. |
| `freshness.tiktok_id_anchor` | Mental anchor for "bigger TikTok ID = newer". Update periodically. |
| `search.keywords` | Per-language keyword lists for search-page browsing. |

## License

MIT — add your own `LICENSE` file (not included by default).

---

**Note on plugin format:** This repo is a standalone skill, not a Claude Code plugin. That means install is `cp`/`ln -s` into `~/.claude/skills/` — no `/plugin install owner/repo` path. If you want plugin-style install later, wrap the contents in `skills/daily-missing-juenu/` and add `.claude-plugin/plugin.json` at a new top level.

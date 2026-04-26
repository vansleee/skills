# claude-skills

Personal collection of Claude Code skills. Each skill is a self-contained subdirectory.

## Skills

| Skill | Description |
|-------|-------------|
| [daily-missing-juenu](daily-missing-juenu/) | Daily digest of 李珠珢 fan videos → Slack draft (never auto-sends) |

## Structure convention

Each skill directory contains:

```
<skill-name>/
├── SKILL.md              ← workflow instructions Claude reads at runtime
├── README.md             ← setup guide
├── config.example.yaml   ← copy → config.yaml and fill in secrets
├── scripts/              ← Python modules
├── tests/                ← stdlib unittest, safe to run anytime
└── data/                 ← runtime state (gitignored except example files)
```

## Adding a skill

1. Create `<skill-name>/` following the structure above
2. Add entry to this README's Skills table
3. Add entry to `CLAUDE.md`
4. Symlink into `~/.claude/skills/` for Claude Code to pick it up:
   ```bash
   ln -s $(pwd)/<skill-name> ~/.claude/skills/<skill-name>
   ```

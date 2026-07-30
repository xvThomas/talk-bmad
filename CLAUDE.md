# talk-bmad

BMad methodology hub for the talk project.
Contains all agents, skills, and planning artifacts shared across `talk-backend` and `talk-ui`.

## Directory Layout

| Path | Purpose |
|------|---------|
| `.github/agents/` | bmad agent definitions (Architect, Developer, PM, Analyst, Tech Writer, UX Designer) |
| `.agents/skills/` | bmad skills — invocable as `/skill-name` slash commands |
| `_bmad/` | Installer config (`config.toml`) and team/user customizations (`custom/`) |
| `_bmad-output/` | Generated artifacts — PRDs, epics, stories, architecture docs, project context |

## Cross-repo Usage

`talk-backend` and `talk-ui` reference agents and skills from this repo via `../talk-bmad/`.
Their `AGENTS.md` files list available agents and skills with their relative paths.

## Agents

To activate a bmad agent in Claude Code, load the corresponding file:

| Agent | File |
|-------|------|
| Architect | `@.github/agents/bmad-agent-architect.agent.md` |
| Developer | `@.github/agents/bmad-agent-dev.agent.md` |
| PM | `@.github/agents/bmad-agent-pm.agent.md` |
| Analyst | `@.github/agents/bmad-agent-analyst.agent.md` |
| Tech Writer | `@.github/agents/bmad-agent-tech-writer.agent.md` |
| UX Designer | `@.github/agents/bmad-agent-ux-designer.agent.md` |

## Skills

All bmad skills are in `.agents/skills/`. Load any skill file with `@.agents/skills/<name>/SKILL.md`
or invoke it as a slash command if supported by the editor.

### Making skills discoverable by Claude Code

Claude Code only discovers skills under `.claude/skills/` — it does **not** scan `.agents/skills/`,
and mentioning skills in `CLAUDE.md`/`AGENTS.md` does not register them (that only injects text
into context). To bridge this, [`scripts/link-skills.sh`](scripts/link-skills.sh) (and its
`.ps1` twin) populate `.claude/skills/` with one link **per skill folder**, drawing from:

1. the bmad hub skills (always), and
2. any repo-local `.agents/skills` roots passed as arguments.

Linking per-skill (not the whole `skills/` dir) lets a repo combine the shared bmad skills with
its own local skills in a single `.claude/skills/`. No file content is duplicated — the links
point back to `.agents/skills/`, the single source of truth.

`link-skills.sh` is the cross-platform entrypoint: on Windows (Git Bash/MSYS) it delegates to
`link-skills.ps1`, which creates junctions (no admin needed); on Linux/macOS it creates symlinks.

**You normally don't run this by hand** — each repo's `.claude/settings.json` has a `SessionStart`
hook that regenerates the links on every session start. `.claude/skills/` is machine-local and
gitignored; only the script + `.claude/settings.json` are committed. A newly added skill shows up
the session *after* it's created (or after a Claude Code window reload).

## BMad Configuration

- Team config: `_bmad/config.toml` (managed by installer — do not edit manually)
- Team overrides: `_bmad/custom/config.toml`
- Personal overrides: `_bmad/custom/config.user.toml` (gitignored)

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

## BMad Configuration

- Team config: `_bmad/config.toml` (managed by installer — do not edit manually)
- Team overrides: `_bmad/custom/config.toml`
- Personal overrides: `_bmad/custom/config.user.toml` (gitignored)

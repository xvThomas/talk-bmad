#!/usr/bin/env python3
"""
sync-github-projects.py — Sync sprint-status.yaml → GitHub Projects

Reads _bmad-output/implementation-artifacts/sprint-status.yaml and ensures
both GitHub projects reflect the current story statuses.

  Backend  : https://github.com/orgs/pixime-net/projects/3
  Frontend : https://github.com/orgs/pixime-net/projects/4

Usage:
  python3 scripts/sync-github-projects.py [--dry-run]

Requirements:
  gh CLI authenticated with 'project' scope (gh auth refresh -s project).
"""

import sys, re, subprocess, json, argparse
from pathlib import Path

# ── Project node IDs (stable — update only if projects are recreated) ──

PROJECTS = {
    "backend": {
        "id":           "PVT_kwDOD6CgEc4Bh__8",
        "number":       3,
        "owner":        "pixime-net",
        "status_field": "PVTSSF_lADOD6CgEc4Bh__8zhg5lIM",
        "epic_field":   "PVTSSF_lADOD6CgEc4Bh__8zhg5lmQ",
        "status_options": {
            "todo":          "73c468bb",
            "in-progress":   "aa63eb8e",
            "review":        "59b9ac55",
            "done":          "2266d1ff",
        },
        "epic_options": {
            "1": "35409a15",
            "2": "f8252ca9",
            "3": "b4cd44b4",
            "8": "616b70e8",
        },
        "epic_range": range(1, 4),
    },
    "frontend": {
        "id":           "PVT_kwDOD6CgEc4Bh__9",
        "number":       4,
        "owner":        "pixime-net",
        "status_field": "PVTSSF_lADOD6CgEc4Bh__9zhg5lJE",
        "epic_field":   "PVTSSF_lADOD6CgEc4Bh__9zhg5lng",
        "status_options": {
            "todo":          "a9c995a1",
            "in-progress":   "ae4e7b3d",
            "review":        "81055b5d",
            "done":          "7a2b2779",
        },
        "epic_options": {
            "4": "de4f6245",
            "5": "0c4727f6",
            "6": "b0b9eafe",
            "7": "77243781",
            "9": "f3a13ecd",
        },
        "epic_range": range(4, 8),
    },
}

# Maps sprint-status.yaml status values → project option key
STATUS_MAP = {
    "done":          "done",
    "in-progress":   "in-progress",
    "review":        "review",
    "backlog":       "todo",
    "ready-for-dev": "todo",
}

SPRINT_STATUS_PATH = (
    Path(__file__).parent.parent
    / "_bmad-output" / "implementation-artifacts" / "sprint-status.yaml"
)
EPICS_PATH = (
    Path(__file__).parent.parent
    / "_bmad-output" / "planning-artifacts" / "epics.md"
)


# ── Helpers ─────────────────────────────────────────────────────────────

def run_graphql(query: str) -> dict:
    r = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"GraphQL error: {r.stderr[:300]}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(r.stdout)
    if "errors" in data:
        print(f"GraphQL errors: {data['errors']}", file=sys.stderr)
        sys.exit(1)
    return data


def yaml_key_to_story_key(yaml_key: str) -> str | None:
    """
    Convert sprint-status.yaml key to dot-notation story key.
    '1-1-talk-serve-command'         → '1.1'
    '1-4-5-unified-handler'          → '1.4.5'
    'epic-1'                         → None  (epic rows)
    '1-1-retrospective'              → None  (retro rows)
    """
    if yaml_key.startswith("epic-"):
        return None
    if "-retrospective" in yaml_key:
        return None
    m = re.match(r'^(\d+(?:-\d+)*)-[a-z]', yaml_key)
    if not m:
        return None
    parts = m.group(1).split("-")
    return ".".join(parts)


def story_key_to_project(story_key: str) -> str | None:
    """Return 'backend' or 'frontend' for the given story key."""
    first = int(story_key.split(".")[0])
    for name, cfg in PROJECTS.items():
        if first in cfg["epic_range"] or str(first) in cfg["epic_options"]:
            return name
    return None


def parse_sprint_status() -> dict[str, str]:
    """Return {story_key: status_string} from sprint-status.yaml."""
    text = SPRINT_STATUS_PATH.read_text(encoding="utf-8")
    results: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s{2}([\w-]+):\s*(\S+)", line)
        if not m:
            continue
        yaml_key, status = m.group(1), m.group(2)
        story_key = yaml_key_to_story_key(yaml_key)
        if story_key:
            results[story_key] = status
    return results


def title_from_epics(story_key: str) -> str | None:
    """Try to extract a story title from epics.md for new item creation."""
    if not EPICS_PATH.exists():
        return None
    text = EPICS_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"### Story {re.escape(story_key)}:\s*(.+)", re.IGNORECASE
    )
    m = pattern.search(text)
    if m:
        return f"{story_key} · {m.group(1).strip()}"
    return None


# ── GitHub queries ───────────────────────────────────────────────────────

def fetch_project_items(project_id: str) -> list[dict]:
    """Fetch all items with their status and title."""
    data = run_graphql(f"""
    query {{
      node(id: "{project_id}") {{
        ... on ProjectV2 {{
          items(first: 100) {{
            nodes {{
              id
              content {{ ... on DraftIssue {{ id title }} }}
              fieldValues(first: 20) {{
                nodes {{
                  ... on ProjectV2ItemFieldSingleSelectValue {{
                    name
                    field {{ ... on ProjectV2SingleSelectField {{ name }} }}
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """)
    return data["data"]["node"]["items"]["nodes"]


def items_by_story_key(nodes: list[dict]) -> dict[str, dict]:
    """Return {story_key: {pvti_id, di_id, title, status_name}} from project items."""
    result: dict[str, dict] = {}
    for node in nodes:
        content = node.get("content") or {}
        title = content.get("title", "")
        m = re.match(r"^([\d.]+)\s", title)
        if not m:
            continue
        key = m.group(1)
        status_name = None
        for fv in node.get("fieldValues", {}).get("nodes", []):
            field = fv.get("field", {}) or {}
            if field.get("name") == "Status":
                status_name = fv.get("name")
        result[key] = {
            "pvti_id":     node["id"],
            "di_id":       content.get("id"),
            "title":       title,
            "status_name": status_name,
        }
    return result


# ── GitHub mutations ─────────────────────────────────────────────────────

def update_status(project_id: str, pvti_id: str, field_id: str, option_id: str,
                  dry_run: bool) -> bool:
    if dry_run:
        return True
    data = run_graphql(f"""
    mutation {{
      updateProjectV2ItemFieldValue(input: {{
        projectId: "{project_id}"
        itemId:    "{pvti_id}"
        fieldId:   "{field_id}"
        value:     {{ singleSelectOptionId: "{option_id}" }}
      }}) {{ projectV2Item {{ id }} }}
    }}
    """)
    return "errors" not in data


def create_item(proj_number: int, owner: str, title: str, dry_run: bool) -> str | None:
    """Create a draft item and return its PVTI_ ID."""
    if dry_run:
        return "DRY_RUN"
    r = subprocess.run(
        ["gh", "project", "item-create", str(proj_number),
         "--owner", owner, "--title", title, "--format", "json"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"  create error: {r.stderr[:200]}", file=sys.stderr)
        return None
    return json.loads(r.stdout)["id"]


# ── Main sync ────────────────────────────────────────────────────────────

def sync(dry_run: bool = False) -> None:
    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"{prefix}Reading sprint-status.yaml…")
    sprint = parse_sprint_status()
    print(f"  {len(sprint)} stories found\n")

    for proj_name, cfg in PROJECTS.items():
        print(f"── {proj_name} (#{cfg['number']}) {'─'*40}")
        nodes = fetch_project_items(cfg["id"])
        existing = items_by_story_key(nodes)

        updated = created = skipped = 0

        for story_key, raw_status in sorted(
            sprint.items(), key=lambda x: [int(p) for p in x[0].split(".")]
        ):
            proj = story_key_to_project(story_key)
            if proj != proj_name:
                continue

            option_key = STATUS_MAP.get(raw_status)
            if option_key is None:
                print(f"  WARN {story_key}: unknown status '{raw_status}' — skipped")
                continue

            if story_key in existing:
                item = existing[story_key]
                current_name = (item["status_name"] or "").lower()
                # Normalise names like "In Progress" → "in-progress"
                current_key = current_name.replace(" ", "-")
                if current_key == option_key:
                    skipped += 1
                    continue
                option_id = cfg["status_options"][option_key]
                ok = update_status(cfg["id"], item["pvti_id"],
                                   cfg["status_field"], option_id, dry_run)
                status_char = "✓" if ok else "✗"
                print(f"  {prefix}{status_char} {story_key}: "
                      f"{current_key} → {option_key}")
                if ok:
                    updated += 1
            else:
                # Item missing from project — create it
                title = title_from_epics(story_key) or f"{story_key} · (story)"
                pvti_id = create_item(cfg["number"], cfg["owner"], title, dry_run)
                if pvti_id:
                    option_id = cfg["status_options"][option_key]
                    update_status(cfg["id"], pvti_id, cfg["status_field"], option_id, dry_run)
                    epic_num = story_key.split(".")[0]
                    epic_option_id = cfg["epic_options"].get(epic_num)
                    if epic_option_id:
                        update_status(cfg["id"], pvti_id, cfg["epic_field"],
                                      epic_option_id, dry_run)
                    print(f"  {prefix}+ {story_key}: created [{option_key}]  '{title}'")
                    created += 1
                else:
                    print(f"  {prefix}✗ {story_key}: failed to create item")

        print(f"  → {updated} updated, {created} created, {skipped} already in sync\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without making API calls")
    args = parser.parse_args()
    sync(dry_run=args.dry_run)

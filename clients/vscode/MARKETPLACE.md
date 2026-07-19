# Squads

**Browse your squads-managed project's work items without leaving VS Code.**

This extension brings your [squads](https://github.com/TheCaptainCat/squads) project's work items, team roster, and workflow directly into VS Code — a read-only browse companion that keeps you in context while you code.

## Features

### Browse & Search

- **Work Items tree** — Explore your squad's hierarchy from a dedicated activity-bar view. Select any item to open its full dossier.
- **Roster view** — One place for all team roles, skills, and operators, organized in fixed buckets (Roles / Skills / Operators).
- **Workspace auto-discovery** — The extension finds `sq` automatically: workspace virtualenv, `uv`, `poetry`, or PATH.

### Item Preview

- **Full dossier rendering** — Click any work item to open its complete `sq show` output as a clean, readable HTML panel. Never hijacked by opening other markdown files.
- **Navigable references** — Links to parent items and related references are clickable: single-click opens in the same panel; Ctrl/Cmd+click or middle-click opens in a new panel.
- **Sub-entities** — Collapsed/expandable sections for stories, subtasks, and findings with their own status, severity, and assignee.
- **Discussion history** — Read comments and decisions in a collapsed/expandable timeline.
- **Reference & subtree graphs** — Two collapsible mermaid diagrams show what an item depends on and what depends on it.
- **Workflow cheatsheet** — A view-title button opens the workflow state machine diagram for quick reference.

### Display Controls

- **Filter by type** — Quick-pick to focus on one item type or see all.
- **Group by type** — Toggle to flatten the hierarchy and organize by type.
- **Show closed items** — Toggle to include closed/terminal items (rendered dimmed for clarity).
- **Clear filters** — Reset to the default hierarchy view.
- **Collapse all** — Fold all expanded groups at once.

### Polish

- **Auto-refresh** — Both views refresh automatically when `.squads.json` changes (when agents run commands, or after a `git pull`).
- **Hover tooltips** — Hover over any item to see status, assignee, and priority/severity badges at a glance.
- **Active-role highlights** — Items in active status (work in flight) appear in green for instant visibility.
- **Custom type icons** — Optionally remap work-item type names to VS Code codicons via settings.

## Getting Started

### 1. Install

Install **Squads** from the VS Code marketplace or from a `.vsix` build.

### 2. Open a Squads Project

Open a folder or workspace containing a `squads/` directory and `.squads.toml` configuration. The extension activates automatically.

### 3. Discovery & Configuration

The extension finds `sq` in this order:

1. **Explicit config** (`squads.sqPath` — an absolute path, or `squads.command` — a command array like `["uv", "run", "sq"]`)
2. **Workspace virtualenv** (`.venv/bin/sq`)
3. **`uv` on PATH** (if a `pyproject.toml` exists → `uv run sq`)
4. **`poetry` on PATH** (if a `pyproject.toml` exists → `poetry run sq`)
5. **Bare `sq` on PATH** (fallback)

**To override**, open VS Code settings and set one of:

```json
{
  "squads.sqPath": "/absolute/path/to/sq",
  "squads.command": ["uv", "run", "sq"]
}
```

### 4. Browse

- Click the **Squads** icon in the activity bar (left sidebar) to expand the work items and roster.
- Click any item to view its full details in the preview panel.
- Use the toolbar buttons to filter, group, and navigate.

## Requirements

- **VS Code** 1.85 or later
- **A squads-managed project** with a `.squads.toml` file
- **`sq` available** on your PATH or explicitly configured (see **Getting Started** above)

## Currently Read-Only

This extension is a browse-only client. Creating, editing, and updating items is a planned feature; for now, use the `sq` CLI to author and mutate work.

## Troubleshooting

If the views show an error about finding `sq`:

1. Verify `sq` is installed and on PATH (run `sq --version` in a terminal)
2. If you're using a virtualenv or project wrapper, set `squads.sqPath` or `squads.command` in your VS Code settings
3. Reload the VS Code window (`Cmd/Ctrl+Shift+P` → **Developer: Reload Window**)

---

Made by the squads team. For issues, questions, or contributions, visit the [squads repository](https://github.com/TheCaptainCat/squads).

# Squads

**See what your AI-agent team is working on, without leaving the editor.**

[squads](https://github.com/TheCaptainCat/squads) is a command-line coordination layer (`sq`) for a
team of AI coding agents working on one repository. It gives them a structure to share: a stable ID
for every piece of work, named roles with defined skills, a status lifecycle per item type, and a
handoff protocol — comments, `@mentions`, an inbox — so work moves from one agent to the next
instead of living in one chat window. All of it is markdown under a `squads/` folder in the repo, so
the team's state is committed, diffable, and reviewed like the code it describes.

This extension is the window onto that state from your editor. Once agents are doing the typing, the
question you spend the day on is less "what am I writing" and more "where is the work, and what moved
while I was in this file". That's what these views answer — three trees in the activity bar, a
rendered dossier for any item, and diagrams of how items connect. They update themselves each time an
agent touches the board.

**This extension reads; it does not write.** Creating, editing and transitioning items is still the
`sq` CLI's job. The **What it doesn't do** section below spells out the boundary — read it before you
install.

## Three views in the sidebar

- **Work Items** — epics, features, tasks, bugs and code reviews (or whichever work types your
  project declares) in their real parent/child hierarchy, from the top of a feature down to the
  subtask an agent is on right now.
- **Records** — the durable side of the project: architecture decisions, guides, and any other
  record type your project declares, each in its own bucket.
- **Roster** — who is on the team. Roles and the skills attached to them, plus the human operators
  registered alongside the agents.

Item icons are coloured from the workflow's own semantics rather than a fixed palette: work in
flight stands out, blocked items are flagged, finished ones are dimmed. Hover any row for its
status, assignee, and priority or severity badges. Type icons can be remapped to your preferred VS
Code codicons in settings.

## The item dossier

Select an item and it opens in a dedicated panel — a real dossier, not a raw file:

- **The item itself** — description and body rendered as markdown, in a panel this extension owns
  end to end, so opening another markdown file never steals it.
- **Sub-entities** — a feature's stories, a task's subtasks, a review's findings, each carrying its
  own status, assignee and severity, in a collapsible section.
- **Discussion** — the comment history that agents use to hand work over, in a collapsible
  timeline, with `@mentions` and item IDs as live links.
- **Two graphs** — one for the item's subtree, one for its references (what it points at, and what
  points back), rendered as mermaid diagrams. Click a node to open that item.
- **Navigation** — every ID reference is clickable: a plain click follows it in place, middle-click
  opens a second panel, and back/forward buttons retrace your path through the graph.
- **Workflow cheatsheet** — one button prints your project's actual state machine: which statuses
  each item type has, and which transitions are legal.

## It updates while you work

The views watch the project index on disk. When an agent runs a command, or when you pull or switch
a branch, the trees and any open dossier refresh on their own — without a keystroke from you. That's
the difference between reading a snapshot and watching a board: leave the sidebar open beside the
code and status changes land in it as agents make them.

## Finding things

- **Search** — run **Squads: Search…** from the command palette to search titles, bodies and
  discussion across the project, narrowing by type, status, or category as you type. Pick a hit to
  open its dossier.
- **Filter by type** — focus the work tree on a single item type.
- **Group by type** — flatten the hierarchy into per-type groups instead.
- **Show closed items** — bring finished and cancelled work back into view, dimmed.
- **Clear filters** and **Collapse all** — get back to a clean hierarchy in one click.

## What it doesn't do

- **No writing.** You cannot create, edit, transition, assign or comment from here. Do that with
  `sq` in a terminal, or let an agent do it — either way the views pick the change up a moment
  later. Editing from the editor is a planned direction, not a shipped feature.
- **It doesn't bundle squads.** The extension is a client; it needs the `sq` CLI installed and a
  project already under squads management.
- **It doesn't phone home.** No network calls, no telemetry, no account. It runs your local `sq`,
  renders the output, and draws the diagrams from a script bundled in the package.

## Getting started

### 1. Install the extension

Install **Squads** from the VS Code Marketplace, or from a `.vsix` build.

### 2. Install the CLI

The extension needs `sq` on your machine. See the
[squads repository](https://github.com/TheCaptainCat/squads) for CLI install instructions, then run
`sq init` in a project to set the team up — or open a project someone else has already initialised.

### 3. Open the project

Open a folder or workspace containing a `.squads.toml` file and its `squads/` directory. The Squads
icon appears in the activity bar; the views load on their own. If no squad is found, the tree says
so rather than failing silently.

### 4. Point the extension at `sq`

Discovery is automatic, in this order:

1. **Explicit config** — `squads.sqPath` (an absolute path) or `squads.command` (a command array
   like `["uv", "run", "sq"]`)
2. **Workspace virtualenv** — `.venv/bin/sq`
3. **`uv` on PATH** — used as `uv run sq` when a `pyproject.toml` is present
4. **`poetry` on PATH** — used as `poetry run sq` when a `pyproject.toml` is present
5. **Bare `sq` on PATH**

To override, set one of these in VS Code settings:

```json
{
  "squads.sqPath": "/absolute/path/to/sq",
  "squads.command": ["uv", "run", "sq"]
}
```

## Requirements

- **VS Code** 1.85 or later
- **A squads-managed project** — a `.squads.toml` file at the workspace root
- **The `sq` CLI** — on your PATH, or configured as above

## Troubleshooting

**The views report that `sq` can't be found.**

1. Check the CLI works on its own: run `sq --version` in a terminal.
2. If `sq` lives in a virtualenv or behind a project runner, set `squads.sqPath` or
   `squads.command` in your settings.
3. Reload the window (`Cmd/Ctrl+Shift+P` → **Developer: Reload Window**).

**The views don't refresh on their own.** Auto-refresh watches the project index on the local
filesystem, so it stays quiet in workspaces that aren't backed by one — a virtual filesystem, for
instance. The refresh button on each view still works.

**An item looks out of date in the dossier.** The dossier reflects what `sq` reports; if the
markdown file was edited by hand outside the CLI, run `sq repair` to bring the index back in line
with the files.

---

Squads is open source under the MIT licence. The CLI, the documentation and the issue tracker all
live in the [squads repository](https://github.com/TheCaptainCat/squads) — that's the place for bug
reports, questions, and a closer look at how the team structure works.

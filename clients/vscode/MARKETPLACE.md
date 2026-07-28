# Squads

**See what your AI-agent team is working on, without leaving the editor.**

[squads](https://github.com/TheCaptainCat/squads) is a command-line coordination layer (`sq`) for a
team of AI coding agents working on one repository. This extension is the window onto it from VS
Code — three trees in the activity bar, a rendered dossier for any piece of work, and diagrams of
how the work connects, refreshing on their own as agents move the board.

If you've not met squads before, the next few sections are for you: what it's for, how the model
works, and what using it looks like. The extension picks up further down.

**The extension reads; it does not write.** Creating, editing and transitioning work is the `sq`
CLI's job. The **What it doesn't do** section spells out the boundary — read it before you install.

## The problem it solves

An agent's memory ends when its session does. Put two agents on the same codebase and each one's
understanding of the plan lives in its own transcript — invisible to the other, invisible to you
tomorrow, and impossible to review. Coordination degrades into a human retyping context into the
next chat window.

squads moves that state out of the chat and into the repository. What each piece of work is, who
owns it, what it's waiting on, what was decided and why: all of it is markdown in a `squads/`
folder, addressed by a stable ID and committed alongside the code it describes. An agent starting
cold reads the same board the last one left behind. You review it in a pull request like anything
else.

## The model

- **Named roles, not anonymous prompts.** A squad has a roster — an architect, a tech lead, a
  reviewer, a QA engineer, a product owner, developers per stack — each a named agent with a defined
  mission and its own set of skills. Work is addressed to a role, not to whoever happens to be in
  the window.
- **Typed work items with stable IDs.** `FEAT-20`, `TASK-21`, `BUG-34`: a single global counter, so
  a number is unique across the whole project — there is no `TASK-7` and `BUG-7` to confuse. Each
  type carries its own status lifecycle — a task runs `Draft → Ready → InProgress → InReview → Done`,
  a bug runs `Open → InProgress → Fixed → Verified` — and transitions are validated, not free text.
- **Breakdown that holds together.** Epics contain features, features contain tasks. A feature's
  user stories map onto the subtasks that implement them, so a piece of work always knows which
  larger thing it serves.
- **Handoff in writing.** An agent hands work on by commenting on the item and `@mentioning` the
  next role; that role finds it with `sq inbox <role>`. The discussion is append-only, so the
  reasoning behind a decision outlives the session that produced it.
- **Records, not just tickets.** Architecture decisions and guides are first-class items with their
  own lifecycles — the durable side of the project, kept beside the work that caused it.
- **Humans on the roster too.** Operators are registered alongside the agents: they author items,
  comment under their own name, and have work assigned to them.

Only the markdown is authoritative. The index file beside it is a rebuildable cache — delete it and
`sq repair` reconstructs it from the files.

## What using it looks like

One piece of work, from proposal to closed, as the team would actually run it:

```bash
# The product owner opens a feature and the stories under it
sq create feature "Password reset" --author product-owner --desc "Email a signed link, 30-minute expiry"
sq feature 20 add-story "Request a reset link by email" --assignee python-dev

# The tech lead turns it into implementation work, mapped to that story
sq create task "Signed reset tokens" --author tech-lead --parent FEAT-20
sq task 21 add-subtask "Reject tokens past their expiry" --story US1

# A developer picks it up, and hands it on through the item's own discussion
sq task 21 status InProgress
sq task 21 comment --as python-dev -m "HMAC-signed tokens, 30-minute TTL." -m "@reviewer ready for a look"

# The reviewer finds it waiting for them, and records what they found
sq inbox reviewer
sq task 21 status InReview
sq create review "Reset token review" --author reviewer --ref TASK-21
sq review 22 add-finding "Expiry not enforced on a resend" --severity high

# Findings are closed on the record, and the work lands
sq review 22 finding 1 update --status Fixed
sq review 22 status InReview      # a review can't jump straight to Approved
sq review 22 status Approved
sq task 21 status Done
```

Every one of those commands writes markdown a human can read and git can diff. Agents run them
themselves: the roster, the skills and the handoff protocol are installed into the project at setup,
so an agent knows the process without being told it again each session.

## Works with your agent tooling

The agent-facing files are written by a pluggable backend, so squads isn't tied to one assistant.
Two ship today: `claude_code` writes pointer files under `.claude/` plus a managed section in
`CLAUDE.md`; `agents_md` writes a single `AGENTS.md`, the cross-tool convention other AI coding
tools read. Pick either at setup, or keep both current at once — the coordination model underneath
is identical.

---

That's squads. The rest of this page is the extension.

## Three views in the sidebar

- **Work Items** — epics, features, tasks, bugs and code reviews (or whichever work types your
  project declares) in their real parent/child hierarchy, from the top of a feature down to the
  subtask an agent is on right now.
- **Records** — the durable side: architecture decisions, guides, and any other record type your
  project declares, each in its own bucket.
- **Roster** — who is on the team. Roles and the skills attached to them, plus the human operators
  registered alongside the agents.

Item icons are coloured from the workflow's own semantics rather than a fixed palette: work in
flight stands out, blocked items are flagged, finished ones are dimmed. Hover any row for its
status, assignee, and priority or severity badges.

## The item dossier

Select an item and it opens in a dedicated panel — a real dossier, not a raw file:

- **The item itself** — description and body rendered as markdown, in a panel this extension owns
  end to end, so opening another markdown file never steals it.
- **Sub-entities** — a feature's stories, a task's subtasks, a review's findings, each carrying its
  own status, assignee and severity.
- **Discussion** — the handoff history in a collapsible timeline, with `@mentions` and item IDs as
  live links: a plain click follows one in place, middle-click opens a second panel, and
  back/forward buttons retrace your path.
- **Two graphs** — one for the item's subtree, one for its references (what it points at, and what
  points back), as mermaid diagrams. Click a node to open that item.
- **Workflow cheatsheet** — one button prints your project's actual state machine: which statuses
  each item type has, and which transitions are legal.

## It updates while you work

The views watch the project index on the local filesystem. When an agent runs a command, or when you
pull or switch a branch, the trees and any open dossier refresh on their own — without a keystroke
from you, though a workspace not backed by a local filesystem falls back to each view's refresh
button. That's the difference between reading a snapshot and watching a board: leave the sidebar open
beside the code and status changes land in it as agents make them.

## Finding things

- **Search** — run **Squads: Search…** from the command palette to search titles, bodies and
  discussion across the project, narrowing by type, status, or category as you type. Pick a hit to
  open its dossier.
- **View controls** — filter the work tree to one type, group by type instead of hierarchy, bring
  closed items back into view (dimmed), collapse everything, or reset it all in one click.
- **Type icons** — remap any work-item type to the VS Code codicon you prefer, in settings.

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

### 2. Install the CLI and set a project up

`sq` is a Python tool (3.14 or newer):

```bash
uv tool install squads     # or: pipx install squads
cd your-project
sq init --roles all        # scaffolds squads/, the roster, and the agent files
```

Or open a project a teammate has already initialised — the squad folder is committed, so there's
nothing to set up per machine.

### 3. Open the project

Open a folder or workspace containing a `.squads.toml` file and its `squads/` directory. The Squads
icon appears in the activity bar and the views load on their own. If no squad is found, the tree
says so rather than failing silently.

### 4. If the views can't find `sq`

This is the one failure worth knowing up front, since the extension shells out to a CLI it doesn't
bundle. Discovery is automatic in the usual cases — a workspace virtualenv, `uv` or `poetry`, or your
PATH — so first check that the CLI works on its own (`sq --version` in a terminal). If it lives
somewhere less obvious, name it in VS Code settings and reload the window
(`Cmd/Ctrl+Shift+P` → **Developer: Reload Window**):

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

---

Squads is open source under the MIT licence. The CLI, its documentation and the issue tracker all
live in the [squads repository](https://github.com/TheCaptainCat/squads) — that's the place for bug
reports, questions, and the full picture of how a squad is put together.

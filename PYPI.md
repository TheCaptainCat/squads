# squads

**A coordination layer for a team of AI coding agents working on one repository.**

`squads` (`sq`) gives those agents somewhere to work: a stable ID for every piece of work, named
roles with defined skills, a status lifecycle per item type, and a handoff protocol — comments,
`@mentions`, an inbox — so work moves from one agent to the next. It is all markdown under a
`squads/` folder in your repository, committed alongside the code it describes.

## Install

```bash
uv tool install squads        # or: pipx install squads
```

Python 3.14 or newer. Add the `tui` extra if you want the terminal browser (`sq ui`):
`uv tool install "squads[tui]"`.

## Start a squad

```bash
cd your-project
sq init --roles all
sq workflow                   # the team's process, printed
```

`sq init` writes the `squads/` folder — the team's source of truth — activates a roster of named
agents, and installs the agent-facing files: for Claude Code, thin pointer files under `.claude/`
plus a managed section in `CLAUDE.md` that teaches the agents the process. Commit all of it.

## The problem it solves

An agent's memory ends when its session does. Put two agents on the same codebase and each one's
understanding of the plan lives in its own transcript — invisible to the other, invisible to you
tomorrow, and impossible to review. Coordination degrades into a human retyping context into the
next chat window.

squads moves that state out of the chat and into the repository: what each piece of work is, who
owns it, what it is waiting on, what was decided and why. An agent starting cold reads the same
board the last one left behind, and you review it in a pull request like anything else.

## The model

- **Named roles, not anonymous prompts.** A squad has a roster — an architect, a tech lead, a
  reviewer, a QA engineer, a product owner, developers per stack — each a named agent with a defined
  mission and its own skills. Work is addressed to a role, not to whoever is in the window.
- **Typed work items with stable IDs.** `FEAT-20`, `TASK-21`, `BUG-34`: a single global counter, so
  a number is unique across the whole project. Each type carries its own status lifecycle — a task
  runs `Draft → Ready → InProgress → InReview → Done`, a bug runs
  `Open → InProgress → Fixed → Verified` — and transitions are validated, not free text.
- **Breakdown that holds together.** Epics contain features, features contain tasks; a feature's
  user stories map onto the subtasks that implement them.
- **Handoff in writing.** An agent hands work on by commenting on the item and `@mentioning` the
  next role, which finds it with `sq inbox <role>`. The discussion is append-only, so the reasoning
  behind a decision outlives the session that produced it.
- **Records, not just tickets.** Architecture decisions and guides are first-class items with their
  own lifecycles — the durable side of the project, kept beside the work that caused it.
- **Humans on the roster too.** Operators are registered alongside the agents: they author items,
  comment under their own name, and have work assigned to them.

Only the markdown is authoritative. `squads/.squads.json` is a rebuildable index — delete it and
`sq repair` reconstructs it from the files.

## What using it looks like

One piece of work, from proposal to closed. `sq create` prints the ID it allocated — substitute it
wherever these show `FEAT-<n>`, `TASK-<n>` or `REV-<n>`:

```bash
# Developer roles are per stack; the bundled roster is the process roles
sq dev add --tech python

# The product owner opens a feature and the stories under it
sq create feature "Password reset" --author product-owner --desc "Email a signed link, 30-minute expiry"
sq feature FEAT-<n> add-story "Request a reset link by email" --assignee python-dev

# The tech lead turns it into implementation work, mapped to that story
sq create task "Signed reset tokens" --author tech-lead --parent FEAT-<n>
sq task TASK-<n> add-subtask "Reject tokens past their expiry" --story US1

# A developer picks it up, and hands it on through the item's own discussion
sq task TASK-<n> status InProgress
sq task TASK-<n> comment --as python-dev -m "HMAC-signed tokens, 30-minute TTL." -m "@reviewer ready for a look"

# The reviewer finds it waiting for them, and records what they found
sq inbox reviewer
sq task TASK-<n> status InReview
sq create review "Reset token review" --author reviewer --ref TASK-<n>
sq review REV-<n> add-finding "Expiry not enforced on a resend" --severity high

# Findings are closed on the record, and the work lands
sq review REV-<n> finding 1 update --status Fixed
sq review REV-<n> status InReview      # a review can't jump straight to Approved
sq review REV-<n> status Approved
sq task TASK-<n> status Done
```

Every one of those commands writes markdown a human can read and git can diff. Agents run them
themselves — the roster, the skills and the handoff protocol are installed into the project, so an
agent knows the process without being told it again each session.

Read the board back with `sq tree`, `sq list`, `sq blocked`, `sq mine <role>`, or
`sq task TASK-<n> show --full --comments` for one item's whole dossier.

## Works with your agent tooling

The agent-facing files are written by a pluggable backend, so squads is not tied to one assistant.
Two ship today: `claude_code` writes the `.claude/` pointer files plus the managed `CLAUDE.md`
section; `agents_md` writes a single `AGENTS.md`, the cross-tool convention other AI coding tools
read. Pick either at `sq init`, or keep both current at once — the coordination model underneath is
identical.

## Reading the board outside the terminal

Two read-only clients exist for browsing a squad: `sq ui`, a terminal browser included with the
`tui` extra, and a
[VS Code extension](https://marketplace.visualstudio.com/items?itemName=pierre-chat.squads-vscode)
that puts the work items, records and roster in the sidebar with a rendered dossier per item.
Neither writes anything today — every mutation goes through `sq`. Editing from a client is a planned
direction, not a shipped feature.

## Documentation

- [Tutorial](https://github.com/TheCaptainCat/squads/blob/main/docs/tutorial.md) — a first squad,
  end to end, in about fifteen minutes.
- [Workflow](https://github.com/TheCaptainCat/squads/blob/main/docs/workflow.md) — who creates and
  links what, and the status lifecycle per item type.
- [Agents](https://github.com/TheCaptainCat/squads/blob/main/docs/agents.md) — operating *as* an
  agent inside a squad.
- [Roles](https://github.com/TheCaptainCat/squads/blob/main/docs/roles.md) — the bundled roster and
  stack developers.
- [Adoption](https://github.com/TheCaptainCat/squads/blob/main/docs/adoption.md) — bringing an
  existing project under squads without losing its history.
- [Overrides](https://github.com/TheCaptainCat/squads/blob/main/docs/overrides.md) — your own item
  types, templates, and role definitions.
- [All docs](https://github.com/TheCaptainCat/squads/blob/main/docs/README.md) ·
  [repository](https://github.com/TheCaptainCat/squads)

The same pages are readable offline, without leaving the terminal: `sq docs`.

## Where it is

squads is pre-1.0 and under active development: surfaces are still being settled, and a release can
change the on-disk schema. When one does, `sq migrate up` carries an existing squad forward — a squad
created on any 0.x release reaches 1.0 intact. What is and is not going to be stable after 1.0 is written
down in [the stability contract](https://github.com/TheCaptainCat/squads/blob/main/docs/stability.md).

MIT licensed. Issues and questions:
[github.com/TheCaptainCat/squads](https://github.com/TheCaptainCat/squads).

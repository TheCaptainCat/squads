# Your first squad

A 15-minute, end-to-end walkthrough of the coordination layer your team will work in. By the end
you'll have an epic → feature → task hierarchy with user stories, subtasks, a comment, a bug fix
link, and a clean `sq check`.

Commands use bare `sq` (a tool install); from a source checkout prefix with `uv run`.

## 0. Install & initialize

```bash
uv tool install squads          # or: uvx --from squads sq …
cd your-project
sq init --roles all
```

`init` writes `.squads.toml`, the `squads/` folder (one subfolder per type) + `.squads.json`, and
the `.claude/` scaffolding (role pointers, the `squads` skill, a managed `CLAUDE.md` section). Open
Claude Code here and you can greet an agent ("Hi Robert") to have it impersonate that role — but for
this tutorial we'll drive `sq` directly.

On a real project this is also the moment to consider the optional init-time interview — see
[agents.md](agents.md#opening-a-new-squad-the-interview).

## 1. An epic (the umbrella)

```bash
sq create epic "Authentication platform" --author product-owner
# → created EPIC-21 → /path/to/your-project/squads/epics/EPIC-000021-authentication-platform.md
```

Every item has an author: `--author` is required on every `sq create`, and takes a registered
slug — a role (`sq role list` shows them) or `op-<slug>` for a human operator. The IDs below are what a fresh `sq init --roles all`
gives: the global counter has already spent 1–20 on the eight bundled roles and their generated
skills. If your squad has a different roster, your numbers differ; substitute the ID each `create`
prints.

### The pattern: `sq` scaffolds, **you set the body with a command**

This is the heart of squads. `sq create` writes a *skeleton* with a placeholder body; you fill it
through `sq <type> <n> body` — never by hand-editing the file. Reading works the same way round:
`sq <type> <n> show` is the read surface, not the file. The fresh epic looks like:

```markdown
---
id: EPIC-21
sequence_id: 21
type: epic
title: Authentication platform
status: Draft
...
---
<!-- sq:body -->
## Summary

_TODO: summarise this epic._

## Goals

-

## Scope
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
```

Set the body with a command (write the full markdown yourself: each `-m` is one paragraph, or pass
`--file body.md` for long content):

```bash
sq epic 21 body -m "## Summary" -m "One login service for every product." -m "## Goals" -m "- Email + password login with lockout."
sq epic 21 show                         # read the summary + body back
```

`sq` owns the whole file — **never touch the `<!-- sq:* -->` markers or the frontmatter**. `--desc`
sets only the short one-line *summary* (shown in `sq list`), not the body. Every
`create`/`add-story`/`add-subtask` below follows the same flow: scaffold, then set the body via a
command.

## 2. A feature with user stories (product owner)

```bash
sq create feature "Login" --parent EPIC-21 --author product-owner
sq feature 22 body -m "## Summary" -m "Email + password login with lockout."   # set the body
sq feature 22 add-story "As a user, I want to log in so that I can access my account"
sq feature 22 add-story "As an admin, I want to lock accounts after 5 failed tries"
```

Flesh out each story's body (acceptance criteria, etc.) **through `sq`** — no manual file editing:

```bash
sq feature 22 story 1 body -m "As a user, I want to log in…" -m "Acceptance: …"
sq feature 22 story 2 body -m "As an admin, I want to lock accounts…" -m "Acceptance: …"
sq feature 22 story 1 show     # read its status, body, and discussion back
```

You write the prose via `-m`/`--file`; `sq` keeps the structure. A story or subtask left with its
placeholder body is something `sq check` flags, so give each one a body.

## 3. A task with subtasks (tech lead)

A task's parent is the feature; each subtask maps to one user story:

```bash
sq create task "Validate credentials" --parent FEAT-22 --author tech-lead -m "Verify hash; lock after 5 fails."
sq task 23 add-subtask "Check password hash" --story US1 -m "Use the stored argon2 hash."
sq task 23 add-subtask "Lock after 5 failures" --story US2 -m "Count failures per account; lock at 5."
```

## 4. Do the work

```bash
sq task 23 status InProgress
sq task 23 comment --as tech-lead -m "Hashing done" -m "@qa ready for lockout tests"
sq task 23 subtask 1 update --status Done --force
sq task 23 status InReview
```

(`--as` must be a registered slug: a role such as `tech-lead`, a developer such as `python-dev`
once you have run `sq dev add --tech python`, or `op-<slug>` for a human operator. The comment
header records that slug with the author's name. An unknown slug is refused.)

## 5. A bug, linked to a fix

```bash
sq create bug "Lockout counter resets on refresh" --author qa
sq task 23 ref add BUG-24 --kind fixes
sq bug 24 refs --in        # the bug shows the task that fixes it (computed)
```

## 6. Record a decision and a guide (architect)

```bash
sq create decision "Use argon2id for password hashing" --author architect
sq decision 25 status Accepted
sq create guide "Password hashing" --tech security --author architect
```

## 7. See it and check it

```bash
sq tree EPIC-21         # the epic → feature → task hierarchy
sq list --type task     # filtered table
sq check                # validates markers, links, status, drift  → ✓ no issues
```

A bare `sq tree` shows every root, the roster's roles and skills included, so root it at the epic to
see just the hierarchy (or pass `--category work` to keep every work item and drop the roster and
records).

## 8. Inbox & workflow

```bash
sq inbox qa             # open items mentioning @qa
sq workflow             # the team-workflow cheatsheet
```

## Where everything landed

```
squads/
├─ .squads.json                       # the index (counter + items + refs)
├─ epics/EPIC-000021-authentication-platform.md
├─ features/FEAT-000022-login.md      # contains US1, US2 + their bodies/discussion
├─ tasks/TASK-000023-validate-credentials.md   # contains ST1, ST2
├─ bugs/BUG-000024-lockout-counter-resets-on-refresh.md
├─ adrs/ADR-000025-use-argon2id-for-password-hashing.md
├─ guides/GUIDE-000026-password-hashing.md
└─ agents/                            # the roles and skills sq init generated
```

Commit the `squads/` folder, `.squads.toml`, `CLAUDE.md`, and `.claude/`. Next: read
[workflow.md](workflow.md) for the rules, [agents.md](agents.md) for the agent loop, and
[recipes.md](recipes.md) for copy-paste sequences.

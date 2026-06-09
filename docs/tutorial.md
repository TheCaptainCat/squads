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

## 1. An epic (the umbrella)

```bash
sq create epic "Authentication platform"
# → created EPIC-000009 → squads/epics/EPIC-000009-authentication-platform.md
```

(Your numbers differ — the global counter already spent IDs on the bundled roles.)

### The pattern: `sq` scaffolds, **you set the body with a command**

This is the heart of squads. `sq create` writes a *skeleton* with a placeholder body; you fill it
through `sq body` — never by hand-editing the file. The fresh epic looks like:

```markdown
---
id: EPIC-000009
type: epic
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

<!-- sq:discussion -->
<!-- sq:discussion:end -->
```

Set the body with a command (write the full markdown yourself; `-m` paragraphs or `--file` for long
content):

```bash
sq epic 9 body --file epic-body.md     # or: -m "## Summary" -m "…" -m "## Goals" -m "…"
sq epic 9 show                          # read the summary + body back
```

`sq` owns the whole file — **never touch the `<!-- sq:* -->` markers or the frontmatter**. `--desc`
sets only the short one-line *summary* (shown in `sq list`), not the body. Every
`create`/`story add`/`subtask add` below follows the same flow: scaffold, then set the body via a
command.

## 2. A feature with user stories (product owner)

```bash
sq create feature "Login" --parent EPIC-000009
sq feature 10 body -m "## Summary" -m "Email + password login with lockout."   # set the body
sq feature 10 add-story "As a user, I want to log in so that I can access my account"
sq feature 10 add-story "As an admin, I want to lock accounts after 5 failed tries"
```

Flesh out each story's body (acceptance criteria, etc.) **through `sq`** — no manual file editing:

```bash
sq feature 10 story 1 body -m "As a user, I want to log in…" -m "Acceptance: …"
sq feature 10 story 1 show     # read its status, body, and discussion back
```

You write the prose via `-m`/`--file`; `sq` keeps the structure.

## 3. A task with subtasks (tech lead)

A task's parent is the feature; each subtask maps to one user story:

```bash
sq create task "Validate credentials" --parent FEAT-000010 -m "Verify hash; lock after 5 fails."
sq task 11 add-subtask "Check password hash" --story US1 -m "Use the stored argon2 hash."
sq task 11 add-subtask "Lock after 5 failures" --story US2
```

## 4. Do the work

```bash
sq task 11 status InProgress
sq task 11 comment --as developer -m "Hashing done" -m "@qa ready for expiry tests"
sq task 11 subtask 1 update --status Done --force
sq task 11 status InReview
```

(`--as developer` only resolves to a full name if you've activated a dev role; otherwise use a
real slug like `architect`, or `operator`.)

## 5. A bug, linked to a fix

```bash
sq create bug "Lockout counter resets on refresh"
sq task 11 ref add BUG-000012 --kind fixes
sq bug 12 refs --in        # the bug shows the task that fixes it (computed)
```

## 6. Record a decision and a guide (architect)

```bash
sq create decision "Use argon2id for password hashing"
sq decision 13 status Accepted
sq create guide "Password hashing" --tech security
```

## 7. See it and check it

```bash
sq tree                 # the epic → feature → task hierarchy
sq list --type task     # filtered table
sq check                # validates markers, links, status, drift  → ✓ no issues
```

## 8. Inbox & workflow

```bash
sq inbox qa             # open items mentioning @qa
sq workflow             # the team-workflow cheatsheet
```

## Where everything landed

```
squads/
├─ .squads.json                       # the index (counter + items + refs)
├─ epics/EPIC-000009-authentication-platform.md
├─ features/FEAT-000010-login.md      # contains US1, US2 + their bodies/discussion
├─ tasks/TASK-000011-validate-credentials.md   # contains ST1, ST2
├─ bugs/BUG-000012-lockout-counter-resets-on-refresh.md
├─ adrs/ADR-000013-use-argon2id-for-password-hashing.md
└─ guides/GUIDE-000014-password-hashing.md
```

Commit the `squads/` folder, `.squads.toml`, `CLAUDE.md`, and `.claude/`. Next: read
[workflow.md](workflow.md) for the rules, [agents.md](agents.md) for the agent loop, and
[recipes.md](recipes.md) for copy-paste sequences.

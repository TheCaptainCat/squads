# Your first squad

A 15-minute, end-to-end walkthrough. By the end you'll have an epic → feature → task hierarchy with
user stories, subtasks, a comment, a bug fix link, and a clean `sq check`.

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

## 2. A feature with user stories (product owner)

```bash
sq create feature "Login" --parent EPIC-000009
sq story add FEAT-000010 "As a user, I want to log in so that I can access my account"
sq story add FEAT-000010 "As an admin, I want to lock accounts after 5 failed tries"
```

`story add` prints the file + the line range to write between — open the feature file and flesh out
each story's body (acceptance criteria, etc.) inside its `<!-- sq:story:US1:body -->` region.

## 3. A task with subtasks (tech lead)

A task's parent is the feature; each subtask maps to one user story:

```bash
sq create task "Validate credentials" --parent FEAT-000010
sq subtask add TASK-000011 "Check password hash" --story US1
sq subtask add TASK-000011 "Lock after 5 failures" --story US2
```

## 4. Do the work

```bash
sq status TASK-000011 InProgress
sq comment TASK-000011 --as developer -m "Hashing done" -m "@qa ready for expiry tests"
sq subtask done TASK-000011 ST1
sq status TASK-000011 InReview
```

(`--as developer` only resolves to a full name if you've activated a dev role; otherwise use a
real slug like `architect`, or `operator`.)

## 5. A bug, linked to a fix

```bash
sq create bug "Lockout counter resets on refresh"
sq ref add TASK-000011 BUG-000012 --kind fixes
sq refs BUG-000012 --in        # the bug shows the task that fixes it (computed)
```

## 6. Record a decision and a guide (architect)

```bash
sq create decision "Use argon2id for password hashing"
sq status ADR-000013 Accepted
sq guide add "Password hashing" --tech security
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

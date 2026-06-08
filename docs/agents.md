# Working as an agent in a squad

How an AI agent (or a human role-playing one) operates inside a squads-managed project. If you're an
agent reading this in a session: this is your operating manual. See [workflow.md](workflow.md) for
who-does-what and the status rules.

## You have a name

After `sq init`/`sq adopt`, the project's `CLAUDE.md` carries a managed section that tells you:

- **Greeting → impersonation.** If the operator opens with a greeting to an agent by name
  ("Hi Robert", "Hey Mara"), adopt that agent: load their role definition from
  `squads/agents/roles/ROLE-*.md` and act as them — refer to yourself by full name.
- **No name → Catherine Manager** (`manager`), the default. She triages the request and routes it to
  the right specialist.

Each role's Claude pointer (`.claude/agents/<slug>.md`) preloads the `squads` skill plus the
item-type skills that role manages (e.g. the product owner gets `sq-feature`/`sq-epic`). **Open the
relevant `sq-<type>` skill** for role-directed guidance before you work an item of that type.

## The loop

```
   scope ──▶ create ──▶ write body ──▶ track status ──▶ hand off
     ▲                                                      │
     └──────────────────── @mention / inbox ◀──────────────┘
```

1. **Scope** — see what exists and what's waiting for you:
   ```bash
   sq list --status InProgress        sq tree           sq show TASK-000003
   sq inbox <your-role>               # open items that @mention you
   ```
2. **Create** with `sq` (it allocates the ID and prints the file path):
   ```bash
   sq create task "Validate token" --parent FEAT-000002
   # → created TASK-000003 → squads/tasks/TASK-000003-validate-token.md
   ```
3. **Write the body directly in that file** — your prose goes between the `<!-- sq:body -->`
   markers. For features scaffold user stories, for tasks scaffold subtasks (each returns the exact
   region to fill):
   ```bash
   sq story add FEAT-000002 "As a user, I want to log in"
   sq subtask add TASK-000003 "Check expiry" --story US1
   ```
4. **Track status** as work moves (validated per type):
   ```bash
   sq status TASK-000003 InProgress
   sq status TASK-000003 Done
   ```
5. **Hand off & discuss** — leave dated notes attributed to yourself; `@mention` to notify another
   role:
   ```bash
   sq comment TASK-000003 --as architect -m "Reuse the clock abstraction" -m "@qa verify expiry edges"
   ```
6. **Link context** so the next agent reads the right things:
   ```bash
   sq ref add TASK-000003 GUIDE-000004 --kind implements
   sq ref add TASK-000003 BUG-000009 --kind fixes
   ```

## Golden rules

- **`sq` owns the frontmatter, the status, and the discussion.** You own everything else.
- **Never edit a `<!-- sq:* -->` marker line.** Write prose *between* the markers; the markers let
  `sq` find sections without clobbering your text. `sq check` flags broken markers.
- **The `.md` frontmatter is the source of truth** — don't hand-edit `id`/`status`/`parent`; use the
  commands so the index stays in sync.
- **Reference items by ID** (`TASK-000003`, `GUIDE-000004`) in prose and comments so developers and
  reviewers can follow the trail.
- **Work chronologically** and comment as you go — the dated discussion entries are the history.

## By role (quick notes)

- **Product owner (Nina Product)** — write features + user stories; define acceptance criteria.
- **Tech lead (Olivia Lead)** — break features into tasks (`--parent` the feature), map subtasks to
  user stories, link bugs/reviews with `--kind fixes|addresses`, sequence and unblock.
- **Developer (`<tech>-dev`)** — implement the assigned task; write tests; comment progress; address
  review feedback.
- **Reviewer (Paul Reviewer)** — drive review items to a verdict; request changes or approve.
- **QA (Mara Tester)** — derive tests from user stories; verify fixes; file bugs.
- **Architect (Robert Architect)** — record ADRs; author guides; review designs.
- **Tech writer (Theo Writer)** — keep guides and docs current.

Lost? Run **`sq workflow`** for the cheatsheet, or `sq <command> --help`.

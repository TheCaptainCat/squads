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
   scope ──▶ create ──▶ set body (sq body) ──▶ track status ──▶ hand off
     ▲                                                      │
     └──────────────────── @mention / inbox ◀──────────────┘
```

1. **Scope** — see what exists and what's waiting for you:
   ```bash
   sq list --status InProgress        sq tree           sq task 3 show
   sq inbox <your-role>               # open items that @mention you
   ```
2. **Create** with `sq` (it allocates the ID and prints the file path):
   ```bash
   sq create task "Validate token" --parent FEAT-000002
   # → created TASK-000003 → squads/tasks/TASK-000003-validate-token.md
   ```
3. **Set the body with a command** — never hand-edit the file. Items and sub-entities both take
   `-m "…"` (repeatable) or `--file`; read back with `sq show` / `sq <kind> show`:
   ```bash
   sq task 3 body -m "Validate the JWT exp + signature; reject clock skew > 60s."
   sq feature 2 add-story "As a user, I want to log in" -m "Acceptance: …"
   sq task 3 add-subtask "Check expiry" --story US1
   sq task 3 subtask 1 body -m "Reject tokens past exp; cover clock skew."
   ```
4. **Track status** as work moves (validated per type):
   ```bash
   sq task 3 status InProgress
   sq task 3 status Done
   ```
5. **Hand off & discuss** — leave dated notes attributed to yourself; `@mention` to notify another
   role:
   ```bash
   sq task 3 comment --as architect -m "Reuse the clock abstraction" -m "@qa verify expiry edges"
   ```
6. **Link context** so the next agent reads the right things:
   ```bash
   sq task 3 ref add GUIDE-000004 --kind implements
   sq task 3 ref add BUG-000009 --kind fixes
   ```

## Golden rules

- **`sq` owns the whole `.md` file** — frontmatter, markers, and every region. You author the content
  through commands, not your editor.
- **Never hand-edit a `.md` file.** Set bodies with `sq body` / `sq <kind> body`, comment with
  `sq comment`, change state with `sq update`/`status`. `sq check` flags broken markers.
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

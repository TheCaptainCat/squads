# squads

A CLI (`squads` / `sq`) that manages a **team of AI agents** working on a code project.

squads bootstraps agent **roles** and **skills**, produces markdown in a predictable structure,
and gives every tracked artifact a stable JIRA-like ID (`TASK-000003`). Claude Code is the first
supported backend; the design is pluggable.

The real content lives under a relocatable `squads/` folder. The files written into `.claude/`
are **thin pointers** to those definitions, plus a managed `squads` skill and a managed section in
`CLAUDE.md` that teaches the agents how to work.

---

## Install

Requires Python ≥ 3.14. Install as a **tool** so `squads` / `sq` land on your `PATH`:

```bash
# with uv (recommended)
uv tool install squads          # from PyPI, once published
uv tool install .               # from a local checkout

# or with pipx
pipx install squads             # from PyPI
pipx install .                  # from a local checkout
```

Then `sq` is available everywhere:

```bash
sq --help
sq --version
```

Try it once without installing, via `uvx` (or `pipx run`):

```bash
uvx --from squads sq --help     # or: uvx --from . sq --help  in a checkout
```

> **From source / development:** `uv sync` creates the project venv and exposes the CLI as
> `uv run sq …`. The examples below use bare `sq` (tool install); prefix with `uv run` if you're
> working from a source checkout.

## Quickstart

```bash
cd your-project
sq init --roles all                 # scaffold squads/, .claude/, CLAUDE.md
sq create feature "User authentication" --desc "Login & sessions"
sq create task "Validate token expiry" --parent FEAT-000010
sq status TASK-000011 InProgress
sq comment TASK-000011 --as architect -m "Reuse the clock abstraction" -m "@qa verify edges"
sq tree
```

---

## Concepts

- **Items** — every tracked thing is an item with a type and a stable ID. Types: `epic`,
  `feature`, `task`, `bug`, `decision` (ADR), `review`, `guide`, `role`, `skill`.
- **Global IDs** — `PREFIX-NNNNNN` with a single global counter, so the number is unique across
  all types (you never have both `TASK-000002` and `BUG-000002`). The prefix marks the type:
  `EPIC FEAT TASK BUG ADR REV GUIDE ROLE SKILL`.
- **Source of truth** — the markdown **frontmatter** is durable truth; `squads/.squads.json` is a
  fast index that is fully rebuildable from the files (`sq repair`).
- **sq-owned sections** — files carry invisible markers (`<!-- sq:body -->`, `<!-- sq:discussion -->`,
  …). `sq` owns the frontmatter and marked sections (status, discussion); **agents write all other
  prose directly** and must never touch the marker lines.
- **Agents** — named roles (real name + slug, e.g. *Robert Architect* / `architect`). The `.claude/`
  files are pointers to the real definitions under `squads/agents/`.

### On-disk layout

```
your-project/
├── .squads.toml                 # config (squad dir, backend, version, default role)
├── CLAUDE.md                    # managed section: process + greeting impersonation
├── .claude/
│   ├── agents/<slug>.md         # POINTER → squads/agents/roles/ROLE-*.md
│   └── skills/{squads,<slug>}/SKILL.md
└── squads/                      # self-contained & relocatable (override with --dir)
    ├── .squads.json             # the index: counter + all items + refs
    ├── epics/ features/ tasks/ bugs/ adrs/ reviews/ guides/
    └── agents/{roles,skills}/
```

### Status workflows

| Type | Lifecycle |
|------|-----------|
| epic / feature / task / bug | `Draft → Ready → InProgress → InReview → Done` (+ `Blocked`, `Cancelled`) |
| decision (ADR) | `Proposed → Accepted → Superseded` (+ `Rejected`, `Deprecated`) |
| review | `Requested → InReview → ChangesRequested → Approved` (+ `Rejected`) |
| guide | `Draft → Published → Deprecated` |
| role / skill | `Draft → Active → Archived` |

`sq status` validates transitions; use `--force` to override.

---

## Command reference

**Setup**
- `sq init [--squad-dir squads] [--backend claude_code] [--roles all|core|minimal|<slugs>] [--no-claude] [--force]`
- `sq workflow` — print the team-workflow cheatsheet
- `sq sync` — regenerate tool-owned managed files to the current version
- `--dir PATH` (global) — operate on the squad folder at PATH instead of walking up to `.squads.toml`

**Items**
- `sq create epic|feature|task|bug|decision|review|guide TITLE [--parent ID] [--desc] [--label] [--ref ID] [--assignee] [--json]`
- `sq list [--type|--status|--parent|--label|--assignee] [--json]` · `sq show ID [--json]` · `sq tree [ROOT_ID]`
- `sq update ID [--title|--desc|--assignee|--add-label|--rm-label]` (`--title` renames the file)
- `sq status ID STATUS [--force]` · `sq link CHILD --parent P` · `sq unlink CHILD`

**Collaboration**
- `sq comment ID -m "…" [-m "…"] [--as <slug|operator>] [--story USn|--subtask STn]` (use `@role` to notify)
- `sq story add FEAT-ID [LABEL] [--json]` · `sq story list FEAT-ID`
- `sq subtask add TASK-ID [LABEL] [--story USn] [--json]` · `sq subtask list TASK-ID` · `sq subtask done TASK-ID STn [--undo]`
- `sq inbox <role>` — open items mentioning `@role`

`story add` / `subtask add` **scaffold an empty block with a writable body region** and print
(or return, with `--json`) the file and the marker/line range to write between — the agent then
fills it with free-form paragraphs or bullet lists. The optional `LABEL` is just a short heading;
the substance lives in the body. `sq` still owns the discussion and the subtask checkbox.

**Cross-linking**
- `sq ref add FROM TO [--kind related|blocks|implements|fixes|addresses]` · `sq ref rm FROM TO`
- `sq refs ID [--out|--in|--all] [--json]` (forward edges stored; backrefs computed)

**Agents**
- `sq role list [--available] | show <slug> | activate <slug> | regen ID | rm ID [--purge]`
- `sq dev add --tech <t> [--name] [--model] | list` — stack-specific developers
- `sq skill add NAME [--desc|--when-to-use|--allowed-tools] | list | show | regen | rm [--purge]`
- `sq guide add TITLE [--tech] [--tag] | list`

**Maintenance**
- `sq check` — lint markers, dangling parent/ref IDs, invalid status, index drift
- `sq repair [--renumber]` — rebuild the index from frontmatter; `--renumber` resolves merged ID collisions

---

## Working with agents

After `sq init`, open Claude Code in the project. `CLAUDE.md` tells the agents how the process
works and how to **impersonate a role on greeting**: say *"Hi Robert"* and Claude becomes Robert
Architect; with no name it defaults to **Catherine Manager**, who triages and routes the request.

The bundled roster: Catherine Manager (`manager`, default), Robert Architect (`architect`),
Olivia Lead (`tech-lead`), Paul Reviewer (`reviewer`), Mara Tester (`qa`), Hugo Ops (`devops`),
Nina Product (`product-owner`), Theo Writer (`tech-writer`). Add stack developers with `sq dev add`.

Agents create items with `sq`, get back the file path, write the body directly, and hand off via
`sq comment … @role`. Status and discussion stay owned by the CLI.

`sq init`/`sq sync` also generate a **skill per item type** (`sq-feature`, `sq-task`, `sq-bug`, …)
with role-directed guidance, plus the general `squads` skill. Each role's `.claude/agents/<slug>.md`
pointer preloads (via `skills:`) only the skills for the item types that role manages — so the
product owner gets `sq-feature`/`sq-epic`, a developer gets `sq-task`/`sq-bug`/`sq-review`, and the
manager (who triages rather than owning a type) gets just `squads`. Run `sq workflow` for the
cheatsheet.

### Team workflow

squads encodes a light division of labour (enforced by validation + `sq check`):

- The **product owner** writes **features** and their **user stories**
  (`sq create feature`, `sq story add`).
- The **tech lead** writes **tasks**. A task's **parent is the feature** it implements, and each
  **subtask maps to one user story**:
  ```bash
  sq create task "Token validation" --parent FEAT-000002
  sq subtask add TASK-000003 "Validate expiry" --story US1   # US1 must exist in FEAT-000002
  ```
- A task may instead/also link a **bug** or **review** via typed refs — or nothing if it's purely
  technical:
  ```bash
  sq ref add TASK-000003 BUG-000009 --kind fixes
  sq ref add TASK-000003 REV-000010 --kind addresses
  ```

A task's parent must be a feature (link a bug/review with a ref, not as parent); a feature's parent
must be an epic. Invalid links are rejected at create/link time and flagged by `sq check`.

---

## Git notes

Commit `.squads.toml`, the `squads/` folder, `CLAUDE.md`, and `.claude/` (the pointers + squads
skill). `squads/.gitignore` already excludes the lock/temp files. On a merge conflict in
`.squads.json`, take either side and run `sq repair` (the frontmatter is the truth);
if two branches reused an ID number, run `sq repair --renumber`.

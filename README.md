# squads

A CLI (`squads` / `sq`) that is the **coordination layer** for a team of AI agents working on one
codebase.

squads gives the team a shared structure to work in: a stable JIRA-like ID for every piece of work
(`TASK-000003`), defined **roles** and the **skills** that go with them, a status lifecycle, and a
handoff protocol (comments, `@mentions`, an inbox) — so work moves cleanly from one agent to the
next and everyone reads the same source of truth. Your agents — you, in Claude Code, adopting a
role — do the building; squads keeps them coordinated. Claude Code is the first supported backend;
the design is pluggable.

That shared structure lives under a relocatable `squads/` folder — the team's source of truth. The
files written into `.claude/` are **thin pointers** to those definitions, plus a managed `squads`
skill and a managed section in `CLAUDE.md` that teaches the agents how to work.

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

## Shell completion

`sq` supports tab-completion for **bash** and **zsh** (and also fish and PowerShell).

**bash**

```bash
sq --install-completion bash
# then restart your terminal (or source the new file printed by the command)
```

**zsh**

```bash
sq --install-completion zsh
# then restart your terminal (or source the new file printed by the command)
```

`--install-completion` writes a shell-specific script to your home directory and prints the path.
Once the shell is restarted, pressing `Tab` after `sq ` completes commands, options, and arguments.

To inspect the script without installing it:

```bash
sq --show-completion bash
sq --show-completion zsh
```

> **Note:** completion requires `sq` to be on your `PATH` (i.e. installed as a tool via `uv tool install` or `pipx install`). It will not work through `uv run sq` because `uv run` wraps the entry point in a way that the shell cannot discover.

## Quickstart

```bash
cd your-project
sq init --roles all                 # scaffold squads/, .claude/, CLAUDE.md
sq create feature "User authentication" --desc "Login & sessions"
sq create task "Validate token expiry" --parent FEAT-000010
sq task 11 status InProgress
sq task 11 comment --as architect -m "Reuse the clock abstraction" -m "@qa verify edges"
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

## Documentation

Full docs (with diagrams) live in **[docs/](docs/README.md)**:

- **[tutorial](docs/tutorial.md)** — a 15-minute, end-to-end first squad.
- **[workflow](docs/workflow.md)** — who creates & links what, and the per-type status lifecycles.
- **[agents](docs/agents.md)** — operating *as* an agent inside a squad.
- **[roles](docs/roles.md)** — the bundled roster, bundles, and stack developers.
- **[recipes](docs/recipes.md)** — copy-paste sequences · **[faq](docs/faq.md)** — common errors.
- **[adoption](docs/adoption.md)** — migrating an existing project (`sq adopt`, `--at`).
- **[internals](docs/internals.md)** / **[backends](docs/backends.md)** — under the hood & writing a backend.

Contributing: **[CONTRIBUTING.md](CONTRIBUTING.md)** · contributors: **[CONTRIBUTORS.md](CONTRIBUTORS.md)** · changes: **[CHANGELOG.md](CHANGELOG.md)**.

---

## Command reference

**Setup**
- `sq init [--squad-dir squads] [--backend claude_code] [--roles all|core|minimal|<slugs>] [--no-claude] [--force]`
- `sq adopt [--squad-dir squads] [--backend] [--roles] [--no-claude]` — bring an *existing* project under sq management (non-destructive; imports existing items). See [docs/adoption.md](docs/adoption.md).
- `sq workflow` — print the team-workflow cheatsheet
- `sq sync` — regenerate tool-owned managed files to the current version
- `--dir PATH` (global) — operate on the squad folder at PATH instead of walking up to `.squads.toml`
- `--at WHEN` (global) — forge timestamps (ISO 8601, UTC) for this command, to preserve history when migrating

Items are addressed by `<type> <number>` (bare `35`, padded `000035`, or full `TASK-000035`; the
type word validates). Create with `sq create`; operate with `sq <type> <n> <verb>`.

**Items**
- `sq create epic|feature|task|bug|decision|review|guide TITLE --author <slug> [--parent ID] [--desc] [--label] [--ref ID] [--assignee] [--priority urgent|high|medium|low] [-m "body"|--file] [--json]`
- `sq list [--type|--status|--parent|--label|--assignee|--priority] [--all] [--json]` · `sq tree [ROOT_ID] [--all] [--json]` — closed (Done/Cancelled/…) items are hidden unless `--all` (or an explicit `--status`); `tree --json` emits the nested subtree (status/priority/assignee/blocked) for orchestrating agents
- `sq <type> <n> show [--json]` · `sq <type> <n> body [-m "…"|--file PATH] [--append]`
- `sq <type> <n> update [--title|--desc|--author|--status|--force|--parent|--no-parent|--assignee|--priority|--no-priority|--add-label|--rm-label|--set k=v|--unset k]`
- `sq <type> <n> status STATUS [--force]` · `sq <type> <n> comment -m "…" [--as <slug>]`

**Find & focus**
- `sq search TEXT [--type] [--json]` — match item titles, summaries, and bodies/discussion
- `sq blocked [--json]` — open items blocked by other open items (via the `blocks` ref kind)
- `sq mine [ROLE] [--all] [--json]` — items assigned to a role (default: the squad's default role)
- `sq workload [--json]` — open/closed/total work-item counts per assignee
- `sq inbox <role>` — open items mentioning `@role`

**Sub-entities** (stories on features, subtasks on tasks, findings on reviews)
- `sq feature <n> add-story "…" [--assignee] [-m|--file]` · `sq feature <n> stories`
- `sq task <n> add-subtask "…" [--story USn] [--assignee] [-m|--file]` · `sq task <n> subtasks`
- `sq review <n> add-finding "…" [--severity] [--assignee] [-m|--file]` · `sq review <n> findings`
- `sq <type> <n> <kind> <k> show|update|body|comment` — `update` sets `--title`/`--status`/`--assignee` (+ a subtask's `--story`, a finding's `--severity`)

`add-<kind>` **scaffolds an empty block**; set its body with the nested `… <kind> <k> body` (or pass
`-m`/`--file` to `add-<kind>`). `sq` owns the body, meta (status/assignee/severity/story), and
discussion — all written through commands.

**Cross-linking**
- `sq <type> <n> ref add TARGET [--kind related|blocks|implements|fixes|addresses]` · `sq <type> <n> ref rm TARGET`
- `sq <type> <n> refs [--out|--in|--all] [--json]` (forward edges stored; backrefs computed)

**Agents**
- `sq role list [--available] | show <slug> | activate <slug> | regen ID | rm ID [--purge]`
- `sq dev add --tech <t> [--name] [--model] | list` — stack-specific developers
- `sq operator add "NAME" [--slug] | list | rm ID [--purge]` — register **humans** (`op-<first>` slug); assignable and can author items/comments
- `sq skill add NAME [--desc|--when-to-use|--allowed-tools] | list | show | regen | rm [--purge]`
- `sq create guide TITLE [--tech] [--tag] | list`

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
  sq task 3 add-subtask "Validate expiry" --story US1   # US1 must exist in FEAT-000002
  ```
- A task may instead/also link a **bug** or **review** via typed refs — or nothing if it's purely
  technical:
  ```bash
  sq task 3 ref add BUG-000009 --kind fixes
  sq task 3 ref add REV-000010 --kind addresses
  ```

A task's parent must be a feature (link a bug/review with a ref, not as parent); a feature's parent
must be an epic. Invalid links are rejected at create/link time and flagged by `sq check`.

---

## Backends

squads ships two backends; select with `--backend` at `sq init` or via `default_backend` in
`.squads.toml`.

### `claude_code` (default)

Writes thin pointer files into `.claude/agents/` and `.claude/skills/`, plus a managed section in
`CLAUDE.md`. Each role and skill gets its own pointer file that @-includes the real definition
from `squads/agents/`. Designed for Claude Code.

```bash
sq init --backend claude_code   # default; creates .claude/ + CLAUDE.md
```

Commit `.squads.toml`, the `squads/` folder, `CLAUDE.md`, and `.claude/`.

### `agents_md`

Writes a single `AGENTS.md` file at the project root — the cross-tool AGENTS.md convention
(understood by Gemini CLI, Cursor, and other AI-enabled editors). No pointer files are created.
`sq sync` keeps the managed section current without touching user prose outside the
`<!-- squads:start -->` / `<!-- squads:end -->` markers.

```bash
sq init --backend agents_md     # creates AGENTS.md at the project root
sq sync                         # refresh AGENTS.md after adding roles/operators
```

Internal staging files live in `.agents_md/` (one per role/skill); commit `AGENTS.md` but
`.agents_md/` can be gitignored.

---

## Git notes

Commit `.squads.toml`, the `squads/` folder, `CLAUDE.md`, and `.claude/` (the pointers + squads
skill). `squads/.gitignore` already excludes the lock/temp files. On a merge conflict in
`.squads.json`, take either side and run `sq repair` (the frontmatter is the truth);
if two branches reused an ID number, run `sq repair --renumber`.

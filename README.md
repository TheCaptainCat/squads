# squads

A CLI (`squads` / `sq`) that is the **coordination layer** for a team of AI agents working on one
codebase.

squads gives the team a shared structure to work in: a stable JIRA-like ID for every piece of work
(`TASK-<n>`), defined **roles** and the **skills** that go with them, a status lifecycle, and a
handoff protocol (comments, `@mentions`, an inbox) — so work moves cleanly from one agent to the
next and everyone reads the same source of truth. Your agents — you, in Claude Code, adopting a
role — do the building; squads keeps them coordinated. Claude Code is the first supported backend
and an `AGENTS.md` backend ships alongside it; the design is pluggable.

That shared structure lives under a relocatable `squads/` folder — the team's source of truth. The
files written into `.claude/` are **thin pointers** to those definitions, plus a managed `squads`
skill and a managed section in `CLAUDE.md` that teaches the agents how to work.


---

## Install

Requires Python ≥ 3.14. Install as a **tool** so `squads` / `sq` land on your `PATH`:

```bash
# with uv (recommended)
uv tool install squads          # from PyPI
uv tool install .               # from a local checkout

# or with pipx
pipx install squads             # from PyPI
pipx install .                  # from a local checkout
```

Add the `tui` extra if you want the terminal browser (`sq ui`): `uv tool install "squads[tui]"`.

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
sq init --roles all                 # scaffolds squads/, the roster, .claude/, CLAUDE.md
sq create feature "User authentication" --author product-owner --desc "Login & sessions"
sq create task "Validate token expiry" --author tech-lead --parent FEAT-<n>
sq task TASK-<n> status InProgress
sq task TASK-<n> comment --as architect -m "Reuse the clock abstraction" -m "@qa verify edges"
sq tree
```

`sq create` prints the ID it allocated — substitute it for `FEAT-<n>` / `TASK-<n>` above. Every item
is authored by a role (`--author`), which is why a squad starts by activating a roster.

---

## Working with agents

After `sq init`, open Claude Code in the project. `CLAUDE.md` tells the agents how the process
works and how to **impersonate a role on greeting**: say *"Hi Robert"* and Claude becomes Robert
Architect; with no name it defaults to **Catherine Manager**, who triages and routes the request.

The bundled roster: Catherine Manager (`manager`, default), Robert Architect (`architect`),
Olivia Lead (`tech-lead`), Paul Reviewer (`reviewer`), Mara Tester (`qa`), Hugo Ops (`devops`),
Nina Product (`product-owner`), Theo Writer (`tech-writer`). Add stack developers with `sq dev add`.

Agents create items with `sq`, fill in the body with `sq <type> <n> body`, and hand off with
`sq <type> <n> comment … @role`. Everything an item knows — body, status, discussion — arrives
through the CLI; the `.md` files are never hand-edited.

`sq init`/`sq sync` also generate a **skill per item type** (`sq-feature`, `sq-task`, `sq-bug`, …)
with role-directed guidance, plus the general `squads` skill. Each role's `.claude/agents/<slug>.md`
pointer preloads (via `skills:`) only the skills for the item types that role manages — so the
product owner gets `sq-feature`/`sq-epic`, a developer gets `sq-task`/`sq-bug`/`sq-review`, and the
manager (who triages rather than owning a type) gets just `squads`. Run `sq workflow` for the
cheatsheet.

### Team workflow

squads encodes a light division of labour (enforced by validation + `sq check`):

- The **product owner** writes **epics**, **features** and their **user stories**
  (`sq create epic`, `sq create feature`, `sq feature <n> add-story`).
- The **tech lead** writes **tasks**. A task's **parent is the feature** it implements, and each
  **subtask maps to one user story**:
  ```bash
  sq create task "Token validation" --author tech-lead --parent FEAT-<n>
  sq task TASK-<n> add-subtask "Validate expiry" --story US1   # US1 must exist on FEAT-<n>
  ```
- A task may instead/also link a **bug** or **review** via typed refs — or nothing if it's purely
  technical:
  ```bash
  sq task TASK-<n> ref add BUG-<n> --kind fixes
  sq task TASK-<n> ref add REV-<n> --kind addresses
  ```

A task's parent must be a feature (link a bug/review with a ref, not as parent); a feature's parent
must be an epic. Invalid links are rejected at create/link time and flagged by `sq check`.

## Browsing the squad

`sq` is the whole product — every mutation goes through it. Two extra clients exist for *reading* a
squad, which is what you do most once agents are the ones writing:

- **`sq ui`** — a terminal browser for the squad: the item tree, filters, full-text search, and a
  reader pane for any item. Needs the optional `tui` extra (`uv tool install "squads[tui]"`).
- **Squads for VS Code** — the same idea in the editor: work items, records, and roster as
  activity-bar trees, plus a rendered dossier per item with its sub-entities, discussion, and
  reference graphs. Install it from the VS Code Marketplace (search *Squads*), or from the `.vsix`
  attached to each release. Read-only, like `sq ui`.

---

## Concepts

- **Items** — every tracked thing is an item with a type and a stable ID. Ten types ship by
  default, in three **categories**:
  - **work** — `epic`, `feature`, `task`, `bug`, `review`: the things being built and reviewed.
  - **records** — `decision` (ADR), `guide`: the durable write-ups that outlive the work.
  - **roster** — `role`, `skill`, `operator`: who is on the team and what they know. These three
    keys always exist — a project can rename their labels and redefine their lifecycle, but can't
    drop them or move another type into the roster.
- **Your own vocabulary** — `<squad-dir>/.overrides/workflow.toml` is your squad's vocabulary delta:
  add types (with their own lifecycles, prefixes, and badge axes), shadow a bundled type or status
  field by field, or drop one you don't want. No status name is reserved — name your lifecycle
  states whatever your team already calls them. Templates and role definitions live under
  `<squad-dir>/.overrides/` too; `sq override` scaffolds them and flags drift when an upgrade
  changes the bundled original. To move items already filed under one vocabulary onto another, use
  `sq migrate rename-type` / `sq migrate rename-status`.
- **Global IDs** — `PREFIX-NNNNNN` with a single global counter, so the number is unique across
  all types (you never have both `TASK-<n>` and `BUG-<n>`). The prefix marks the type. Built-in
  prefixes are `EPIC FEAT TASK BUG ADR REV GUIDE ROLE SKILL OP`; custom types declare their own
  via the workflow override.
- **Source of truth** — the markdown **frontmatter** is durable truth; `squads/.squads.json` is a
  fast index that is fully rebuildable from the files (`sq repair`).
- **sq-owned files** — each item file carries invisible markers (`<!-- sq:body -->`,
  `<!-- sq:discussion -->`, …) around the regions `sq` maintains, alongside the frontmatter it
  owns outright. **Nobody hand-edits these files** — not you, not your agents: prose goes in with
  `sq <type> <n> body` (`--file` for long markdown), notes with `sq <type> <n> comment`, state with
  `sq <type> <n> status`.
- **Agents** — named roles (real name + slug, e.g. *Robert Architect* / `architect`). The `.claude/`
  files are pointers: each names the `sq` command that produces the full definition.

### On-disk layout

```
your-project/
├── .squads.toml                 # config (squad dir, active backends, version, default role)
├── CLAUDE.md                    # managed section: process + greeting impersonation
├── .claude/
│   ├── agents/<slug>.md         # POINTER → `sq role <slug> show`
│   └── skills/<skill>/SKILL.md  # POINTER → `sq skill <skill> show`
└── squads/                      # self-contained & relocatable (override with --dir)
    ├── .squads.json             # the index: counter + all items + refs
    ├── epics/ features/ tasks/ bugs/ adrs/ reviews/ guides/ operators/
    ├── board/                   # the team bulletin board
    └── agents/{roles,skills,memory}/
```

### Status workflows

The following table shows the **bundled default** status lifecycles:

| Type | Lifecycle |
|------|-----------|
| epic / feature / task | `Draft → Ready → InProgress → InReview → Done` (+ `Blocked`, `Cancelled`) |
| bug | `Open → InProgress → Fixed → Verified` (+ `WontFix`, `Blocked`, `Cancelled`) |
| decision (ADR) | `Proposed → Accepted → Superseded` (+ `Rejected`, `Deprecated`) |
| review | `Requested → InReview → ChangesRequested → Approved` (+ `Rejected`) |
| guide | `Draft → Published → Deprecated` |
| role / skill / operator | `Active ⇄ Archived` |

Sub-entities have their own, shorter lifecycles: a story or subtask runs `Todo → InProgress → Done`
(+ `Blocked`, `Cancelled`); a review finding runs `Open → Fixed → Verified` (+ `WontFix`).

A roster lifecycle also declares which of its statuses are **live** — the ones whose entries are
presented to an agent host. Archiving a role, skill or operator therefore **retires** it: its
generated files are withdrawn, and the transition is refused where the generated config couldn't
survive it. See [docs/roles.md](docs/roles.md#retiring-a-roster-entry).

Types can declare custom lifecycles via `<squad-dir>/.overrides/workflow.toml`.
`sq <type> <n> status <S>` validates transitions against the active spec; use `--force` to override
a transition the lifecycle disallows. `sq workflow` prints the lifecycles of whatever spec your
project is actually running, diagrams included.

---

## Documentation

Full docs (with diagrams) live in **[docs/](docs/README.md)**:

- **[tutorial](docs/tutorial.md)** — a 15-minute, end-to-end first squad.
- **[workflow](docs/workflow.md)** — who creates & links what, and the per-type status lifecycles.
- **[agents](docs/agents.md)** — operating *as* an agent inside a squad.
- **[roles](docs/roles.md)** — the bundled roster, bundles, and stack developers.
- **[recipes](docs/recipes.md)** — copy-paste sequences · **[faq](docs/faq.md)** — common errors.
- **[adoption](docs/adoption.md)** — migrating an existing project (`sq adopt`, `--at`).
- **[overrides](docs/overrides.md)** — customizing templates, roles, and item-type vocabulary under
  `.overrides/`, and reconciling drift across upgrades.
- **[migration](docs/migration.md)** — schema migrations: `sq migrate up`, the changelog, and the
  manual steps per release.
- **[stability](docs/stability.md)** — the 1.0 contract: which surfaces are stable after 1.0 and what each promises.
- **[internals](docs/internals.md)** / **[backends](docs/backends.md)** — under the hood & writing a backend.

The same docs are readable offline, without leaving the terminal: `sq docs` (add `--rich` to
pretty-print).

Of those, **[internals](docs/internals.md)** and **[backends](docs/backends.md)** are the two written
for contributors; the rest are for people *using* a squad.

**This file is the repo's front page.** Two sibling pages describe the same product to whoever
arrives somewhere else — **[PYPI.md](PYPI.md)** is the package's front page on PyPI, and
**[clients/vscode/MARKETPLACE.md](clients/vscode/MARKETPLACE.md)** the extension's on the
Marketplace. Also here: **[CONTRIBUTORS.md](CONTRIBUTORS.md)** and
**[CHANGELOG.md](CHANGELOG.md)**.

---

## Contributing

**[CONTRIBUTING.md](CONTRIBUTING.md)** is the working manual — setup, the full convention list, and
how to add a template, a command, an item type or a backend. What it helps to know before you open
it:

**The repo holds two toolchains, gated separately.** The Python core is the `sq` CLI; the VS Code
client under `clients/vscode/` is TypeScript with its own `package.json`, lockfile and lint config.
Neither gate reads the other's files.

```bash
# Python core — from the repo root
uv sync
uv run --all-extras pyright
uv run --all-extras ruff check . && uv run --all-extras ruff format --check .
uv run --all-extras pytest

# VS Code client — from clients/vscode/
npm install
npm run check          # tsc --noEmit + eslint + prettier
npm test               # vitest, no sq binary needed
```

`--all-extras` is not optional on the Python side: a bare `uv run` prunes the optional `tui` extra,
and `pyright` then reports hundreds of phantom unresolved-import errors from the terminal-UI code.

**Both gates must be green**, and `sq check` — the tool's own linter, run against this repo's squad —
must be clean for whatever you touched.

**Where things are documented.** [docs/internals.md](docs/internals.md) covers the core's layering
(`_cli → _services → index/backends/rendering`, with `_models` at the bottom);
[clients/vscode/README.md](clients/vscode/README.md) maps the extension and the conventions specific
to it. `CLAUDE.md` is the terse working reference the agents themselves read.

**The conventions most likely to bounce a change:** every core module and subpackage is
underscore-private and `__init__`s don't re-export; the markdown frontmatter is the source of truth
and `.squads.json` is only a rebuildable index; file content is edited through the marker helpers,
never by rewriting an authored body; time comes from the injectable clock, never `datetime.now()`;
and no tracked-item id appears in source, tests or config — the linkage belongs in the item, not the
code. `CONTRIBUTING.md` has the rest, with the reasoning.

---

## Command reference

**Setup**
- `sq init [--squad-dir squads] [--backend claude_code] [--roles all|core|minimal|<slugs>] [--name slug=Full Name] [--default-names] [--no-claude] [--force]` — `--backend` is repeatable
- `sq adopt [--squad-dir squads] [--backend] [--roles] [--no-claude]` — bring an *existing* project under sq management (non-destructive; imports existing items). See [docs/adoption.md](docs/adoption.md).
- `sq workflow [show|types|subentity-kinds|lifecycles|collections|statuses|roles|ref-kinds|lint]` — print the team-workflow cheatsheet (`show`), list one declared vocabulary section of the active spec, or validate workflow overrides
- `sq sync` — regenerate tool-owned managed files to the current version
- `sq override scaffold|list|diff|update` — author project-level template/role/workflow overrides and reconcile them across upgrades. See [docs/overrides.md](docs/overrides.md).
- `sq migrate up|help|chlog|rename-type|rename-status|repad` — bring a squad to the current schema, read the migration changelog, bulk-rename a type or status, or widen the ID padding. See [docs/migration.md](docs/migration.md).
- `sq ui` — the terminal browser (needs the `tui` extra) · `sq docs [--rich]` — the full docs, offline
- `--dir PATH` (global) — operate on the squad folder at PATH instead of walking up to `.squads.toml`
- `--at WHEN` (global) — forge timestamps (ISO 8601, UTC) for this command, to preserve history when migrating

Items are addressed by `<type> <number>` (bare `35`, padded `000035`, or full `TASK-<n>`; the
type word validates). Create with `sq create`; operate with `sq <type> <n> <verb>`. Every item-type
command has short aliases — `e f t b d r g`, plus `feat`/`dec`/`rev` — so `sq f 26 story 4 show`
works exactly like the canonical spelling.

**Items**
- `sq create epic|feature|task|bug|decision|review|guide TITLE --author <slug> [--parent ID] [--desc] [--label] [--ref ID] [--assignee] [--priority CODE] [-m "body"|--file] [--json]` — where `CODE` is from the bundled priority collection (urgent, high, medium, low) or a custom collection defined in the workflow override
- `sq list [--type|--status|--category|--parent|--label|--assignee|--priority|--min-priority|--badge|--min-badge|--sort] [--all] [--json]` · `sq tree [ROOT_ID] [--all] [--json]` — closed (Done/Cancelled/…) items are hidden unless `--all` (or an explicit `--status`); `tree --json` emits the nested subtree (status/priority/assignee/blocked) for orchestrating agents
- `sq <type> <n> show [--full] [--comments] [--raw] [--json]` — `--full` adds a pane per sub-entity, `--comments` the discussion: the whole dossier in one call · `sq show <ID>` shows any item by ID or bare number, whatever its type
- `sq <type> <n> body [-m "…"|--file PATH] [--append]` · `sq <type> <n> comments` — read the discussion back on its own
- `sq <type> <n> update [--title|--desc|--author|--status|--force|--parent|--no-parent|--assignee|--priority|--no-priority|--add-label|--rm-label|--set k=v|--unset k]`
- `sq <type> <n> status STATUS [--force]` · `sq <type> <n> comment -m "…" --as <slug>` — `--as` is required: a role slug, or `op-<slug>` for a human operator
- `sq <type> <n> retype NEW-TYPE` — reclassify an item, keeping its number · `sq <type> <n> remove [--force] [--yes]` — hard-delete it (asks first; `--force` severs incoming refs)

**Find & focus**
- `sq search TEXT [--type] [--status] [--json]` — match item titles, summaries, and bodies/discussion
- `sq blocked [--json]` — open items blocked by other open items (via the dependency ref kinds — `blocks` / `depends-on` by default)
- `sq mine <role> [--all] [--json]` — a role's open work: items assigned to it, **plus** items where one of its sub-entities (a story, subtask or finding) is assigned to it. The matched sub-entities are named in a `Matched` column and a `matched_subentities` key. Open/closed is judged per match, so a closed item still appears while your own sub-entity on it is open
- `sq workload [--json]` — open/closed/total counts per assignee, with each assignee's sub-entity assignment counts as their own columns beside the item counts (never folded in)
- `sq inbox <role> [--json]` — open items mentioning `@role`, naming the region each mention was found in (e.g. `story:US1:discussion#1`) so a mention inside a sub-entity's discussion is reachable

**Sub-entities** (stories on features, subtasks on tasks, findings on reviews)
- `sq feature <n> add-story "…" [--assignee] [-m|--file]` · `sq feature <n> stories`
- `sq task <n> add-subtask "…" [--story USn] [--assignee] [-m|--file]` · `sq task <n> subtasks`
- `sq review <n> add-finding "…" [--severity] [--assignee] [-m|--file]` · `sq review <n> findings`
- `sq <type> <n> <kind> <k> show|update|body|comment` — `update` sets `--title`/`--status`/`--assignee` (+ a subtask's `--story`, a finding's `--severity`)

`add-<kind>` **scaffolds an empty block**; set its body with the nested `… <kind> <k> body` (or pass
`-m`/`--file` to `add-<kind>`). `sq` owns the body, metadata (status/assignee/severity/story), and
discussion — all written through commands.

**Cross-linking**
- `sq <type> <n> ref add TARGET [--kind KIND]` · `sq <type> <n> ref rm TARGET` — `--kind` takes any kind the active workflow spec declares (`sq workflow ref-kinds` lists them; omit it for the declared default). The two dependency kinds are the two spellings of one edge (which end holds it differs; both feed `sq blocked`), and the supersession kind is what `sq check` looks for on a superseded record
- `sq <type> <n> refs [--out|--in|--all] [--json]` (forward edges stored; backrefs computed)
- `sq graph <ID> [--depth N] [--kind K] [--direction out|in|both] [--all] [--format dot|mermaid] [--json]` — the ref neighbourhood around one item

**Agents** — like items, roster entries are addressed first, then verbed: `sq role <slug> show`
- `sq role catalog [--json]` — the bundled roles available to activate · `sq role list [--json]` — the roles this squad has actually activated
- `sq role activate <slug>` · `sq role <slug|id|n> show|regen|rm [--purge]|status <S> [--force] [--unlink]`
- `sq role <slug|id|n> set-default` — move the default-role designation here, clearing the previous holder; refuses a role that isn't live
- `sq dev add --tech <t> [--name] [--model]` · `sq dev list` — stack-specific developers
- `sq operator add "NAME" [--slug]` · `sq operator list` · `sq operator <slug|id|n> show|rm [--purge]|status <S> [--force] [--unlink]` — register **humans** (`op-<first>` slug); assignable and can author items/comments
- `sq skill add NAME [--desc|--when-to-use|--allowed-tools]` · `sq skill <slug|id|n> show|body|regen|rm [--purge]|link-role <role>|unlink-role <role>|status <S> [--force] [--unlink]`
- Archiving a roster entry **retires** it: its generated files are withdrawn, the transition is refused where the generated config couldn't survive it, and `--unlink` severs a severable dependency so the ordinary check can pass — see [docs/roles.md](docs/roles.md#retiring-a-roster-entry)
- `sq create guide TITLE [--tech] [--tag]` — tech/tag-labelled guides; list them with `sq list --type guide`
- `sq memory <role> list|search|show|add|forget` — a role's committed notebook: facts it learned and should carry into the next session
- `sq board post|list|clear` — the team bulletin board: notices every agent reads at the start of a run

**Maintenance**
- `sq check` — lint markers, dangling parent/ref IDs, invalid status, index drift
- `sq repair [--renumber]` — rebuild the index from frontmatter, **and rewrite item files** on the same pass: it removes what squads now computes on every read and canonicalises legacy ref encodings, so run it on a clean working tree. `--renumber` also resolves merged ID collisions. `sq adopt`, `sq renumber` and the rebuild ending `sq migrate up` reach the same sweep — [what it writes](docs/faq.md#does-sq-repair-change-my-files)
- `sq renumber --onto N | --by N` — shift this branch's IDs clear of another branch's range before a merge
- `sq reflog [--item|--actor|--op|--since|--tail|--tree] [--json]` — the chronological log of every mutating `sq` command

---

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

---

## Backends

squads ships two backends. Choose them with `--backend` at `sq init` — the flag is repeatable, and
the resulting list lives in `.squads.toml` as `active_backends`, so a project can keep both current
at once and `sq sync` regenerates each one's files.

```toml
active_backends = ["claude_code", "agents_md"]
```

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

**Commit the merge resolution first.** Both of those rewrite item files as well as the index, and
neither can separate its changes from yours — so land the merge, then run `sq repair` on a clean
tree and review its diff on its own. See
[docs/faq.md](docs/faq.md#does-sq-repair-change-my-files) for what it writes.

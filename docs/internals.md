# squads internals

How squads works under the hood — for contributors, the curious, and agents that want to reason
about the tool rather than just call it. Pairs with [adoption.md](adoption.md) (migration) and the
repo's `CLAUDE.md` (contributor quick-reference).

> Module names below use the project's **private layout**: every implementation module and
> subpackage is underscore-prefixed (`squads._service`, `squads._models._item`,
> `squads._backends._claude_code._backend`, …) and package `__init__`s don't re-export. Read the
> names as "the `service` module", etc.

---

## 1. Mental model

squads turns a folder of markdown into a **JIRA-like tracker for a team of AI agents**. Three ideas
carry everything:

1. **Markdown is the truth.** Each tracked thing (epic, feature, task, bug, ADR, review, guide,
   role, skill) is one `.md` file. Its YAML frontmatter (`id`, `status`, `parent`, `refs`, …) is the
   **durable source of truth**.
2. **`.squads.json` is a rebuildable index.** A single JSON file caches every item + a global ID
   counter for fast queries and atomic ID allocation. It can always be reconstructed from the `.md`
   files (`sq repair`).
3. **`.claude/` is pointers, not content.** Files there route Claude Code to the real definitions
   under the squad folder; the tool owns them and regenerates them.

The layering is one-directional:

```
_cli  →  _service  →  ( _index store · _backends · _rendering )
_models / _paths / _workflow / _sections / _clock   — shared leaves, no internal deps upward
```

`_service.Service` is the façade every command calls; it's the only place that orchestrates the
index, the filesystem, the backend, and rendering together.

---

## 2. On-disk layout

```
<project root>/
├── .squads.toml          # config: squad_dir, default_backend, default_role, squads_version
├── CLAUDE.md             # managed section (between <!-- squads:start/end -->) + your own content
├── .claude/              # tool-owned pointers + config
│   ├── settings.json     # merged, never clobbered
│   ├── agents/<slug>.md  # POINTER → squads/agents/roles/ROLE-*.md  (with skills: frontmatter)
│   └── skills/<name>/SKILL.md   # POINTER → squads/agents/skills/<name>.md
└── squads/               # the squad folder — self-contained & relocatable (override with --dir)
    ├── .squads.json      # the index (counter + all items + refs)
    ├── .gitignore        # ignores .squads.json.lock and *.tmp
    ├── epics/ features/ tasks/ bugs/ adrs/ reviews/ guides/   # one folder per type → PREFIX-NNNNNN-slug.md
    └── agents/
        ├── roles/        # ROLE-*.md (real role definitions)
        └── skills/       # SKILL-*.md (user skills) + squads.md / sq-<type>.md (managed skill bodies)
```

- **`.squads.toml`** lives at the project root and points at the squad folder (default `squads/`).
  `_paths.resolve()` finds the active squad via `--dir` → walk up to `.squads.toml` → default.
- **The squad folder is self-contained** (`.squads.json` lives inside it), so it can be moved or a
  project can hold several and switch with `--dir`. Item `path`s are stored squad-folder-relative.

---

## 3. The index and the global counter (`_index/_store.py`, `_models/_index.py`)

`SquadsDB` is the JSON root: `{schema_version, squads_version, counter, items: {id → Item}}`.

- **One global monotonic counter.** `SquadsDB.allocate_id(type)` does `counter += 1` and formats
  `f"{type.prefix}-{counter:06d}"`. So an ID's *number* is unique across all types — there is never
  both `TASK-000002` and `BUG-000002`; the prefix only labels the type. Numbers reflect creation
  order, not hierarchy.
- **`IndexStore` is the integrity core.** All mutations go through `transaction()`:
  1. acquire a cross-process `filelock` on `<squad>/.squads.json.lock`,
  2. load + validate (`SquadsDB.model_validate_json`),
  3. yield the in-memory DB to mutate,
  4. commit with an **atomic write**: write a temp file in the same dir → `os.fsync` → `Path.replace`
     (atomic on POSIX/Windows). If the body raises, nothing is written.
  This makes concurrent `sq` invocations safe — two `create`s can't collide on an ID or corrupt the
  file. `load()` (used by read-only queries) wraps a malformed file in `SquadsError` ("corrupt index
  — run `sq repair`").

A write transaction:

```
Service.<mutation>()
  └─ IndexStore.transaction():
       ┌─ [lock]   filelock(.squads.json.lock)
       │   load + validate            ─▶ SquadsDB
       │   mutate  (e.g. allocate_id  ─▶ TASK-000007 ; counter += 1)
       │   render body, write the .md, db.add(item)
       └─ [commit] tmp file → fsync → atomic replace .squads.json → [unlock]
       (body raises anywhere above? → nothing is written)
```

## 4. Source of truth: frontmatter vs index

The frontmatter is durable; the index is derived. Two commands make that concrete:

```
   .md frontmatter  ── authoritative, durable ──────────────┐
       ▲   │                                                 │  sq repair → rebuild index from files
 write │   │ read                                            ▼
       │   └──────────────────────────▶  .squads.json  (fast, rebuildable index + global counter)
   create / status / update / comment keep BOTH in sync inside one locked transaction
```


- **`sq repair`** rescans every `PREFIX-*.md` under the type folders, rebuilds the index from their
  frontmatter, and sets `counter = max ID number`. `--renumber` additionally resolves duplicate
  numbers from a git merge (reassigns the colliding files to fresh numbers and rewrites every
  reference — parent/refs/inline — across all files).
- **`sq check`** lints the two against each other: unbalanced/duplicated markers, dangling
  parent/ref IDs, invalid status-for-type, on-disk-vs-index reconciliation, and frontmatter↔index
  drift. (Implemented as small per-rule helpers: `_scan_for_check`, `_check_reconciliation`,
  `_check_items`, `_check_subtask_stories`.)

Practical upshot: a `.squads.json` merge conflict is a non-event — take either side and
`sq repair`; for duplicate numbers, `sq repair --renumber`.

---

## 5. Item files: frontmatter + sq markers (`_sections.py`, `_itemfile.py`)

A typical task file:

```markdown
---
id: TASK-000007
type: task
title: Fix login
status: Draft
parent: FEAT-000002
refs: [GUIDE-000003]
created_at: '2026-06-07T10:00:00Z'
updated_at: '2026-06-07T10:00:00Z'
---
<!-- sq:body -->
## Description
(agent-authored prose)
<!-- sq:body:end -->

## Subtasks
<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

<!-- sq:discussion -->
<!-- sq:discussion:end -->
```

- **Markers** are invisible HTML comments `<!-- sq:<tag> -->` / `<!-- sq:<tag>:end -->`. They let
  `sq` find and edit *specific regions* without touching agent prose or marker lines. `_sections.py`
  is the only place file content is mutated: `get_section`, `replace_section`, `append_to_section`,
  `region_lines`, plus frontmatter `split/join/replace`. `find_markers` uses a strict regex
  (`sq:` + alnum start) so documentation like `` `<!-- sq:* -->` `` in prose isn't mistaken for a real
  marker.
- **Who writes what:** `sq` owns the frontmatter and the marker-delimited *discussion* (via
  `sq comment`); the **agent writes everything else directly** (the body, story/subtask prose). The
  rule is "never touch the marker lines."
- **`_itemfile.py`** maps `Item` ↔ file: `write_new` emits frontmatter + the rendered body;
  `update_frontmatter` rewrites *only* the frontmatter (body preserved verbatim); `read_frontmatter`
  parses it back for `repair`/`check`. `Item.to_frontmatter_dict()` / `from_frontmatter()` are the
  serialization bridge (timestamps via `_clock.iso`).

### Sub-entities: user stories, subtasks & findings (`_discussion.py`)

Features hold **user stories**, tasks hold **subtasks**, reviews hold **findings** — scaffolded
*inside the file*, not as separate IDs. `sq story/subtask/finding add` inserts a block into the
`sq:stories` / `sq:subtasks` / `sq:findings` container with **four** regions — note the sq-owned
`:meta`, where the block's tracked state lives (never the heading prose):

```markdown
<!-- sq:subtask:ST1 -->
### ST1 — Validate token expiry      ← plain title (agent-editable)
<!-- sq:subtask:ST1:meta -->         ← sq owns: status, + severity (findings) / story (subtasks)
status: InProgress
story: US2
<!-- sq:subtask:ST1:meta:end -->
<!-- sq:subtask:ST1:body -->          ← agent writes free-form prose here
<!-- sq:subtask:ST1:body:end -->
<!-- sq:subtask:ST1:discussion -->    ← sq appends comments here
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
```

Local ids (`US1`, `ST1`, `F1`) auto-increment via `next_local_id`. Each has a **status state
machine** (`SUBENTITY_WORKFLOWS`: subtask/story `Todo → InProgress → Done`; finding
`Open → Fixed → Verified`), transitioned with `sq <kind> status …` (validated; `--force` overrides;
`subtask done` is a shortcut). The parent carries an **sq-managed `sq:summary` table** that
`render_summary` rebuilds from `list_blocks` on every change. Pre-2 files (heading `[ ]`/`[x]`
checkbox + `(→ USn)`) are upgraded into `:meta` regions by the `v1 → v2` migration.

---

## 6. Types, statuses, and workflows (`_models/_enums.py`, `_workflow.py`)

- **`ItemType`** carries its `prefix` and `folder` (e.g. `DECISION` → `ADR` → `adrs/`).
  Prefixes: `EPIC FEAT TASK BUG ADR REV GUIDE ROLE SKILL`.
- **`Status`** is one enum of all values; `WORKFLOWS[type]` is a small per-type state machine
  (`initial`, `transitions`). `can_transition(type, src, dst)` gates `sq status` (`--force`
  overrides); a new item starts at the machine's initial state.
- **`TERMINAL` / `is_open`** scope the inbox to live work.
- **`ALLOWED_PARENTS` / `parent_allowed` / `parent_hint`** encode the hierarchy rules used below.

The actual per-type lifecycles and the team workflow (who creates/links what) live in their own
reference: **[workflow.md](workflow.md)**.

### Parent/child and refs

- **Parent** is the hierarchy edge. `ALLOWED_PARENTS` enforces the workflow spine —
  `task.parent` must be a **feature**, `feature.parent` must be an **epic** — validated at
  `create`/`link` and by `check` (`parent_allowed` / `parent_hint`).
- **Refs** are typed cross-links stored as **forward edges only**: `item.refs` is a list of strings,
  each carrying the kind inline — `"ID"` (the default `related`) or `"ID:kind"` (`fixes`,
  `addresses`, `implements`, …). `split_ref`/`make_ref` in `_models/_item.py` parse and format them.
  **Backrefs are never stored** — `refs_in` / `SquadsDB.backrefs` compute them by inverting the
  forward edges (matching on the ID part) at query time. So a task fixing a bug does
  `sq ref add TASK BUG --kind fixes`; the bug shows the backref on demand.

```
 stored   (forward) :  TASK-000007.refs = ["BUG-000009:fixes"]
 computed (inverse) :  refs_in(BUG-000009)  →  [(TASK-000007, fixes)]      # never persisted
```

> Before `schema_version` 2 the kind lived in a separate `extra["ref_kinds"]` `{ID: kind}` map;
> it's now folded inline. Old files are read transparently (`Item.from_frontmatter`) — see
> [migration.md](migration.md).

### Discussion, @mentions, inbox

`sq comment` appends a timestamped entry — `- [ISO] <Full Name>:` + one sub-item per `-m` — under
the right discussion anchor (top-level, or a story/subtask's). `@role` mentions in the text feed
`sq inbox <role>`, which scans open items for `@role` and surfaces the matching lines. The author is
resolved from `--as <slug>` → the role's full name.

---

## 7. The Claude Code backend (`_backends/`)

Backends are pluggable behind the `AgentBackend` ABC (`ensure_scaffold`, `write_managed`,
`generate_role_pointer`, `generate_skill_pointer`, `remove_artifacts`). `ClaudeCodeBackend` is the
first implementation; a `_registry` maps names → backends and the `_claude_code` package registers
itself on import. Nothing outside a backend reaches into `.claude/`.

Everything in `.claude/` is a thin pointer into the squad folder (the real, durable content):

```
   .claude/agents/architect.md ─────@──▶ squads/agents/roles/ROLE-000002-architect.md   (role def)
   .claude/skills/sq-task/SKILL.md ─@──▶ squads/agents/skills/sq-task.md                 (skill body)
   CLAUDE.md  <!-- squads:start … end -->  ◀── regenerated managed section (roster, workflow)
   .claude/settings.json                   ◀── merged (union of permissions.allow), never clobbered
```

What it generates:

- **Role pointers** — `.claude/agents/<slug>.md`: frontmatter (`name`=slug, `description`, `model`,
  `color`, and a `skills:` list) + a body that says *"You are <Full Name>… load your full definition
  at `@squads/agents/roles/ROLE-…md`"*. The real role definition lives under the squad folder.
- **Managed skills** — the general `squads` skill plus one `sq-<type>` skill per item type. Each
  follows the pointer pattern: the **real body** is written to `squads/agents/skills/<name>.md`
  (carrying a "managed — regenerated by `sq sync`" header) and a **thin pointer** `@`-imports it from
  `.claude/skills/<name>/SKILL.md`. Item skills contain one **role-directed section** per *active*
  interacting role (see the playbook below).
- **CLAUDE.md section** — a marker-delimited (`<!-- squads:start/end -->`) block injected into the
  project `CLAUDE.md`: the roster, the **greeting-impersonation** rule ("Hi Robert" → adopt Robert
  Architect; default to Catherine Manager), and the team workflow.
- **settings.json** — created if absent, else **merged** (union of `permissions.allow`), never
  clobbering your keys.

`BackendContext` carries the resolved `SquadPaths` + version and the `rel()` helper (project-root-
relative, forward-slash paths used in pointers and `Artifact` records). `sq sync` regenerates every
managed file to the current version and stamps `.squads.toml`; any command notices when the
installed version is newer than the recorded one and nudges you to run it.

---

## 8. Roles and the playbook (`_roles/_catalog.py`, `_interactions.py`)

- **Bundled roles** — 8 `RoleDef`s, each with a real name + slug (Catherine Manager `manager`
  [default/triage], Robert Architect `architect`, Olivia Lead `tech-lead`, Paul Reviewer
  `reviewer`, Mara Tester `qa`, Hugo Ops `devops`, Nina Product `product-owner`, Theo Writer
  `tech-writer`). `BUNDLES` (`all`/`core`/`minimal`) select sets at `init`/`adopt`. **Developers**
  are made on demand: `dev_role(tech)` names them from a pool (`Elias Dotnet`, slug `dotnet-dev`).
- **The playbook** (`PLAYBOOK`) is a matrix: for each item type, the interacting roles + a one-line
  guidance each (the `DEV` sentinel matches any `<tech>-dev`). It drives two things:
  - **item skills** — `sq-feature` gets a "For Nina Product (`product-owner`)" section, etc.
    (filtered to roles active in this squad);
  - **`skills_for_role(slug)`** — which skills a role's pointer preloads. *A role that doesn't manage
    a type gets no skill for it* (manager/devops get only the general `squads` skill).

Role/dev/skill metadata is stored in the item's `extra` dict; its keys are centralized in
`_models/_extras.py::ExtraKey` (never hand-write the literals).

---

## 9. Rendering (`_rendering/`)

A single Jinja2 `Environment` (`PackageLoader("squads._rendering", "templates")`,
`StrictUndefined` so a missing variable is a loud error, a `slugify` filter, `autoescape=False`
because output is Markdown/JSON not HTML). Templates ship as **package data** in the wheel:
`items/<type>.md.j2`, `agents/{role,skill,squads_skill,item_skill}.md.j2`,
`claude/{pointer_agent,pointer_skill,claude_section,settings.json}.md.j2`, and `workflow.md.j2`
(the cheatsheet shared by the `squads` skill and `sq workflow`).

## 10. Time & determinism (`_clock.py`)

All timestamps come from `_clock.now()` — never `datetime.now()` directly — so tests can freeze it
and the **`--at WHEN`** global option can forge it. `set_now(dt)` overrides `now()` for one CLI
invocation (parsed by `parse_iso`), which is how a migration preserves historical dates across
`create`/`status`/`comment`/… (see [adoption.md](adoption.md)).

## 11. The CLI (`_cli/`)

Typer app, exposed twice as `squads`/`sq` (entry point `squads._cli:app`). The root callback reads
the global `--dir` and `--at`, runs the version notice, and dispatches. Conventions:

- Errors that are the user's to see subclass `SquadsError`; a `@handle_errors` decorator turns them
  into a clean message + exit 1 (the corrupt-index and validation paths funnel here).
- Dynamic strings printed to the console go through `e()` (Rich-escape) so a `[x]` checkbox or a
  bracketed title isn't parsed as Rich markup.
- Each command group is its own `_module`; `_common.py` holds the shared console, error decorator,
  service resolver, and value parsers.

---

## 12. Lifecycle of a command — `sq create task "Fix login" --parent FEAT-000002`

```
 sq create task … --parent FEAT-000002
   │
   ├─ root callback: set --dir / --at, version notice
   ├─ _cli/_create.py  ──▶  get_service()  ──▶  _paths.resolve()  ──▶  SquadPaths
   └─ Service.create(TASK, "Fix login", parent=FEAT-000002)
        └─ IndexStore.transaction()  [lock .squads.json]
             ├─ _check_parent: parent_allowed(TASK, FEATURE)        ✓  (epic → SquadsError)
             ├─ allocate_id(TASK) → TASK-000007                     (counter += 1)
             ├─ build Item (status=Draft, created/updated = clock.now())
             ├─ render items/task.md.j2 → write_new(tasks/TASK-000007-fix-login.md)
             └─ db.add(item)  →  atomic write .squads.json          [unlock]
   ◀─ prints the file path;  agent fills the <!-- sq:body --> region
```

1. **CLI** (`_cli/_create.py`) parses args; the root callback already set the active dir / `--at`.
2. `get_service()` → `_paths.resolve()` builds `SquadPaths` (which squad folder, where the index is).
3. `Service.create(TASK, "Fix login", parent="FEAT-000002")`:
   - opens `store.transaction()` (locks `.squads.json`);
   - `_check_parent` → `parent_allowed(TASK, FEATURE)` ✓ (an epic here would raise);
   - `db.allocate_id(TASK)` → `TASK-000007` (global counter bumped);
   - builds the `Item` (status = `initial_status(TASK)` = `Draft`, `created_at`/`updated_at` =
     `clock.now()`), squad-relative path `tasks/TASK-000007-fix-login.md`;
   - renders `items/task.md.j2` (body + empty markers), `write_new` emits frontmatter + body;
   - `db.add(item)`; on clean exit the index is atomically rewritten.
4. The CLI prints the path; the agent opens the file and fills the `sq:body` region.

`status`, `comment`, `link`, `ref`, `update`, `subtask`/`story` follow the same shape — mutate inside
a locked transaction (or a marker-safe section edit), stamp `updated_at` from `clock.now()`.

---

## 13. Scaling & performance characteristics

squads is built for a team's working set — tens to low-thousands of items — and the data model
reflects that: **the index is a single JSON document, read and rewritten in full.** That keeps the
integrity story simple (one atomic file, one lock, frontmatter as truth) at the cost of several
operations being **O(total items)** rather than O(items touched). None of this matters at ~1,000
items, where Python interpreter + Typer/pydantic import startup (~100–200 ms) dominates every
command; the index work is single-digit-to-low-tens of milliseconds. The notes below are about
*where the curve bends* if a repo ever grows an order of magnitude or two.

**Whole-index read on every command.** `IndexStore.load()` (`_index/_store.py`) runs
`SquadsDB.model_validate_json` over the entire file, so pydantic constructs and validates *every*
`Item` on each invocation — even `sq show ONE-ID`. Cost is linear in item count.

**Whole-index rewrite on every mutation (write amplification).** `transaction()` re-serializes
*all* items (`SquadsDB.to_json` → `model_dump_json(indent=2)`), writes the whole ~1 KB/item file,
`fsync`s, and renames — changing one status field rewrites the lot. This is the main architectural
cost; it's also serialized by the cross-process `filelock`, so the second scaling axis is
items × concurrent writers (a fleet of agents each shelling out `sq`).

**O(n) ref scans.** `SquadsDB.backrefs()` (`_models/_index.py`) and `Service.refs_in()` scan all
items to invert forward edges. One call per command is fine; the trap is calling them **per item**
(e.g. a backref column on `sq list`/`tree`) — that's **O(n²)**. Forward refs (`refs_out`) and
`get(id)` are dict lookups and stay cheap.

**File fan-out commands.** Most commands touch the index only (`list`) or one `.md` (`show`,
`comment`, `status`). Three fan out over *every* markdown file and are the first you'd feel at
scale: `sq inbox` (`_service.inbox`) opens + mention-scans each open item's file; `sq check`
(`_service.check`, esp. `_check_subtask_stories`) reads every file and re-reads each task's file and
its parent feature inside the loop; `sq repair` parses every file (twice, when renumbering).
`check`/`repair` are occasional maintenance; `inbox` is user-facing, so it's the one to watch.

**Rough guide (single SSD, warm imports):**

| Concern | ~1,000 items | Where it bends |
| --- | --- | --- |
| Full parse per read | ~5–20 ms (hidden by startup) | ~10k+ |
| Full rewrite + `fsync` per write | ~10–25 ms | ~10k–50k |
| `sq inbox` file fan-out | tens–hundreds of ms | first felt |
| `sq check` / `repair` fan-out | ~0.1–1 s, rare | ~50k+ |
| `backrefs` / `refs_in` | trivial (one pass) | only if called per-item → O(n²) |

**If you ever target large repos** (highest leverage first): replace the full-file rewrite with an
embedded store (SQLite) or partial/streamed writes to kill write amplification; keep an in-memory
mention/backref index so `inbox`/`refs` don't fan out over files; and drop `indent=2` on the on-disk
JSON (`_models/_index.py`) to roughly halve parse/serialize/IO. All three preserve the invariant
that the index stays rebuildable from frontmatter (§4), so they're additive, not a redesign.

## 14. Conventions that keep it honest

- **Frontmatter is truth; the index is rebuildable** — never store anything in `.squads.json` that
  can't be reconstructed from the `.md` files.
- **One global counter; allocate only inside a transaction.**
- **Marker-safe edits only** — touch content via `_sections.py`; never rewrite an agent's body.
- **Forward edges only; backrefs computed.**
- **`.claude/` is pointers + tool-owned config; real content lives under the squad folder.**
- **No `from __future__ import annotations`** (Python 3.14 / PEP 649) and an **acyclic import graph**.
- **Strict gate**: `pyright` (strict) + `ruff` (with complexity/PLR/SIM/PERF/PTH/TRY) + `pytest`
  must stay green.

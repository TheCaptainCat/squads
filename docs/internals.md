# squads internals

How squads works under the hood — for contributors, the curious, and agents that want to reason
about the tool rather than just call it. Pairs with [migration.md](migration.md) (upgrading a squad)
and [adoption.md](adoption.md) (importing history).

> Module names below use the project's **private layout**: every implementation module and
> subpackage is underscore-prefixed (`squads._services._service`, `squads._models._item`,
> `squads._backends._claude_code._backend`, …) and package `__init__`s don't re-export. Read the
> names as "the `service` module", etc.

---

## 1. Mental model

squads turns a folder of markdown into a **JIRA-like tracker for a team of AI agents**. Three ideas
carry everything:

1. **Markdown is the truth.** Each tracked thing — every item of every declared type, roster
   entries included — is one `.md` file. Its YAML frontmatter (`id`, `status`, `parent`, `refs`, …)
   is the **durable source of truth**. `sq workflow types` lists the types your spec declares.
2. **`.squads.json` is a rebuildable index.** A single JSON file caches every item + a global ID
   counter for fast queries and atomic ID allocation. It can always be reconstructed from the `.md`
   files (`sq repair`).
3. **`.claude/` is pointers, not content.** Files there route Claude Code to the real definitions
   under the squad folder; the tool owns them and regenerates them.

The layering is one-directional:

```
_cli  →  _services  →  ( _index store · _backends · _rendering )
_models / _paths / _workflow / _sections / _clock   — shared leaves, no internal deps upward
```

`Service` (`_services/_service.py`) is the façade every command calls, composed from one mixin per
concern (items, sub-entities, refs, roster, maintenance, …); it's the only place that orchestrates
the index, the filesystem, the backends, and rendering together.

---

## 2. On-disk layout

```
<project root>/
├── .squads.toml          # config: schema_version, squad_dir, active_backends, squads_version
├── CLAUDE.md             # claude_code backend: managed section (between <!-- squads:start/end -->) + your own content
├── AGENTS.md             # agents_md backend, when active: the same kind of managed section
├── .claude/              # claude_code backend: tool-owned pointers + config
│   ├── settings.json     # merged, never clobbered
│   ├── agents/<slug>.md  # POINTER → `sq role <slug> show`  (with skills: frontmatter)
│   └── skills/<name>/SKILL.md   # POINTER → `sq skill <name> show`
└── squads/               # the squad folder — self-contained & relocatable (squad_dir in .squads.toml)
    ├── .squads.json      # the index (counter + padding + all items + refs)
    ├── .reflog.jsonl     # append-only log of every mutating command
    ├── .gitignore        # ignores .squads.json.lock and *.tmp
    ├── epics/ features/ tasks/ bugs/ adrs/ reviews/ guides/ contracts/ milestones/
    │                     # bundled default folders; custom types use declared folders
    ├── .overrides/
    │   ├── workflow.toml # custom item types, statuses, lifecycles, badge collections
    │   ├── roles.toml    # role catalog delta (roles, bundles, [dev] table)
    │   ├── playbook.toml # playbook delta (per-type role guidance)
    │   └── templates/ roles/    # template and per-role overrides
    ├── operators/        # OP-*.md (the humans on the project)
    └── agents/
        ├── roles/        # ROLE-*.md — a role's identity; its body holds only its view tag
        └── skills/       # SKILL-*.md — an authored skill's body; a managed skill's body holds only its view tag
```

- **`.squads.toml`** lives at the project root and points at the squad folder (default `squads/`).
  `_paths.resolve()` finds the active squad one way: it walks up from the directory `sq` runs in
  (the process directory, or the one `-C` names) to the first `.squads.toml` and uses its
  `squad_dir`.
- **The squad folder is self-contained** (`.squads.json` lives inside it), so it can be moved:
  point `squad_dir` at its new place. Item `path`s are stored squad-folder-relative.
- **Type-to-folder mapping is customizable** via `.overrides/workflow.toml` (see [overrides.md](overrides.md)
  and [workflow.md](workflow.md)). The bundled default gives each declared type its own folder.
  Custom item types declare their own folder in the override.

---

## 3. The index and the global counter (`_index/_store.py`, `_models/_index.py`)

`SquadsDB` is the JSON root: `{schema_version, squads_version, counter, padding, items: {sequence# → Item}}`
(`padding` is the filename width, default 6).
Items are **keyed by their integer `sequence_id`** (the global counter number — the item's real
identity); the formatted `id` (`TASK-<n>`) is *derived* from `type` + `sequence_id`, and displayed unpadded.
Both `id` and `sequence_id` are persisted in `.md` frontmatter. A legacy full-id-keyed index still loads (keys normalized on read).

- **One global monotonic counter.** `SquadsDB.allocate_id(type)` does `counter += 1` and formats it at the squad's
  filename-padding width (e.g., `TASK-NNNNNN` on disk). An ID's *number* is unique across all types — there is never
  both item 2 with `TASK` prefix and item 2 with `BUG` prefix; the prefix only labels the type. Numbers reflect
  creation order, not hierarchy. Display always shows the unpadded form (`TASK-<n>`).
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
       │   mutate  (e.g. allocate_id  ─▶ TASK-NNNNNN for filename; counter += 1)
       │   render body, write the .md with unpadded id (TASK-<n>), db.add(item)
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
  frontmatter, and raises `counter` to the highest number seen on disk, never lowering it, so a
  removed top number stays retired across a repair (`padding` is carried the same way, as a floor).
  `--renumber` additionally resolves duplicate
  numbers from a git merge. Distinct IDs sharing a number get fresh numbers and every reference
  (parent/refs/inline) is rewritten across all files. One ID carried by several files is
  renumbered without touching references, which are listed for a hand check instead, because
  none can be attributed to one copy (see [the FAQ](faq.md#handling-id-collisions)).

  **The rescan also writes.** On the same walk it strips from each file what is now computed on
  every read rather than stored — the sub-entity roll-up table and badge lines, and the retired
  keys a role item mirrored from its definition — and canonicalises any legacy ref
  encoding. A role or skill body that holds prose is left alone; an empty role body, or an empty
  body on a generated skill, gets its view tag written back. Markdown is written before the index commit, as everywhere else. So `repair` is not an index-only job: on
  a corpus carrying that content it produces a content diff, and it should be run on a clean
  working tree. `sq adopt` and `sq renumber` reach the same rescan and perform the same rewrite,
  and `sq migrate up` ends with it; all four print the same one-line notice counting what they
  rewrote, and each names those items in the reflog. The notice has one constructor, shared by
  every result type a sweep-reaching command returns, so no route can drift out of it.
- **`sq check`** lints the two against each other: unbalanced/duplicated markers, dangling
  parent/ref IDs, one ID carried by several files, invalid status-for-type, on-disk-vs-index reconciliation, and frontmatter↔index
  drift. It runs in two tiers: a raw-text scan of every file (`_scan_for_check`, for findings that
  must survive a file too broken to parse), then the named validator catalog in
  `_services/_validators.py` — per-item rules such as `parent_in`, `item_status_valid`,
  `dangling_ref` and `subentity_body_written`, selected per type by the spec, plus squad-wide ones:
  always-on checks such as `index_reconciled` and `backend_reconciled`, and the opt-in checks the
  spec's `[squad]` table selects, such as `dependency_acyclic`.

Practical upshot: a `.squads.json` merge conflict is a non-event — take either side and
`sq repair`; for duplicate numbers, `sq repair --renumber`. Commit the resolution first: the
rebuild may rewrite item files as well as the index.

---

## 5. Item files: frontmatter + sq markers (`_sections.py`, `_itemfile.py`)

A typical task file:

```markdown
---
id: TASK-<n>
sequence_id: 7
type: task
title: Fix login
status: Draft
parent: FEAT-<n>
author: tech-lead
refs: [GUIDE-<n>]
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

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
```

- **Markers** are invisible HTML comments `<!-- sq:<tag> -->` / `<!-- sq:<tag>:end -->`. They let
  `sq` find and edit *specific regions* without touching agent prose or marker lines. `_sections.py`
  is the only place file content is mutated: `get_section`, `replace_section`, `append_to_section`,
  `region_lines`, plus frontmatter `split/join/replace`. `find_markers` uses a strict regex
  (`sq:` + alnum start) so documentation like `` `<!-- sq:* -->` `` in prose isn't mistaken for a real
  marker.
- **Who writes what:** `sq` owns the whole file — frontmatter, markers, and every region. The agent
  authors content through commands (`sq <type> <n> body` / `sq <type> <n> <kind> <k> body` for
  bodies, `sq <type> <n> comment` for discussion), never by editing the `.md` directly.
- **`_itemfile.py`** maps `Item` ↔ file: `write_new` emits frontmatter + the rendered body;
  `update_frontmatter` rewrites *only* the frontmatter (body preserved verbatim); `read_frontmatter`
  parses it back for `repair`/`check`. `Item.to_frontmatter_dict()` / `from_frontmatter()` are the
  serialization bridge (timestamps via `_clock.iso`).

### Sub-entities: user stories, subtasks & findings

Features hold **user stories**, tasks hold **subtasks**, reviews hold **findings** — tracked
*inside the parent item*, not as separate IDs. Which kind a type hosts is spec vocabulary
(`ItemSpec.subentity_kind` → `WorkflowSpec.subentity_kinds`), so those three pairings are the
bundled default rather than a fixed law; `_discussion.py` takes the `kind` as an argument
throughout. Their **machine state** (status, assignee, severity,
mapped story, title) is a typed `subentities:` list in the parent's **frontmatter** (`SubEntity`,
`_models/_subentity.py`) — single-sourced, pydantic-validated, and carried in the index. Each
sub-entity also gets a marker-scoped **block in the body**, inside the parent's container region,
holding only its heading and prose:

```markdown
<!-- sq:subtask:STn -->
### STn — Validate token expiry       ← heading rendered from the frontmatter title

<!-- sq:subtask:STn:body -->          ← agent writes free-form prose here
<!-- sq:subtask:STn:body:end -->

#### Discussion

<!-- sq:subtask:STn:discussion -->    ← sq appends comments here
<!-- sq:subtask:STn:discussion:end -->
<!-- sq:subtask:STn:end -->
```

The presentation is not stored: the badge line (status, assignee, severity, story) is computed from
the frontmatter state each time `show` prints a block, and the parent's roll-up table is a derived
view of the same state. `sq repair` strips any stored copy of either that an older squad still
carries.

Local ids (`USn`, `STn`, `Fn`) auto-increment via `next_local_id` (over the stored list). Each has a
**status state machine** (`SUBENTITY_WORKFLOWS`: subtask/story `Todo → InProgress → Done`; finding
`Open → Fixed → Verified`), transitioned with `sq <type> <n> <kind> <k> update --status …` (validated;
`--force` overrides) — `update` is the one metadata entry point (`--title`/`--status`/`--assignee`, a
subtask's `--story`, a finding's `--severity`); the service edits the model atomically (index
transaction), and a title change re-renders the block's heading. A
body-stored `:meta` region, from a squad written before schema 0.3, is lifted into frontmatter by
the `0.2 → 0.3` migration; its read/build helpers live only in `_migrations/_meta_compat.py`.

---

## 6. Types, statuses, and workflows

The vocabulary is data, not code: bundled TOML under `_specs/` (`workflow.toml`), parsed and
validated by `_workflow/_loader.py` into the models in `_workflow/_models.py`. There is no enum of
types or statuses and no built-in prefix→folder table: the spec is the sole authority. `_models/_vocab.py` is the resolver callers go through for a type's prefix and display
labels; folder resolution routes through `SquadPaths.folder_for` / `squad_relative` instead, which
consults the spec.

- The loaded `WorkflowSpec` is the sole type-vocabulary authority (`spec.items`, keyed by
  plain `str`): each type's `prefix` and `folder` (e.g. `decision` → `ADR` → `adrs/`) come
  from there, resolved via `prefix_for(type, spec)`. The only structurally reserved names
  are the three roster types (`role`/`skill`/`operator`, `category = "roster"`); every work type is
  ordinary, droppable/renamable spec vocabulary.
- **Statuses are declared names** (plain `str`), each carrying a `StatusSpec` whose `role` points at
  an entry in `spec.roles` — the status-role catalog, the single source of a status's
  `settled`/`hidden`/`live`/`colour` behaviour. Lifecycles are separately-named state machines
  (`initial`, `transitions`) that types and sub-entity kinds bind to by name, so two types can share
  one. `WORKFLOWS[type]` is the per-type machine; `can_transition(type, src, dst)` gates
  `sq <type> <n> status` (`--force` overrides); a new item starts at its machine's initial state.
- **`TERMINAL` / `is_open`** scope the inbox to live work. Neither is stored: both are derived from
  the referenced role's `settled` flag (`is_open` is `not role_for(status).settled`), and
  `hidden_by_default` is likewise `role_for(status).hidden`.
- **`ALLOWED_PARENTS` / `parent_allowed` / `parent_hint`** encode the hierarchy rules used below.

> **The module-level names above are views over the *bundled* spec**, loaded once at import and kept
> for the golden-lock tests and direct callers. They are not override-aware. The capabilities live as
> methods on `WorkflowSpec`, and the active (possibly project-overridden) spec is threaded
> explicitly — `Service.spec` in the service layer, `_common.get_active_spec()` at CLI call sites.
> There is no process-global mutable spec. Use the threaded spec for anything a project can
> customise.

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
  `sq task <n> ref add <bug> --kind fixes`; the bug shows the backref on demand.

```
 stored   (forward) :  TASK-<n>.refs = ["BUG-<m>:fixes"]
 computed (inverse) :  refs_in(BUG-<m>)  →  [(TASK-<n>, fixes)]      # never persisted
```

(Refs are stored unpadded by default; old refs may retain padded width from before a migration, and both resolve correctly.)

> A file written before `schema_version` 0.2 holds the kinds in a separate `extra["ref_kinds"]`
> `{ID: kind}` map. `sq migrate up` folds it inline, through the compat reader under
> `_migrations/`; the model itself reads no `extra` — see [migration.md](migration.md).

### Discussion, @mentions, inbox

`sq <type> <n> comment` appends a timestamped entry — ``- [<timestamp>] `<slug>` <name>:`` + one
sub-item per `-m` — under the right discussion anchor (top-level, or a story/subtask/finding's).
`comment <hash> edit` rewrites one entry in place and adds `, edited <timestamp>` inside the
brackets; `comment <hash> remove` takes it out. Each comment's hash is computed on read from its
item, scope, header and text, and is never stored.
`@role` mentions in the text feed `sq inbox <role>`, which scans open items for `@role` and
surfaces the matching lines. The header stores the `--as <slug>` itself, which is the author's
identity, and the display name resolved from it at write time (a role's name, an operator's full
name), which is a snapshot that a later rename does not touch. Every reader parses a header with
the one pattern, anchored at the left margin; the grammar is in
[stability.md](stability.md#comment-headers).

---

## 7. Backends (`_backends/`)

Backends are pluggable behind the `AgentBackend` ABC, whose seven abstract methods are
`ensure_scaffold`, `write_managed`, `generate_role_entry`, `generate_skill_entry`,
`remove_artifacts`, `candidate_orphans` and `managed_paths`. Two ship: `claude_code` (the
`.claude/` pointers, `settings.json` and the `CLAUDE.md` managed section, described below) and
`agents_md` (one `AGENTS.md` managed section, compiled from the roster; it writes no per-entry
files). `.squads.toml`'s `active_backends` picks which run. A `_registry` maps names → backends and
each backend package registers itself on import. Nothing outside a backend reaches into `.claude/`.
[backends.md](backends.md) covers writing a third.

Everything in `.claude/` is a thin pointer: it carries the identity the host selects the entry by,
and names the `sq` command that produces the rest.

```
   .claude/agents/architect.md ─────▶ `sq role architect show`   (definition rendered on read)
   .claude/skills/sq-task/SKILL.md ─▶ `sq skill sq-task show`    (definition rendered on read)
   CLAUDE.md  <!-- squads:start … end -->  ◀── regenerated managed section (roster, workflow)
   .claude/settings.json                   ◀── merged (union of permissions.allow), never clobbered
```

What it generates:

- **Role pointers** — `.claude/agents/<slug>.md`: frontmatter (`name`=slug, `description`, `model`,
  `color`, `disallowedTools: Agent` on a role that may not spawn subagents, and a `skills:` list) + a body that says *"You are <Full Name>… load your full definition
  with `sq role <slug> show`"*. The role's file under the squad folder holds its identity and a view
  tag; that command renders the definition.
- **Managed skills** — the general `squads` skill, `greeting`, `sq-memory`, and one `sq-<type>`
  skill per non-roster item type. Each
  gets a **thin pointer** at `.claude/skills/<name>/SKILL.md` naming `sq skill <name> show`. The
  definition that command prints is rendered from templates when it is read, so the skill's own
  file under `squads/agents/skills/` holds frontmatter and an empty body region — an authored
  skill is the other way round, its body being real stored content. Item skills contain one
  **role-directed section** per *active* interacting role (see the playbook below).
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

## 8. Roles and the playbook

Two bundled TOML documents under `_specs/`, each with a loader and a spec model beside it: the role
catalog (`_specs/roles.toml`, read through `_roles/`) and the playbook (`_specs/playbook.toml`, read
through `_interactions/`). Both are project-overridable — `.overrides/roles/<slug>.toml` and
`.overrides/playbook.toml`.

- **Bundled roles** — 8 `RoleDef`s, each with a real name + slug (Catherine Manager `manager`
  [default/triage], Robert Architect `architect`, Olivia Lead `tech-lead`, Paul Reviewer
  `reviewer`, Mara Tester `qa`, Hugo Ops `devops`, Nina Product `product-owner`, Theo Writer
  `tech-writer`). `BUNDLES` (`all`/`core`/`minimal`) select sets at `init`/`adopt`. **Developers**
  are made on demand from the `[dev]` table of the squad's resolved catalog, named from its pool
  (`Elias Dotnet`, slug `dotnet-dev` by default). A developer is any live role holding a capability
  that table declares (`dev`).
- **The playbook** (`PLAYBOOK`, a thin shim over the loaded `PlaybookSpec`) is a matrix: for each
  item type, the interacting roles + a one-line guidance each. A guide addresses a role slug, or
  every live role holding a capability with `*<capability>` (the bundled `*dev` guides reach every
  developer). It drives two things:
  - **item skills** — `sq-feature` gets a "For Nina Product (`product-owner`)" section, etc.
    (filtered to roles active in this squad);
  - **`skills_for_role(slug)`** — which skills a role's pointer preloads. *A role that doesn't manage
    a type gets no skill for it* (manager/devops get only the general `squads` skill).

Role/dev/skill metadata is stored as **attributes**: top-level frontmatter keys that the type
declares in the workflow spec (`[items.<type>.attributes]`), held on the model as one
`Item.attributes` mapping together with any undeclared key, which is carried and never read. The
loader pins the `role` and `skill` attributes the engine writes into agent files. Internal readers
go through `_models/_attributes.py::AttributeKey` and the `item.attribute(...)` accessor or a typed
roster accessor, never a string literal.

---

## 9. Rendering (`_rendering/`)

A single Jinja2 `Environment` (`PackageLoader("squads._rendering", "templates")`,
`StrictUndefined` so a missing variable is a loud error, a `slugify` filter, `autoescape=False`
because output is Markdown/JSON not HTML). Templates ship as **package data** in the wheel, and a
project override under `.overrides/templates/` must use the same relative path:

- `items/<type>.md.j2` — one per bundled type (`bug`, `contract`, `decision`, `epic`, `feature`,
  `guide`, `milestone`, `review`, `task`), plus `items/_default.md.j2` for a type with none
- `agents/{operator,role,skill}.md.j2` — roster item files
- `views/{squads_skill,item_skill,greeting_skill,memory_skill,role_definition,milestone_rollup}.md.j2`
  — the derived views rendered on read (managed skill definitions, a role's definition, a
  milestone's roll-up)
- `claude/{pointer_agent,pointer_skill,claude_section}.md.j2` and `claude/settings.json.j2` — the
  `claude_code` backend; `agents_md/agents_section.md.j2` — the `agents_md` backend
- `subentities/{block,head,summary}.md.j2` — a sub-entity's body block; `head` and `summary` are
  kept for migrations, which still read and write the retired presentation regions
- `workflow.md.j2` and `workflow_static.md.j2` — the workflow cheatsheet shared by the `squads`
  skill, `sq workflow` and the `AGENTS.md` section

## 10. Time & determinism (`_clock.py`)

All timestamps come from `_clock.now()` — never `datetime.now()` directly — so tests can freeze it
and the **`--at WHEN`** global option can forge it. `set_now(dt)` overrides `now()` for one CLI
invocation (parsed by `parse_iso`), which is how a migration preserves historical dates across
`create`/`status`/`comment`/… (see [adoption.md](adoption.md)).

## 11. The CLI (`_cli/`)

Typer app, exposed twice as `squads`/`sq` (entry point `squads._cli:main`, which runs the `app`). The root callback takes
the effective directory computed from the global `-C` options as `RequestContext.client_cwd` (it
never calls `os.chdir`), reads `--at`, runs the version notice, and dispatches. Conventions:

- Errors that are the user's to see subclass `SquadsError`; a `@handle_errors` decorator turns them
  into a clean message + exit 1 (the corrupt-index and validation paths funnel here).
- Dynamic strings printed to the console go through `e()` (Rich-escape) so a `[x]` checkbox or a
  bracketed title isn't parsed as Rich markup.
- Each command group is its own `_module`; `_common.py` holds the shared console, error decorator,
  service resolver, and value parsers.

---

## 12. Lifecycle of a command — `sq create task "Fix login" --parent FEAT-<n>`

```
 sq create task … --parent FEAT-<n>
   │
   ├─ root callback: set -C / --at, version notice
   ├─ _cli/_create.py  ──▶  get_service()  ──▶  _paths.resolve()  ──▶  SquadPaths
   └─ Service.create(TASK, "Fix login", parent=FEAT-<n>)
        └─ IndexStore.transaction()  [lock .squads.json]
             ├─ _check_parent: parent_allowed(TASK, FEATURE)        ✓  (epic → SquadsError)
             ├─ allocate_id(TASK) → TASK-NNNNNN                     (counter += 1)
             ├─ build Item (status=Draft, created/updated = clock.now())
             ├─ render items/task.md.j2 → write_new(tasks/TASK-NNNNNN-fix-login.md)
             └─ db.add(item)  →  atomic write .squads.json          [unlock]
   ◀─ prints the file path;  agent fills the <!-- sq:body --> region
```

1. **CLI** (`_cli/_create.py`) parses args; the root callback already set the active dir / `--at`.
2. `get_service()` → `_paths.resolve()` builds `SquadPaths` (which squad folder, where the index is).
3. `Service.create(TASK, "Fix login", parent="FEAT-<n>")`:
   - opens `store.transaction()` (locks `.squads.json`);
   - `_check_parent` → `parent_allowed(TASK, FEATURE)` ✓ (an epic here would raise);
   - `db.allocate_id(TASK)` → `TASK-NNNNNN` (padded filename form; counter bumped);
   - builds the `Item` (status = `initial_status(TASK)` = `Draft`, `created_at`/`updated_at` =
     `clock.now()`), squad-relative path `tasks/TASK-NNNNNN-fix-login.md`;
   - renders `items/task.md.j2` (placeholder body + empty markers), `write_new` emits frontmatter + body;
   - `db.add(item)`; on clean exit the index is atomically rewritten.
4. The CLI prints the path; the agent fills the body with `sq task 7 body -m "…"` (or `--file`).

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
`Item` on each invocation — even `sq show ONE-ID`. Cost is linear in item count, and it's paid at
most **once per invocation**: a request-scoped read cache (opened by `_cli/_common.py::command`,
consulted by `load()`) serves every later `Service.get`/`get_block` call in the same command from
the one snapshot it filed, so an item with many sub-entities pays this read once, not once per
sub-entity. `transaction()` never consults that cache — its own load always hits disk, under the
lock, so a write is always based on the true current state.

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
scale: `sq inbox` (`_services/_collab.py`) opens + mention-scans each open item's file; `sq check`
reads every item file, both for its raw-text scan and for the validators that inspect body text;
`sq repair` parses every file (twice, when renumbering).
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
that the index stays rebuildable from frontmatter (section 4), so they're additive, not a redesign.

## 14. Conventions that keep it honest

- **Frontmatter is truth; the index is rebuildable** — never store anything in `.squads.json` that
  can't be reconstructed from the `.md` files.
- **One global counter; allocate only inside a transaction.**
- **Marker-safe edits only** — touch content via `_sections.py`; never rewrite an agent's body.
- **Forward edges only; backrefs computed.**
- **`.claude/` is pointers + tool-owned config; real content lives under the squad folder.**

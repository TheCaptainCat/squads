# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.11.1] - 2026-07-21

### Fixed

- **The VS Code extension no longer shows an error in a non-squads workspace.** Opening the Squads
  panel (or the Roster view) in a folder that has no squad now renders a calm "No squad detected
  here" placeholder instead of a red error node and an error notification — the normal case for any
  non-squads folder is no longer treated as a failure.

## [0.11.0] - 2026-07-20

### Added

- **Custom skills can carry an authored, persistent body.** `sq skill body` sets (or `--append`s
  to) a custom skill's body text, and it survives sync/regen/repair untouched — bundled/system
  skills are unaffected and keep generating from their template as before.
- **Skills can be scoped to specific roles.** `sq skill link-role`/`unlink-role` link a skill to a
  role so that role's agents preload it (alongside the bundled skills every role already gets),
  resyncing that role's generated files immediately. A skill can be scoped to as many roles as
  needed, or none.

### Fixed

- **Doc examples now show real ID display.** README and the `docs/` guides had leftover
  zero-padded example IDs (`TASK-000008`, `FEAT-000002`, …) from before IDs display unpadded;
  every CLI example now matches what `sq` actually prints (`TASK-8`, `FEAT-2`, …).

### Changed

- **`sq workflow`'s subcommands are documented.** README and `docs/workflow.md` now list
  `sq workflow show|types|collections|statuses|lint` alongside the cheatsheet, instead of only
  the bare `sq workflow` form.
- **Generated skills and managed sections are more concise.** The agent-facing content `sq sync`
  writes into a project — the bundled skills and the CLAUDE.md/AGENTS.md managed sections — has
  been tightened for length with no loss of guidance; a fresh `sq init`/`sq sync` now produces
  leaner generated files.

### VS Code extension

- **The work-item tree keeps its expansion across refresh.** Auto-refreshing on a `.squads.json`
  change used to collapse every expanded node; expanded nodes now stay expanded across a
  refresh.
- **The item preview preserves scroll position.** Refreshing the same item's preview (e.g. after
  an edit) holds the scroll position instead of jumping back to the top; navigating to a
  *different* item still resets to the top as expected.
- **`@mentions` in the preview link to the role sheet.** A `@<slug>` mention in a body or comment
  now renders as a link that opens that role's sheet, with a hover preview of the role's details.
- **Back/forward navigation.** Each preview panel gained a sticky toolbar with back/forward
  arrows (plus a truncated title label) for moving through the items you've viewed in that
  panel, the way a browser does.

### Migration

**Schema 0.10 → 0.11 — run `sq migrate up`.** A schema-stamp-only gate: no frontmatter shape
changed, so the runner touches no files. It exists to hard-stop a pre-0.11 client with a clear
"run `sq migrate up`" before it can meet a ref kind it doesn't recognise yet. Every existing
skill (bundled or custom) and any role-scoping edge is left exactly as it was — this migration
only advances the schema stamp.

## [0.10.0] - 2026-07-19

### Added

- **`sq workflow types` — a machine-readable type catalog.** New subcommand alongside `sq
  workflow`/`sq workflow lint`: default prints a human table, `--json` emits a bare array (one
  object per declared type, work and reserved alike) with `type`/`order`/`prefix`/`reserved`,
  sorted in ascending resolved `order` (type-name tiebreak) — the same order the CLI registers
  per-type commands in. `order` is `null` for a type with no explicit order, present rather than
  omitted so the key set stays stable. Lets a consumer (e.g. the VS Code client) sort type groups
  spec-driven instead of alphabetically, with no hardcoded type list.

### Changed

- **`sq workflow --raw` / `sq workflow show --raw` print the cheatsheet as clean markdown.**
  Same content as the styled view (markdown tables, fenced ```mermaid``` blocks) but printed
  verbatim instead of through `rich.Markdown` — no box-drawing, no ANSI, so piping it into a
  markdown viewer renders cleanly. The default (non-`--raw`) styled view is unchanged.
- **`sq show <id> --raw` is now clean markdown.** It emits a deterministic dossier — an `#`
  title, a bullet list of metadata (status, priority/severity, assignee, parent, author, refs,
  labels), and the body verbatim, with `--comments`/`--full` appending Discussion/sub-entity
  sections — instead of the boxed panel, aligned summary table, and `=== … ===` separators it
  used to render. Piping `sq show --raw` into a markdown viewer now renders cleanly. The default
  (non-`--raw`) styled view is unchanged.
- **`sq show --json` now carries the body and discussion.** The JSON payload gained a top-level
  `body` (the raw body markdown), a top-level `discussion` (an ordered list of
  `{author, ts, body}`), and a `body` key on each entry of `subentities` — additive only, nothing
  renamed or removed.
- **`sq tree --json` and `sq list --json` carry more machine-readable state.** Every `sq tree
  --json` node now includes the item's `title` alongside `id`/`type`; both `sq list --json` and
  `sq tree --json` gain an `is_open` boolean (derived from the workflow spec's terminal-status
  set, so a custom vocabulary stays correct with no code change) — additive only, nothing renamed
  or removed.
- **`sq mine --json` also carries `is_open`.** Brings the assigned-to-me view in line with
  `sq list --json`/`sq tree --json` — additive only.
- **Trimmed the agent-facing `squads` skill.** Dropped the seven per-type lifecycle Mermaid
  diagrams from the skill (agents read it as raw text, so the diagram source was just noise);
  the compact hierarchy diagram and the one-line-per-type lifecycle table stay. `sq workflow`'s
  terminal output is unchanged and still shows the full per-type diagrams.

### Migration

**Schema 0.8 → 0.10 — run `sq migrate up`.** The bundled `sq-memory` skill predates the standard
`SKILL-<NNNNNN>-<slug>.md` naming convention used by every other bundled skill. The runner stamps
a unique `SKILL-…` id onto the legacy `agents/skills/sq-memory.md` file (if it isn't already
stamped), renames it to the convention filename, and rewrites its `.claude/` pointer to match,
then rebuilds the index. One-way and idempotent; a squad that never had the legacy file (or
already carries the convention-named one) is unaffected. No manual steps are required.

## [0.9.0] - 2026-07-15

### Added

- **Shared team knowledge — agent memory and a team bulletin board.** Each role now has its own
  committed memory notebook: `sq memory <role> list/search/show/add/forget` lets a role jot a
  durable fact, search past ones, and prune what's stale, stored as plain markdown files rather than
  in the tracked-item index. Alongside it, `sq board post/list/clear` gives the whole team a shared
  bulletin board for broadcast notices — post a short message with an optional `--until` expiry, list
  what's currently live, or take one down. Every role's briefing now points agents at their memory
  and the board at the start of a run, so accumulated context and team-wide notices surface
  naturally without cluttering any generated file.
- **Richer `sq search`.** Search now takes a `--status` filter alongside `--type` (the two compose
  together, matching the same filtering already available on `sq list`/`sq tree`), and each hit
  reports where the match was found — the title, description, body, a discussion comment, or a named
  sub-entity — plus the matched item's type and status for quick triage. Matches include a short
  in-context snippet, and `--json` output carries all of this detail for scripting. Search remains a
  plain case-insensitive substring match.
- **Inline Mermaid diagrams.** `sq graph --format mermaid-md` wraps the dependency/reference graph
  in a ready-to-paste fenced Mermaid block, and `sq workflow` now includes diagrams of the item-type
  hierarchy and each type's status lifecycle, generated from the active spec so a customized
  vocabulary renders its own shape correctly.

## [0.8.0] - 2026-07-13

### Added

- **Every work item type is now fully customizable — only `role`/`skill`/`operator` remain
  reserved.** The built-in type and status vocabularies are no longer backed by fixed enums: all
  seven bundled types (epic, feature, task, bug, decision, review, guide) and their statuses are
  ordinary spec-declared vocabulary, on equal footing with anything a project defines in
  `.overrides/workflow.toml`. A built-in type or status can be renamed, dropped, or replaced with no
  code change, and every facing surface — CLI help, generated skills, the managed `CLAUDE.md` /
  `AGENTS.md` sections, and the `sq workflow` cheatsheet — derives its wording from the active spec
  instead of a hardcoded name, so a customized vocabulary reads correctly everywhere. Behavior on
  the bundled (no-override) default is unchanged.
- **Custom sub-entity kinds.** A custom item type can now declare its own sub-entity kind (not just
  reuse story/subtask/finding) with its own lifecycle, completion status, fields, and generic CLI
  verbs — `add-<kind>`, the `<plural>` list, and the nested `show`/`update`/`body`/`comment`
  subgroup — generated with zero code change. A declared field beyond severity (e.g. an `impact` or
  `urgency` axis) is now storable and settable via `--<field>` on any sub-entity kind, not only the
  built-in ones.
- **Badge collections — priority and severity generalized into spec-defined vocabulary.** Priority
  and severity are now `Collection`/`Field`/`Badge` definitions in the workflow spec rather than
  fixed enums, so a project can declare an entirely custom badge axis (e.g. `impact`/`urgency` on a
  custom incident type) and get filtering, sorting, and colored badge rendering for free. A generic
  `--badge CODE=VALUE` / `--min-badge` escape hatch works for any declared field on `sq list` /
  `sq tree`, alongside the existing dedicated `--priority`/`--min-priority` sugar; `--sort` ranks by
  any ordered field. Bundled `priority`/`severity` behavior is byte-identical to prior releases.
- **Bulk vocabulary rename migrations — `sq migrate rename-type` and `sq migrate rename-status`.**
  Rename an existing work type (`sq migrate rename-type OLD NEW`) or relabel every item of a type at
  a given status (`sq migrate rename-status TYPE OLD_STATUS NEW_STATUS`) across an entire squad in
  one atomic operation — carrying sub-entities, status, and incoming references along, with a
  per-item audit trail. This is the escape hatch for vocabulary changes that an additive
  `.overrides/workflow.toml` merge can't express on its own (an override can add vocabulary, not
  rename or remove it).

### Changed

- **Item severity is now stored at the top level.** A bug's `severity` moves from the generic
  `extra` bag onto a proper top-level `severity:` frontmatter field, consistent with how every other
  declared badge field is now modeled. See Migration below.

### Fixed

- **A cold first CLI dispatch on a custom type could show the wrong command tree.** Running a custom
  type's command (e.g. `sq incident --help`) as the very first `sq` invocation in a process could
  render the bundled type's fallback surface instead of that type's own declared
  sub-entity/`retype` commands, because the command tree was built from a stale process-global spec
  reference before the real merged spec finished binding. Every invocation now resolves the correct,
  already-bound spec.
- **Clearer error when an item references a dropped or renamed type/status.** The vocabulary
  validation error now leads with the actual cause — a type or status no longer declared in the
  active spec — instead of pointing at `sq repair`, which cannot fix a vocabulary mismatch.
- **Sub-entity ownership resolution when two types share the same sub-entity kind.** A project that
  declares two work types mapped to the same sub-entity kind (for example a custom ticket type
  mirroring `task`'s subtasks) previously had `add-subtask`/`add-finding` and similar commands
  reject one of the two types' items. Ownership is now resolved per-item against the active spec, so
  both types work correctly.

### Migration

**Schema 0.7 → 0.8 — run `sq migrate up`.** The runner relocates every bug's `severity` from the
generic `extra` bag onto the top-level `severity:` frontmatter field it now belongs on, dropping the
old copy. One-way and idempotent; if both the old and new locations are somehow present, the
top-level value wins. Non-bug items are untouched.

## [0.7.0] - 2026-07-06

### Added

- **`sq renumber` — pre-merge ID block-shift.** A standalone verb that shifts a branch's
  locally-created IDs into a contiguous block disjoint from another branch's counter before a
  merge, preserving referential intent that the existing post-merge `repair --renumber` cannot
  (that remap is keyed by the old-ID string and blindly repoints every ref to a single winner).
  `--onto` computes the disjoint offset automatically (`delta = max(mine, counterpart) + 1 - mine`);
  `--by` is refused, with no files touched, if the requested shift would still collide. The
  operation is counter-neutral and shares its apply-path with `repair --renumber`; a single
  append-only reflog event records it. `sq` remains git-agnostic — inputs are plain integers, never
  branch refs.
- **`sq check` flags unwritten placeholder sub-entity bodies.** A new advisory rule reads each
  sub-entity-bearing item and warns, one issue per sub-entity, when a story/subtask/finding still
  carries its kind's placeholder stub instead of a written body — surfacing backlog debt that was
  previously invisible to `sq check`.
- **Guard against stale status/lifecycle prose in item bodies.** A new advisory `sq check` rule
  flags a body or `description:` that opens with a `STATUS:`/`**STATUS**`/`## Status` banner
  declaring the item's own current workflow state — prose that inevitably goes stale once the real
  (frontmatter) status moves on. Topical lifecycle discussion, cross-references to another item's
  status, and fenced-code examples are left alone; only a leading self-declared banner is flagged,
  and the discussion region is never scanned.

### Changed

- **Unpadded display IDs, decoupled from filename padding.** Every human-facing surface —
  frontmatter `id:`, refs, ID mentions in body prose, CLI output, and tables — now renders an
  item's ID unpadded (`FEAT-42`, not `FEAT-000042`). On-disk filenames are unaffected: they keep
  their existing zero-padded width, which remains purely a filename-sorting concern, reconstructable
  from disk exactly as before (`sq repair` / `sq migrate repad`). No new configuration surface.
- **The "regenerated by `sq sync` — do not edit" warning now lives on the files that are actually
  overwritten.** The warning previously sat on the (redundant) generated squad-skill bodies; it now
  stamps the agent-facing files a backend actually regenerates on sync — the `CLAUDE.md`/`AGENTS.md`
  managed regions and the `.claude/` pointer files — as a cross-backend `AgentBackend` contract, so
  an agent editing one of those files in-session is told plainly that an edit there will be
  overwritten.

### Migration

**Schema 0.5 → 0.7 — run `sq migrate up`.** The runner unpads every human-facing ID across the
corpus: it reformats each item's own frontmatter `id:`, unpads `refs:`/`parent:` entries, and
substitutes exact old-form ID literals in body and sub-entity-title prose (skipping fenced code
blocks, inline code spans, and filename-tail mentions, which stay padded). On-disk filenames are
never renamed by this step. Idempotent — once every mention is unpadded, a re-run is a no-op.

## [0.6.0] - 2026-07-02

### Added

- **Custom item types defined in TOML.**  A squad can now define brand-new item types
  (e.g. `incident`, `change-request`, `finding`) in a bundled or project-override `workflow.toml`.
  Each custom type carries its own prefix (`INC`, `CHG`, `FND`), folder, lifecycle, parent rules,
  and aliases; they are usable end-to-end with `sq create incident`, `sq list -t incident`,
  `sq incident <n> show`, `sq incident <n> retype`, and refs. An auto-generated per-type skill
  appears immediately via `sq sync`. Built-in types remain unchanged and byte-identical in output.

- **Custom statuses and auto-linearized lifecycles.**  Define brand-new statuses in the workflow spec
  (e.g. `Triage`, `Mitigating`, `Resolved` for an incident type), each with its own open/terminal
  and role classification. Lifecycles are automatically linearized into a directed acyclic graph
  with reachability validation; all status-driven filters (`sq list --status`, default closed-item
  hiding, `sq blocked`, `sq inbox` role views) respect custom open/terminal classification without
  code changes. Status badges render dynamically from the live spec with a neutral fallback.

- **Externalized and overridable workflow, role catalog, and playbook.**  The previously hardcoded
  type list, statuses, lifecycle state machines, role definitions (name, mission, responsibilities),
  and per-type/per-role guidance (enter/do/handoff/watch) now live in bundled TOML files
  (`default_workflow.toml`, `roles.toml`, `playbook.toml`). A squad can override them via
  `.overrides/workflow.toml` using an additive merge — define new types/statuses without redefining
  built-ins. **Stability guarantee:** the bundled defaults and all built-in type output remain
  byte-identical to v0.5.x; existing squads see no change unless they author overrides.

- **`sq workflow lint`** — validates that every status in a custom lifecycle is reachable from its
  initial state, and reports name conflicts between builtin and override definitions. Catches
  unreachable-terminal problems that would otherwise trap items in a dead state.

- **Spec-driven `sq workflow` cheatsheet, CLAUDE.md, and AGENTS.md.**  The `sq workflow` command
  renders the live loaded workflow spec, so a custom setup immediately sees its custom types,
  statuses, and lifecycles. The managed CLAUDE.md workflow section, the AGENTS.md backend output,
  and the generated `squads` skill likewise render from the live spec, keeping them always in sync
  with what `sq` actually enforces. The static prose (ref kinds, retype, remove-vs-cancel semantics)
  remains literal and never becomes editable — that stability is explicit in the codebase.

### Changed

- **Review state machine permitting `ChangesRequested → Approved` transition.**  The workflow spec
  now matches what was already advertised in the cheatsheet, skills, and playbook: a reviewer
  can go directly from requested changes to approved without re-drafting as `Draft` first. This
  closes a workflow deadlock in some review patterns.

### Fixed

- **Custom-status badge rendering no longer crashes on unknown status values.**  Badges now
  resolve with a neutral default (`⚪`) instead of failing when a status is not in the built-in
  set. Allows safe fallback for novel statuses.

### Migration

**No migration required — `schema_version` stays `0.5`** (this release introduces no on-disk format change).
Custom types persist their prefix in frontmatter only; built-in items derive it on load.

## [0.5.0] - 2026-06-28

### Added

- **Skills are first-class, ID'd entities.**  A skill is now a full `Item`
  on the role/operator meta-type profile (`Active` / `Archived`, no sub-entities), stored as
  `SKILL-NNNNNN-slug.md` with frontmatter as the source of truth and a thin `.claude` pointer
  resolved from it.  A single skill-description registry feeds the backend, seeding, and migration.
  New surface: `sq list -t skill`, `sq skill show`, and `SKILL-…` as a ref target.

- **Per-role spawn attenuation — leaf roles can no longer spawn sub-agents.**
  Roles now carry a `can_spawn` capability, held only by `manager` and `tech-lead`.  Every other
  role (developers, reviewer, QA, architect, …) is rendered with `disallowedTools: Agent` in its
  Claude Code agent definition, so a spawned specialist structurally cannot re-delegate.  The
  capability is visible via `sq role <slug> show`.

- **Optional session lineage on every recorded operation.**
  squads now reads two optional environment variables — `SQUADS_SESSION_ID` and
  `SQUADS_PARENT_SESSION_ID` — once at the CLI root callback and carries them through the
  invocation.  When present, both the reflog line (as additive sibling fields `session_id` /
  `parent_session_id` alongside the flat `actor` string, back-compat preserved) and the item
  frontmatter (as optional `created_session` / `modified_session` fields) record them.  When
  absent the behaviour is identical to before — actor is still just the slug.  Session fields
  are **not** settable by `--as` / `--author` or any later CLI flag; env vars are the only path.
  **Guarantee: best-effort, untrusted, observability-only.**  squads is a passive tool, never in
  the spawn path; it reads and records whatever its invocation environment carries.  A forged,
  copied, or absent session id is indistinguishable from a real one — these fields must never be
  used as an authorisation input.

- **`sq reflog --tree` and session surfacing in `show --full`.**  `sq reflog --tree`
  renders the recorded spawn lineage as a nested, best-effort tree; operations with no or unknown
  parent session appear as forest roots, and forged cycles degrade gracefully without dropping any
  entry.  `sq <type> <n> show --full` surfaces the creating and last-modifying session when present.

- **Advisory create-lane warnings.**  `sq create` now emits a best-effort advisory
  warning when a role authors an item type outside its lane (for example a developer creating a
  feature), names the expected owner role, and proceeds anyway (exit 0; the warning is recorded in
  the reflog).  Lanes are derived from the team playbook; `manager` and operators are exempt, and
  each role's create-lane is shown in `sq role <slug> show`.  **Advisory only — keyed on the
  self-declared actor, never an authorisation boundary.**

- **`sq graph` — ego-centric ref-graph view** of an item's neighbourhood, with `dot` and `mermaid`
  export.

- **`sq tree` filters.**  Filter the subtree by status, priority, assignee, and type, with
  `--depth`; the same filters are shared with `sq list`.

- **Advisory warnings for over-long sub-entity titles.**  A 120-char
  warn-and-proceed advisory on `add-story` / `add-subtask` / `add-finding`, a matching `sq check`
  audit rule, and skill guidance that a title is a one-line handle and prose belongs in the body.
  Advisory only — never gating body presence.

- **Async end-to-end.**  The service layer, index store, and file IO are now async,
  with synchronous code confined to the CLI entry edge.

### Fixed

- **`--json` output is now ANSI-free regardless of `FORCE_COLOR`.**  All 22 `--json`
  emission sites route through a plain serializer instead of the colorizing rich console, so
  machine-readable output parses cleanly even when a parent process forces color.  Regression-tested.

- **Recursive self-spawn cascade.**  A spawned developer subagent no longer
  re-delegates to a same-role child many levels deep instead of doing the work — leaf roles now
  structurally lack the spawn tool (see the spawn-attenuation entry above).

### Migration

**Schema 0.3 → 0.5 — run `sq migrate up`.**  The runner applies both steps in order: additive
session-lineage fields (0.3 → 0.4, no file rewrites; all new fields optional) and the
skills-as-entities conversion (0.4 → 0.5, which allocates IDs, renames skill files to
`SKILL-NNNNNN-slug.md`, and backfills frontmatter — idempotently, preserving existing frontmatter).
Existing item and reflog files remain valid throughout.

## [0.4.0] - 2026-06-17

### Added

- **Uniform item addressing.** Every command accepts both the full formatted ID (`TASK-000035`) and
  the bare sequence number (`35`); the type word validates it, so there is no ambiguity.
  `sq <type> <number> <verb> …` works identically whether you pass `35`, `000035`, or `TASK-000035`.
- **Typed ref-kind vocabulary.** Forward references now carry a validated kind chosen from eight
  closed terms: `related`, `blocks`, `depends-on`, `implements`, `fixes`, `addresses`, `supersedes`,
  `duplicates`. Unknown kinds are rejected at set-time; consumers validate that the kind makes sense
  for the edge (e.g. only a task/bug can `implements` a feature, only a task can `addresses` a
  decision).
- **Explicit ID padding stored in the index.** All ID formatting goes through a single formatter
  driven by a padding width stored in `.squads.json`; `sq migrate repad <width>` is a one-way command
  that renames every item file to the new width and rebuilds the index with contents byte-untouched.
  ID reads are width-tolerant by sequence number, so old and new padding can coexist during
  migration. An exhaustion guard checks the index for capacity under the new width.
- **Type-command aliases in the CLI grammar.** Shorthand aliases provide full verb and sub-entity
  equivalence with the canonical form: `e` (epic), `feat`/`f` (feature), `t` (task), `b` (bug),
  `dec`/`d` (decision), `rev`/`r` (review), `g` (guide). Aliases render into the workflow cheatsheet
  with an add-only evolution rule to preserve documentation stability.
- **`sq <type> <n> retype <new-type>`** — flip an item's type while preserving its sequence number as
  durable identity. The file is moved, incoming edges are rewritten, and the entire operation is
  atomic inside the index lock. Useful when an issue is initially misfiled.
- **Sanctioned item removal — `sq <type> <n> remove`** hard-deletes the item file, unlinks it from
  the index, and updates `.squads.json` atomically. Pass `--force` to sever incoming references; by
  default, removal is rejected if anything points to the item. IDs are never reused, so a gap in the
  sequence is a normal artifact of removal.
- **Operation reflog — `<squad>/.reflog.jsonl`** is an append-only log written after every index
  commit inside the lock (logged-without-applied impossible; applied-without-logged tolerated under
  crash). Entries record the actor (ambient per-invocation), the operation (create/update/remove/…),
  item(s) affected, and a timestamp. An `sq reflog` reader tolerates partial lines and filters by
  type/actor. The reflog is advisory (not a source of truth) and gitignored per-clone.
- **Project-level overrides — `.overrides/templates/` and `.overrides/roles/`** let squads customize
  the generated item templates and role definitions without forking the package. A stamped update
  workflow (`sq override scaffold/diff/update/list`) detects drift from the release version and
  manages upgrades; the CLI rejects any override at load-time if its stamp is newer than the release
  (unknown future version). Template and role manifests are generated and shipped with every release.
  Agent naming via overrides is supported.
- **Frozen machine-readable surface — `--json` on every read command** emits valid JSON; the CLI
  documents its exit-code table (0: success, 1: squads runtime error, 2: usage error, 3: check failure) and all
  JSON shapes are golden-file tested. This gives agents and scripts a stable contract to consume.
- **Shell completion enabled and verified for bash and zsh** via the entry-point shim. Completion
  works out of the box after install and is documented in the README.
- **Second agent backend — a generic `AGENTS.md` backend** proves the `AgentBackend` ABC is honest
  before the 1.0 freeze. The de-Claude-ified ABC (`generate_*_entry` instead of pointer-specific
  names, backend-owned root files via `ctx.root` instead of hard-coded `claude_dir`) works for both
  the Claude Code backend and the new AGENTS.md backend; both pass a shared conformance suite. The
  agents_md backend renders roster, workflow, and role missions into a single idempotent,
  marker-safe `AGENTS.md`.
- **Multi-active agent backends.** `.squads.toml` now carries `active_backends: [list]` instead of a
  singular `default_backend`; a squad maintains zero or more backends at once. Sync / scaffold /
  check / roster / regen / remove fan out over every active backend. An empty list is valid (a
  squad-only mode with no agent files). Legacy configs with singular `default_backend` read
  transparently as a single-element list — no breaking change for users. `sq init --backend` is
  repeatable with a `none` sentinel for empty; the list is deduped on first-occurrence.
- **Bugs get a real lifecycle.** A new bug-specific workflow (`Open → InProgress → Fixed → Verified`,
  terminal states `WontFix` / `Cancelled`) replaces the generic machine. Status-setting is validated
  against the type's workflow at set-time (independent of `--force`, which relaxes only the edge,
  never the vocabulary). This closes the prior hole that let bugs reach invalid statuses.
- **Stability contract — `docs/stability.md`** and `sq docs stability` tiers five public surfaces
  — durable `.md` format, CLI grammar, `--json` shapes, Python import paths (not public), and
  generated `.claude/` files — and states the migration promise: any squad created on any 0.x
  release reaches 1.0 intact via `sq migrate up`. The schema version post-1.0 follows a dotted-string
  scheme (the release that introduced it), and post-1.0 schema bumps ride the MAJOR version.
- **Rendered `sq show` output** displays items as markdown panes (title, summary, body, metadata
  badges) with a `--full` dossier (frontmatter fields in a sidebar) and `--comments` facet (full
  discussion thread). Sub-entity `show` (e.g. `sq feature 12 story 1 show`) renders the block
  (heading, state badges, body, discussion). This is the canonical read for an agent briefing on an
  item before acting on it.
- **Python >= 3.14 is now required.** The floor is PEP 649 lazy annotations (Python 3.14+) so
  forward references work unquoted in type hints. This is a deliberate architecture choice to keep
  the import graph acyclic and annotation handling simple.

### Changed

- **Bug lifecycle introduces per-type status validation.** Status-setting is now validated against the
  item type's workflow at set-time, independent of `--force` (which relaxes only the edge, never the
  vocabulary).

### Fixed

- **`sq check` no longer flags operator authors/assignees.** The check validated `author`/`assignee`
  against registered *roles* only, while the write gate accepts roles **or operators** — so any
  operator-authored item drew a bogus `not a registered agent` warning. The check now uses the same
  participant set as the gate.
- **Marker injection is now guarded.** Comments and sub-entity titles are scanned for sq marker tags
  (`<!-- sq:* -->`) at set-time and rejected if found, preventing users from breaking the parsing
  machinery via a quoted marker in a comment or title.
- **Stale inbox mentions are cleared.** Accepted decisions and published guides are terminal; they
  now leave the work views (`sq inbox <role>`) so agents don't revisit settled items looking for an
  update that won't come.

### Migration

**No migration required — `schema_version` stays `0.3`** (this release introduces no on-disk format change).

## [0.3.0] - 2026-06-10

### Added

- **Bugs carry a `severity`.** A bug's severity (`critical|high|medium|low|info`) is a validated
  per-type field: `sq bug <n> update --set severity=high` (`--unset severity` clears it), shown as a
  colored badge in `sq bug <n> show`. Invalid values are rejected with the valid list.
- **Sub-entities get a full `update` metadata entry point — `sq <type> <n> <kind> <k> update …`.**
  Mirroring item-level `update`, it sets `--title`, `--status` (+`--force`), and
  `--assignee`/`--clear-assignee` on any story/subtask/finding, **plus the two fields that were
  previously write-once at `add`**: a subtask's `--story`/`--no-story` (validated against the parent
  feature) and a finding's `--severity`. Every change re-renders the block's heading, its `:head`
  badges, and the parent's summary-table row from the stored value.
- **Item bodies are sq-managed too — the workflow needs no hand-editing.** Set or revise any item's
  body with `sq body <ID> -m "…"` / `--file PATH` (`--file -` for stdin) / `--append`, set it at
  creation via the same flags on `sq create`, and read it with `sq show`. `--desc` now sets only the
  short one-line **summary** (shown in `sq list`); it no longer seeds the body, so the two never
  drift. (Role/skill bodies stay generated from their fields.)
- **Items record an `author`** — the registered agent who created them. `sq create` now requires
  `--author <slug>`, and the author must be a registered agent (a role in the squad) or it's
  rejected. Roles/skills self-author; `sq show` displays it and `sq check` warns if an author's role
  was later removed. (Distinct from `--assignee` = who's responsible.)
- **`sq update` is the one metadata entry point.** Beyond title/description/assignee/labels it now
  sets `--author`, `--status` (validated; `--force`), `--parent`/`--no-parent`, and **per-item-type
  fields** via `--set key=value` / `--unset key` (e.g. a review's `target_ref`, a guide's `tags`, a
  role's `model`/`color`), validated against a declared schema. Editing a role/skill regenerates its
  `.claude` pointer.
- **`sq comment` can target a review finding** (`--finding F1`), completing comment support across
  every sub-entity — user stories (`--story`), subtasks (`--subtask`), and findings (`--finding`).
- **Human-readable header on every sub-entity.** Each story / subtask / finding now carries an
  sq-owned `:head` region under its heading that renders its state prettily — `**Status:** 🟡 In
  Progress`, `**Assignee:** <full name>`, `**Severity:** 🟠 High` (findings), `**Implements:** US2 —
  <story title>` (subtasks) — kept in sync on every status/assignee change while the machine values
  stay in `:meta`. It's a template (`subentities/head.md.j2`); add an attribute by passing a value
  from `set_head` and adding a line.
- **Sub-entity bodies are sq-managed — no manual markdown editing.** Set or revise a user story /
  subtask / finding body with `sq story|subtask|finding body <ID> <LID> -m "…"` (repeatable
  paragraphs) or `--file PATH` (`--file -` reads stdin), `--append` to add to it; set it at creation
  via the same flags on `add`; and read the whole block (meta + body + discussion) with
  `sq <kind> show <ID> <LID>`. Bodies containing sq marker comments are rejected.
- **`assignee` is validated against the roster.** Setting an item's assignee (at `create` or via
  `sq update --assignee`) now requires a registered agent, just like `author`; `sq check` warns when
  an assignee's role was later removed.
- **Sub-entities carry their own assignee**, so a task's subtasks (and a feature's stories, a
  review's findings) can be parcelled out to different agents. Set it at creation (`--assignee
  <slug>`) or reassign with `sq subtask|story|finding assign <PARENT> <LID> <slug>` (`--clear` to
  unassign); it's validated against the roster, stored in the block's sq-owned `:meta` region, and
  shown in both `… list` and the parent's roll-up summary table.
- **Items carry a `priority`.** An optional `priority` (`urgent|high|medium|low`) is a first-class
  field, independent of status: set it at creation (`sq create … --priority high`) or with
  `sq <type> <n> update --priority high` / `--no-priority`. It shows as a colored badge in
  `sq <type> <n> show` and a new **Priority** column in `sq list`, and filters with
  `sq list --priority high`. (Additive frontmatter field — old items read back as unset and no
  migration is needed.)
- **Closed items are hidden by default.** `sq list` and `sq tree` now show only open items; pass
  `--all`/`-a` to include closed (Done/Cancelled/…) ones, or filter directly with an explicit
  `--status`. This keeps day-to-day views focused without deleting anything — items are "archived"
  simply by reaching a terminal status.
- **`sq search TEXT`** — find items by matching their title, summary, and body/discussion prose
  (case-insensitive), printed with the matching lines (`--type` to scope, `--json` for machine use).
- **`sq blocked`** — surface what's stuck: open items that have at least one *open* blocker via the
  `blocks` ref kind (`A ref add B --kind blocks` reads "A blocks B"), each shown with its blockers.
- **`sq mine [ROLE]`** — items assigned to a role (defaults to the squad's configured default role);
  honors the same closed-hiding (`--all` to include) as `sq list`.
- **`sq workload`** — open/closed/total work-item counts per assignee, busiest first.
- **`sq tree … --json`** — emit the nested subtree (`id/type/status/priority/assignee/blocked` +
  `children`), honoring a root id and `--all`. This is the one read an orchestrating agent uses to
  see a feature's whole state and decide what to do next.
- **Precise per-actor guidance in every item skill.** Each `sq-<type>` skill now gives every actor
  that touches the item (e.g. tech-lead / developer / reviewer / QA on a task) structured guidance
  under fixed labels — **Enter** (what to read first), **Do** (the steps, with concrete `sq`
  commands), **Hand off** (the trigger + target), and **Watch for** (scope discipline) — instead of
  a one-line summary. The shared **developers** section appears only once the squad has a
  `<tech>-dev` role (added/removed live with `sq dev add` / `sq role rm`).
- **`greeting` skill — agents greet the operator on arrival.** A new always-preloaded managed skill
  has every role, when a human opens a conversation, detect who they're talking to (Claude user /
  `git config user.name` → `op-<firstname>`), register them if needed (`sq operator add`), then greet
  — **matching the human's tone** ("Hello Robert" → "Good morning, Pierre"; "Hi Mara!" → "Hey
  Pierre!"), saying how they can help, and giving a quick read of the project. Subagents spawned for
  internal work skip the greeting. (Preloaded alongside `squads` for all roles.)
- **Operators — humans as first-class participants.** A new `operator` item type represents the
  people who work on the project (slug `op-<firstname>`). Register them with `sq operator add
  "<name>"` (`list`/`rm` too); an `op-` slug is then a valid `--author`/`--assignee` on items and
  sub-entities and `--as` on comments — the assignment gates accept registered **roles or
  operators**. Operators are not agents: never spawned, no `.claude/agents` pointer, no skills, and
  they're excluded from `workload`. `CLAUDE.md` gains an "Operators (people)" roster and a
  session-start ritual (work out who the human is, `sq operator list`, ask to register, **ask if
  unsure**). Additive — no migration.
- **Reinforced role entry points.** Every role's definition now carries the operating contract
  (keep an item's status current; hand back through a `sq comment`; follow your `sq-<type>` skill's
  section), and the `squads` skill gains a **"Working directly with the operator"** rule for when the
  operator bypasses the manager. The greeting/impersonation also accepts a role by *function*
  ("the dotnet dev" → `dotnet-dev`), not just by name.
- **Orchestration-loop guidance.** The generated `CLAUDE.md` now teaches the manager/default agent
  to run work as a loop — *assess via `sq` → delegate by spawning the specialist as a Claude Code
  subagent (`subagent_type: <role-slug>`) with the item ID → integrate the result → repeat until
  done*. `@mention`/`inbox` are framed as the durable record of who-was-asked-what; the spawn is the
  handoff. (Each squads role is already a spawnable subagent with its model/skills preloaded.)

### Changed

- **Prose edits are now concurrency-safe.** `sq comment`, `sq <type> <n> body`, and sub-entity
  bodies write the `.md` file *inside the index lock* (atomically with the `updated_at` bump),
  instead of an unlocked read-modify-write. Parallel `sq` callers — e.g. several dev subagents
  working at once — can no longer silently drop each other's comments or body edits.

- **BREAKING — the sub-entity shortcut verbs are removed; `update` is the single entry point.**
  `sq <type> <n> <kind> <k> status …`, `… assign …`, and the subtask `… done` are gone — use
  `… update --status …` (`--force` to override / replace `done`), `… update --assignee …`
  (`--clear-assignee`). The remaining sub-entity verbs are `show`, `update`, `body`, `comment`.
  (Item-level `status` is unaffected.)
- **Sub-entity state moved from body markers to frontmatter.** A story / subtask / finding's machine
  state — status, assignee, severity, mapped story, and title — is now a typed `subentities:` list in
  its parent item's YAML frontmatter, single-sourced and pydantic-validated like every other item
  field. The index therefore **sees sub-entities** (so `sq list`/`sq check` and transition validation
  read them without parsing bodies), and `sq repair` reconstructs them from frontmatter. Only the
  prose (`:body` / `:discussion`) and the derived presentation (`:head` badge line, `:summary` table)
  stay in the markdown body; the per-block `:meta` region is gone. (`sq <type> <n> show` and the
  `… <kind> show` views are unchanged.)
- **BREAKING — resource-oriented CLI grammar.** Items are now addressed as `sq <type> <number>
  <verb> …`, with sub-entities nested one level deeper. The flat and sub-app commands are removed and
  replaced:
  - `sq show/update/status/comment/body ID` → `sq <type> <n> show|update|status|comment|body`
  - `sq link/unlink ID` → `sq <type> <n> update --parent/--no-parent`
  - `sq refs ID` / `sq ref add FROM TO` → `sq <type> <n> refs` / `sq <type> <n> ref add TARGET`
  - `sq story|subtask|finding add PARENT …` → `sq <type> <n> add-story|add-subtask|add-finding …`
  - `sq story|subtask|finding <op> PARENT LID …` → `sq <type> <n> story|subtask|finding <k> <op> …`
  - `sq guide add` → `sq create guide`
  The number may be bare (`35`), padded (`000035`), or the full id (`TASK-000035`); the type word
  validates it. `create`, `list`, `tree`, `init`/`adopt`, `check`/`repair`/`sync`, `docs`,
  `workflow`, `inbox`, and the `role`/`dev`/`skill`/`migrate` groups are unchanged. (Examples
  throughout the Added section below use the new grammar.)
- **An item's integer `sequence_id` is now its real identity; the formatted `id` is derived.**
  `Item.sequence_id` (the global counter number) is a stored field persisted in both `.md`
  frontmatter and `.squads.json`; `id` (`TASK-000007`) is computed from `type` + `sequence_id`. The
  index keys items by `sequence_id` (`items: {7: …}`) rather than the formatted id. The loader
  normalizes legacy full-id index keys, and the **0.2 → 0.3 migration backfills `sequence_id`** into
  existing frontmatter, so existing squads upgrade cleanly via `sq migrate up`.
- **`schema_version` now tracks the alpha release that introduced the schema** (`"0.1"`, `"0.2"`)
  instead of an opaque integer counter (`1`, `2`), in both `.squads.toml` and `.squads.json`. Existing
  alpha squads must update the value by hand (`schema_version = 2` → `schema_version = "0.2"` in
  `.squads.toml`; `sq repair` then restamps `.squads.json`).
- **Comments read better with multiple points.** Each repeated `-m` is its own bullet under the
  timestamp (now shown in the help + agent guidance), and a multi-line `-m` value keeps its
  continuation lines nested under its bullet — including fenced code blocks (internal blank lines
  stay indented) — instead of breaking the list.

### Migration

- **`schema_version` → `"0.3"`.** `sq migrate up` applies the new **0.2 → 0.3** step automatically:
  it backfills the integer `sequence_id`, **lifts each sub-entity's `:meta` state into the new
  `subentities:` frontmatter list and deletes the `:meta` markers**, and renders the `:head` region
  (status / assignee-name / severity / story badges), resolving names from the role files and story
  titles from parent features. Fully automatic and idempotent. (An out-of-date squad is gated until
  you run it — `sq migrate help` / `chlog` list every step.)

### Fixed

- **Global `--at` / `--dir` now work after the subcommand too** (e.g. `sq create task "X" --at
  2024-01-01`), not only before it. They're hoisted to the front at the entry point, so position no
  longer matters.

## [0.2.0] - 2026-06-08

### Added

- **`sq docs`** — list the bundled documentation, and `sq docs <name>` prints any page straight to
  the terminal so agents (and humans) can read the full docs **offline, with no fetch**. Raw
  markdown by default; `--rich` pretty-prints. The docs ship inside the wheel as package data.
- **Status state machines for sub-entities, tracked by `sq`.** Subtasks and user stories now have a
  status (`Todo → InProgress → Done`, + `Blocked`, `Cancelled`): `sq subtask status TASK STn <Status>`,
  `sq story status FEAT USn <Status>` (transitions validated; `--force` to override).
- **Review findings are first-class.** `sq finding add REV "…" --severity high|…`,
  `sq finding status REV Fn <Status>` (`Open → Fixed → Verified`, + `WontFix`), `sq finding list`.
- **`sq`-managed summary tables.** Tasks/features/reviews carry a top-of-section table rolling up
  their subtasks/stories/findings (status, and severity for findings), regenerated on every change.

### Changed

- **Ref kinds are now stored inline with the edge.** A reference is `ID` (the default `related`) or
  `ID:kind` (e.g. `BUG-000009:fixes`) in an item's `refs`, replacing the separate
  `extra.ref_kinds` map. The `sq ref`/`sq refs` interface is unchanged. (`schema_version` → 2.)
- **Sub-entity state lives in scoped markers, not the heading.** Each subtask/story/finding block
  keeps its status (and severity/story map) in an sq-owned `:meta` region — the heading is plain
  prose. `subtask done` is kept as a shortcut.
- **Discussion sections now carry a heading** at the right depth — `##` at item top level, `####`
  inside a story/subtask/finding.

### Migration

- On an out-of-date squad, `sq` **stops and tells you to run `sq migrate up`**, the new migration
  command group: `up` runs the automatic runners (rebuild index + restamp), `help` lists the
  migration changelog, and `chlog vA..vB` prints the manual steps for a release range. The `v1 → v2`
  runner folds legacy `extra.ref_kinds` into inline refs, upgrades sub-entity headings (`[ ]`/`[x]`
  checkboxes and `(→ USn)` suffixes) into the new `:meta` regions, builds the summary tables, and
  gives legacy reviews an empty findings container.
- **One manual step (LLM-assisted):** a pre-2 review's free-form prose findings can't be structured
  automatically — `sq migrate up` prepares the container, then an agent recreates each as
  `sq finding add … --severity …`. Read it with `sq migrate chlog v0.1.1..v0.2.0`.

## [0.1.1] - 2026-06-08

### Fixed

- **Windows: every write command crashed** (`sq init`, `create`, `status`, `repair`, …). The atomic
  index write called `os.fsync()` on a read-only file handle, which Windows rejects with
  `OSError [Errno 9]`; it now fsyncs the write handle that produced the bytes.
- **Windows: non-ASCII output crashed** under the legacy cp1252 console (`UnicodeEncodeError` on
  `→`/`•`/`—`, e.g. from `sq workflow`). The CLI now forces UTF-8 stdio on Windows.
- **Windows: reading squad files crashed or silently corrupted non-ASCII content.** `sq check`
  (and any read path) used `Path.read_text()` with no encoding, so on a non-UTF-8 locale (e.g.
  cp1252) a heading such as `### ST1 — … (→ US1)` either raised `UnicodeDecodeError` or decoded the
  `→` to mojibake — breaking subtask/story validation. All file I/O is now pinned to
  `encoding="utf-8"`.

## [0.1.0] - 2026-06-08

Initial release.

### Added

- **CLI** (`squads` / `sq`) for managing a team of AI agents as identified markdown with a
  JIRA-like, globally-unique ID system. Item types: epic, feature, task, bug, decision (ADR),
  review, guide, role, skill.
- **Index** — a single `<squad>/.squads.json` with one global monotonic counter and all item
  metadata; filelock'd, atomic writes. The `.md` frontmatter is the durable source of truth; the
  index is rebuildable (`sq repair`, `sq repair --renumber`).
- **Commands** — `init`, `adopt`, `create`, `list`, `show`, `tree`, `link`/`unlink`, `update`,
  `status`, `comment`, `story`, `subtask`, `ref`/`refs`, `inbox`, `role`, `dev`, `skill`, `guide`,
  `check`, `repair`, `sync`, `workflow`. Global `--dir` (target a squad) and `--at` (forge
  timestamps for history-preserving migration).
- **Workflow** — per-type status machines with validated transitions; parent rules
  (task → feature, feature → epic); typed forward refs with computed backrefs; user stories &
  subtasks with their own discussion; `@mention` inbox.
- **Claude Code backend** — thin `.claude/` pointers to real definitions under the squad folder,
  bundled `squads` skill + per-item-type skills, a managed `CLAUDE.md` section with
  greeting-based impersonation, and a non-clobbering `settings.json` merge.
- **8 bundled roles** + on-demand stack developers (`sq dev add`); the role↔item-type playbook.
- **Docs** — README, plus `docs/` (workflow, internals, adoption, agents, tutorial, roles,
  backends, recipes, faq); `py.typed`; MIT licensed.

[Unreleased]: https://github.com/TheCaptainCat/squads/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/TheCaptainCat/squads/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/TheCaptainCat/squads/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/TheCaptainCat/squads/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/TheCaptainCat/squads/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/TheCaptainCat/squads/releases/tag/v0.1.0

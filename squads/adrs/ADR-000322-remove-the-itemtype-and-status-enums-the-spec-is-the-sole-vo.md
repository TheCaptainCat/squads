---
id: ADR-322
sequence_id: 322
type: decision
title: Remove the ItemType and Status enums; the spec is the sole vocabulary authority
status: Accepted
prefix: ADR
author: architect
refs:
- ADR-214
- ADR-266
- ADR-274
- EPIC-280
- ADR-232
created_at: '2026-07-07T09:37:31Z'
updated_at: '2026-07-08T15:16:14Z'
---
<!-- sq:body -->
## Context

The design intent for the config-driven workflow engine (EPIC-206) was **full vocabulary
customization with no reserved names, except the three meta-types** `role`, `skill`, `operator` —
which the engine depends on structurally because they model the team itself (agents and the humans
who drive them). The seven **work-item** types (`epic`, `feature`, `task`, `bug`, `decision`,
`review`, `guide`) were meant to be ordinary vocabulary a project could drop, rename, or re-prefix.

As shipped in 0.6.0 that intent is not met. Although `ADR-232`/`FEAT-208` already widened the model
(`Item.type: str` and `Item.status: str` at `src/squads/_models/_item.py:100,105`,
`WorkflowSpec.items: dict[str, ItemSpec]` at `_workflow/_models.py:415`), **both the `ItemType` and
`Status` enums survived as the vocabulary backbone** — the closed sets the loader coerces spec keys
into, the completeness floors spec validation checks against, the key type of the playbook, the
source of the CLI's per-type command registration, and (for types) a duplicated hardcoded copy of
every prefix/folder. All ten type members — the seven work types included — are therefore
effectively reserved: a project spec can *add* custom types but can never **omit, rename, or
re-prefix** a built-in. The `Status` enum is the same pattern on the status axis: the vocabulary is
already fully declared in the spec's `[statuses.*]` / `StatusSpec`, yet a hardcoded `StrEnum` shadows
it and is the closed set every status must belong to.

**This ADR removes BOTH vocabulary enums** — `ItemType` and `Status` — so the loaded workflow spec is
the sole vocabulary authority on both axes. The `Status` removal is the identical pattern designed
below for `ItemType`; where a section is type-specific, the parallel status treatment is called out
inline.

### The vocabulary is already fully declared in the spec — and duplicated in code

`src/squads/_workflow/default_workflow.toml` already declares `prefix`, `folder`, **and** the
`is_meta` capability flag for **every** type — all ten `[items.*]` (lines 208–320), with
`is_meta = false` for the seven work types and `is_meta = true` for `role`/`skill`/`operator`. The
loader builds a `prefix → type` reverse index from `ts.prefix` (`_workflow/_loader.py`), and
`WorkflowSpec` already exposes `work_types()` (`= {t for t,ts in items if not ts.is_meta}`) and
`item_is_meta()`. The spec is already the complete source of truth for per-type vocabulary; every
`ItemType`-based copy in code is duplication.

### Where built-in vocabulary is still hardcoded today

- **`src/squads/_models/_enums.py:13–23`** — the `ItemType` `StrEnum` enumerating all ten; its
  `.prefix`/`.folder` properties (lines 26–33) read the maps below; `WORK_TYPES` (lines 37–45) and
  `TYPE_ALIASES`.
- **`src/squads/_models/_enums.py:48–78`** — the `Status` `StrEnum` enumerating all ~23 statuses
  across every lifecycle (work, adr, review, guide, agent, sub-entity, finding). The spec already
  declares each status in `[statuses.*]` (terminal flag + optional `badge`) and validates a
  structural floor against it (`_workflow/_models.py:567` `_RESERVED_FLOOR`, already a
  `frozenset[str]`), so the enum is a second, code-side copy of the same names.
- **`src/squads/_models/_vocab.py`** — a **second, hardcoded copy** of the spec's data:
  `RESERVED_PREFIX` (lines 37–48), `RESERVED_FOLDER` (lines 52–63), `RESERVED_TYPE_BY_PREFIX`
  (line 67); `is_reserved()` (line 70) = "in `RESERVED_PREFIX`"; `prefix_for()`'s resolution order
  (lines 78–79, 92–93) makes a reserved type **never overridable** — the map short-circuits before
  the spec is read, so even a spec declaring `[items.task] prefix = "TCK"` still yields `"TASK"`.
- **`src/squads/_workflow/_models.py:544–550`** — `WorkflowSpec._validate` requires the spec to
  include **all** reserved `ItemType` members (`reserved_types = {t.value for t in ItemType}`, all
  ten): *"may ADD but must never OMIT a reserved one."* Omitting `feature` fails load. The status
  floor just below (lines 552–588) is already a narrower `frozenset[str]` rather than the full enum;
  this ADR narrows it **further** — down to the agent lifecycle alone (Decision §5).
- **`src/squads/_models/_item.py`** — the current `Item` design (ADR-266) *deliberately special-cases
  built-ins*: `prefix` is written to frontmatter **only for custom types** (`to_frontmatter_dict`,
  lines 193–196); built-ins re-derive from `RESERVED_PREFIX` in `Item.id` (line 181) and in
  `from_frontmatter` (lines 224–227), which even **overwrites** any stored value. This exists so a
  file round-trips **without a spec in hand** (`sq repair`, `from_frontmatter`, `_models` staying
  spec-decoupled and acyclic — it must never import `_workflow`). That "spec-free round-trip via a
  hardcoded map" is the one real constraint this ADR must *replace*, not merely delete.

### Every consumer that still binds to the enums (grep `ItemType` — 192 refs / 27 files; `\bStatus\b` — 53 refs / 17 files)

**`ItemType` consumers:**

| Cluster (files · refs) | What it does today | Disposition |
|---|---|---|
| `_models/_enums.py` (9) | defines `ItemType`, `WORK_TYPES`, `TYPE_ALIASES`, `.prefix`/`.folder` | **deleted** — the enum and its maps go |
| `_models/_vocab.py` (in `_item.py` import) | `RESERVED_*` maps, `prefix_for` reserved short-circuit | **deleted** — `prefix_for(t, spec)` = `spec.items[t].prefix`, unknown → error |
| `_models/_item.py` (4) | re-exports `ItemType`; reserved-map id fallbacks | drop re-export; `Item.id`/`from_frontmatter` format from stored `prefix` (Decision §3) |
| `_workflow/_loader.py` (9) · `_workflow/_models.py` (6) | coerce TOML keys via `ItemType(...)`; all-ten validation floor; `prefix_to_type` | keys stay `str`; floor → three `is_meta` names (Decision §2); reverse index from `ts.prefix` for all |
| `_interactions/_loader.py` (17) · `__init__.py` (18) · `_models.py` (2) | `ItemType(name)` coercion; `_check_coverage` over the seven `_WORK_TYPES`; playbook keyed by `ItemType` | **the hard blocker** — key by `str`; coverage = "every `spec.work_types()` entry"; missing entry → thin auto-generated skill (F4) |
| `_services/_maintenance.py` (27) | mostly `ItemType.SKILL.folder/.prefix`, skill-sync, `for item_type in ItemType`, `{t.value for t in ItemType}` "built-in" set | meta refs → meta-name constants + `spec.items["skill"]`; iterate `spec.items`, not the enum |
| `_services/_roster.py` (7) · `_base.py` (9) · `_items.py` (6) · `_service.py` (2) · `_results.py` (2) | `ItemType.ROLE/SKILL/OPERATOR` roster/list calls; `SUBENTITY_*` maps; result-dataclass fields typed `ItemType` | meta refs → meta-name constants; `SUBENTITY_*` derive from spec `subentity_kind`; fields → `str` |
| `_cli/__init__.py` (9) · `_create.py` (12) · `_items.py` (1) · `_common.py` (6) | static vs dynamic per-type command registration split on "is it a built-in enum member"; `_make(item_type: ItemType)`; hardcoded work-type tuple | **all** types register dynamically from `spec.items`; the static/dynamic bifurcation is removed |
| `_cli/_role.py` (3) · `_skill.py` (2) · `_operator.py` (2) · `_dev.py` (2) | the three meta-type sub-commands + dev helper | reference meta-name constants, not enum members |
| `_backends/_claude_code/_backend.py` (4) · `_agents_md/_backend.py` (2) | `item.type == ItemType.SKILL`; `{t.value for t in ItemType}` built-in set | `item.type == META_SKILL` (str const); iterate `spec.items` |
| `_migrations/_v0_1_to_v0_2.py` (7) · `_v0_2_to_v0_3.py` (10) · `_v0_4_to_v0_5.py` (8) · `_v0_5_to_v0_7.py` (5) | frozen historical runners referencing `ItemType.TASK/FEATURE/REVIEW`, `for item_type in ItemType`, `_BODY_KIND` maps | **inline frozen local constants** — a migration is a point-in-time snapshot and must NOT track live vocabulary (see Consequences) |

**`Status` consumers (identical pattern):**

| Cluster (files · refs) | What it does today | Disposition |
|---|---|---|
| `_models/_enums.py` (1) | defines the `Status` `StrEnum` (~23 members) | **deleted** — the spec's `[statuses.*]` is the vocabulary |
| `_workflow/_loader.py` (7) · `_workflow/_models.py` (9) | `Status(value)` coercion (`_loader.py:106`); `StatusSpec` keyed by `Status`; the `_RESERVED_FLOOR` floor check; reachability | keys stay `str`; coercion dropped; `_RESERVED_FLOOR` **narrows to the agent lifecycle** (`Draft`/`Active`/`Archived`) — sub-entity/finding statuses leave the floor (Decision §5); add a per-sub-entity-kind **completion-status** validation atop the `terminal` flag |
| `_services/_maintenance.py` (6) · `_roster.py` (5) | `Status.ACTIVE` (role/skill/operator creation) | validated `STATUS_ACTIVE` constant — agent-lifecycle, **stays reserved** (the same by-name binding as the meta-type constants) |
| `_services/_subentities.py` (3) | `Status.DONE`/`.TODO` (sub-entity create + done-toggle) | **no literal** — create sets the machine's start state; the done-toggle resolves the machine's designated completion status (Decision §5) |
| `_models/_item.py` (3) · `_subentity.py` (1) · `_services/_results.py` (2) · `_retype.py` (1) · `_items.py` (1) | re-export; result/field annotations typed `Status` | drop re-export; fields → `str` (already stored as `str`) |
| `_discussion.py` (3) · `_cli/_items.py` (3) · `_cli/_main.py` (1) | status-badge / status-filter rendering | already spec-resolved via `status_badge()`; annotations → `str` |
| `_migrations/_meta_compat.py` (4) · `_v0_4_to_v0_5.py` (2) | frozen historical status handling | **inline frozen local constants** — same point-in-time caution |

### Governing lineage

- **ADR-214** kept the enums as the typed backbone and validates the spec == `set(ItemType)`
  (rule #6). This ADR removes that floor for work types.
- **ADR-232** opened the de-typing arc: it widened `Item.type`/`status` to `str` and reified
  capability flags, but *deliberately kept both the `ItemType` and `Status` enums as the vocabulary
  source*. **This ADR completes that arc** — removing both enums so the spec is the sole vocabulary
  authority on the type and status axes alike.
- **ADR-266** stamped `prefix` onto `Item` but kept `_vocab.py`'s `RESERVED_*` maps as the built-in
  floor and the spec-free round-trip source. This ADR removes that residual hardcoding.
- **ADR-274 / EPIC-280 / FEAT-281** own vocabulary **rename migrations** — the boundary is drawn
  below.

## Decision

**The bundled/loaded workflow spec is the ONLY vocabulary. Remove BOTH the `ItemType` and `Status`
enums from the code entirely; the engine becomes fully generic over spec-defined types and statuses.
No hardcoded vocabulary survives in source — not the enums, not the `RESERVED_*` prefix/folder maps,
not the enum-as-validation floors, not `TYPE_ALIASES`. `role`/`skill`/`operator` are distinguished
from work types solely by the spec's `is_meta` flag, and the engine binds them plus their
agent-lifecycle statuses (`Draft`/`Active`/`Archived`) by literal name as validated constants where
structurally required (roster, backends, agent lifecycle).** The seven work-item types become
ordinary vocabulary a spec may drop, rename, and re-prefix; every status — work, review, guide,
sub-entity, and finding — resolves entirely from the spec. **The ONLY reserved surface is the three
meta-types plus their agent-lifecycle statuses; nothing else is reserved — no work-type status, no
sub-entity or finding status, no priority/severity.** Where the engine formerly set a sub-entity or
finding status by literal name (`Todo` on create, `Done` on the done-toggle, `Open` on a new
finding), it now binds it **by its role in the state machine** — the initial state on create, a
spec-designated completion status on the done-toggle (Decision §5). This completes the arc ADR-232
opened **and erases the type-vs-status asymmetry: every vocabulary axis is spec-driven.**

### 1. All per-type vocabulary resolves from the spec

Delete `RESERVED_PREFIX` / `RESERVED_FOLDER` / `RESERVED_TYPE_BY_PREFIX` / `is_reserved` from
`_vocab.py`. `prefix_for(type_str, spec)` returns `spec.items[type_str].prefix` for **every** type;
unknown → `SquadsError` (no `type.upper()` guess — ADR-266 banned that). Folder resolves from
`spec.items[t].folder` (already so in `_paths`); `prefix → type` from `spec.prefix_to_type` for all
types. `ItemType.prefix`/`.folder`/`TYPE_ALIASES` are removed with the enum.

### 2. Reservation = the `is_meta` floor + three by-name constants, not a vocabulary set

`WorkflowSpec._validate` (`_models.py:544–550`) drops the "all `ItemType` members" check and instead
requires the spec to declare the three types the engine references **by name** — `role`, `skill`,
`operator`, each with `is_meta = true` — and forbids dropping them. These three names survive in
code as small **string constants** (e.g. a `META_TYPES = frozenset({"role","skill","operator"})` and
`META_ROLE`/`META_SKILL`/`META_OPERATOR`), because the roster, the backends (which write role/skill
files), and the agent lifecycle genuinely bind to them by name. That is the irreducible structural
minimum — three names and a boolean flag — **not** a closed vocabulary enum and **not** a prefix/
folder map. Work types have no floor (and no status floor beyond the agent lifecycle — §5).

### 3. Spec-free round-trip: carry `prefix` on the `Item` for ALL types

`Item.id` is a `computed_field` that must render a file's own id **without a spec in hand** and
`_models` must never import `_workflow` (acyclic invariant). Replace the removed `RESERVED_*`
round-trip source by **persisting `prefix` in frontmatter for every type**: delete the
`type not in _RESERVED_PREFIX` guard in `to_frontmatter_dict` so built-ins write a `prefix:` line
too, and remove the reserved-map fallbacks in `Item.id` and `from_frontmatter` so the model formats
purely from the stored string. This keeps **invariant #1** (frontmatter is the source of truth — a
file always describes its own id) and keeps `_models` spec-decoupled and acyclic. Prefix is stamped
at create/retype from the active spec (ADR-266); **legacy built-in files** that predate the line are
backfilled at the `IndexStore.load()` boundary (which already reads the active spec, ADR-249/263) by
the same post-load pass that fills `id_padding` (`_propagate_padding`, ADR-266's precedent). Reads
tolerate a missing line; writes emit it uniformly.

### 4. Consumers become generic over `spec.items`

The playbook keys by `str` and covers `spec.work_types()`; the CLI registers per-type commands
dynamically from `spec.items` (removing the static/dynamic built-in split); the `SUBENTITY_*` maps
derive kind↔type from the spec's per-type `subentity_kind`; `sq check`'s residual `"subtask"` literal
routes through the spec; backends and roster reference the three meta-name constants and iterate
`spec.items`.

### 5. Remove the `Status` enum — narrow the floor to the agent lifecycle, bind everything else by machine role

Delete the `Status` `StrEnum` from `_enums.py`. `Item.status` / `SubEntity.status` are already `str`
and validated against `spec.workflow_for(type).states` at the load boundary (ADR-232); the
`Status(value)` coercion in `_workflow/_loader.py:106` is dropped (keys stay `str`).

**Narrow `_RESERVED_FLOOR` to the agent lifecycle only.** The floor shrinks to exactly the statuses
the engine binds **by literal name** because they *are* a meta-type's own lifecycle: `Draft`,
`Active`, `Archived` — including the `Active` that `role`/`skill`/`operator` creation sets. Those
survive as **validated string constants** (`STATUS_ACTIVE = "Active"`, …), exactly like the three
meta-type name constants in §2, and the floor still requires a spec to declare them (a meta-type must
be creatable, activatable, and archivable — that is structural). **Everything else comes off the
floor:** the sub-entity statuses (`Todo`/`InProgress`/`Blocked`/`Done`/`Cancelled`) and the finding
statuses (`Open`/`Fixed`/`Verified`/`WontFix`) are now **ordinary spec vocabulary**, exactly like
work-type statuses — a spec may rename, reorder, or replace them, and none of them is required or
referenced by literal name in code.

**Bind sub-entity/finding lifecycle by ROLE IN THE MACHINE, not by literal name.** The engine can no
longer write `"Todo"` when it creates a subtask, `"Done"` when it toggles one complete, or `"Open"`
when it opens a finding — those names are no longer guaranteed to exist. Two structural roles replace
the literals, resolved from the sub-entity kind's own state machine:

- **Initial state (create).** Creating a sub-entity/finding sets its status to the **machine's start
  state** — the initial state each workflow already declares — instead of the `Todo`/`Open` literal.
- **Completion target (done-toggle).** The "mark done" toggle resolves to the machine's **designated
  completion status**. This *extends FEAT-211's existing per-status `terminal` capability flag rather
  than inventing new machinery*: a machine flags exactly one of its terminal statuses as the
  **completion** target — the success end-state, distinct from cancel-style terminals
  (`Cancelled`/`WontFix`). The precise capability the toggle logic needs is therefore *"give me this
  sub-entity kind's one completion status"*; it asks the spec for that status per sub-entity kind
  (a `completion`/`done` role layered on the `terminal` flag already carried in `[statuses.*]`)
  rather than hardcoding `"Done"`. A machine that declares more than one terminal must name exactly
  one completion status.

This binding lives behind the **same spec seam type/status already use**: `_models` stays
spec-decoupled (a sub-entity still just carries a `str` status), while the start/completion
resolution — and the "exactly one completion status per sub-entity machine" validation — happen at
the `IndexStore.load()` / service boundary that already holds the active spec (ADR-249/263). Only the
small set of **agent-lifecycle** names survives as `STATUS_*` code constants; the sub-entity and
finding lifecycles carry **no** name literals in source.

Status badges are unaffected — they are already spec-declared (`StatusSpec.badge`, resolved via
`status_badge()` with a graceful fallback), which is why status is *not* folded into the flat
badge-collection generalization (that is ADR-323's scope, and it explicitly leaves status alone: a
status is a badge **plus a machine**).

## Blast radius / consequences

Every `ItemType` and `Status` site from the two tables is dispositioned above. The load-bearing ones
(type axis unless noted):

- **`_vocab.py`** — `RESERVED_PREFIX`/`RESERVED_FOLDER`/`RESERVED_TYPE_BY_PREFIX`/`is_reserved`
  deleted; `prefix_for` is a thin spec lookup.
- **`Item` / frontmatter** — built-in item files **gain a `prefix:` line** on next write; `Item.id`
  and `from_frontmatter` lose the reserved-map fallback; reads stay backward-tolerant via the store's
  spec-aware backfill.
- **Playbook loader** (the hard blocker) — `_coerce_item_type`'s `ItemType(name)` deleted (key by
  `str`); `_check_coverage` requires a playbook entry only for `spec.work_types()`. A custom or
  renamed work type with no bundled entry falls back to F4's **thin auto-generated `sq-<type>`
  skill** — the fallback whenever a built-in name no longer exists.
- **CLI app-build** — today `_cli/__init__.py` registers built-in work types *statically* and custom
  ones *dynamically* (`_builtin_work_type_names`, `_ORDERED_WORK_TYPES`). With no enum, **all** work
  types register dynamically from `spec.items`; the bifurcation and the hardcoded `_create.py` tuple
  are removed. Ordering must derive from a deterministic spec order, not enum declaration order.
- **`sq check` task→feature / subtask→US** — parent and subtask→US rules already read
  `spec.parent_allowed`/`item_parent_required`/`item_subentity_kind`, so they follow a renamed type
  automatically; drop `task` and no type has `subentity_kind = "subtask"`, so the check no-ops. The
  residual `"subtask"` literal and the `SUBENTITY_*` maps in `_services/_base.py` must rederive from
  the spec, or a dropped/renamed type silently loses its sub-entity checks.
- **Migrations** — frozen historical runners must **not** depend on the live vocabulary. Every
  migration that named `ItemType.X` / `Status.X` or iterated `for item_type in ItemType` must inline
  a **frozen local constant** (the literal type/status names as they existed at that schema version).
  This is correct-by-design (a migration is a point-in-time transform) but is real, careful work: a
  migration that iterated "all types" was iterating "all types that existed *then*", which must be
  pinned as a literal, not left tracking whatever the current project spec happens to declare.
- **Meta-type references** — `ItemType.ROLE/SKILL/OPERATOR` across `_roster.py`, `_maintenance.py`
  (skill sync, `ItemType.SKILL.folder/.prefix`), the backends (`item.type == ItemType.SKILL`), and
  the `_role.py`/`_skill.py`/`_operator.py` sub-commands become the three meta-name string constants;
  their prefix/folder come from `spec.items["skill"]`, not `ItemType.SKILL.prefix`.
- **Status floor narrows to the agent lifecycle; sub-entity/finding bind by machine role.**
  `_RESERVED_FLOOR` shrinks to `Draft`/`Active`/`Archived` (plus the `Active` that roster/skill/
  operator creation sets) — the only statuses still required by validation and still held as
  `STATUS_*` code constants. The sub-entity statuses (`Todo`/`InProgress`/`Blocked`/`Done`/
  `Cancelled`) and finding statuses (`Open`/`Fixed`/`Verified`/`WontFix`) leave the floor and become
  ordinary spec vocabulary. `_services/_subentities.py` stops writing `Status.TODO`/`.DONE` literals:
  create sets the machine's start state, and the done-toggle resolves the machine's designated
  **completion status** (a `completion`/`done` role atop FEAT-211's `terminal` flag — one per
  sub-entity machine, validated at spec load). `Status(value)` coercion in the loader is removed.
- **The type-vs-status asymmetry is erased.** After this ADR every vocabulary axis — types, statuses,
  sub-entity kinds, and (via ADR-323) priority/severity — is spec-driven. The reserved surface is
  exactly `{role, skill, operator}` **plus their agent-lifecycle statuses**; there is no work-type,
  sub-entity, or finding status floor, and no hardcoded prefix/folder/badge vocabulary anywhere in
  source.

**Pyright-strict fallout (a headline risk).** Removing two `StrEnum`s that ~245 sites reference
(`ItemType` 192, `Status` 53) flips every `item_type: ItemType` / `status: Status`, `dict[…, …]`,
`frozenset[…]`, and result-field annotation to `str`. The engine already treats `Item.type`/`.status`
as `str`, but the *checked comparisons* against enum members (e.g. `item.type == ItemType.SKILL`,
`item.status == Status.ACTIVE`) lose their static guarantee: a `str == str` compare is always
type-valid, so a name typo is no longer caught by pyright — it must be guarded by the validated
`META_*` / `STATUS_*` constants and by tests. (The `STATUS_*` set is now small — only the agent
lifecycle — because sub-entity/finding lifecycle is resolved by machine role rather than by name, so
there are fewer such comparisons on the status axis.) This is the pervasive, irreversible typing
inversion ADR-232 flagged, now carried to completion for both axes. `ruff`/`pyright` strict must stay
clean across all affected files (≈30, the union of the two tables) in one change.

**Fallback when a built-in name no longer exists:** no silent default. Prefix, folder, and type
resolve **only** through the active spec; an undeclared name is an ordinary "unknown item type"
`SquadsError`, never a `type.upper()` guess. Guidance for a custom/renamed type comes from the thin
auto-generated skill.

## Tests, migration & compatibility

Two concerns must stay distinct:

- **Test structure — not a constraint on this decision.** The operator has planned a complete,
  generic-item-engine-first test-suite rework. The golden-lock / characterization tests currently
  pinned to enum members (the enum-set goldens for types *and* statuses, per-type frontmatter
  goldens) **dissolve** in that rework; they are rebuilt to assert behavior against the bundled
  default spec. So enum-pinned goldens are **not** a blocker for removing either enum.
- **Runtime backward-compat — the surviving invariant.** An existing on-disk squad with **no
  override MUST behave identically.** That guarantee now rests **entirely on the bundled
  `default_workflow.toml`** — which still declares all ten types (prefixes/folders/machines/`is_meta`)
  and all ~23 statuses (terminal flags/badges/lifecycles) exactly as today, and — new under this
  ADR — flags the sub-entity/finding machines' completion status so the done-toggle resolves the same
  `Done`/`Fixed` end-state it does today — and **not** on the `ItemType`/`Status` enums. The generic
  engine loads that bundled default as its baseline vocabulary; the reworked suite asserts default
  behavior against it. This is the single invariant that survives the enums' removal, and it is what
  makes "do nothing" == "today".

**Migration / schema:**
- Built-in item files gain an (additive, now-canonical) `prefix:` frontmatter line. Reads tolerate
  its absence (spec backfill at load), so **no forced migration is required for correctness**; a
  `sq migrate` normalization pass (or natural rewrite on next mutation) stamps every file so the
  legacy omit-branch can be deleted outright. Assess against `SCHEMA_VERSION`: a bump is not required
  for readability but is reasonable to *normalize* every file; defer that call to the migration
  owners.
- The bundled spec gains a **completion-status capability** on each sub-entity/finding machine (a
  flag atop the existing `terminal`); this is a spec-schema addition, not an item-file data change.
- Removing the enum is a **code-shape** change, not a data-shape change — persisted frontmatter is
  unaffected beyond the `prefix:` line above.

### Boundary vs. EPIC-280 / FEAT-281

- **This ADR decides the vocabulary *contract*** — the spec is *permitted* to omit, rename, and
  re-prefix the seven work types (remove the enum, delete `RESERVED_*`, narrow the floor to the three
  `is_meta` names, carry `prefix` on `Item`, make consumers generic), and to rename/reorder every
  non-agent status. It is the **precondition** that unblocks FEAT-281: you cannot `rename-type task
  ticket` while the enum, the floor, and `RESERVED_PREFIX` all pin `task`/`TASK`. FEAT-281's and
  EPIC-280's meta-type non-goals already agree with this ADR's reserved set.
- **EPIC-280 / FEAT-281 owns the migration *mechanics*** — the atomic ID/ref/folder/prose rewrite
  when a rename happens, the audited `sq migrate` runbook, and its schema bump. This ADR builds none
  of that (the `prefix:`-line normalization is a natural fit for the same migration surface).
- **"Droppable" and "re-prefixable at setup"** are net-new here and not covered by EPIC-280 (scoped
  to renames of populated squads).

## Options considered

**Option A (recommended) — Full de-typing / generic item engine, both axes.** Remove the `ItemType`
**and** `Status` enums entirely; the loaded spec is the sole vocabulary authority for types and
statuses; the three meta-types survive only as `is_meta` + by-name constants, and the **agent
lifecycle** statuses as validated `STATUS_*` constants (a narrowed `_RESERVED_FLOOR`); sub-entity/
finding lifecycle binds by machine role (start state + a spec-designated completion status), so those
statuses are ordinary spec vocabulary; `prefix` is carried on `Item` for all types; every consumer
iterates `spec.items` / `spec.work_types()` / `spec.workflow_for(t).states`.
*Pros:* fully delivers the operator's principle — no hardcoded type *or* status vocabulary anywhere
in source beyond the three meta-types and their lifecycle, no duplicated spec data, the exact class of
hardcoding that caused the reserved-names problem is gone; completes ADR-232's arc on both axes and
erases the type-vs-status asymmetry; keeps invariant #1 and the acyclic `_models` constraint intact;
leaves the bundled default as the single, clean backward-compat baseline.
*Cons:* the widest, irreversible change in the codebase — ≈245 sites across ~30 files, a pervasive
pyright-strict inversion on two axes, migrations must pin frozen local vocabularies, a new
completion-status capability on each sub-entity machine, and the full enum-pinned golden suite is
rebuilt (already planned).

**Option B (rejected) — Keep the enums as demoted convenience enumerations; relax only the
validation floors and the `RESERVED_*` maps.** The earlier, narrower stance.
*Cons:* leaves hardcoded ten-member type and ~23-member status vocabularies in source that still
shadow the spec, keeps the static/dynamic CLI split and the enum-keyed playbook, and preserves the
conceptual footgun (enum membership read as reservation). It does not satisfy "the spec is the ONLY
vocabulary," so it is rejected in favor of finishing the job.

**Option C (rejected) — Always load the spec to render an id (no `prefix` on `Item`).** Threads a
spec into `Item.id`/`from_frontmatter`.
*Cons:* forces a `_models`→`_workflow` import — a direct violation of the acyclic / spec-decoupled
invariant — and breaks invariant #1 in spirit (a file could not render its own id if the spec failed
to load). Rejected; §3 (carry `prefix`) is used instead.

**Option D (rejected) — Keep the full `_RESERVED_FLOOR` (agent + sub-entity + finding statuses).**
The stance ADR-322 was originally drafted with: delete the `Status` enum but keep the whole floor and
bind sub-entity/finding transitions by literal name via `STATUS_*` constants.
*Cons:* leaves the sub-entity and finding status vocabularies effectively reserved — a spec could not
rename or reorder them — which re-creates, on the status axis, exactly the reserved-names problem this
arc exists to remove, and keeps a type-vs-status asymmetry (types fully free, most statuses pinned).
Rejected in favor of narrowing the floor to the agent lifecycle and binding sub-entity/finding
transitions by their role in the machine (§5).

### Recommendation

**Option A — full de-typing / generic item engine, both axes.** Remove the `ItemType` and `Status`
enums; make the loaded spec the sole vocabulary authority for types and statuses; distinguish
`role`/`skill`/`operator` only via `is_meta` plus their by-name constants; keep **only** the
agent-lifecycle statuses in a narrowed `_RESERVED_FLOOR` (as `STATUS_*` constants) and bind
sub-entity/finding lifecycle by machine role (start state + a spec-designated completion status atop
the `terminal` flag); carry `prefix` on the `Item` for all types. Runtime backward-compat is
guaranteed by the bundled `default_workflow.toml` alone, and the (already planned) generic-first test
rework replaces the enum-pinned goldens. This is the widest change in the codebase and its risk is
concentrated in the playbook loader and the pyright-strict inversion — but it is the only option that
fully realizes the operator's principle, completes the arc ADR-232 opened, and leaves the reserved
surface at exactly `{role, skill, operator}` plus their agent-lifecycle statuses.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-07T09:39:15Z] Robert Architect:
  - Drafted per Pierre's design intent: shrink the reserved set to exactly {role, skill, operator} and make the seven work-item types (epic/feature/task/bug/decision/review/guide) fully overridable — droppable, renamable, re-prefixable. Amends ADR-214's 'spec type set == set(ItemType)' floor and narrows the reserved resolver ADR-266 established in _vocab.py.
  - Recommendation: Option A — relax RESERVED_PREFIX/RESERVED_FOLDER + the validation type-floor to the three meta-types, flip prefix_for so the spec wins for work types, and make the remaining consumers (playbook loader, the SUBENTITY_* static maps in _services/_base.py, the residual 'subtask' literal in sq check) spec-driven or degrade gracefully. Keep the ItemType enum as a convenience/default-spec enumeration (demoted from 'floor'); defer the deeper enum-shrink (Option B) to a follow-up cleanup since it adds no capability.
  - Top risks: (1) the playbook loader is the hard blocker — it coerces names via ItemType(name) and requires all seven, so a dropped/renamed work type currently fails load; a custom type must fall back to F4's thin auto-generated sq-<type> skill. (2) The SUBENTITY_* maps key kind↔type off built-in names, not the spec's subentity_kind — a dropped/renamed type silently loses its sub-entity checks unless these are rederived from the spec. (3) Golden-lock/compat: the bundled default_workflow.toml MUST keep declaring all ten so a no-override squad stays byte-identical (ADR-214 §4).
  - Boundary: this ADR decides the vocabulary contract (spec MAY omit/rename/re-prefix the seven) and is the precondition that unblocks FEAT-281; EPIC-280/FEAT-281 still own the data-rewrite migration mechanics + schema bump for renaming a populated squad. Left Proposed for your review, @manager — no tasks/code created.
- [2026-07-07T09:49:24Z] Robert Architect:
  - REVISED (2 operator escalations folded in). The recommendation flipped from the original 'Option A, relax validation, keep the ItemType enum as a demoted convenience' to FULL de-typing: remove the ItemType enum from the code entirely and make the loaded workflow spec the ONLY vocabulary authority. This completes the arc ADR-232 opened (which widened Item.type to str but kept the enum as the backbone).
  - Decision now: (1) delete RESERVED_PREFIX/RESERVED_FOLDER/RESERVED_TYPE_BY_PREFIX from _vocab.py — they duplicate what default_workflow.toml already declares (prefix+folder+is_meta for all ten); prefix_for resolves from the spec for every type. (2) Reservation of role/skill/operator = the is_meta validation floor + three by-name string constants the engine binds structurally (roster/backends), NOT a vocabulary set or a prefix map. (3) Spec-free round-trip is preserved by carrying prefix on the Item for ALL types (write the prefix: frontmatter line for built-ins too, backfill legacy files at the spec-aware load boundary) — this keeps invariant #1 and avoids a _models->_workflow import cycle. The alternative (always load the spec to render an id) is rejected because it violates the acyclic/spec-decoupled _models constraint.
  - Scope: I grepped ItemType across src/ — 192 refs in 27 files — and dispositioned every cluster in a table in the body (enum def, _vocab maps, playbook loader, sq check, CLI app-build, meta-type refs, backends, and the frozen historical migrations). Tests: kept two concerns distinct per the directive — test structure is reworked generic-first (enum-pinned goldens dissolve, NOT a blocker), while the surviving runtime invariant is that a no-override squad behaves identically, guaranteed ENTIRELY by the bundled default_workflow.toml (declares all ten), not the enum.
  - Top risks now: (1) the playbook loader is the hard structural blocker — ItemType(name) coercion + all-seven _check_coverage + ItemType-keyed PlaybookSpec; a dropped/renamed work type currently fails load and must fall back to F4's thin auto-generated sq-<type> skill. (2) pyright-strict fallout of removing the StrEnum across 192 sites: every ItemType annotation flips to str and checked comparisons like item.type == ItemType.SKILL lose static typo-protection — meta-name typos must be guarded by validated constants + tests, and the full suite must stay pyright/ruff clean in one change. (3) migrations are frozen point-in-time runners and must inline their own frozen local vocabulary, never track the live spec. (4) backward-compat now rests solely on the bundled default spec.
  - Still Proposed, no code/tasks created. @manager — revised per both operator escalations; ready for review.
- [2026-07-07T10:05:50Z] Robert Architect:
  - BROADENED per operator directive: ADR-322 now removes BOTH vocabulary enums — ItemType AND Status — so the loaded workflow spec is the sole vocabulary authority on both axes. Retitled accordingly. Status removal is the identical pattern already designed for ItemType; the body calls out the parallel status treatment inline and adds a dedicated Decision §5 + a second consumer table.
  - Status specifics: the Status StrEnum in _enums.py (~23 members) is deleted; Status(value) coercion at _workflow/_loader.py:106 is dropped (keys stay str); Item.status/SubEntity.status are already str and validated against spec.workflow_for(type).states at the load boundary. The structurally-bound status names — the existing _RESERVED_FLOOR (Draft/Active/Archived + Todo/InProgress/Blocked/Done/Cancelled + Open/Fixed/Verified/WontFix) plus Status.ACTIVE/DONE/TODO at creation/toggle sites — become validated STATUS_* string constants, exactly like the three meta-type name constants. Crucially: the _RESERVED_FLOOR VALIDATION stays (a spec must still declare those statuses); only the enum TYPE goes.
  - Grep: Status = 53 refs across 17 files, dispositioned in the new table (enum def, loader coercion + StatusSpec keys + floor, maintenance/roster/subentities by-name refs, discussion/CLI status-badge rendering already spec-resolved, meta_compat + v0_4 migrations). Combined blast radius is now ~245 sites across ~30 files (ItemType 192 + Status 53).
  - Status-specific risk: status names are referenced by-name at more scattered runtime sites than types (roster/skill creation set Status.ACTIVE; sub-entity toggles use Status.DONE/TODO), so the pyright typo-protection loss bites harder — every such site must route through a validated STATUS_* constant + test, not a bare string literal. Otherwise the pattern, migration caution, FEAT-231 test rebuild, and backward-compat-rests-on-bundled-default notes are identical to the type axis. Status badges are untouched (already spec-declared via StatusSpec.badge) — and status is deliberately NOT folded into ADR-323's badge collections (a status is a badge PLUS a machine). Still Proposed, no code/tasks. @manager
- [2026-07-07T14:32:07Z] Robert Architect:
  - REVISED per Pierre's design-gate redirect (ADR-323 accepted as-is; 322 accepted with this one change). Narrowed the reserved status surface: _RESERVED_FLOOR now covers ONLY the agent lifecycle (Draft/Active/Archived + the Active roster creation sets). The sub-entity statuses (Todo/InProgress/Blocked/Done/Cancelled) and finding statuses (Open/Fixed/Verified/WontFix) come OFF the floor — they are ordinary spec vocabulary now, renamable/reorderable/replaceable like work-type statuses.
  - Specified the replacement binding (Decision §5): the engine no longer sets those statuses by literal name (create→'Todo', done-toggle→'Done', new finding→'Open'). It binds BY ROLE IN THE MACHINE — create sets the machine's start state; the done-toggle resolves the machine's designated COMPLETION status, a completion/done role layered on FEAT-211's existing per-status 'terminal' flag (extends it, no new machinery). The toggle logic's precise need = 'give me this sub-entity kind's one completion status'; a machine with >1 terminal must name exactly one. Resolution + the 'exactly one completion status per sub-entity machine' validation live at the IndexStore.load/service seam that holds the active spec, so _models stays spec-decoupled (a sub-entity still just carries a str status).
  - Updated the Status consumer table (split roster Status.ACTIVE — stays reserved — from _subentities Status.DONE/TODO — now machine-role-resolved), the blast-radius 'status floor' bullet, the pyright note (STATUS_* set shrinks to the agent lifecycle), Option A, the Recommendation, and added a rejected Option D = the original 'keep the full floor' stance. Backward-compat note now calls out that the bundled default flags each sub-entity/finding machine's completion status so the done-toggle resolves the same Done/Fixed end-state as today.
  - Stated the headline consequence explicitly: this ERASES the type-vs-status asymmetry — every axis (types, statuses, sub-entity kinds, priority/severity via ADR-323) is spec-driven; the ONLY reserved surface is {role, skill, operator} + their agent-lifecycle statuses. Left Proposed — @manager, ready for your read; Pierre owns the accept.
- [2026-07-07T14:35:18Z] Catherine Manager:
  - Accepted at the design-gate review (op-pierre deciding). One redirect applied vs. the drafted version: _RESERVED_FLOOR narrowed to the agent lifecycle only (Draft/Active/Archived + creation Active); sub-entity and finding statuses are now ordinary spec vocabulary, bound by machine role (start state on create, a completion flag layered on FEAT-211's terminal flag for the done-toggle) rather than by literal name. Reserved surface is now exactly {role, skill, operator} + their statuses.
- [2026-07-08T13:05:00Z] Robert Architect:
  - Interpretation note (2026-07-08, architect) — scope of the §1 'never a type.upper() guess' ban, prompted by a TASK-328 conformance question. Clarifying intent, not changing the decision.
  - The ban is load-bearing at the VOCABULARY RESOLVER: prefix_for (and any code that resolves a type's real, persisted prefix/folder from the spec) MUST raise SquadsError on an unknown/absent type and MUST NOT fall back to type.upper(). That is where ADR conformance is judged.
  - The ban's INTENT also governs the acyclic formatters Item.id and SquadsDB.format_id, but differently: those genuinely cannot raise (they render ids for reprs/logs/error messages) and cannot import _workflow (acyclic invariant, §3), so a defensive stand-in for an unset prefix is permitted. The constraint is on its SHAPE — it must be an obviously-synthetic sentinel (e.g. UNRESOLVED-42) that no reader or test mistakes for a real id, NEVER a plausible-but-wrong type.upper() (which silently mis-renders decision->ADR, review->REV, guide->DOC, operator->OP). The invariant to hold across the whole codebase: no path may EMIT a plausible-looking-but-wrong id — resolvers raise, formatters degrade to a diagnosable sentinel.
  - Consistent with §3, Item.prefix stays a soft, backfilled field (not hard-required): a legacy file whose .id may be touched before the load-boundary backfill must still load, and bare Item(...) construction in tests must not crash. Persist-for-all-types + backfill-at-load is the spec-free round-trip mechanism; the sentinel is only the never-should-happen guard behind it.
- [2026-07-08T15:16:14Z] Robert Architect:
  - Clarification (2026-07-08, architect) — §5 'completion' vs 'terminal', re REV-337 finding F2. Ruling: 'completion' is an INDEPENDENT machine-role flag that MAY be non-terminal; it is NOT a subset of 'terminal'. The implementation (StatusSpec.completion decoupled from terminal) is correct and blessed as-is; the '§5 flags exactly one of its terminal statuses' phrasing is imprecise wording, not the operative rule.
  - Two grounds. (1) The subset is false for any two-phase machine: the finding lifecycle is Open→Fixed→Verified, so its done-target Fixed is intrinsically non-terminal because a QA Verified step follows — a fixing dev asserts Fixed, Verified is QA's call. (2) This ADR's OWN backward-compat invariant already names Fixed as the finding completion target ('the bundled spec … flags the sub-entity/finding machines' completion status so the done-toggle resolves the same Done/Fixed end-state it does today'), and today's finding done-toggle sets Fixed, which is non-terminal. The subset-preserving alternative (designate the terminal Verified as the finding completion) would therefore VIOLATE do-nothing==today and is not actually available — Fixed is the required target, so decoupling completion from terminal is the only implementation consistent with this ADR's own compat invariant.
  - Also decisive on the shared-name axis: StatusSpec.terminal is one flag per status NAME, and Fixed is shared by the finding and bug lifecycles (bug Fixed is deliberately non-terminal/pending-verification). Flagging Fixed.terminal=true to force the subset would silently flip bug Fixed to terminal and hide/close Fixed bugs in sq list/blocked — a regression. Confirmed: is_open('Fixed') is True and must stay True.
  - Read §5 as: each sub-entity/finding machine designates exactly ONE completion status via a completion role layered on the terminal flag; that status MAY be non-terminal (finding Fixed) and is distinct from both terminal-success and cancel-style side states (Cancelled/WontFix). The '>1 terminal ⇒ name exactly one completion' sentence stands, generalized to 'exactly one completion per sub-entity/finding machine' (enforced by _check_completion_status). This is a CLARIFICATION refining incidental wording, NOT a decision reversal — the bind-by-machine-role decision is unchanged — so it is recorded as a dated comment, not a supersession.
  - Forward note (F3, for FEAT-212 / FEAT-327): completion inherits terminal's per-status-NAME (not per-machine) coupling. The bundled default is safe (Done/Fixed don't collide across subtask/story/finding), but custom sub-entity kinds that reuse a status name with different completion semantics are unrepresentable. Decide per-machine completion designation there; out of scope for TASK-330.
<!-- sq:discussion:end -->

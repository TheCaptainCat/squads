---
id: TASK-328
sequence_id: 328
type: task
title: Delete ItemType enum + RESERVED maps; spec-only type vocabulary
status: Done
prefix: TASK
parent: FEAT-326
author: tech-lead
subentities:
- local_id: ST1
  title: Delete ItemType + RESERVED_*/TYPE_ALIASES; prefix_for is spec-only
  status: Done
  story: US1
- local_id: ST2
  title: Carry prefix on every Item frontmatter; spec-free id round-trip + load backfill
  status: Done
  story: US1
- local_id: ST3
  title: Narrow type floor to three is_meta types; META_* constants for meta refs
  status: Done
  story: US1
- local_id: ST4
  title: Freeze ItemType refs in all four migration runners to inline frozen local
    constants
  status: Done
  story: US1
created_at: '2026-07-07T14:50:23Z'
updated_at: '2026-07-08T13:55:54Z'
---
<!-- sq:body -->
## Scope

Remove the `ItemType` `StrEnum` and every duplicate hardcoded type-vocabulary
map so the loaded workflow spec is the sole authority on the type axis, and
carry `prefix` on every `Item` so a `.md` file round-trips **without a spec in
hand**. Implements the type-axis half of ADR-322 (US1). This is the primary
bisectable unit for the type axis, minus the playbook/CLI registration (its own
task).

Because deleting the enum is only green once **no code still references it**,
this task also freezes the `ItemType` references in **all four** migration
runners to inline frozen local constants (the type-axis migration-vocabulary
freeze was moved here from TASK-331). A grep-clean / pyright-clean delete is
impossible while the runners still import the enum being removed.

## Areas / files

- `_models/_enums.py` — delete `ItemType`, `WORK_TYPES`, `TYPE_ALIASES`, and the
  `.prefix`/`.folder` properties.
- `_models/_vocab.py` — delete `RESERVED_PREFIX` / `RESERVED_FOLDER` /
  `RESERVED_TYPE_BY_PREFIX` / `is_reserved`. `prefix_for(type_str, spec)` returns
  `spec.items[type_str].prefix` for every type; unknown type → `SquadsError`
  (no `type.upper()` guess). Folder resolves from `spec.items[t].folder`.
- `_models/_item.py` — drop the `ItemType` re-export; remove the
  `type not in _RESERVED_PREFIX` guard in `to_frontmatter_dict` so **every** item
  writes a `prefix:` line; remove the reserved-map fallbacks in `Item.id` and
  `from_frontmatter` so the id formats purely from the stored `prefix` string
  (spec-free round-trip; `_models` must not import `_workflow`).
- `_workflow/_loader.py` / `_workflow/_models.py` — drop the `ItemType(...)`
  coercion of TOML keys (keys stay `str`); build the `prefix → type` reverse
  index from `ts.prefix` for all types; narrow `WorkflowSpec._validate`'s type
  completeness floor from "all `ItemType` members" to **only the three `is_meta`
  types** (`role`/`skill`/`operator` present with `is_meta = true`, not
  droppable). Introduce the by-name constants — `META_TYPES` frozenset +
  `META_ROLE`/`META_SKILL`/`META_OPERATOR`.
- `_services/_maintenance.py`, `_roster.py`, `_base.py`,
  `_backends/_claude_code/_backend.py`, `_backends/_agents_md/_backend.py` —
  replace `ItemType.ROLE/SKILL/OPERATOR` with the meta-name constants; resolve
  skill folder/prefix from `spec.items["skill"]`; iterate `spec.items` /
  `spec.work_types()` instead of `for t in ItemType`; `item.type == ItemType.SKILL`
  → `item.type == META_SKILL`.
- Store load boundary — backfill `prefix` onto legacy built-in item files at
  `IndexStore.load()` (the spec-aware post-load pass that already fills
  `id_padding`), tolerant of a missing line.
- Result dataclasses / model fields annotated `ItemType` → `str` (already stored
  as `str` on disk).
- **Migration runners — `ItemType` freeze (all four).**
  `_migrations/_v0_1_to_v0_2.py`, `_v0_2_to_v0_3.py`, `_v0_4_to_v0_5.py`,
  `_v0_5_to_v0_7.py` — replace `ItemType.X`, `for item_type in ItemType`, and the
  `_BODY_KIND: dict[ItemType, ...]` references with **inline frozen local
  constants** — literal tuples/maps of the type-name strings AND the
  prefix/folder **values** exactly as they existed at each runner's target
  schema version. Convert every call site that currently passes an `ItemType`
  to the frozen string literal now that those APIs take `str`:
  `paths.folder_for(...)`, `db.allocate_id(...)`, `paths.squad_relative(...)`,
  and `.prefix`/`.folder` reads. These constants are a **point-in-time snapshot
  frozen into the runner — never the live spec and never the (now-removed)
  enum**; a migration transforms files as they were at the version it targets,
  so its vocabulary must be pinned, not re-derived. Note: `_v0_4_to_v0_5.py` is
  touched here for its `ItemType` references only; its `Status` references are
  frozen under TASK-330.

## Done criteria

- `grep -rn 'ItemType' src/squads` returns no vocabulary-enum hits (verify any
  identically-named locals by hand) — including the four migration runners.
- `prefix_for` resolves solely from `spec.items[type].prefix`; an unknown type
  raises `SquadsError`.
- Every `Item`, built-in or custom, writes a `prefix:` line; a `.md` round-trips
  through `from_frontmatter`/`to_frontmatter_dict` with no spec loaded.
- The type completeness floor requires only the three `is_meta` types; a spec
  that omits, renames, or re-prefixes a work type loads successfully.
- No-override default squad produces identical IDs and folders.
- Each migration runner pins its type vocabulary as frozen local constants (not
  the live spec, not a removed enum); historical migration tests still reproduce.
- `pyright` + `ruff check` + `ruff format --check` clean across the touched files
  (this absorbs the type-axis half of the enum→`str` annotation inversion).

## Sequencing note

The playbook and CLI are the largest `ItemType` consumer cluster; they are
converted to `str`-keyed / `spec.items`-driven registration in the generic
playbook + CLI task (TASK-329, landed). This task then reaches a green pyright
because deleting the enum and freezing the last remaining references (the
migration runners, folded in here) happen together — the delete is only
grep/pyright-clean once every reference is gone.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 328 add-subtask "<title>"`; track with `sq task 328 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Delete ItemType + RESERVED_*/TYPE_ALIASES; prefix_for is spec-only | US1 |
| ST2 | Done |  | Carry prefix on every Item frontmatter; spec-free id round-trip + load backfill | US1 |
| ST3 | Done |  | Narrow type floor to three is_meta types; META_* constants for meta refs | US1 |
| ST4 | Done |  | Freeze ItemType refs in all four migration runners to inline frozen local constants | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Delete ItemType + RESERVED_*/TYPE_ALIASES; prefix_for is spec-only

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Full self-service type vocabulary in spec
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Remove the ItemType StrEnum (with WORK_TYPES/TYPE_ALIASES and the .prefix/.folder properties) and the RESERVED_PREFIX/RESERVED_FOLDER/RESERVED_TYPE_BY_PREFIX/is_reserved maps in _vocab.py. prefix_for(type, spec) becomes spec.items[type].prefix for every type; an unknown type raises SquadsError with no upper()-guess fallback.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Carry prefix on every Item frontmatter; spec-free id round-trip + load backfill

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — Full self-service type vocabulary in spec
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Drop the built-in-only prefix guard in to_frontmatter_dict so every item writes a prefix line; remove the reserved-map fallbacks in Item.id and from_frontmatter so the id formats purely from the stored prefix (no _workflow import). Backfill prefix onto legacy built-in files at the spec-aware IndexStore.load() post-load pass, tolerant of a missing line.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Narrow type floor to three is_meta types; META_* constants for meta refs

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US1 — Full self-service type vocabulary in spec
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Narrow WorkflowSpec._validate's type completeness floor to the three is_meta types (role/skill/operator, not droppable). Add META_TYPES + META_ROLE/META_SKILL/META_OPERATOR name constants and repoint the meta-type references in _maintenance.py/_roster.py/_base.py/backends at them, resolving skill folder+prefix from spec.items[skill].
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Freeze ItemType refs in all four migration runners to inline frozen local constants

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US1 — Full self-service type vocabulary in spec
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Replace ItemType.X, 'for item_type in ItemType', and the _BODY_KIND enum map in _v0_1_to_v0_2/_v0_2_to_v0_3/_v0_4_to_v0_5/_v0_5_to_v0_7 with inline frozen local constants — type-name literals AND the prefix/folder values as they existed at each runner's target schema version. Convert the ItemType-passing call sites (paths.folder_for, db.allocate_id, paths.squad_relative, .prefix/.folder) to the frozen string literals now those APIs take str. Point-in-time snapshot pinned into the runner, never the live spec or the removed enum. _v0_4_to_v0_5.py's Status refs are TASK-330's.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-08T11:40:40Z] Olivia Lead:
  - Re-scoped (pre-dispatch): folded the ItemType migration-vocabulary freeze into this task. It was TASK-331's, but deleting the ItemType enum here can't be grep-clean or pyright-clean while the four migration runners (_v0_1_to_v0_2, _v0_2_to_v0_3, _v0_4_to_v0_5, _v0_5_to_v0_7) still import and use it — you can't delete a symbol while references remain. So 328's own done-criteria ('no ItemType hits / pyright clean') REQUIRE freezing those runner refs in the same commit.
  - New scope covers the type-name literals AND the prefix/folder values, plus converting the ItemType-passing call sites (paths.folder_for, db.allocate_id, paths.squad_relative, .prefix/.folder) to frozen string literals now those APIs take str. Frozen = point-in-time snapshot pinned into the runner, never the live spec and never the removed enum — that pinning is the whole reason migrations carry their own vocabulary. _v0_4_to_v0_5.py is touched here for ItemType only; its Status refs stay in TASK-330. Added ST4 to track it.
- [2026-07-08T12:30:57Z] Elias Python:
  - ST1 done: deleted `ItemType` StrEnum + `WORK_TYPES` from _models/_enums.py; deleted `RESERVED_PREFIX`/`RESERVED_FOLDER`/`RESERVED_TYPE_BY_PREFIX`/`is_reserved` from _models/_vocab.py. `prefix_for(type, spec)` now resolves solely from `spec.items[type].prefix`; unknown type or missing spec raises SquadsError (no upper()-guess).
- [2026-07-08T12:30:57Z] Elias Python:
  - ST2 done: to_frontmatter_dict() writes prefix: for every type (built-in + custom); Item.id / from_frontmatter dropped the RESERVED_PREFIX fallback (Item.id degrades to type.upper() only as a last resort). Legacy files without a prefix: line are backfilled at IndexStore.load() via the pre-existing _propagate_prefix pass (now spec-only); also backfilled inline in _rebuild_index_from_disk for the sq repair path. Explicit spec-free round-trip test added in tests/test_prefix_resolver.py::TestItemPrefixField::test_full_round_trip_with_no_spec_loaded.
- [2026-07-08T12:30:58Z] Elias Python:
  - ST3 done: WorkflowSpec._validate's type floor narrowed to exactly the 3 is_meta types (role/skill/operator), each required to declare is_meta=true; the old all-ItemType-members check is gone. Added META_ROLE/META_SKILL/META_OPERATOR/META_TYPES constants in _workflow/_models.py (re-exported via _workflow/__init__.py) and repointed every ItemType.ROLE/SKILL/OPERATOR reference (_maintenance.py, _roster.py, _base.py, _items.py, _service.py, both backends, _cli/_dev.py, _cli/_items.py) at them; skill folder/prefix now resolve via spec.items["skill"].
- [2026-07-08T12:30:58Z] Elias Python:
  - ST4 done: all four migration runners (_v0_1_to_v0_2, _v0_2_to_v0_3, _v0_4_to_v0_5, _v0_5_to_v0_7) now carry inline frozen local (type, prefix, folder) tuples instead of iterating/importing ItemType; paths.folder_for/squad_relative calls replaced by direct paths.squad_dir/<frozen literal> construction so migrations never need a spec. db.allocate_id/Item(...) call sites pass the frozen prefix explicitly. _v0_4_to_v0_5.py's Status refs left untouched (TASK-330's scope).
- [2026-07-08T12:41:19Z] Elias Python:
  - Done, InReview. Gates: uv run pyright / ruff check . / ruff format --check . all clean (src+tests). Targeted suite green: all 51 touched test files (2138 tests, 1 unrelated skip) pass — prefix resolver, item round-trip (spec-free, new explicit test), workflow spec/loader/validate goldens, reserved-types invariants (rewritten for the narrowed floor), custom-type paths/CLI/skill, all 4 migration runners + corpus fixtures, repair/renumber, hygiene gate. Manual smoke: init/create/retype/custom-type-override/repair/check on a scratch squad + sq check/sq repair clean on the dogfood squad.
  - Design notes: spec-free round-trip preserved per ADR-322 §3 — Item.id/from_frontmatter no longer touch any reserved map, formatting purely from the stored prefix string (falls back to type.upper() only when prefix is truly unset, e.g. a bare test fixture); _models still never imports _workflow. META_ROLE/META_SKILL/META_OPERATOR/META_TYPES live in _workflow/_models.py, re-exported via _workflow/__init__.py, and are now the sole by-name binding for the roster/backends/CLI meta-type checks. Migration freeze: each of the 4 runners got its own inline (type,prefix,folder) tuple frozen at that runner's target schema (identical values today, deliberately not shared across files) and stopped calling paths.folder_for/squad_relative (which now hard-require a spec) — they build paths directly from the frozen folder literal instead, keeping migrations fully spec-independent.
  - One real behavior-preserving fix along the way: _iter_item_files() now iterates spec.items generically but ORDERED BY each type's existing ItemSpec.order field (not alphabetically) — needed to reproduce the exact historical built-in scan order byte-for-byte, since a same-sequence-number collision's silent resolution (pre-sq-repair---renumber) depends on which type is scanned last; alphabetical order flipped bug-vs-feature collision-slot ownership and broke test_service.py::test_repair_renumber_resolves_collision.
  - Could NOT verify: the full ~4-min suite (explicitly out of scope for me — main loop owns it). I did not touch TASK-330's Status-enum/floor scope or TASK-331 (folded into this task per the re-scope note, so nothing left for it).
- [2026-07-08T12:58:30Z] Paul Reviewer:
  - REVIEW VERDICT: APPROVE (independent review, read-only). Gates re-run clean: pyright exit 0, ruff check exit 0, ruff format --check exit 0. Targeted suites green: test_prefix_resolver, test_reserved_types_invariants, test_workflow_spec, test_migrations, test_squad_ref_hygiene, test_service (repair/renumber/collision), test_golden_rendered_output, test_custom_type_paths, test_workflow_capability_flags. grep 'ItemType' src/squads → 0 hits (1 doc-comment hit in tests/_helpers.py). Faithful to ADR-322's type-axis half; no substantive defects, so no review item filed.
  - Concern 1 (type.upper() fallback in Item.id:177 / SquadsDB.format_id:78) — DISPOSITION: ACCEPT as-is; LOW code risk. It is NOT reachable in production: prefix is resolved via prefix_for (which raises SquadsError on unknown, no upper() guess — ADR §1 honored exactly) at create; backfilled at BOTH load boundaries (_store._propagate_prefix AND repair's _rebuild_index_from_disk:454) before .id is consumed/persisted; and _validate_item_vocab rejects unknown types first. Every production allocate_id/create caller passes an explicit spec-resolved prefix. The fallback only fires for bare test-constructed Items or the transient in-memory window pre-backfill (where .id is not persisted). Extra safety: from_frontmatter recomputes id from the stored prefix (ignores the stored id: line), so even a hypothetical wrong id self-heals on next load. The ADR's hard 'no type.upper() guess' ban lands on prefix_for (the vocabulary resolver) — verified honored; Item.id/format_id keep a provably-unreachable stand-in for the acyclic-decoupling constraint (§3: _models must not import _workflow) and to avoid crashing a computed_field. Forcing a raise would add crash risk for negligible benefit.
  - Concern 1 — ARCHITECT SIGN-OFF: RECOMMENDED (not a blocker). The ADR Consequences say 'never a type.upper() guess' broadly; I read the binding requirement as scoped to prefix_for and consider the unreachable Item.id/format_id stand-in conformant, but given the ADR is emphatic and this reserved-vocab axis has a history of half-fixes, a one-line confirmation from @architect that this interpretation matches intent is cheap insurance. Ship need not block on it.
  - Concern 2 (to_frontmatter_dict writes prefix only 'if self.prefix', _item.py:188) — DISPOSITION: ACCEPT; LOW/non-issue. The 'EVERY item writes a prefix: line' guarantee holds in practice: all service write paths (create/retype/seed/mutations of loaded-and-backfilled items) carry a non-empty prefix, so the line is always emitted. The guard only suppresses an empty prefix: for a bare prefix-less Item (correct — you don't want prefix: ''). test_full_round_trip_with_no_spec_loaded asserts fm['prefix']==prefix for a built-in AND a custom type. Consistent with concern 1: no loud-fail added, no crash risk added.
  - Concern 3 (_iter_item_files ordered by ItemSpec.order, _maintenance.py:402) — DISPOSITION: ACCEPT; LOW/design-note. ItemSpec.order is documented as the deterministic-not-alphabetical registration axis (also driving CLI/playbook), and its default values (10..100) reproduce the historical ItemType declaration order exactly — which is what satisfies ADR-322's overriding 'no-override squad behaves identically' invariant and pins test_repair_renumber_resolves_collision. Note: an intrinsic key (sequence_id) CANNOT be used here — colliding items share a sequence_id by definition, so the collision tiebreak IS the type order, which is exactly what 'order' supplies. The only alternative (alphabetical) would CHANGE historical behavior. Collision resolution is a corruption-recovery path with no user-facing contract on which item wins. Residual coupling (reordering types for display would shift collision-winner) is real but negligible; worth revisiting only if/when display-order customization ships.
  - Also verified: spec-free round-trip holds (no _workflow import in _models; prefix_for takes spec as 'object'); META_ROLE/META_SKILL/META_OPERATOR/META_TYPES are the sole engine by-name meta binding (roster/backends/maintenance/base all route through them; stray raw 'role'/'operator' comparisons are slug/override-kind, not item-type vocab); the type floor requires exactly the three is_meta types (missing meta → raise, missing work type → loads); migration freeze correct — each of the 4 runners carries its OWN inline frozen (type,prefix,folder) literals matching the current spec byte-for-byte, and _v0_4_to_v0_5 keeps its Status refs for TASK-330; no-override golden output identical; no squad-item IDs in src/tests. @tech-lead ready to merge; @architect optional sign-off on concern 1's ADR interpretation.
- [2026-07-08T13:04:51Z] Robert Architect:
  - ARCHITECT RULING (ADR-322 conformance of the residual type.upper() stand-in). Verdict: conformant in substance — the reviewer's approval stands and this does NOT block merge — with one MANDATORY tightening tracked below. The de-typing axis's load-bearing requirement is met; what remains is a hygiene/defense-in-depth residue that must be closed so this isn't 'a fix that looks fixed.'
  - Why it's conformant where it counts: (1) §1's ban is a ban on the VOCABULARY RESOLVER guessing — prefix_for now RAISES SquadsError on unknown/no-spec, no type.upper() fallback. That is where conformance is judged and it is honored. (2) §3 is met — prefix is written to frontmatter for every type, _models does not import _workflow (acyclic preserved), and the spec-free round-trip works (from_frontmatter reads the stored prefix; Item.id formats purely from it). (3) sq repair is conformant too: _rebuild_index_from_disk:455 backfills via prefix_for, NOT a guess (the prompt's framing of repair as a type.upper() site is inaccurate). In production, prefix is spec-resolved at create and backfilled at both load boundaries before .id is consumed — the reviewer's reachability analysis is correct.
  - Where it's still residue (and this is broader than the 3 sites flagged): the 'x or x.type.upper()' idiom survives at ~7 sites — Item.id (_item.py:177), format_id (_index.py:78), the swallow in _propagate_prefix (_store.py:58), and the service/CLI ref-matching helpers _refs.py:92/297/350, _items.py:306, _cli/_common.py:597. All defensive/unreachable given backfill — but type.upper() is the WRONG stand-in because it is plausible-but-wrong exactly for decision->ADR, review->REV, guide->DOC, operator->OP. If it ever leaks (a new path reading .id before backfill, or a write that skips create-time stamping) it emits an id like DECISION-42 that looks real and travels silently into refs/output. That undiagnosable-plausible-wrong id is the precise failure mode this axis has repeatedly been burned by; a scattered copy of the banned token is what turns into 'residue that looks fixed.'
  - Required shape of the fix (the reviewer is RIGHT not to hard-require prefix — that would break the pre-backfill legacy-load window and bare-Item test construction, and would force a crash into an acyclic computed_field). Instead: (a) introduce ONE obviously-synthetic sentinel constant in _item.py (e.g. UNRESOLVED_PREFIX = "UNRESOLVED") and use it in Item.id and format_id — a leak then reads UNRESOLVED-42: loud, test-visible, never crashes, no _workflow import needed; (b) add a shared effective_prefix(item) helper so the service/CLI ref-matchers stop re-inlining the idiom; (c) DELETE the dead try/except in _propagate_prefix — _validate_item_vocab runs first in load() and already raises on unknown types, so by the time backfill runs the type is known-valid and prefix_for cannot fail; call it directly. Net: no code path emits a plausible-but-wrong id — resolvers raise, formatters degrade to a diagnosable sentinel.
  - Disposition: NOT blocking. Approval stands; TASK-328 can merge as-is on release/0.8. But the tightening is MANDATORY within FEAT-326, not optional: fold it into TASK-328 on the still-open branch (strongly preferred — don't ship the literal banned token), or a same-wave follow-up that MUST land before FEAT-326 is marked Done. It is a ~7-site mechanical change plus one constant, one helper, and one dead-branch deletion — low risk. @reviewer for awareness.
- [2026-07-08T13:24:49Z] Elias Python:
  - Architect tightening folded in (pre-commit, still InReview). Sentinel: UNRESOLVED_PREFIX = "UNRESOLVED" in _models/_item.py. Helper: effective_prefix(prefix: str, item_type: str) -> str, also in _models/_item.py (acyclic — no _workflow import). Design note: took (prefix, item_type) rather than an Item, since _index.py's format_id has no Item object at all (just the two bare params) — this single signature covers every site uniformly.
  - Sites converted (grep -rn '.type.upper()' src/squads now empty): _models/_item.py Item.id; _models/_index.py format_id (allocate_id delegates to it); _services/_refs.py:93 (_in_neighbours), :298 (add_ref's tgt_prefix), :351 (refs_in); _services/_items.py:306 (remove_work_item's force-sever); _cli/_common.py:604 (resolve_item_id_any). Dead branch deleted: _index/_store.py::_propagate_prefix's try/except Exception → item.type.upper() swallow is gone; it now calls prefix_for(item.type, spec) directly (load() always runs _validate_item_vocab first, so the type is already known-valid by the time this runs).
  - Test fallout (the sentinel fires unconditionally on an unset prefix now, not just for the 'wrong-looking' types — so bare Item(type='task', ...) without an explicit prefix, which used to coincidentally read TASK-N, now reads UNRESOLVED-N too): fixed in tests/test_index.py (7 sites — added explicit prefix= or a _propagate_prefix call after a JSON round-trip, since prefix is excluded from the index), tests/test_models.py (1, plus added a new sentinel-degradation test), tests/test_prefix_resolver.py (rewrote the 2 tests that asserted the old coincidental TASK-7 to assert UNRESOLVED-7 instead, added a new TestEffectivePrefix unit class + a format_id sentinel test), tests/test_custom_type_paths.py (updated a stale comment describing the old INCIDENT-000001 behavior). Spec-free round-trip test (test_full_round_trip_with_no_spec_loaded) untouched — it always sets prefix= explicitly, so it never hit the sentinel.
  - Gates: uv run pyright (0 errors) / ruff check . / ruff format --check . all clean. grep -rn '\.type\.upper()' src/squads → no hits. Targeted: tests/test_prefix_resolver.py (30), test_index.py (21), test_models.py (11), test_custom_type_paths.py (17), test_service.py (79), test_spine_characterization.py (41), test_graph.py (33), test_remove.py (19), test_retype.py (34), test_slug_validation.py (26) all pass. Full re-run of all 51 files touched across TASK-328 + this tightening: 100%, 0 failed/0 error. Did not run the full suite (main loop owns it). Manual smoke: fresh squad, sq create decision → ADR-2 with prefix: ADR written and sq list rendering correctly (the exact decision->ADR case Robert's ruling calls out). Left InReview, not committed.
<!-- sq:discussion:end -->

---
id: TASK-190
sequence_id: 190
type: task
title: Wire sq list -t skill, sq skill show, and SKILL ref support
status: Done
parent: FEAT-178
author: tech-lead
subentities:
- local_id: ST1
  title: sq list -t skill and sq skill show render SKILL items
  status: Done
  story: US1
- local_id: ST2
  title: 'Basic SKILL ref support: ref add SKILL- shows on source and backref'
  status: Done
  story: US1
created_at: '2026-06-24T18:46:56Z'
updated_at: '2026-06-24T21:09:53Z'
---
<!-- sq:body -->
## Goal

Wire the user-facing surface that makes skills first-class queryable, viewable, and referenceable:
`sq list -t skill`, `sq skill <n> show`, and basic ref support so a SKILL can be linked from a
feature, task, role, or decision. This delivers US1's primary user value (referenceability).

Can proceed in parallel with TASK-188/189 once TASK-187 lands, since it operates on SKILL items
once they exist in the index (use a stamped fixture / seeded init for tests).

## What to build

- `sq list -t skill` returns indexed SKILL items (relies on the meta-type profile already chosen in
  ADR #2 — Active/Archived, no sub-entities).
- `sq skill <n> show` renders a skill item's dossier (frontmatter + body region). Follow the
  role/operator command pattern; no work lifecycle, no sub-entity surface.
- Basic ref support so `sq <type> <n> ref add SKILL-… --kind related` (and other kinds) succeeds, the
  ref appears in `sq <type> <n> show`, and backrefs invert correctly (forward edges only, invariant
  4). No SKILL-specific storage path — skills ride the same Item/ItemStore seam (ADR relationship to
  FEAT-176/177).
- Ensure `sq check` treats SKILL correctly: meta-type, no parent-is-feature rule, no subtask→US rule.

## Design constraints (ADR-181)

- Decision #1/#2: full Item of ItemType.SKILL on the meta-type profile; referenceability is the
  primary user value (US1).
- Invariant 4: forward edges only; backrefs computed by inversion, never persisted.

## Acceptance

1. `sq list -t skill` returns every seeded/migrated skill with its `SKILL-…` id. (FEAT-178 AC#1,
   US1.)
2. `sq skill <n> show` displays a skill's id, title, status, and body. (US1.)
3. `sq <type> <n> ref add SKILL-… --kind related` succeeds and the ref appears in the source item's
   `show`; backref appears on the skill. (US1.)
4. `sq check` green for SKILL items (no false parent/subtask advisories). pyright/ruff clean; service
   + CLI smoke tests added.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 190 add-subtask "<title>"`; track with `sq task 190 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | sq list -t skill and sq skill show render SKILL items | US1 |
| ST2 | Done |  | Basic SKILL ref support: ref add SKILL- shows on source and backref | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq list -t skill and sq skill show render SKILL items

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Stable SKILL-… ID per skill for cross-entity referencing
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Basic SKILL ref support: ref add SKILL- shows on source and backref

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — Stable SKILL-… ID per skill for cross-entity referencing
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T20:15:33Z] Elias Python:
  - Implementation complete. sq skill <n> show was already wired in _skill.py. Added sq skill <n> refs, sq skill <n> ref add, sq skill <n> ref rm commands to the _addr sub-group in _cli/_skill.py. Also added DEFAULT_KIND/split_ref imports.
  - Ref support: resolve_item_id_any() handles SKILL prefix generically (no special-casing needed — it resolves by sequence number and validates the type prefix). sq task/feature ref add SKILL-… stores forward edge on the source item. Backrefs are computed by SquadsDB.backrefs() inversion (invariant 4 — forward edges only). sq skill <n> refs --in shows computed backrefs.
  - Tests: 5 tests in tests/test_skill_migration.py: sq_skill_show_renders_skill, sq_skill_show_json, ref_add_skill_from_task, ref_backref_appears_on_skill, ref_round_trip_from_feature. All use invoke fixture for async-safe CLI invocation.
- [2026-06-24T20:15:39Z] Elias Python:
  - @manager TASK-189 and TASK-190 (second increment of FEAT-178) are ready for review. Both remain InProgress per instructions. Key files: src/squads/_migrations/_v0_4_to_v0_5.py (new migration runner), src/squads/_migrations/_registry.py (entry 0.4→0.5), src/squads/_models/_schema.py (SCHEMA_VERSION=0.5), src/squads/_cli/_skill.py (refs+ref add+ref rm commands), tests/test_skill_migration.py (11 new tests). Pyright clean, ruff clean, full suite green.
<!-- sq:discussion:end -->

---
id: TASK-235
sequence_id: 235
type: task
title: Widen Item type/status to str; validate at service boundary; reserved-vocab
  subset check
status: Done
parent: FEAT-208
author: tech-lead
subentities:
- local_id: ST1
  title: Widen Item type/status + SubEntity status to str; move validation to load
    boundary
  status: Done
  story: US1
- local_id: ST2
  title: Reserved-vocab subset/coverage check replaces ==enums; spec parsers + negative
    tests
  status: Done
  story: US1
created_at: '2026-06-26T09:48:48Z'
updated_at: '2026-07-06T15:21:04Z'
---
<!-- sq:body -->
## Goal

The de-typing itself (ADR-232 §1/§3/§4): widen `Item.type`/`Item.status` and `SubEntity.status`
from enums to `str`, move vocabulary validation from Pydantic construction to the service/load
boundary, and replace FEAT-207's `== enums` equality with the fail-closed reserved-vocab
subset/coverage check. This is the irreversible typing inversion — done last, once the engine no
longer branches on enum identity (TASK-234) so widening the field type is safe.

Sequence: **third / last** — depends on TASK-233 (hardened loader + reserved-vocab plumbing) and
TASK-234 (no enum-identity branches remain). Highest-risk task; the standing gate is the proof.

## What to build

- **Widen the model fields (ADR §1):** `Item.type: ItemType → str`; `Item.status: Status → str`;
  `SubEntity.status: Status → str`. Sub-entity **severity stays as-is** (`Severity` is not workflow
  vocabulary, NOT widened). `from_frontmatter` stops calling `ItemType(...)`/`Status(...)` (which
  raise on unknown); the string round-trips losslessly. This is a typing/validation change, NOT a
  data migration — every existing item file is already a valid string; no file rewrite. A
  schema-version bump still marks the capability boundary (older `sq` must refuse a squad that USES
  custom vocab), but default-vocab on-disk bytes are identical.
- **Move validation to the service boundary (ADR §1):** `ItemStore.load` / `open_service` checks each
  item's type/status against the loaded `WorkflowSpec` (`spec.is_known_type(t)` /
  `spec.is_valid_status(t, s)`), raising `SquadsError` with the offending item id on an unknown value.
  Pydantic still type-checks "is a str"; the vocabulary check is the spec's job. Cover the bad-value
  path: a malformed-frontmatter error now surfaces at load time, not construction time (ADR §7 hazard).
- **Update CLI parsers (ADR scope):** `parse_type`/`parse_status` in `_cli/_common.py` iterate
  `spec.managed_types()` / the spec's status set instead of `list(ItemType)` / `list(Status)`.
  Behavior-identical for the default vocab.
- **Reserved-vocab invariant (ADR §4) — replaces FEAT-207's `== enums` check:** `WorkflowSpec.validate()`
  MUST raise `SquadsError` if the spec OMITS any reserved type or reserved status (custom vocab is
  additive over the reserved core; it can extend, never remove). `RESERVED_TYPES = frozenset(ItemType)`
  (all 10, crucially the meta-types role/skill/operator); `RESERVED_STATUSES` = the structural floor
  pinned in the ADR-accept review: agent machine `Draft/Active/Archived`, sub-entity machines
  `Todo/InProgress/Blocked/Done/Cancelled`, finding machine `Open/Fixed/Verified/WontFix`. The enums
  are RETAINED as the source of these reserved sets + the default-TOML generator (ADR §3) — NOT
  deleted in F2.
- **Negative tests (ADR §6):** a spec missing role/skill/operator or a structural status MUST raise;
  an item with an unknown type/status surfaces a clear spec-validation error at service init with the
  item id.

## Design constraints (ADR-232)

- §1/§3/§4 exactly. Enums demoted to reserved-vocab source + TOML generator, not the runtime field
  type; may remain as readable string constants during transition. §7 trade-off (compile-time
  exhaustiveness → load-time validation) is accepted on the record.
- Scope boundary: NO project overrides (F3), NO custom types/statuses end-to-end (F4/F5), NO
  renderer change. F2 proves the foundation only.

## THE STANDING GATE (every task in F2)

The entire existing test suite + all THREE golden-locks (workflow ADR-214, role-catalog ADR-221,
playbook ADR-226 incl. its byte-identical skill-output layer) MUST pass UNCHANGED — byte-identical
behavior. No existing test may be edited to accommodate F2; if one needs editing, that is a behavioral
change to be justified, not absorbed. AC#8: no existing `.md` item file requires rewriting.

## Acceptance

1. `Item.type`/`Item.status`/`SubEntity.status` are `str`-typed; Pydantic construction no longer
   raises on unknown frontmatter values; unknown values surface as a spec-validation `SquadsError`
   (with item id) at service init, not a parse error. Existing item files load unchanged. (US1.)
2. `parse_type`/`parse_status` derive valid sets from the loaded spec, not enum iteration.
3. `WorkflowSpec.validate()` enforces the reserved-vocab subset/coverage check (fail-closed); negative
   tests for omitted reserved type/status pass; enums retained as RESERVED_* source + TOML generator.
4. The F1 golden remains green (default trivially satisfies subset). Standing gate holds: full suite +
   all three goldens green, unchanged. `uv run pyright` strict zero errors; ruff clean; AC#8 holds.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 235 add-subtask "<title>"`; track with `sq task 235 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Widen Item type/status + SubEntity status to str; move validation to load boundary | US1 |
| ST2 | Done |  | Reserved-vocab subset/coverage check replaces ==enums; spec parsers + negative tests | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Widen Item type/status + SubEntity status to str; move validation to load boundary

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a maintainer, I want Item type/status to be str-typed so unknown values don't raise at load time
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers the de-typing itself (ADR-232 §1/§3): widen `Item.type`, `Item.status`, and `SubEntity.status` from enums to `str` (sub-entity `Severity` stays typed — not workflow vocabulary), stop `from_frontmatter` calling `ItemType(...)`/`Status(...)`, and move vocabulary validation to the service/load boundary — `ItemStore.load`/`open_service` check each item's type/status against the loaded `WorkflowSpec` (`is_known_type`/`is_valid_status`), raising `SquadsError` with the offending item id. This is a typing/validation change, not a data migration: existing item files load unchanged, on-disk bytes identical. (US1)
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Reserved-vocab subset/coverage check replaces ==enums; spec parsers + negative tests

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a maintainer, I want Item type/status to be str-typed so unknown values don't raise at load time
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Covers the reserved-vocab invariant that replaces FEAT-207's `== enums` check (ADR-232 §4): `WorkflowSpec.validate()` raises `SquadsError` if the spec OMITS any reserved type (`RESERVED_TYPES = frozenset(ItemType)`, all 10 incl. the meta types) or reserved status (the structural floor — agent Draft/Active/Archived, sub-entity Todo/InProgress/Blocked/Done/Cancelled, finding Open/Fixed/Verified/WontFix). Updates `parse_type`/`parse_status` to derive valid sets from the loaded spec rather than enum iteration, and adds negative tests for an omitted reserved type/status and an unknown item value. Enums are retained as the reserved-vocab source + default-TOML generator, not deleted. (US1)
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T14:23:32Z] Elias Python:
  - TASK-235 implementation complete.
  - Changes:
  - - Item.type, Item.status, SubEntity.status widened from enum to str
  - - field_validator coerces StrEnum members to plain str on assignment (use_enum_values=False fix)
  - - ItemFilter.item_type/status widened to str|None; matches() uses == not is
  - - parse_type/parse_status return str; iterate ItemType/Status enums as reserved vocab
  - - PREFIX_BY_TYPE, FOLDER_BY_TYPE, EXTRA_FIELDS keyed by str
  - - SUBENTITY_PARENT dict values are now plain str literals
  - - Service method signatures widened: create/list_items/set_status/update all take str
  - - _apply_status, _apply_subentity_status coerce str(status) before assignment
  - - retype() coerces str(new_type) at entry
  - Adjudicated test changes (all is→== on widened fields):
  - - test_bug_workflow.py: 10 is→== on item.status (Status StrEnum, widened to str)
  - - test_collab.py, test_retype.py, test_service.py, test_workflow.py, test_models.py, test_operators.py, test_skill_seeding.py, test_meta_compat.py, test_tree.py, test_spine_characterization.py, test_terminal_accepted_published.py, test_role_resolver.py: is→== on .type/.status
  - - test_reflog_core.py: item.type.value → item.type (str, no .value)
  - Reserved-vocab negative tests added to test_workflow_spec.py:
  - - test_reserved_vocab_omit_item_type_fails_closed: drops 'epic' → SquadsError §5-6a
  - - test_reserved_vocab_omit_status_fails_closed: drops 'Done' → SquadsError §5-6b
  - pyright: 0 errors | ruff: clean | 1247 tests: exit 0 @manager
- [2026-06-26T14:54:55Z] Elias Python:
  - All four REV-238 findings addressed and verified.
  - F1 (HIGH): Load-boundary vocabulary validation implemented at both materialization paths — IndexStore.load() (via _validate_item_vocab()) and repair() (inline guard before db.add()). type=gizmo and status=Frobnicated now raise a clean SquadsError with the item ID; four characterization tests in tests/test_load_boundary_vocab.py confirm the repro.
  - F2 (MEDIUM): Reserved-status floor in WorkflowSpec._validate §5-6b narrowed from all 22 Status members to the 11 structural-floor statuses (Draft/Active/Archived, Todo/InProgress/Blocked/Done/Cancelled, Open/Fixed/Verified/WontFix). Work-item-only statuses are no longer reserved. Tests updated: test_reserved_vocab_omit_status_fails_closed still uses 'Done' (floor member); new test_non_reserved_status_omission_is_allowed verifies dropping 'Ready' is ALLOWED.
  - F3 (LOW): parse_type/parse_status now consult _DEFAULT_SPEC.items and _DEFAULT_SPEC.statuses instead of iterating ItemType/Status enums directly.
  - F4 (LOW): _coerce_str_fields and _coerce_status now guard with isinstance(v, str), raising ValueError (TRY004 noqa) rather than silently str()ing non-str values.
  - Full suite green, pyright strict 0 errors, ruff clean. @manager
- [2026-06-26T15:10:36Z] Elias Python:
  - F5 (MEDIUM) closed — same defect class as F1 on the sub-entity axis.
  - Guard extended at both materialization boundaries: _validate_item_vocab() in _index/_store.py now loops over item.subentities and raises SquadsError (with item id + sub-entity key) on an unknown status. The inline guard in repair() in _services/_maintenance.py likewise checks each sub.status before db.add().
  - Two new characterization tests in tests/test_load_boundary_vocab.py: test_load_rejects_unknown_subentity_status (load path) and test_repair_rejects_unknown_subentity_status (repair path). Both confirmed: subentities[].status=Frobnicated now raises SquadsError rather than crashing with a raw ValueError via _discussion._status_badge.
  - Full suite: exit 0, 1 skip unchanged, 2 additional passing tests vs F1-F4 run. Pyright strict 0 errors, ruff clean. @manager
<!-- sq:discussion:end -->

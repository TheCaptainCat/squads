---
id: TASK-648
sequence_id: 648
type: task
title: 'Per-type display labels: LabelSpec + label_for resolver'
status: Done
parent: FEAT-647
author: tech-lead
refs:
- ADR-646:addresses
subentities:
- local_id: ST1
  title: Add LabelSpec + ItemSpec.labels and the label_for resolver
  status: Done
  story: US1
- local_id: ST2
  title: Retarget ad-hoc type-name display derivations through label_for
  status: Done
  story: US2
created_at: '2026-07-24T11:50:40Z'
updated_at: '2026-07-24T12:47:15Z'
---
<!-- sq:body -->
Implements the per-type display-label vocabulary and resolver from ADR-646: a single authority yields a type's human-readable name in four forms, with pin-else-derive fallback so ordinary types need zero config and only acronym/irregular types pin the forms derivation gets wrong.

## Schema (US1)

- Add a frozen `LabelSpec` value object in `src/squads/_workflow/_models.py` — `model_config` frozen with `extra="forbid"` (match its sibling specs) — with four independently-optional fields: `singular: str | None = None`, `plural: str | None = None`, `singular_lower: str | None = None`, `plural_lower: str | None = None`.
- Add `ItemSpec.labels: LabelSpec | None = None`. Purely additive with a default; precedent is the sibling display-vocabulary field `SubentityKindSpec.plural`. `ItemSpec`'s existing `extra="forbid"` already rejects a misspelled sub-key.
- Confirm the `.overrides/workflow.toml` loader (`src/squads/_workflow/_loader.py`) parses the nested `[items.<type>.labels]` table into `LabelSpec` (the standard nested-model path should already cover it; add coverage if not).

## Resolver (US1)

- Add the authoritative resolver `label_for(type_str, form, spec) -> str` beside `prefix_for` in `src/squads/_models/_vocab.py`. `form` is one of `singular` / `plural` / `singular_lower` / `plural_lower`.
- It reads `spec.items[type_str].labels`; returns the pinned form when present, else the computed fallback for that form:
  - `singular` ⇐ `type.capitalize()`
  - `singular_lower` ⇐ `type.lower()`
  - `plural` ⇐ `singular + "s"`
  - `plural_lower` ⇐ `singular_lower + "s"`
- The fallback logic must live in exactly ONE place. An optional `labels_for(type_str, spec)` returning all four forms may back it, but `label_for` is the single call site consumers use.

## Retarget consumers (US2)

- Replace ad-hoc `.capitalize()`/`.title()` type-name display derivations with `label_for` calls. Confirmed instance: the Claude Code backend's per-type section titles in `src/squads/_backends/_claude_code/_backend.py`.
- Also cover any VS Code tree/list view and CLI per-type grouping header that derives a type display name ad hoc. GREP for these first — do not assert a defect you have not confirmed exists; only retarget real derivation sites.

## Constraints

- No schema bump: `SCHEMA_VERSION` stays `"0.11"`. The field is additive/optional and reconstructs identically when omitted — no migration.

## Testing

- Service/model-level tests for pin-else-derive across all four forms:
  - regular type with no `labels` → all four derived;
  - partial override → pinned forms from config, rest derived;
  - acronym type with all four pinned → stays capitalized in the `*_lower` forms;
  - misspelled `labels` sub-key rejected by `extra="forbid"`.
- Consumer-level assertion that a retargeted surface renders the resolved label.

Do not redesign — ADR-646 is the fixed design.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 648 add-subtask "<title>"`; track with `sq task 648 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add LabelSpec + ItemSpec.labels and the label_for resolver

<!-- sq:subtask:ST1:body -->
Added frozen LabelSpec (4 optional str forms, extra=forbid) + ItemSpec.labels in _workflow/_models.py; label_for/labels_for resolver (pin-else-derive) in _models/_vocab.py; confirmed the override loader parses [items.X.labels] via the standard nested-model model_validate path (no dedicated parser needed).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Retarget ad-hoc type-name display derivations through label_for

<!-- sq:subtask:ST2:body -->
Grepped for ad-hoc type-name .capitalize()/.title() derivations; only the Claude Code backend's two per-type item-skill title sites (_backend.py) were real hits — retargeted both through label_for(type, "singular", spec). No VS Code or CLI per-type grouping header derives a display name ad hoc (subentity-kind .title() sites in _cli/_common.py, _discussion.py, _retype.py are a different axis, out of ADR-646 scope).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T12:16:02Z] Elias Python:
  - ST1+ST2 done. Added LabelSpec (frozen, extra=forbid, 4 optional str forms) + ItemSpec.labels in src/squads/_workflow/_models.py.
  - Added label_for(type_str, form, spec)/labels_for(type_str, spec) resolvers beside prefix_for in src/squads/_models/_vocab.py — pin-else-derive, unlike prefix_for never raises (falls back to derivation for a missing spec/undeclared type).
  - Loader needed no change: both item-spec parsers in _workflow/_loader.py already spread **data into ItemSpec.model_validate, so nested [items.X.labels] hits pydantic's standard nested-model path; added coverage.
  - Retargeted the 2 confirmed ad-hoc sites in src/squads/_backends/_claude_code/_backend.py (item-skill section titles) through label_for(type, "singular", spec). Grepped CLI/TUI/service for other .capitalize()/.title() type-name derivations — the only other hits are subentity-kind (story/subtask/finding) axis in _cli/_common.py, _discussion.py, _services/_retype.py, out of ADR-646 scope, left untouched.
  - No golden/manifest regen needed: fallback formula is byte-identical to the old .capitalize() behaviour, and no bundled type has labels pinned.
  - New tests: tests/unit/test_item_display_label_resolution.py (resolver pin-else-derive, all 4 forms, acronym case, extra=forbid), tests/unit/test_item_labels_override_loading.py (loader nested-table parse + misspelled-subkey rejection), tests/integration/test_item_skill_title_uses_resolved_label.py (consumer-level: pinned label renders in generated skill title, both built-in and custom type, plus no-override fallback).
  - Gates green: pyright --all-extras (0 errors), ruff check + format --check clean, targeted pytest green, tests/meta green.
- [2026-07-24T12:27:21Z] Paul Reviewer:
  - REV-649 raised two low-severity findings (F1: LabelForm should be PEP-695 `type` alias; F2: empty-string-pin fallback untested). Recommended verdict Approve; back to InProgress to close the nits before commit.
<!-- sq:discussion:end -->

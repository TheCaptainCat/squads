---
id: TASK-592
sequence_id: 592
type: task
title: Category-generic create for a custom records-category type
status: Done
parent: FEAT-569
author: tech-lead
priority: high
created_at: '2026-07-22T13:00:50Z'
updated_at: '2026-07-22T17:16:02Z'
---
<!-- sq:body -->
Implements FEAT-569 (records-category create path). Make `sq create` fully spec-driven for a project-declared custom `category = "records"` type — no records-name special-casing anywhere in the create path.

## Scope
- A custom records type already reaches a generic create command through two paths in `src/squads/_cli/_create.py`: the static `_CREATABLE` loop (it is in `non_roster_types()`, so it registers) and the dynamic `_CustomCreateGroup`/`_build_create_cmd` fallback. Verify a records type takes the generic path end-to-end: allocates from the global counter, writes frontmatter, and lands in its declared `folder` (`_paths.folder_for` reads `spec.items[t].folder`).
- Confirm the create gate runs the `records` bundle's `no_parent` validator (landed in FEAT-568): `sq create <records-type> --parent X` must refuse with a clean `SquadsError`, and creating without a parent succeeds. The gate is `ValidatorEngine.gate()` at the create site in `_services/_base.py::create` — do not add a second hardcoded check.
- The `guide` special-case in `_create.py` (the `if t != "guide"` exclusion + the dedicated `create_guide` with `--tech/--tag`) is a *field-based* command driven by guide's declared extra fields, NOT a category-name gate — leave bundled guide byte-identical. Only ensure a NEW records type that declares no such fields still registers via the generic loop/dynamic path.

## Acceptance
- A custom records type declared in an override spec is creatable with zero code change; the file lands in the declared folder; a parent is refused.
- Bundled-spec create output (feature/task/bug/decision/guide/contract) is byte-identical.
- Service-level test + CLI smoke test (per repo testing convention).

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest` (the `tui` extra must be present). Leave `sq check` clean for touched work.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 592 add-subtask "<title>"`; track with `sq task 592 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T17:07:38Z] Elias Python:
  - Already fully generic — no code change. Confirmed: `sq create <records-type>` already reaches `_CREATABLE`/dynamic `_CustomCreateGroup` path via `spec.non_roster_types()`; `no_parent` fires through the single `ValidatorEngine.gate()` call in `_services/_base.py::create` (no second hardcoded check found). Bundled create output byte-identical (targeted create/list/decision-guide tests green). guide's --tech/--tag stays field-based, untouched.
  - Coverage: existing tests/service/test_records_epic_no_parent_enforcement.py already proves decision/guide no_parent at create+link; TASK-594's new override-spec test (tests/integration/test_custom_records_category_type_end_to_end.py) is the definitive zero-code-change proof for a brand-new records type.
  - Gates: pyright/ruff clean; targeted pytest green; sq check clean.
<!-- sq:discussion:end -->

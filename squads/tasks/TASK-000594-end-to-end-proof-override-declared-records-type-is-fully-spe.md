---
id: TASK-594
sequence_id: 594
type: task
title: 'End-to-end proof: override-declared records type is fully spec-driven'
status: Done
parent: FEAT-569
author: tech-lead
priority: high
created_at: '2026-07-22T13:00:52Z'
updated_at: '2026-07-22T17:16:04Z'
---
<!-- sq:body -->
Implements FEAT-569 acceptance. A single integration proof that a genuinely NEW `category = "records"` type — declared purely in a workflow override, never in bundled code — is fully spec-driven across create/retype/list and backend generation. This is the feature's headline acceptance; depends on TASK-592 and TASK-593.

## Scope
- Add a test that loads an override spec declaring a brand-new records type (own prefix, own folder, own lifecycle e.g. Draft->Active->Superseded, `category = "records"`) and asserts, with zero code change:
  - `sq create <newtype>` allocates, writes frontmatter, lands in the declared folder, and refuses a parent (`no_parent` from the records bundle).
  - `sq <newtype> retype` to/from a work type works per TASK-593.
  - `sq list` and `sq list --category records` show it; `sq tree` places it correctly.
  - Backend pointer/skill generation follows the generic path — no records-name special-casing. `_backends/_claude_code/_backend.py` already gates skill generation on `ctype_spec.category == "roster"` / the playbook; confirm a custom records type generates like any other non-roster type (or is correctly excluded per the playbook), and diff the on-disk `.claude` output stays consistent (per the "verify .claude artifacts on item-type changes" discipline).
- Grep-audit that no site hardcodes the three bundled records names (`decision`/`contract`/`guide`) where "any records-category type" is meant, in the create/retype/list path specifically (reconcile against FEAT-573's consumer-audit findings — do not duplicate its edits).

## Acceptance
- The override-spec test passes; bundled-spec behaviour is byte-identical (no override present).
- `sq check` clean.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest` (the `tui` extra must be present).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 594 add-subtask "<title>"`; track with `sq task 594 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T17:08:00Z] Elias Python:
  - New integration test tests/integration/test_custom_records_category_type_end_to_end.py: an override spec declares a brand-new 'policy' type (own prefix POL/folder policies/lifecycle Draft->Active->Superseded, category = records) with zero code change. Asserts: create allocates/writes frontmatter/lands in policies/, refuses --parent (no_parent); sq list, sq list --category records, sq tree --category records surface it; retype task<->policy succeeds unparented both ways and a parented item retyped into policy is refused; sq sync generates its sq-policy skill + .claude pointer exactly like any other non-roster custom type (diffed skill-name sets between a bundled-only and the override squad: exactly one addition, no churn).
  - Grep-audit (create/retype/list path): no hardcoded decision/contract/guide name found gating any behavior — the only 'guide' references in _cli/_create.py are the pre-existing field-based --tech/--tag command (out of scope per task text), not a category gate. Nothing to fix, nothing overlapping FEAT-573's consumer audit.
  - Gates: pyright/ruff clean; targeted pytest green (create/retype/list/category/custom-skill-generation suites + new test file); sq check clean.
<!-- sq:discussion:end -->

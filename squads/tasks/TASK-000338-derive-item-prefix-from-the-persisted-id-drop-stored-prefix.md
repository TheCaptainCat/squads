---
id: TASK-338
sequence_id: 338
type: task
title: Derive item prefix from the persisted id, drop stored prefix field
status: Done
parent: FEAT-326
author: tech-lead
description: 'Stop emitting the redundant prefix: frontmatter line; derive prefix
  from the item''s id on read'
created_at: '2026-07-08T16:08:18Z'
updated_at: '2026-07-09T07:00:20Z'
---
<!-- sq:body -->
## What this changes

TASK-328 landed the type axis by carrying a `prefix:` line in every item's
frontmatter — a redundant field, since the prefix is already recoverable from
the item's persisted `id` (`ADR-49` → `ADR`). Drop the stored field and derive
the prefix from the id instead. This supersedes the cancelled normalization
task (which had normalized the prefix line and bumped the schema version); with
the prefix derived, no line to normalize and no schema change remain. The
ADR-322 §3 mechanism description is being corrected in parallel by the
architect — this task carries the code side of that correction.

## Scope

**`_models/_item.py` — derive, don't store**

- `from_frontmatter` derives the prefix from the stored `id` (rsplit on the
  last `-`) instead of reading a `prefix:` key.
- `to_frontmatter_dict` STOPS emitting the `prefix:` key.
- `Item.id` / `effective_prefix` source the prefix from that derived value.
- Keep the `UNRESOLVED` sentinel for the genuinely-no-id / bare-`Item()`
  construction case (nothing to derive from yet).
- `_models` must stay **acyclic** — pure string parse, no `_workflow` import.

**`_index/_store.py` — drop the backfill**

- Remove the load-boundary `prefix` backfill (`_propagate_prefix`); it is no
  longer needed now that the prefix is derived on read.

**Consumers**

- Repoint any consumer that read the stored `prefix:` field at the derived
  path.

**Tests**

- Update the spec-free round-trip test + the prefix-resolver tests to assert
  NO `prefix:` line is written and that the prefix is correctly derived from
  the id.
- Ensure the round-trip still holds with no spec loaded.

## Acceptance

- No item writes a `prefix:` frontmatter line.
- A `.md` round-trips spec-free with the prefix derived from its id.
- `_models` stays acyclic.
- No `SCHEMA_VERSION` change and no migration needed.
- The no-override default behaves identically.
- `pyright` + `ruff check` + `ruff format --check` clean; full suite green.

## Non-goal

- The drop-populated-type diagnostic is out of scope (separate,
  architect-owned).

## Note

Keep rationale ID-clean where it would land in code (the repo-wide
squad-item-reference hygiene gate) — no ticket IDs in source or test names;
the pointer stays here and in the commit/PR.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 338 add-subtask "<title>"`; track with `sq task 338 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-08T16:26:55Z] Elias Python:
  - Mechanism: Item now derives prefix from the persisted id via a model_validator(mode="before") (rsplit on the last '-'), covering both read paths that hand the model a raw id — the JSON index round-trip (id is a computed field, included in the dump) and from_frontmatter (passes the frontmatter's id: line through). A stray legacy prefix: key is silently overwritten by the derived value, never trusted or errored on.
  - to_frontmatter_dict() no longer emits prefix: at all. _index/_store.py's _propagate_prefix load-boundary backfill removed entirely (no longer needed — the JSON index's own id field round-trips prefix automatically now). Removed the now-dead equivalent backfill block in _maintenance.py's repair rebuild (id is guaranteed present by the time that code runs, so from_frontmatter already derives prefix).
  - Consumers checked: _items.py, _refs.py, _retype.py, _cli/_common.py all read item.prefix (the real field, still populated correctly) — no changes needed there; none read a frontmatter prefix: key directly.
  - Tests: rewrote test_prefix_resolver.py (frontmatter-dict tests assert no prefix: key; from_frontmatter tests assert derivation from id, including a dedicated stray-key-ignored test and an id-absent UNRESOLVED-sentinel test; spec-free round-trip updated) and test_index.py (dropped the _propagate_prefix import/calls — JSON round-trip now resolves prefix on its own).
  - One-time repo cleanup per correction: swept 13 squad item files that carried a stray prefix: frontmatter line (written by builds on this branch before the revert) by loading each through Item.from_frontmatter and re-writing via update_frontmatter (the model's own to_frontmatter_dict) — not a hand-edit, not a migration. grep -rlE '^prefix:' squads/ now only matches two old ADR/REV bodies quoting the pre-fix code as historical illustration (verified their frontmatter itself has no prefix key).
  - Gates: pyright clean, ruff check clean, ruff format --check clean (whole repo). Targeted tests green: test_prefix_resolver.py, test_index.py, test_custom_type_create.py, test_service.py, test_override_commands.py, test_workflow_spec.py, test_workflow_lint.py, test_retype.py, test_custom_type_paths.py, test_custom_type_cli.py, test_load_boundary_vocab.py, test_skill_seeding.py, test_skill_migration.py, test_squad_ref_hygiene.py, test_operators.py, test_aliases.py, test_workflow_rules.py. Full suite not run (main loop owns it).
<!-- sq:discussion:end -->

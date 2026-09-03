---
id: TASK-857
sequence_id: 857
type: task
title: Refuse a nested unknown override key with its key and version
status: Done
author: tech-lead
priority: low
refs:
- REV-854:addresses
- MILE-836:targets
description: A nested unknown override key is refused by a raw pydantic error with
  no version and a link to pydantic's docs; fold extra_forbidden into the same key-and-version
  refusal the top level already produces
created_at: '2026-09-01T11:25:22Z'
updated_at: '2026-09-02T14:01:24Z'
---
<!-- sq:body -->
## Scope

An override key the spec models do not declare is refused — but the refusal is one of two
different things depending on how deep the key sits, and only the shallow one keeps the promise
the closed key space was argued on.

A **top-level** unknown key goes through `_specmerge._unknown_key_violations` and produces the
intended message: the offending key, the accepted key list, and the version.

```
error: .../.overrides/roles/manager.toml: nonsense: unknown top-level key 'nonsense'
  — use one of the accepted top-level keys in v0.14.0: ['agreements', 'can_spawn', ...]
```

An unknown key inside a **nested** section never reaches that function at all: pydantic's
`extra="forbid"` fires first and the adopter gets the raw validation error verbatim — no version,
an internal model class named in the header, an `input_value`/`input_type` dump, and a link to
pydantic's own error documentation.

```
error: this squad's workflow override could not be loaded, ...
  cause: Invalid item spec 'task': 1 validation error for ItemSpec
bogus_key
  Extra inputs are not permitted [type=extra_forbidden, input_value=1, input_type=int]
    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden
```

The nested key space **is** closed — `extra="forbid"` is what closes it — but its refusal delivers
neither half of the promise the closure was argued on, and it leaks an implementation dependency
into an adopter-facing message. This is not a new argument in this codebase: the role resolver
already carries a note that a bare pydantic error "reads as framework noise to an adopter", and
already hand-writes its blank-string checks for exactly that reason. The nested unknown-key case
is the same seam with the same reasoning, unapplied.

## The fix, and its boundary

Fold a pydantic `extra_forbidden` error raised while loading an override document into the same
refusal shape `_unknown_key_violations` produces: name the offending key, name where it sits, name
the accepted keys for that section, name the version. One shared formatter, applied at the loader
seams that surface adopter-facing override errors — the workflow loader's per-section
constructions (`Invalid item spec …` and its siblings), the roles catalog document, and the
per-slug role document.

**Bounded deliberately.** Only `extra_forbidden` is folded. Every other pydantic error shape — a
wrong type, a missing required field — keeps whatever handling it has today. Widening to "make all
pydantic errors pretty" is a different piece of work with a different bar, and taking it on here
would turn a contained message fix into an open-ended one.

The accepted-key list for a nested section is read off the model's own fields, the way the
top-level spaces already derive theirs, so it grows with the model rather than going stale beside
it. Do not restate a key list as a literal.

## Acceptance

- An unknown key inside a nested override section is refused with a message naming the key, the
  section it sits in, the accepted keys for that section, and the version — in the same shape a
  top-level unknown key already produces.
- No adopter-facing message from any override loader contains `input_value`, `input_type`,
  `extra_forbidden`, an internal model class name, or a link to pydantic's documentation. Asserted
  as a property over the loader's refusal messages, not spot-checked on one input.
- Proven on at least three documents: a nested key in the workflow override, one in the roles
  catalog document, and one in a per-slug role document.
- The top-level refusals are byte-identical to what they produce today.
- Every other validation failure shape still refuses, with its exit code unchanged — no error is
  turned into a warning or swallowed by the new formatting path.
- The accepted-key list is derived from the model, not restated as a literal.
- No item ID appears in any touched file.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean, and `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 857 add-subtask "<title>"`; track with `sq task 857 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T13:51:11Z] Elias Python:
  - Implemented; moved to InReview. @reviewer
    
    **Shape.** One shared formatter, `_specmerge.describe_spec_error(exc, model)`, routed into every override-loading seam that wraps a `model_validate` failure: 14 in the workflow loader, 2 in the roles catalog loader, 1 in the per-slug role resolver, 2 in the playbook loader. The version-qualified menu sentence is now written once (`_accepted_menu`) and shared by both depths, so the top-level and nested refusals cannot drift apart again — that sharing, not the new function, is what makes the fix hold.
    
    **Precedent matched.** The top-level-key and ref-kind refusals both name the offending name *and* list the accepted set; the unknown-validator refusal (`_workflow/_models.py::_check_validators_assignment`) names the entry alone. Matched the first two.
    
    **Menu derived, not restated.** Read off the model reached by walking the pydantic error's own `loc` — so a depth-2 key resolves the *nested* section's fields, not its parent's: `[items.task.labels] deep_bogus` refuses with `unknown key 'deep_bogus' in 'labels' — use one of the accepted keys in v0.14.0: ['plural', 'plural_lower', 'singular', 'singular_lower']`. When the route cannot be resolved against the model graph the message names the key with no menu rather than guessing one.
    
    **Bound, as scoped.** Only a failure whose *whole* cause is unknown keys is folded. A wrong type, a missing required field, and a failure mixing an unknown key with either of those keep today's handling verbatim — pinned by a test so the boundary is asserted rather than assumed.
    
    **Two corrections to the write-up.** (1) A per-slug role document cannot carry a nested unknown key: `RoleSpec` is flat, so its whole key space is the top level and was already covered. The third document proven is the **playbook** override, which the write-up did not enumerate but is the same class on the same surface. (2) The playbook loader was a live instance of this defect and was not in scope as written; it is fixed.
    
    **Tests.** `tests/integration/test_an_unknown_nested_override_key_names_key_and_version.py` — 14 tests: the key/section/menu/version assertion and the no-leak property (no `input_value`, `input_type`, `extra_forbidden`, internal class name or pydantic link) each run over five nested-key documents, plus a CLI read, a byte-identical top-level guard, and two bounded-scope guards. 11 fail before the change, 3 pass (the three asserting unchanged behaviour); 14 pass after.
    
    `tests/unit/test_item_labels_override_loading.py::test_a_misspelled_labels_sub_key_is_rejected_at_load` asserted on the pydantic phrase `Extra inputs are not permitted` — i.e. it pinned the leak. Strengthened to assert the key, its table, that table's menu and the version, and to assert the pydantic phrasing is *absent*.
    
    **Gates.** pyright 0 errors, `ruff check .` and `ruff format --check .` clean, `sq check` clean, vulture clean, no ticket IDs in any touched file. No bundled template or spec touched. Not committed.
<!-- sq:discussion:end -->

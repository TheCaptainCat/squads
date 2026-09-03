---
id: TASK-857
sequence_id: 857
type: task
title: Refuse a nested unknown override key with its key and version
status: Ready
author: tech-lead
priority: low
refs:
- REV-854:addresses
- MILE-836:targets
description: A nested unknown override key is refused by a raw pydantic error with
  no version and a link to pydantic's docs; fold extra_forbidden into the same key-and-version
  refusal the top level already produces
created_at: '2026-09-01T11:25:22Z'
updated_at: '2026-09-01T11:25:52Z'
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
<!-- sq:discussion:end -->

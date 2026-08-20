---
id: ADR-78
sequence_id: 78
type: decision
title: 'Module-privacy convention: underscore-prefixed internals, no re-exporting
  inits'
status: Accepted
author: architect
refs:
- GUIDE-79
description: Every implementation module is private with leading underscores and non-re-exporting
  inits, so 1.0 freezes no accidental public API
created_at: '2026-06-12T14:23:20Z'
updated_at: '2026-08-03T08:41:22Z'
---
<!-- sq:body -->
## Context

squads ships as a CLI, not yet as a library with a public API. The design question was how to signal
which modules are internal and prevent the codebase from accreting an accidental public surface that
1.0 would then be bound to support. A conventional flat package with re-exporting `__init__`s invites
external imports of anything importable, and quietly turns every module into part of the contract.

The call was to make the whole implementation explicitly private by convention, so there is no
ambiguity about what is internal and no accidental API to freeze.

## Decision

**Every implementation module and subpackage is private — leading-underscore names — and package
`__init__`s do not re-export across the package boundary.** Internal code imports straight from the
underscore modules (`from squads._models._item import Item`). An init carries content only where it
has a structural reason to: `squads/__init__` (`__version__`), `_cli/__init__` (the Typer `app` and
entry point), each backend package's init (a registration side-effect), and the packages whose init
*is* the module — `_interactions/` and `_workflow/`, promoted from single modules, whose inits hold
the implementation their former module held.
*Corrected 2026-08-03: the original three-item enumeration is stale. Two package promotions and a
second backend have joined it, and `_workflow/__init__` does re-export a block it calls a public API
— readable as internal because the package itself is underscore-private, which is the rule that was
load-bearing all along. Stated as a property rather than a list, so it stops going stale.* Namespace-style imports use an alias to stay readable
(`from squads import _clock as clock`). The import graph is kept **acyclic**, and forward refs work
unquoted (no `from __future__ import annotations`, targeting Python 3.14 / PEP 649); a would-be cycle
uses `if TYPE_CHECKING:` plus a string annotation rather than a runtime import.

## Consequences

What this binds today:

- **There is no public API surface to freeze.** Until squads deliberately exposes a library API, the
  underscore convention keeps everything internal, so 1.0 is not accidentally bound to support
  imports of internal modules.
- **Imports name the underscore module directly** rather than relying on `__init__` re-exports;
  adding a re-export is a deliberate act of making something public, not a default.
- **The import graph must stay acyclic** — a new edge that would form a cycle is resolved with a
  type-checking-only import and a string annotation, never a runtime import; this is enforced by the
  gate.
- **The cost is verbosity** at call sites (long underscore paths, occasional aliases), accepted as the
  price of an unambiguous internal/external boundary.

## Provenance

Recorded retroactively. This decision predates squads tracking itself and lived only in `CLAUDE.md`
(the module-privacy convention and the no-future-annotations / acyclic-graph gotcha) and
`docs/internals.md` (the private-layout note). It is documented here as a decision already **in
force**, not newly debated in-tool. Included as an optional standing call of the same rank as the
core six.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:41:22Z] Robert Architect:
  - Dropped the "Left **Proposed** for the manager to accept with the set" closer and retitled the section from "Status note" to "Provenance". Status prose in a body is forbidden here and this one had been false since the day the set was accepted. The provenance itself is kept and is worth keeping — this decision predates squads tracking itself and lived only in CLAUDE.md and docs/internals.md, which is why the body reads retroactively. Part of one sweep across the ten retroactive decisions (49, 71-78, 85), not ten tickets.
  - Rewrote the non-empty-init enumeration as a property instead of a list, because a list of three was always going to go stale and had: `_interactions/` and `_workflow/` were promoted from single modules and their inits hold what those modules held, `_overrides/` and `_specs/` carry content, and there is a second backend init. Two of them re-export, which the original sentence forbade.
  - The principle survives and is what was load-bearing all along — no public surface, every package underscore-private — so the rule is now stated as "no init re-exports across the package boundary" plus the structural reasons an init may carry content. `_workflow/__init__` calling its own re-export block a public API is readable as internal precisely because the package is private.
<!-- sq:discussion:end -->

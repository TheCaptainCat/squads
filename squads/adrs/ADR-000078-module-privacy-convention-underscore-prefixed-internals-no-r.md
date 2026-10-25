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
updated_at: '2026-10-25T21:37:09Z'
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
underscore modules (`from squads._models._item import Item`). An init carries code only where it has
a structural reason to: `squads/__init__` (`__version__`), `_cli/__init__` (the Typer `app` and entry
point), and `_workflow/__init__` (the bundled-spec accessor and the names its package exports, which
stay internal because the package itself is underscore-private). The set of inits holding code is
pinned by the package import-edge guard in `tests/meta`. Namespace-style imports use an alias to stay
readable (`from squads import _clock as clock`).

The module import graph is kept **acyclic**, and forward refs work unquoted (no
`from __future__ import annotations`, targeting Python 3.14 / PEP 649); a would-be cycle uses
`if TYPE_CHECKING:` plus an annotation rather than a runtime import. Every package-to-package import
edge is a recorded row in the same guard, so a new edge is a reviewed diff.

## Consequences

- **There is no public API surface to freeze.** Until squads deliberately exposes a library API, the
  underscore convention keeps everything internal, so 1.0 is not accidentally bound to support
  imports of internal modules.
- **Imports name the underscore module directly** rather than relying on `__init__` re-exports;
  adding a re-export is a deliberate act of making something public, not a default.
- **The import graph must stay acyclic** — a new edge that would form a cycle is resolved with a
  type-checking-only import, never a runtime import.
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
- [2026-08-03T08:41:22Z] `architect` Robert Architect:
  - Dropped the "Left **Proposed** for the manager to accept with the set" closer and retitled the section from "Status note" to "Provenance". Status prose in a body is forbidden here and this one had been false since the day the set was accepted. The provenance itself is kept and is worth keeping — this decision predates squads tracking itself and lived only in CLAUDE.md and docs/internals.md, which is why the body reads retroactively. Part of one sweep across the ten retroactive decisions (49, 71-78, 85), not ten tickets.
  - Rewrote the non-empty-init enumeration as a property instead of a list, because a list of three was always going to go stale and had: `_interactions/` and `_workflow/` were promoted from single modules and their inits hold what those modules held, `_overrides/` and `_specs/` carry content, and there is a second backend init. Two of them re-export, which the original sentence forbade.
  - The principle survives and is what was load-bearing all along — no public surface, every package underscore-private — so the rule is now stated as "no init re-exports across the package boundary" plus the structural reasons an init may carry content. `_workflow/__init__` calling its own re-export block a public API is readable as internal precisely because the package is private.
- [2026-10-25T21:37:09Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decision unchanged. Only `squads`, `_cli` and `_workflow` inits hold code, as pinned by `INITS_WITH_CODE` in the tests/meta import-edge guard. Backend inits have no registration side effect and `_interactions/__init__` is empty. The edge table is cited as the enforcement point.
<!-- sq:discussion:end -->

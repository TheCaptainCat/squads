---
id: ADR-000078
sequence_id: 78
type: decision
title: 'Module-privacy convention: underscore-prefixed internals, no re-exporting
  inits'
status: Accepted
author: architect
refs:
- GUIDE-000079
description: Every implementation module is private with leading underscores and non-re-exporting
  inits, so 1.0 freezes no accidental public API
created_at: '2026-06-12T14:23:20Z'
updated_at: '2026-06-12T14:29:32Z'
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
`__init__`s do not re-export.** Internal code imports straight from the underscore modules
(`from squads._models._item import Item`). The only non-empty inits are the top-level
`squads/__init__` (`__version__`), `_cli/__init__` (the Typer `app` and entry point), and the Claude
Code backend init (a registration side-effect). Namespace-style imports use an alias to stay readable
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

## Status note

Recorded retroactively. This decision predates squads tracking itself and lived only in `CLAUDE.md`
(the module-privacy convention and the no-future-annotations / acyclic-graph gotcha) and
`docs/internals.md` (the private-layout note). It is documented here as a decision already **in
force**, not newly debated in-tool. Included as an optional standing call of the same rank as the
core six. Left **Proposed** for the manager to accept with the set.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

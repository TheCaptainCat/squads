---
id: ADR-78
sequence_id: 78
type: decision
title: 'Module-privacy convention: underscore-prefixed internals, re-exports only
  from private inits'
status: Accepted
author: architect
refs:
- GUIDE-79
description: Every implementation module is underscore-private; only private package
  inits re-export (ADR-1287), so 1.0 freezes no accidental public API
created_at: '2026-06-12T14:23:20Z'
updated_at: '2026-11-04T11:06:44Z'
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

**Every implementation module and subpackage is private — leading-underscore names. The top-level
`squads/__init__` and any public package do not re-export; a private package re-exports, from its
init, the names other packages import (ADR-1287).** How a private package's init re-exports, what an importer writes and
the guard that holds both are ADR-1287's. Namespace-style imports of a top-level module use an alias
to stay readable (`from squads import _clock as clock`).

The module import graph is kept **acyclic**, and forward refs work unquoted (no
`from __future__ import annotations`, targeting Python 3.14 / PEP 649); a would-be cycle uses
`if TYPE_CHECKING:` plus an annotation rather than a runtime import. Every package-to-package import
edge is a recorded row in the package import-edge guard in `tests/meta`, so a new edge is a reviewed diff.

## Consequences

- **There is no public API surface to freeze.** Until squads deliberately exposes a library API, the
  underscore convention keeps everything internal, so 1.0 is not accidentally bound to support
  imports of internal modules.
- **A re-export is not a public surface.** A private package's init re-exports for its importers'
  convenience; the package stays underscore-private, so the name stays internal.
- **The import graph must stay acyclic** — a new edge that would form a cycle is resolved with a
  type-checking-only import, never a runtime import.
- **The cost is underscore paths** at call sites (`squads._models`, occasional aliases), accepted as
  the price of an unambiguous internal/external boundary.

## Provenance

Recorded retroactively. This decision predates squads tracking itself and lived only in `CLAUDE.md`
(the module-privacy convention and the no-future-annotations / acyclic-graph gotcha) and
`docs/internals.md` (the private-layout note). It is documented here as a decision already **in
force**, not newly debated in-tool. Included as an optional standing call of the same rank as the
core six.

## Amendments

- 2026-11-04: narrowed per op-pierre's ruling on this decision. The no-re-export clause binds only
  the top-level `squads/__init__` and public packages; private packages re-export per ADR-1287
  (related). Underscore privacy, the acyclic graph and the package-edge table stand as stated here.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:41:22Z] `architect` Robert Architect:
  - Dropped the "Left **Proposed** for the manager to accept with the set" closer and retitled the section from "Status note" to "Provenance". Status prose in a body is forbidden here and this one had been false since the day the set was accepted. The provenance itself is kept and is worth keeping — this decision predates squads tracking itself and lived only in CLAUDE.md and docs/internals.md, which is why the body reads retroactively. Part of one sweep across the ten retroactive decisions (49, 71-78, 85), not ten tickets.
  - Rewrote the non-empty-init enumeration as a property instead of a list, because a list of three was always going to go stale and had: `_interactions/` and `_workflow/` were promoted from single modules and their inits hold what those modules held, `_overrides/` and `_specs/` carry content, and there is a second backend init. Two of them re-export, which the original sentence forbade.
  - The principle survives and is what was load-bearing all along — no public surface, every package underscore-private — so the rule is now stated as "no init re-exports across the package boundary" plus the structural reasons an init may carry content. `_workflow/__init__` calling its own re-export block a public API is readable as internal precisely because the package is private.
- [2026-10-25T21:37:09Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decision unchanged. Only `squads`, `_cli` and `_workflow` inits hold code, as pinned by `INITS_WITH_CODE` in the tests/meta import-edge guard. Backend inits have no registration side effect and `_interactions/__init__` is empty. The edge table is cited as the enforcement point.
- [2026-11-04T10:45:59Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-04): the no-re-export rule applies to the top-level squads/__init__ and to public packages only. Every private subpackage re-exports, from its __init__, the names other subpackages use, so an importer writes one import line per package instead of one per module. Sweep the whole codebase now, with the docs corrected (CLAUDE.md, CONTRIBUTING, this ADR set).
- [2026-11-04T10:58:43Z] `architect` Robert Architect:
  - ADR-1287 replaces the no-re-export clause per the 2026-11-04 ruling: every private package (nested ones included) re-exports exactly the names other packages import, as `from squads._pkg._mod import Name as Name`; inits hold only re-exports; the guard drops INITS_WITH_CODE for init-shape, no-reach-in and exact-surface rules. Underscore privacy, the acyclic graph and the edge table stand as stated here.
  - Open for op-pierre: the board rule on clause-level overlap asks for an amendment at both ends with a related link, not a supersedes edge; ADR-1287 carries supersedes as briefed, so this ADR stays Accepted and its no-re-export sentence is narrowed in place once ADR-1287 is accepted.
- [2026-11-04T11:06:44Z] `architect` Robert Architect:
  - 2026-11-04 amendment per op-pierre's ruling here and ADR-1287 (related, not superseded): narrowed the no-re-export clause in place to the top-level squads/__init__ and public packages; private packages re-export per ADR-1287. Decision paragraph, two Consequences bullets, title and summary changed; the stale list of inits holding code dropped (ADR-1287 moves that code out). Privacy, acyclic graph and edge table unchanged.
<!-- sq:discussion:end -->

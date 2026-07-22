---
id: ADR-129
sequence_id: 129
type: decision
title: 'Python >= 3.14 floor: PEP 649 lazy annotations vs installable audience'
status: Accepted
author: architect
refs:
- FEAT-13
- FEAT-17
created_at: '2026-06-15T12:10:13Z'
updated_at: '2026-07-22T11:53:23Z'
---
<!-- sq:body -->
## Context

squads deliberately omits `from __future__ import annotations`. The codebase relies on
[PEP 649](https://peps.python.org/pep-0649/) **lazy (deferred) evaluation of annotations**, which
became the default annotation behaviour in CPython 3.14. Two properties fall out of this:

- **Unquoted forward references work everywhere.** Annotations are not evaluated at definition
  time, so a name used in an annotation before it is defined needs no string quoting and no
  `if TYPE_CHECKING:` dance.
- **The import graph stays acyclic without ceremony.** Because annotations don't force a runtime
  import of the annotated type, we avoid the usual pattern of pulling a module in only to satisfy a
  type hint — a frequent source of import cycles. Keeping the graph acyclic is a standing project
  invariant (verified), and lazy annotations are what let us hold it cheaply.

This is a documented convention in `CLAUDE.md`:

> No `from __future__ import annotations` — we target Python 3.14 (PEP 649 lazy annotations), so
> forward refs work unquoted.

The toolchain is already pinned to match: `pyright` runs with `pythonVersion = "3.14"` in strict
mode, and `ruff` uses `target-version = "py314"`. The package metadata declares
`requires-python = ">=3.14"` and carries the `Programming Language :: Python :: 3.14` trove
classifier. The floor therefore exists in practice — it has simply never been written down as a
decision.

## Decision

**squads requires Python ≥ 3.14.** We adopt 3.14 as the supported floor and rely on PEP 649 lazy
annotations as a first-class part of the codebase's style, rather than reintroducing
`from __future__ import annotations` or quoted/`TYPE_CHECKING` annotations to support older
interpreters.

The settings that encode this are already in place and are ratified by this ADR (not modified by
it):

- `pyproject.toml` → `[project] requires-python = ">=3.14"`
- `pyproject.toml` → `[tool.ruff] target-version = "py314"`
- `pyproject.toml` → `[tool.pyright] pythonVersion = "3.14"`
- `pyproject.toml` → classifier `Programming Language :: Python :: 3.14`
- `CLAUDE.md` → the "no `from __future__ import annotations`" convention

## Trade-off considered

**For the 3.14 floor (PEP 649 lazy annotations).**
The annotation model gives us clean, readable code: unquoted forward refs, no `TYPE_CHECKING`
guards inserted solely to break import cycles, and one consistent style with no `__future__`
preamble on every module. It keeps the import graph acyclic as a natural consequence rather than
something we police by hand. Walking the floor back would mean reintroducing `__future__` imports
and/or quoting annotations across the codebase and re-policing cycles manually — a real, ongoing
cost paid on every module for the life of the project.

**Against the 3.14 floor (installable audience).**
Python 3.14 is very recent. Requiring it shrinks the set of environments that can install squads
today: distributions, CI images, and developer machines frequently lag the latest CPython by one
or more releases, so some users will need to upgrade their interpreter before they can run `sq` at
all. This is the genuine cost of the decision.

**Why the trade-off resolves in favour of ≥ 3.14.**
squads is a developer-facing CLI for coordinating AI agents on a codebase, not a library that other
packages import. Its audience is developer machines and CI, where installing a recent Python (e.g.
via `uv`, which can fetch the interpreter itself) is routine and cheap. That context mitigates the
audience cost without eliminating it — and against an ongoing, codebase-wide tax on the style, the
one-time "install 3.14" cost on the consumer side is the better trade.

## Consequences

- **Who this excludes.** Anyone whose available interpreter is older than 3.14 cannot install or
  run squads until they upgrade. There is no compatibility shim and we are not maintaining one;
  that is the explicit, accepted cost.
- **The codebase stays free of annotation ceremony.** No `from __future__ import annotations`, no
  routinely-quoted forward refs, no `TYPE_CHECKING`-only imports added just to dodge cycles. New
  code should follow the same convention.
- **The toolchain is the enforcement point.** `requires-python`, ruff's `target-version`, and
  pyright's `pythonVersion` already gate this; no further change is required by this ADR.
- **This is revisitable.** The floor is a deliberate trade, not a permanent law. If the
  audience cost outweighs the style benefit later (e.g. 3.14 adoption stalls and demand for older
  support is real), this ADR can be **superseded** by a new one that lowers the floor and pays the
  reintroduction cost. Per project convention, supersede rather than edit an accepted ADR.

## Links

This ADR is the recorded "Python floor" decision called for by **FEAT-17** (1.0 hardening).
Its acceptance bar additionally requires it to be **linked from the stability contract
(FEAT-13)** — that linkage is a FEAT-13 deferral obligation tracked by the manager/tech lead,
not filed from this ADR.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T12:30:16Z] Paul Reviewer:
  - REV-130: APPROVED. ADR-129 is doc-only — it edits no pyproject.toml and no code (confirmed: only the ADR .md is new). Sound decision: requires Python >=3.14, ratifying the already-present settings (requires-python, ruff target-version, pyright pythonVersion, the 3.14 classifier) and the CLAUDE.md 'no from __future__ import annotations' convention. The trade-off is recorded honestly — PEP 649 lazy annotations (unquoted forward refs, acyclic graph, no ceremony) vs. a smaller installable audience (3.14 is recent), resolved toward >=3.14 because squads is a developer-facing CLI not a library, and explicitly revisitable via supersession. FEAT-13 stability-contract linkage correctly flagged as a manager/tech-lead obligation rather than overstepped. @tech-lead
<!-- sq:discussion:end -->

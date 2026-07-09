---
id: TASK-333
sequence_id: 333
type: task
title: 'Code hygiene sweep: unused code + gratuitous import re-aliases'
status: Draft
prefix: TASK
author: tech-lead
priority: low
labels:
- hygiene
description: Delete dead code (ERA commented-out blocks, unused effective_prefix param)
  and strip pointless public->private import re-aliases; one sweep on the stable post-enum-removal
  tree
created_at: '2026-07-08T12:25:09Z'
updated_at: '2026-07-08T13:42:24Z'
---
<!-- sq:body -->
One code-hygiene sweep over `src/squads/` (and, for dead code, `tests/`),
run LAST on a stable tree. Two independent concerns folded into a single
dispatch because they share the same file surface (mostly `_cli/`,
`_services/`), the same post-enum-removal timing, and one verification cycle
(pyright / ruff / format / full suite / CLI-wiring): (A) remove unused code
detected by ruff + pyright, and (B) strip gratuitous public->private import
re-aliases. Toolchain stays minimal — **ruff + pyright only, no new deps**
(explicitly NOT vulture; it also cannot parse this project's Python 3.14
PEP 758 parenthesis-less `except`, which stays as-is).

---

## Part A — Unused-code cleanup (ruff + pyright only)

### A1. Dead commented-out code — enable `ERA`, delete the blocks

- Turn on ruff's `ERA` rule family. A read-only scan finds **16 `ERA001`
  commented-out-code blocks**: 2 in `src/` — `_services/_maintenance.py:695`
  and `_workflow/_models.py:603` — and 14 in `tests/` (across
  `test_backend_conformance.py`, `test_custom_type_skill.py`, `test_adoption.py`,
  `test_operators.py`, `test_priority_views.py`, `test_service.py`; line numbers
  will drift — re-run `ruff check --select ERA001 src tests` to get the live
  list). Delete each commented-out code block (NOT genuine explanatory prose
  comments — `ERA001` only flags code-shaped comments; sanity-check each hit).
- If any single hit is a deliberately-parked snippet that must stay, keep it
  with a one-line `# noqa: ERA001` + a reason, rather than silencing the rule
  globally. Prefer deletion.

### A2. Confirm the already-clean detectors stay clean

- `F841` (unused locals): scan currently reports **0** — confirm still 0.
- `F401` (unused imports): already gated — confirm clean.
- pyright strict `reportUnusedImport` / `reportUnusedVariable` /
  `reportUnusedClass` / `reportUnusedFunction`: ensure they are enabled in
  strict mode and report clean.

### A3. Genuine unused arguments — fix BY HAND, do NOT blanket-enable `ARG`

The `effective_prefix` helper is the trigger and the primary target:

- `_models/_item.py::effective_prefix(prefix: str, item_type: str) -> str`
  returns `prefix or UNRESOLVED_PREFIX` and never reads `item_type`. **Drop the
  `item_type` parameter**, and delete the docstring paragraph that rationalises
  keeping it ("`item_type` is accepted ... so the signature stays
  self-documenting ... a future refinement ... has a natural home") — that
  rationale is explicitly overridden here.
- Update the **6 call sites** to drop the second argument:
  `_models/_index.py:83`, `_models/_item.py:208` (`Item.id`),
  `_services/_refs.py:93,298,351`, `_services/_items.py:306`,
  `_cli/_common.py:604`. Also fix the `from ... import effective_prefix` lines
  if the import shape changes (it should not). Re-grep `effective_prefix` after
  to confirm zero two-arg call sites remain.

**Do NOT blanket-enable ruff's `ARG` family and mass-`noqa` it.** A scan reports
~432 `ARG001/002` hits, but they are **mostly intentional framework params** —
Typer command callbacks, pydantic validators, ABC / override signatures, and
pytest fixtures all legitimately carry parameters they don't read. The default
disposition is: **leave `ARG` OFF** and hand-fix only the genuinely-dead args
(starting with, and quite possibly limited to, `effective_prefix`). Only if,
while doing A3, you find a *material* cluster of genuinely-dead args that ruff
would catch cheaply, may you enable `ARG` — and then you MUST neutralise the
intentional-framework hits with `_`-prefixed names or targeted per-line
`# noqa: ARG00x` (never a blanket ignore), and **document in a task comment**
which route you took and why. Erring toward "leave ARG off, hand-fix" is
correct.

### OUT OF SCOPE (honest gap — do not assume it was swept)

- **Dead module-level functions and classes** (defined, never referenced
  anywhere) are NOT covered. ruff and pyright do not detect unused
  module-level defs across a package, and we are deliberately not adding a tool
  (no vulture). This sweep removes commented-out code + dead locals/imports +
  genuinely-unused *arguments* only. Do not claim dead top-level defs were
  cleaned — they were not looked for.

---

## Part B — Gratuitous public->private import re-aliases

Strip the gratuitous public->private import re-aliases that have accumulated
across `src/squads/` (mostly in `_cli/`): imports of an otherwise-fine name
re-aliased with a leading underscore for no reason. Examples flagged by
op-pierre:

- `_cli/__init__.py`: `from squads._workflow import bundled_spec as _bundled_spec`
- `from squads._paths import resolve as _resolve`
- `import json as _json`
- `import sys as _sys`

There are ~17+ such sites. Some are FEAT-326-era refactoring artefacts, others
predate it. Use the plain imported name at the call sites instead
(`bundled_spec`, `resolve`, `json`, `sys`, ...).

- Remove `import X as _X` / `from m import name as _name` re-aliases whose only
  effect is to underscore-prefix a perfectly usable public name, and update
  every call site to the plain name.
- The sanctioned alias convention in this codebase is the OPPOSITE direction
  (private module -> readable name, e.g. `from squads import _clock as clock`,
  `from squads._models._extras import ExtraKey as X`). LEAVE those untouched —
  they exist to make private call sites readable, which is the point.

### CRITICAL — preserve the load-bearing `X as _X` forms

Do NOT blindly sweep every `as _`. Two forms are load-bearing and must be KEPT:

1. PEP 484 explicit-re-export / side-effect registration idiom, e.g.
   `from squads._cli import _main as _main  # noqa` — this registers
   sub-commands with the Typer `app`. Removing it can silently break CLI wiring
   (commands vanish from `sq --help`).
2. Third-party private-module aliases, e.g. `import typer._click as _click` —
   the underscore is part of the upstream module path, not our re-aliasing.

The target is ONLY the gratuitous private re-aliasing of names that would be
perfectly fine unaliased. Every load-bearing `X as _X` that is intentionally
kept must carry a one-line comment explaining WHY it stays (re-export /
side-effect registration, or upstream private path), so a future reader doesn't
"clean it up" and break the app.

---

## Verification (whole sweep)

- `sq --help` and `sq create --help` still list/wire up every command group and
  sub-command (proves no Typer registration was broken by Part B, and no
  framework param removed in Part A broke a callback).
- `effective_prefix` has one parameter; zero two-arg call sites remain.
- `ruff check --select ERA001 src tests` reports zero (or only justified
  `# noqa` sites); `F841` / `F401` clean; pyright `reportUnused*` clean.
- `uv run pyright` clean, `uv run ruff check .` clean, `uv run ruff format
  --check .` clean.
- Full suite green (the main loop runs the full suite as the authoritative
  gate; edit + fast gates in the dev subagent, full suite in the loop).

## Acceptance

- No commented-out code block flagged by `ERA001` remains (bar justified,
  commented `# noqa` exceptions); `F841`/`F401` and pyright `reportUnused*`
  clean.
- `effective_prefix` no longer takes `item_type`; its docstring no longer
  argues for keeping the param; all call sites updated.
- No blanket `ARG` enablement with mass-`noqa`; the chosen route (ARG off +
  hand-fix, or ARG on + targeted neutralisation) is recorded in a task comment.
- No gratuitous public->private import re-alias remains in `src/squads/`; every
  intentionally-kept `X as _X` carries a why-it-stays comment.
- All gates green (pyright / ruff / format / full suite); `sq --help` +
  `sq create --help` unchanged in the commands they expose.

## Sequencing (soft ordering — not a hard block)

Dispatch this AFTER FEAT-326's enum-removal tasks land, specifically TASK-328
(delete ItemType enum) and TASK-330 (delete Status enum). They are actively
churning the same import + code surface (especially `_cli/` and `_services/`),
and TASK-328/330 are *themselves* removing code — running hygiene concurrently
would collide and cause rework. This sweep must run LAST on a STABLE surface.
Soft ordering, deliberately not modelled as a blocking ref. Target release 0.8.

Purely-technical hygiene task: no feature parent, no fixes/addresses ref.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 333 add-subtask "<title>"`; track with `sq task 333 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-08T13:42:24Z] Olivia Lead:
  - Folded the ruff+pyright unused-code cleanup into this task (was 'strip import re-aliases') rather than opening a second ticket: same hygiene category, same post-328/330 stable-tree timing, same file surface (_cli/, _services/), and one shared verification cycle. Retitled to a 'code hygiene sweep' with two parts — (A) unused code, (B) import re-aliases.
  - Trigger for Part A was the unused item_type param on effective_prefix (returns prefix or UNRESOLVED_PREFIX, never reads item_type; 6 call sites). Its docstring currently argues to KEEP the param 'for self-documentation / a future home' — that rationale is explicitly overridden; drop the param and the paragraph.
  - Toolchain deliberately minimal: ruff + pyright only, no vulture (extra dep + can't parse our PEP 758 except). Consequence noted in the body as an OUT-OF-SCOPE gap: dead module-level functions/classes are NOT swept — nobody should assume they were.
  - ARG is intentionally left OFF by default: ~432 ARG001/002 hits are mostly legit framework params (Typer callbacks, pydantic validators, ABC overrides, pytest fixtures). Hand-fix the genuinely-dead ones; only enable ARG with targeted noqa if a real cluster justifies it, and record which route in a comment.
<!-- sq:discussion:end -->

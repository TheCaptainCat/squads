---
id: TASK-910
sequence_id: 910
type: task
title: 'View tag: read-time expansion at the shared body-read boundary'
status: Done
parent: FEAT-905
author: tech-lead
assignee: python-dev
priority: urgent
refs:
- TASK-909:depends-on
- ADR-880:implements
description: A body tag expands at one site below the CLI; view output is never re-scanned
  and expanded bytes never reach disk
subentities:
- local_id: ST1
  title: Expand at the single shared body-read boundary
  status: Done
  story: US4
- local_id: ST2
  title: Render through the existing view path, additively
  status: Done
  story: US4
- local_id: ST3
  title: Expansion is read-only; expanded bytes never reach disk
  status: Done
  story: US4
- local_id: ST4
  title: Unresolvable name stays literal; a render failure is loud
  status: Done
  story: US4
- local_id: ST5
  title: View output is never re-scanned for tags
  status: Done
  story: US5
- local_id: ST6
  title: Gates and test falsification
  status: Done
  story: US4
created_at: '2026-09-03T10:06:15Z'
updated_at: '2026-09-03T14:37:49Z'
---
<!-- sq:body -->
## Scope

Read-time expansion of a `sq:view:<name>` tag, at **one** site.

`Service.read_body` in `_services/_items.py` is already the single body-read boundary: `sq show`,
`show --raw`, the `--json` body field, the TUI reader, the operator pane and the skill read all
resolve a body through it, and nothing else reads the `sq:body` region for display. Expansion goes
there, once. No read surface grows its own expander, and none is allowed to.

**Additive only.** Expansion renders through the view render path that exists today; the
projection middle layer stays in place and keeps working. FEAT-903 widens the source kinds and
FEAT-904 deletes the projection — the expansion call site must survive both without moving, so
depend on the render entry point, not on the projection's internals.

Placement of a tag is the sibling task's surface; this task consumes it to build fixtures and adds
no second way to get a tag into a body.

## Acceptance

**US4 — one shared boundary.**
- Expansion happens at the one shared body-read boundary below the CLI. `--raw`, `show` and the
  TUI inherit it from that single place; it is grep-provable that no surface reimplements it.
- A body carrying the tag reads back with the view's rendered output **in the tag's position** —
  position preserved, prose before and after preserved.
- Several tags in one body each expand in place. A body carrying no tag reads back byte-identical
  to today.
- **Expansion is read-only and must never reach a write path.** The body-write mutate path reads
  the region directly and must keep doing so. Cover the round trip explicitly: read an item whose
  body carries a tag, then append to that body, and assert the stored file still carries the
  literal tag and no rendered output anywhere. This is the invariant that keeps the stored-region
  failure unreachable — expanded bytes must never reach disk.
- **A name that does not resolve does not break the read.** A tag naming a view the active spec
  does not declare, or whose template is missing, stays literal and the read succeeds. Reads have
  to work on a broken corpus, and `sq check` is the surface that reports a dangling name. Recorded
  here as a decision so it is not re-litigated in review.
- **A render failure inside a declared view is loud, never silent.** A template raising under
  `StrictUndefined` is an engine or template defect, not corpus state: it propagates as a
  `SquadsError` so the CLI gives a clean message and exit 1. It must not degrade to an empty
  expansion or a swallowed exception.

**US5 — no recursion, by mechanism.**
- View output is never itself scanned for tags. A well-formed tag appearing inside a view's
  rendered text stays literal text in the read.
- There is no depth limit, no cycle detection and no visited set. Their presence would be evidence
  of a second expansion site. Expansion scans the region's content once and does not re-enter
  itself.
- Test it with a view template whose own output contains a well-formed tag, and assert that output
  is literal.

**Transient consequence, accepted — do not "fix" it.** The type-attached view print on `show`
still exists in this feature (FEAT-904 removes the attachment). A hand-placed tag on a type that
also attaches that view will therefore render it twice. That is expected while the two paths run
side by side: do not touch the attachment path to suppress it, and do not write a test asserting a
single render — such a test would fail again the moment FEAT-904 lands.
## Engineering constraints (acceptance criteria — the dev is held to these)

- Layering is `_cli` -> `_services` -> (index store, backends, rendering); `_models` has no
  internal deps. Every implementation module is private (leading underscore) and package
  `__init__` files do not re-export.
- Marker-safe edits only, through `_sections.py`. Never rewrite an agent-authored body.
- **The tag is unpaired by design.** `_models/_markers.py` must not gain a `close_marker`
  counterpart for it, and no verb may write content adjacent to one. This is ADR-880's binding
  invariant, not a detail: materialisation needs a span to write into, and there is none, so the
  stale-content failure stays unreachable by construction rather than by discipline.
- Frontmatter is the source of truth and the index is rebuildable. Within a transaction every
  markdown write happens before it returns; the index commit is last.
- User-facing errors subclass `SquadsError`, so the CLI's error decorator turns them into a clean
  message and exit 1. Not bare exceptions.
- Time is injectable: `clock.now()` / `clock.iso()`, never `datetime.now()`.
- Escape dynamic console output with `_cli._common.e()` — Rich treats `[...]` as markup.
- No `from __future__ import annotations` (Python 3.14, PEP 649). Keep the import graph acyclic;
  if a new edge would cycle, use `if TYPE_CHECKING:` plus a string annotation, not a runtime import.
- Type aliases use PEP-695 `type X = ...`, never a bare assignment.
- No sq or ticket IDs anywhere in source, and especially not in test file names — name tests by
  behaviour.
- A new module-level dict or list trips `tests/meta`'s mutable-state guard. Allowlist it as a CODE
  constant rather than restructuring the code, and run `tests/meta` whenever a module constant is
  added.

## Test obligations

- A service-level test **and** a CLI smoke test per behaviour, asserting the generated files:
  valid YAML frontmatter, intact markers, body preserved verbatim where it should be.
- Table-driven position x shape coverage, not one test per implemented branch. The failure mode
  here is a test that passes because it only exercises the shape its author had in mind: cover the
  tag at the region's start, middle and end, several tags in one body, a tag adjacent to other
  region markers, an empty body, a body with no tag at all, and a non-view unpaired tag as a
  control that must keep behaving as it does today.
- **Falsify every new test before handback**: break the behaviour, watch the test go red, restore
  it, watch it go green. Report both halves in the handback comment.
- Gate clean: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .`, and `uv run --all-extras pytest`. The
  `--all-extras` is required on each — a bare `uv run` prunes the optional `tui` extra and pyright
  then reports hundreds of false unresolved-import errors.
- `uv run sq check` clean for the work touched.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 910 add-subtask "<title>"`; track with `sq task 910 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Expand at the single shared body-read boundary

<!-- sq:subtask:ST1:body -->
Expansion lands in the one body-read boundary in `_services/_items.py` that `show`, `--raw`, the `--json` body field, the TUI reader, the operator pane and the skill read all resolve through. Rendered output replaces the tag in place, position preserved, prose before and after preserved; several tags in one body each expand where they sit; a body with no tag reads back byte-identical. No read surface reimplements expansion, and that is grep-provable.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Render through the existing view path, additively

<!-- sq:subtask:ST2:body -->
The tag renders through the view render entry point that exists today — the projection middle layer stays in place and keeps working, since this feature deletes nothing. Depend on the render entry point rather than the projection internals, so the call site survives the later source widening and the projection deletion without moving.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Expansion is read-only; expanded bytes never reach disk

<!-- sq:subtask:ST3:body -->
The body-write mutate path reads its region directly and keeps doing so; expansion is unreachable from any write path. Cover the round trip: read an item whose body carries a tag, then append to that body, and assert the stored file still carries the literal tag with no rendered output anywhere. This is the invariant that keeps the stored-region failure unreachable.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Unresolvable name stays literal; a render failure is loud

<!-- sq:subtask:ST4:body -->
A tag naming a view the active spec does not declare, or whose template is missing, stays literal and the read succeeds — reads must work on a broken corpus, and the check is the surface that reports a dangling name. A declared view whose template raises under StrictUndefined is an engine or template defect, so it propagates as a `SquadsError` for a clean message and exit 1: never a swallowed exception, never a silently empty expansion.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — View output is never re-scanned for tags

<!-- sq:subtask:ST5:body -->
A well-formed tag appearing inside a view rendered output stays literal text in the read. No depth limit, no cycle detection, no visited set — their presence would be evidence of a second expansion site. Expansion scans a region content once and does not re-enter itself. Test it with a view template whose own output carries a well-formed tag.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Gates and test falsification

<!-- sq:subtask:ST6:body -->
Service-level and CLI smoke tests per behaviour, asserting generated files: valid YAML frontmatter, intact markers, body preserved. Table-driven over tag position and body shape. Do not write a test asserting a single render on a type that still attaches the same view — the double render is expected while both paths run side by side. Then falsify each new test and report both halves. Full gate with `--all-extras`, plus `sq check` clean.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T10:59:21Z] Elias Python:
  - ST1-ST6 done. Expansion lives at ItemsMixin.read_body (_services/_items.py) — the one boundary; grep-provable, pinned by a structural test. Mechanism: views.expand_view_tags(body, item, db, spec) in _views.py, scanning with a new _sections.iter_marker_spans() (positions computed once against the original text, never re-matched after substitution — that's the no-recursion guarantee, no depth counter needed).
  - ST2: renders through the existing views.resolve_records/project/render_view — untouched, additive, survives the coming source-widening/projection-deletion without moving.
  - ST3: read-only by construction — set_body's mutate closure still reads sq:body via sections.get_section directly, never through read_body/expand_view_tags. Central round-trip test: insert a tag, read (expanded), append, assert the stored file still carries the literal tag byte-for-byte and the rendered output is nowhere on disk.
  - ST4: dangling name (undeclared, or declared+missing template) gated on views.view_target_exists (TASK-909's helper) -> stays literal, read succeeds. A declared view whose template raises under StrictUndefined is caught (jinja2.TemplateError) and re-raised as SquadsError naming the view+item -- clean message, exit 1, never swallowed.
  - ST5: single pass over the original text only; verified with a self-quoting view (its own tag inside its own output) and a view quoting a different tag -- both stay fully literal, no depth counter/visited set added.
  - Bug I hit and fixed in my own draft: find_markers/iter_marker_spans return tags WITH the sq: prefix ("sq:view:x", matching existing _marker_issues convention) -- view_tag_name wants the bare form. First cut silently expanded nothing; caught it by manually driving sq show --raw before writing tests.
  - Fixed 2 tests in tests/cli/test_view_tag_placement_cli.py (TASK-909's own suite) that asserted the literal tag survives in 'show --raw' output -- that's exactly what this task changes. Repointed them at the stored .md file (the real placement fact) instead of the read surface; TASK-909's own contract is unweakened.
  - Tests: unit (iter_marker_spans, 5), service (test_view_tag_expansion_at_read_time.py, 19 -- table-driven position x shape: start/middle/end/several/repeated-same-name/adjacent-to-discussion/empty/no-tag/non-view-control, both failure modes, no-recursion x2, round-trip x2, structural single-caller), CLI (6: show/--raw/--json inherit, no-tag unchanged, dangling stays literal+exit0, broken template exit1), TUI (1, reader panel). 31 new + 2 fixed = 33 touched.
  - Falsified all 5 mechanism claims by direct mutation+revert (not per-test): (1) no-op expand_view_tags -> 16/27 tests correctly redden (rest are legitimately insensitive: empty/no-tag/dangling/structural). (2) naive re-scan (recurse on own output) -> both no-recursion tests redden, one via RecursionError, one via a wrong-content assertion. (3) drop the dangling-name gate -> all 3 stays-literal tests redden (KeyError/uncaught SquadsError). (4) stop catching TemplateError -> both StrictUndefined tests redden with a raw jinja2.UndefinedError leaking through. (5) write-path reads the EXPANDED body instead of raw -> the round-trip test catches it. Also added then removed a second expand_view_tags call site to prove the structural single-caller test fires. Every mutation reverted, full targeted suite reconfirmed green after each.
  - Gates: pyright 0 errors; ruff check all passed; ruff format clean. Targeted pytest (service/cli/unit/tui view-tag files + tests/meta) 378 passed. Wider sweep (tests/service+cli+unit+tui+meta) 3986 passed, 1 skipped. sq check: no issues.
  - Nothing undecided that the task didn't already settle -- ADR-880's amendment covered both failure modes and the no-recursion rule precisely enough to implement directly.
  - One thing I'd flag, not a defect: the accepted double-render (expanded tag + the still-live type-attached view print) means an item whose type attaches a view AND carries a hand-placed tag for that same view renders it twice in --raw/show. Verified live, matches the task's own 'additive, no single-render test' framing -- named here only so the reviewer doesn't mistake it for a regression.
  - @tech-lead ready for review.
- [2026-09-03T11:01:19Z] Catherine Manager:
  - Full suite green as the authoritative gate: 4691 passed, 12 skipped, exit 0. Verified beyond the tests: exactly one expansion call site (read_body, _services/_items.py:589) so every read surface inherits it from one place; and the two TASK-909 CLI tests this task rewrote still assert real behaviour -- they now pin the exact on-disk marker form and keep the occurrence count, which is a stronger assertion than the console substring they replaced.
<!-- sq:discussion:end -->

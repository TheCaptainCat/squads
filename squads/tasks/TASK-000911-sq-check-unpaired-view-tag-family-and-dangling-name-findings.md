---
id: TASK-911
sequence_id: 911
type: task
title: 'sq check: unpaired view tag family and dangling-name findings'
status: Done
parent: FEAT-905
author: tech-lead
assignee: python-dev
priority: urgent
refs:
- TASK-909:depends-on
- ADR-880:implements
description: Balance arithmetic exempts the family by shape; name resolution replaces
  pairing as an error-level, always-on finding
subentities:
- local_id: ST1
  title: Exempt the unpaired view family from pairing arithmetic
  status: Done
  story: US6
- local_id: ST2
  title: Dangling name or missing template as an error finding
  status: Done
  story: US7
- local_id: ST3
  title: Prove the repair sweep needs no change
  status: Done
  story: US7
- local_id: ST4
  title: Retype carries the tag and the check does not fire
  status: Done
  story: US8
- local_id: ST5
  title: Gates and test falsification
  status: Done
  story: US6
created_at: '2026-09-03T10:06:19Z'
updated_at: '2026-09-03T14:37:51Z'
---
<!-- sq:body -->
## Scope

Teach the marker-balance arithmetic the unpaired view family, and replace pairing with name
resolution for that one family.

Driven in ADR-880's amendment, with controls: `_marker_issues` in `_services/_maintenance.py`
counts every well-formed tag `find_markers` returns and reports an unpaired one as an error-level
"unclosed marker" — the same file with the tag removed checks clean, in both inside-body and
outside-region placement. So a correctly placed view tag makes a clean corpus look broken today.
This is not a gap the amendment opened; it is a collision that already exists and the original
ruling did not say so.

## Acceptance

**US6 — exempt by shape.**
- The open/close balance arithmetic exempts the declared unpaired view family, **by shape**,
  through the recogniser the placement task lands in `_models/_markers.py`. Never a name list, and
  never a `sq:view:` literal re-spelled at this site — a name list is exactly what a later view
  falls off.
- The exemption is from the pairing count only. Every other family's balance behaviour is
  unchanged, and a **duplicate** of the same named view tag in one file is still reported: that is
  a distinct signal from pairing, and a doubled tag renders the view twice. Cover it either way it
  is decided, but decide it deliberately.
- Table-driven coverage over position x shape: a view tag inside the body region at its start,
  middle and end; two view tags naming different views; a view tag adjacent to sub-entity region
  markers; a file with balanced regions and no view tag; and a control non-view unpaired tag that
  must still error exactly as it does today.

**US7 — a dangling name or missing template is an error.**
- Error-level and **unconditional**, always on. It sits with the existing always-on file-level
  marker scan, not as a selectable member of the per-item validator catalog: ADR-880 calls it the
  binding invariant, not a catalog-only selection. Do not couple it to FEAT-898's assignment
  grammar, and do not give it a level knob.
- It fires when the named view is not declared by the active spec, **or** when its template is
  missing — resolved through the shared helper the placement task lands, not a second
  implementation of the same question.
- The message names the file or item and the offending view name, and dynamic text reaching the
  console is escaped.
- **The repair sweep needs no change.** `_retired_region_tags` admits only the fixed `sq:summary`
  tag and tags ending in `:head`, and additionally skips any tag whose region is not balanced, so
  a view tag is excluded twice over — by name shape and by having no region at all. Prove it with
  a test that `sq repair` leaves a body carrying a view tag byte-identical, and do not edit the
  sweep.

**US8 — retype carries the tag, and the check does not fire.**
- `sq retype` preserves the whole body verbatim, so a view tag rides along to the item's new type
  and the dangling-name check correctly does not fire: a view is not type-scoped, so the name
  still resolves under the new type just as it did the old one.
- Cover it as an explicit test over a real retype: the tag's bytes and its position survive, and
  `sq check` stays clean afterwards.
- This is accepted, named behaviour — met as a decision rather than filed as a bug later. Add no
  type-scoping to a view, and no retype-time tag handling.

**Out of scope — do not build.** The warn-level advisory for an item whose type's creation
template seeds a tag and no longer carries it. Its condition is keyed on that creation template as
it currently stands, so it rides FEAT-907 alongside the seeding it depends on. Nothing here should
anticipate it.
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

_Add with `sq task 911 add-subtask "<title>"`; track with `sq task 911 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Exempt the unpaired view family from pairing arithmetic

<!-- sq:subtask:ST1:body -->
The open/close balance count in `_services/_maintenance.py` exempts the declared unpaired view family by shape, through the recogniser the placement task lands — never a name list, never the tag prefix re-spelled at this site. The exemption is from the pairing count only; every other family behaves exactly as it does today. A duplicate of the same named view tag in one file is still reported: that is a distinct signal from pairing, and a doubled tag renders the view twice.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Dangling name or missing template as an error finding

<!-- sq:subtask:ST2:body -->
Error-level and unconditional, sitting with the existing always-on file-level marker scan rather than as a selectable member of the per-item validator catalog — the ADR calls it the binding invariant, not a catalog-only selection, so it gets no level knob and no coupling to the assignment-grammar feature. It fires when the named view is undeclared by the active spec or when its template is missing, resolved through the shared helper the placement task lands. The message names the file or item and the offending view name, escaped where it reaches the console.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Prove the repair sweep needs no change

<!-- sq:subtask:ST3:body -->
The retired-region sweep admits only the fixed summary tag and tags ending in `:head`, and additionally skips any tag whose region is not balanced — so a view tag is excluded twice over, by name shape and by having no region at all. Prove it with a test that `sq repair` leaves a body carrying a view tag byte-identical. Do not edit the sweep.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Retype carries the tag and the check does not fire

<!-- sq:subtask:ST4:body -->
Retype preserves the whole body verbatim, so the tag rides along to the new type unchanged.
A view's name is not type-scoped, so the dangling-name check does not fire on the name alone
under the new type -- that part of the original claim stands. A subentity source's
applicability to its host IS type-scoped: when the landing type does not host the projected
kind, the tag is read successfully with its bytes left literal (TASK-913), and TASK-913's
widened check reports it as an error. Cover it over a real retype: the tag bytes and position
survive, and sq check stays clean when the landing type still hosts the view's source, or
reports the applicability finding when it does not. Add no type-scoping to a view and no
retype-time tag handling; this is accepted behaviour met as a decision.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Gates and test falsification

<!-- sq:subtask:ST5:body -->
Table-driven coverage over position and shape: a view tag at the body region start, middle and end; two tags naming different views; a tag adjacent to sub-entity region markers; a balanced file with no view tag; and a control non-view unpaired tag that must still error as it does today. Service-level and CLI smoke tests per behaviour. Then falsify each new test — break it red, restore it green — and report both halves. Full gate with `--all-extras`, plus `sq check` clean.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T11:17:50Z] Elias Python:
  - ST1 (US6): _marker_issues in _services/_maintenance.py exempts the unpaired view family from the unclosed-marker pairing count via markers.view_tag_name(tag) is None — one line, no name list. Duplicate detection (n>1) is untouched, so a doubled view tag still errors as 'duplicate marker'. Every other family's balance arithmetic is byte-identical to before.
  - ST2 (US7): new _dangling_view_issues(text, spec) sits beside _marker_issues in the same always-on file-level scan (_scan_for_check, where self.spec is already in hand) — not in the per-item validator catalog, no level knob, unconditional. Resolves through views.view_target_exists (TASK-909's helper), reusing the exact predicate insert_view already refuses a dangling name through. Message names the file and the offending view name (e.g. sq:view:no-such-view), escaped centrally by the existing e(i.message) at the check CLI's print site — no new escaping code needed.
  - ST3 (US7): proved with tests, not asserted — a view tag alone, alongside authored prose, alongside a genuinely-retired sq:summary region in the same file (which the sweep still strips), and across two successive sweeps all come back byte-identical. No change made to _retired_region_tags/_strip_retired_regions.
  - ST4 (US8): retype's body-copy path never touches sq:body, so a view tag rides the retype verbatim by construction. Covered with a real task->bug retype: tag bytes+position identical, sq check clean after, and a control proving a tag that WAS already dangling before the retype is still reported after (retype doesn't accidentally suppress the finding).
  - Tests: 7 new files, 33 tests total (service: pairing exemption x8 table-driven [start/middle/end/two-views/adjacent-to-story/no-tag/duplicate/control], dangling-name x7, repair-sweep x4, retype x3; CLI smoke: check x4, retype x1, repair x1). Falsified all 4 mechanisms by direct mutation+revert: (1) dropped the view_tag_name guard in _marker_issues -> 8 tests correctly redden (position+duplicate+CLI), balanced/dangling/control tests stayed green; (2) unwired _dangling_view_issues from the scan -> 8 tests redden (all dangling-name cases + retype's suppression control), the positive-control (resolvable view) test correctly stayed green; (3) added an unconditional view-tag strip inside _strip_retired_regions -> 4 of 5 repair tests redden (idempotence test correctly insensitive, since a second sweep on an already-corrupted file is still a no-op); (4) stripped the tag inside retype's container-ensure write -> both tag-preservation tests redden, the 'check stays clean'/control tests correctly stayed green. Every mutation reverted, full targeted set reconfirmed green each time.
  - Gates: pyright 0 errors; ruff check all passed; ruff format 620 files unchanged. Targeted pytest (all check/repair/retype/marker/view test files, 864 tests across service+cli+unit+integration+meta) all passed. tests/meta 279 passed (caught and fixed one stray ticket-ID reference I'd left in a docstring — the hygiene gate working as intended). sq check: no issues.
  - Decision I made, not pre-specified: the dangling-name finding is NOT added to _services/_validators.py's CATALOG/VALIDATOR_NAMES/CONSISTENCY_CLAUSES at all -- it mirrors _marker_issues' own treatment (hardcoded into the always-on scan, never a catalog member), so no member was added to that closure and no guard/floor/argued-no-guard decision was needed for it.
  - No defects found in the acceptance criteria. @tech-lead ready for review; the batch review can pick up all three FEAT-905 tasks together.
- [2026-09-03T11:19:43Z] Catherine Manager:
  - Full suite green as the authoritative gate: 4719 passed, 12 skipped, exit 0. Read the exemption myself: one added condition keyed on markers.view_tag_name, no name list, duplicate detection untouched -- the shape-not-name-list requirement holds. Routing one decision to the batch review rather than accepting it silently: the dangling-view finding was wired into the file-level scan beside _marker_issues instead of the per-item validator catalog, where ADR-880 said "floor". Defensible -- it reads raw text at file level, exactly like _marker_issues -- but it needs ruling, and FEAT-898 must know these two checks sit outside the catalog closure deliberately.
<!-- sq:discussion:end -->

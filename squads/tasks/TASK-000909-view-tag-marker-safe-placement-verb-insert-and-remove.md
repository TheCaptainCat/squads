---
id: TASK-909
sequence_id: 909
type: task
title: 'View tag: marker-safe placement verb, insert and remove'
status: Done
parent: FEAT-905
author: tech-lead
assignee: python-dev
priority: urgent
refs:
- ADR-880:implements
description: The unpaired tag shape, one shared name resolution, and the only path
  a view tag enters or leaves a body region
subentities:
- local_id: ST1
  title: Declare the unpaired view-tag shape and its recogniser
  status: Done
  story: US1
- local_id: ST2
  title: One shared view-name resolution helper
  status: Done
  story: US1
- local_id: ST3
  title: Marker-safe insert inside a region, anchored and idempotent
  status: Done
  story: US1
- local_id: ST4
  title: Marker-safe removal of one named tag
  status: Done
  story: US2
- local_id: ST5
  title: CLI placement verb over both directions
  status: Done
  story: US1
- local_id: ST6
  title: Cover the prose guard as unchanged, with its control
  status: Done
  story: US3
- local_id: ST7
  title: Gates and test falsification
  status: Done
  story: US1
created_at: '2026-09-03T10:06:10Z'
updated_at: '2026-09-03T14:37:48Z'
---
<!-- sq:body -->
## Scope

The tag's shape, and the one path by which a `sq:view:<name>` tag enters or leaves an item's
`sq:body` region.

ADR-880's amendment ruled that the prose guard gets no per-name hole: driven with a control, a
well-formed tag typed into a body write is refused while the same text unwrapped from its
HTML-comment form is accepted. A tag is an instruction, not prose, so it does not enter through
the prose door. Placement is its own marker-safe operation instead. FEAT-907's migration inserts
through this exact path in bulk, so what lands here is the tool's own placement operation applied
at scale — not a bespoke one-off write into authored prose.

**Additive only.** Nothing is deleted. The existing view render path, the projection middle layer
and the type attachment (`ItemSpec.views`) are untouched here — FEAT-903 widens the sources and
FEAT-904 deletes the projection; neither is in scope.

## What lands

**The unpaired tag shape, declared once.** `_models/_markers.py` gains the view-tag constructor
and the shape recogniser that answers "is this tag a member of the unpaired view family, and if so
which view does it name". Both other tasks on this feature consume that recogniser — the
expansion boundary scans with it and `sq check` exempts by it — so it must not be re-derived or
re-spelled as a literal at each site. `_models` has no internal deps; keep the recogniser's home
consistent with that.

**A shared view-name resolution.** One helper answering "is this name declared by the active spec,
and does its template resolve at `templates/views/<name>.md.j2`, including an adopter override in
the squad's own overrides tree". It lands here because insert refuses a dangling name; the check
finding reuses the same helper rather than implementing the question twice.

**A marker-safe insert/remove primitive** in `_sections.py`, operating on unpaired tag content
*inside* a named region, plus the service operation and the CLI verb over it. The verb's name is
the dev's call, with two constraints: it lives in the per-item verb group (`sq <type> <n> ...`) and
it is not a flag on `body`. Placement and body editing must stay visibly separate surfaces.

## Acceptance

**US1 — insert.**
- A distinct verb, not a body replace. The `body` write path is untouched.
- Default position is the end of the `sq:body` region — the same deterministic anchor FEAT-907's
  migration will use.
- Insert-only: it never rewrites, reorders or removes authored text. Every other byte of the body
  is preserved verbatim.
- Idempotent. A body already carrying that named tag is left unchanged and the operation reports it
  was already present; it never duplicates.
- Inserting a name the active spec does not declare, or whose template is missing, is refused with
  a clear `SquadsError` — the same failure mode as the check finding, resolved through the same
  helper.
- Type admissibility is a named decision, not an accident: the verb needs the item file to carry a
  `sq:body` region. It is not required to admit the roster types in this feature (FEAT-906 seeds
  those through their creation templates). If the implementation refuses a type, it refuses with a
  clear `SquadsError` saying why — it does not crash and does not half-write.

**US2 — remove.**
- Removes only the named tag. Everything else in the body — surrounding prose, a second view tag,
  every other marker line — is preserved verbatim.
- Removing an absent tag is a safe no-op with a clear message, not an error, and writes nothing.

**US3 — the prose guard stays closed.**
- `reject_markers` behaviour is unchanged by this feature: no per-name exception, no
  allow/except parameter, no call-site bypass, no caller newly routing around it.
- Cover both halves with the control: a well-formed view tag in `body -m` and in `body --file` is
  still refused, and the same text without its HTML-comment wrapper is still accepted.
- After this task, placement is possible only through the new verb (or, later, a creation template
  under FEAT-907).
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

_Add with `sq task 909 add-subtask "<title>"`; track with `sq task 909 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare the unpaired view-tag shape and its recogniser

<!-- sq:subtask:ST1:body -->
In `_models/_markers.py`: the view-tag constructor plus the recogniser that answers whether a tag belongs to the unpaired view family and, if so, which view it names. No closing counterpart is added. Both sibling tasks consume this recogniser, so the shape is never re-spelled as a literal at a call site. `_models` keeps its no-internal-deps property.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — One shared view-name resolution helper

<!-- sq:subtask:ST2:body -->
One helper answering "is this name declared by the active spec, and does its template resolve at templates/views/<name>.md.j2 including an adopter override". Insert refuses a dangling name through it; the check finding on the sibling task reuses the same helper rather than asking the question twice. Threaded off the active spec, not a module global.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Marker-safe insert inside a region, anchored and idempotent

<!-- sq:subtask:ST3:body -->
The `_sections.py` primitive that inserts unpaired tag content inside a named region, plus the service operation over it. Default anchor is the end of the `sq:body` region — the same anchor the later bulk migration will use. Insert-only: no rewrite, no reorder, no removal of authored text. A body already carrying that named tag is unchanged and the caller is told so.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Marker-safe removal of one named tag

<!-- sq:subtask:ST4:body -->
The removal primitive and its service operation: only the named tag goes, every other byte of the body survives verbatim — surrounding prose, a second view tag, every other marker line. Removing an absent tag is a safe no-op with a clear message and writes nothing.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — CLI placement verb over both directions

<!-- sq:subtask:ST5:body -->
The per-item CLI verb wiring insert and remove. Not a flag on `body` — placement and body editing stay visibly separate surfaces. Refusals surface as `SquadsError` for the clean-message-and-exit-1 path, and dynamic text reaching the console is escaped. Type admissibility is stated deliberately: the verb needs a body region, and a refused type is refused with a reason rather than crashing or half-writing.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Cover the prose guard as unchanged, with its control

<!-- sq:subtask:ST6:body -->
Regression cover that `reject_markers` gained no per-name exception, no allow parameter, and no call-site bypass: a well-formed view tag in `body -m` and in `body --file` is still refused, and the control — the same text without its HTML-comment wrapper — is still accepted. Placement is possible only through the new verb.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Gates and test falsification

<!-- sq:subtask:ST7:body -->
Service-level and CLI smoke tests per behaviour, asserting generated files: valid YAML frontmatter, intact markers, body preserved. Table-driven over tag position and body shape, including the empty body and the no-tag body. Then falsify each new test — break the behaviour, watch it go red, restore it, watch it go green — and report both halves. Full gate with `--all-extras`, plus `tests/meta` if any module constant was added, plus `sq check` clean.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T10:09:46Z] Catherine Manager:
  - Dispatching to @python-dev. First task of the 0.15 sequence; TASK-910 and TASK-911 both gate on it. Additive only -- the type-attached view print still exists in this feature, so a hand-placed tag on an attaching type renders twice until FEAT-904. That is accepted and transient; no test may assert a single render.
- [2026-09-03T10:30:12Z] Elias Python:
  - Implemented all 7 subtasks. ST1: markers.view_tag/view_tag_name in _models/_markers.py — unpaired family recogniser, no close_marker counterpart, structurally guarded by a test that scans module names.
  - ST2: views.view_target_exists(name, spec) in _views.py (top-level, no service dep) — name declared in spec.views AND has_template resolves (bundled or override); render_view refactored to share view_template_name() so the path is composed once.
  - ST3/ST4: _sections.insert_unpaired_marker/remove_unpaired_marker — insert anchors at the region's end via append_to_section, idempotent (membership check first); remove finds the marker and absorbs exactly one adjacent newline so no blank line is left. Both raise KeyError on a missing region. Service ops (ViewsMixin.insert_view/remove_view in _services/_views.py) route through a new ServiceCore._locked_placement_edit (_base.py) — like _locked_section_edit but skips the write and the updated_at/modified_session bump entirely when mutate reports no change, so a no-op genuinely writes nothing (verified by write_text call-count spies, not just byte-equality).
  - ST5: sq <type> <n> view add|rm <name>, nested group mirroring ref add/rm — not a body flag.
  - ST6: reject_markers is untouched (structural test pins its signature to (text, what)); wrapped-vs-unwrapped control covered at both service and CLI layers for -m and --file.
  - Type admissibility: every bundled type's template carries sq:body, so I couldn't drive the missing-region refusal off a real built-in type — droveit by stripping the body region from a real item's file on disk and confirming insert/remove both refuse with a clear SquadsError naming the item.
  - Tests: 6 new files (tests/unit x2, tests/service x2, tests/cli x2), 51 new tests, table-driven over position (start/middle/end/several-tags/adjacent-region) x shape (empty/no-tag). Falsified via 8 targeted mutations (recogniser, insert idempotency, view_target_exists, no-op write skip, CLI wiring, reject_markers signature, remove newline-absorption, KeyError->SquadsError translation) — each redenned the expected subset and was reverted to green; full trace in this session.
  - Gates: uv run --all-extras pyright -> 0 errors; ruff check -> all checks passed; ruff format --check -> 610 files unchanged; targeted pytest (94 tests across the new + adjacent marker/view files) -> 94 passed; tests/meta -> 279 passed; uv run sq check -> no issues.
  - @tech-lead ready for TASK-910/TASK-911 to build on the recogniser (markers.view_tag_name) and the resolution helper (views.view_target_exists).
- [2026-09-03T10:32:28Z] Catherine Manager:
  - Full suite green as the authoritative gate: 4660 passed, 12 skipped, exit 0 (run by the main loop, not the dev). Verified independently of the tests: no board ticket references in any of the 12 touched files, test filenames are behaviour-named, and the unpaired invariant holds -- no close_marker counterpart exists, and the VIEW docstring records why one may never be added. Moving to InReview; the batch review runs once all three FEAT-905 tasks are in.
<!-- sq:discussion:end -->

---
id: FEAT-905
sequence_id: 905
type: feature
title: 'View tag: placement verb, read-time expansion, and check integration'
status: Done
parent: EPIC-897
author: product-owner
priority: urgent
refs:
- MILE-867:targets
- ADR-880:implements
description: A dedicated marker-safe verb places/removes the unpaired tag in sq:body;
  one expansion site at the body-read boundary; sq check learns the unpaired family
  by shape
subentities:
- local_id: US1
  title: A dedicated verb inserts a named view tag into sq:body
  status: Done
- local_id: US2
  title: A dedicated verb removes a named view tag from sq:body
  status: Done
- local_id: US3
  title: Typing a tag into body -m/--file stays refused
  status: Done
- local_id: US4
  title: A body tag expands at one shared body-read boundary
  status: Done
- local_id: US5
  title: View output is never re-scanned for tags
  status: Done
- local_id: US6
  title: sq check exempts the unpaired sq:view family from pairing arithmetic
  status: Done
- local_id: US7
  title: A dangling view name or missing template is an error-level finding
  status: Done
- local_id: US8
  title: sq retype carries the tag; the dangling-name check does not fire
  status: Done
created_at: '2026-09-03T09:10:58Z'
updated_at: '2026-09-04T07:35:30Z'
---
<!-- sq:body -->
## Why

A tag is an instruction, not prose — it does not enter through the prose door, and the
mechanism that reads and writes it is engine work, not adopter typing. ADR-880's amendment
(2026-09-03) settled where it lives (`sq:body`, unpaired) and, driven with controls, found two
gaps the original ruling missed. Both are load-bearing for this feature, not footnotes.

## Scope

**1. A dedicated placement verb — first-class, not a hole in `reject_markers`.**
`reject_markers` refuses any well-formed marker tag typed into a body write, with no exception
— driven: the exact same tag text unwrapped from its HTML-comment form is accepted, wrapped it
is refused. "Type the tag into `sq <type> <n> body`" does not work and never will; punching a
per-name hole in that guard was refused. Instead: a dedicated marker-safe operation inserts or
removes a named view tag within the item's `sq:body` region, distinct from a body replace.
FEAT-907's migration inserts through this exact same path, in bulk — so it is the tool's own
placement operation applied at scale, not a bespoke one-off write into authored prose.
Typing the tag directly into `body -m`/`--file` stays refused, unchanged.

**2. Read-time expansion at one shared boundary.** A `sq:view:<name>` tag in a body expands to
that view's rendered output wherever the body is read — `--raw`, `show`, and the TUI all
inherit it from one shared body-read boundary below the CLI, no per-surface reimplementation.
View output is never itself scanned for tags — no recursion; a tag appearing inside rendered
view text stays literal.

**3. `sq check` learns the unpaired family by shape, not by name list.** Driven: today's
marker-balance check already reports *any* unpaired tag as an error-level "unclosed marker" —
this is not a gap the amendment opens, it is a collision that already exists and the original
ruling didn't say so. The balance check must exempt the declared `sq:view:<name>` shape from
pairing arithmetic; name resolution replaces it — a tag naming a view the active spec doesn't
declare, or whose template is missing, is the error instead. The repair sweep that strips
retired regions needs **no change** — it already admits only `sq:summary` and `*:head` by name
and skips anything unbalanced, so a view tag is excluded twice over already.

**4. `sq retype` consequence, accepted not fixed.** `sq retype` preserves the whole body
verbatim, so a view tag rides along to the item's new type, and the dangling-name check does
not fire — a view is not type-scoped, so the name still resolves against the new type just as
it did the old one. This is correct behaviour, named here so it is met as a decision rather
than filed as a bug later: the tag is a property of the document, and retype preserves the
document.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 905 add-story "As a <role>, I want … so that …"`; track with `sq feature 905 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — A dedicated verb inserts a named view tag into sq:body

<!-- sq:story:US1:body -->
As an operator or agent placing a view on a document, I want a dedicated command that inserts a named sq:view:<name> tag into the item's sq:body region, so I can place a view without hand-typing marker text (which reject_markers refuses).

Acceptance: the operation is a distinct verb, not a body-replace; default position is the end of the body region, matching the migration's anchor (FEAT-907); inserting a tag that names a view the active spec doesn't declare is refused with a clear error, same failure mode as the check finding; inserting an already-present tag is idempotent (no duplicate).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — A dedicated verb removes a named view tag from sq:body

<!-- sq:story:US2:body -->
As an operator or agent, I want a dedicated command that removes a named view tag from sq:body, so I can take a view off a document deliberately.

Acceptance: removes only the named tag, leaving the rest of the body untouched; removing an absent tag is a safe no-op, not an error.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Typing a tag into body -m/--file stays refused

<!-- sq:story:US3:body -->
As the maintainer of reject_markers, I want typing a well-formed view tag directly into body -m or --file to stay refused exactly as it is today, so a tag never enters through the prose door and the guard gets no per-name hole.

Acceptance: reject_markers's behaviour is unchanged by this feature; the same input that is refused today is refused after; placement is possible only through the dedicated verb (US1) or a creation template (FEAT-907).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — A body tag expands at one shared body-read boundary

<!-- sq:story:US4:body -->
As anyone reading an item (sq show, --raw, the TUI), I want a sq:view:<name> tag in its body to expand to that view's rendered output wherever the body is read, so a view renders in place with no stored, staleable copy.

Acceptance: expansion happens at one shared body-read boundary below the CLI; --raw, show, and the TUI all inherit it from that one place -- no per-surface reimplementation of expansion.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — View output is never re-scanned for tags

<!-- sq:story:US5:body -->
As the maintainer of the expansion mechanism, I want a tag appearing inside a view's own rendered output to stay literal text, never re-expanded, so there is no recursion to bound.

Acceptance: view output is not itself scanned for tags; there is no depth limit and no cycle detection, because there is no second expansion site to recurse through.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — sq check exempts the unpaired sq:view family from pairing arithmetic

<!-- sq:story:US6:body -->
As anyone running sq check, I want a well-formed sq:view:<name> tag to stop being reported as an 'unclosed marker' error, so a correctly-placed view tag doesn't make a clean corpus look broken.

Acceptance: driven fact this story fixes -- today _marker_issues counts every well-formed tag and reports an unpaired one as an error in both body-inside and hypothetical outside placement; after this story, the sq:view:<name> shape is exempt from the open/close balance count entirely, by shape (not by a name list).
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — A dangling view name or missing template is an error-level finding

<!-- sq:story:US7:body -->
As anyone running sq check, I want a sq:view:<name> tag naming a view the active spec doesn't declare, or whose template file is missing, flagged as an error, so a dangling reference is caught the way a stale rendered region never could be.

Acceptance: error-level, unconditional (this is the ADR's binding invariant, not a catalog-only selection); name resolution replaces pairing arithmetic for this family entirely (US6); the repair sweep that strips retired regions needs no change -- it already admits only sq:summary and *:head by name and skips anything unbalanced, so a view tag is excluded twice over.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — sq retype carries the tag; the dangling-name check does not fire

<!-- sq:story:US8:body -->
As an author whose item gets retyped (sq retype), I want any view tag in its body to ride
along unchanged to the new type, so a milestone retyped to an epic keeps its roll-up.

Acceptance: sq retype's existing verbatim body preservation already does this -- confirm/cover
it as an explicit test. A view's *name* is not type-scoped, so US7's dangling-name check does
not fire on the name alone under the new type, exactly as before. A subentity source's
*applicability* to its host IS type-scoped (TASK-913): the tag riding along to a non-hosting
type is read successfully with the tag left byte-for-byte literal, and TASK-913's widened check
reports it as an error. Retype's own behaviour is unchanged -- it still preserves the body
verbatim and gains no refusal -- only the outcome for a non-hosting landing type changes, from
a clean check on an unreadable item to a readable item with a reported finding. This is
accepted, documented behaviour, not a defect to file later.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T10:00:06Z] Catherine Manager:
  - Opening 0.15 with this feature, per op-pierre: run the release as a sequence, one feature at a time. FEAT-905 is first because it is additive (the old projection keeps rendering while the new path is built beside it), because FEAT-903/904/906/907/908 now all depend on it, and because it carries the release unknowns -- a new marker-safe verb, a new read-time expansion boundary, and sq check learning an unpaired marker family. Nothing is deleted until the new path is proven.
- [2026-09-03T10:08:52Z] Olivia Lead:
  - Broke this into three tasks, one per coherent surface, subtasks carrying the granularity: TASK-909 the placement verb (US1/US2/US3), TASK-910 the read-time expansion boundary (US4/US5), TASK-911 the sq check integration (US6/US7/US8). All Draft — promotion at dispatch is mine.
  - One change from the surface cut as briefed: US8 (retype carries the tag) sits with the check task, not with expansion — its acceptance is that the dangling-name check does NOT fire, which is only assertable once US7 exists. TASK-909 also carries two shared pieces the other two consume rather than re-derive: the unpaired tag shape/recogniser in _models/_markers.py, and one view-name resolution helper (declared by the active spec + template present). That makes TASK-909 gate the other two; TASK-910 and TASK-911 are independent of each other.
  - Two calls I made in the bodies so they are not re-litigated in review. (1) A tag naming an undeclared view, or one whose template is missing, stays literal on read and the read succeeds — reads must work on a broken corpus and sq check is the reporting surface; a template raising under StrictUndefined is the opposite case and propagates as SquadsError. (2) The family is exempt from open/close balance arithmetic only — a duplicate of the same named tag in one file is still reported, since a doubled tag renders the view twice.
  - Named as accepted and transient in TASK-910 so a dev does not "fix" it: the type-attached view print on show still exists in this feature, so a hand-placed tag on an attaching type renders twice until FEAT-904 removes the attachment. No test may assert a single render. Also fenced out of TASK-911: the warn-level advisory for a lost seeded tag rides FEAT-907 with the seeding its condition is keyed on.
  - sq check clean. @manager the three are ready for dispatch in that order.
- [2026-09-03T11:44:40Z] Paul Reviewer:
  - Batch review of FEAT-905's three commits recorded as REV-912 (refs FEAT-905 addresses,
    ADR-880 related). Ten findings; recommended verdict **ChangesRequested**, on F1 alone.
    
    - **F1 critical** — a placed view tag can make an item unreadable through every read surface
      while `sq check` reports nothing. Expansion gates on name resolution but not on whether the
      view's declared source resolves against the host item, so a subentity-source view placed on a
      non-hosting type raises `SquadsError` out of `read_body`. Driven twice: directly via
      `view add`, and via the retype path US8 accepted. The retype suite asserts the check stays
      clean and never asserts the item is still readable.
    - **F2 high** — `view_tag_name` takes the bare tag while its only producers emit the prefixed
      form, and the mismatch fails silently (returns `None`). Already bit the implementer once; no
      test names the shape.
    - **F3 medium** — `_locked_placement_edit` is a third clone of the frontmatter write seam and
      `_section_edit_core`'s "second of the two write seams" docstring is now false.
    - **F10 medium** — `sq check`'s two tiers are documented at the file-level end and contradicted
      at the catalog end ("sole source"). This is the action item from the placement ruling.
    - **F4/F5/F6/F7 low, F8/F9 info** — an unconditional index load added to the body-read boundary
      (35 ms per TUI body read on this corpus, driven), `view rm` reporting success while a
      duplicate tag still renders, a catalog canary that matches `review`, jinja exception
      translation duplicated at consumers instead of the engine, a removal path that normalises the
      region it promises to preserve, and six build-process narration hits in the new test
      docstrings.
    
    The placement question routed to review is **ruled correct by design** — the dangling-view
    finding stays in the file-level scan, do not move it to `CATALOG`. Full reasoning in REV-912's
    discussion, including what FEAT-898 should carry forward. @tech-lead @manager
    
    I did not touch source, did not transition FEAT-905 or its tasks, and left REV-912 in InReview
    for the approver — recording findings and a recommended verdict is mine, approving is not.
- [2026-09-03T12:06:39Z] Olivia Lead:
  - - Two fix tasks authored against REV-912, both Draft (promotion is mine, at dispatch): TASK-913
      the widened applicability predicate and the recogniser contract (F1, F2), TASK-914 the eight
      non-blocking findings as one pass (F3-F10). Both ref ADR-880 (implements) and REV-912
      (addresses).
    - One deviation from the briefed cut: **F2 rides with F1, not with the cleanup.** The recogniser
      is the seam F1's fix adds consumers to, and both findings land in the same two modules
      (`_views.py`, `_services/_maintenance.py`). Split, the F1 dev writes a third hand-strip the
      cleanup task then removes.
    - **Dependency order: TASK-913, then TASK-914.** Not parallel. F10's docstring must name the
      generalised finding by the name TASK-913 gives it, F4's guard calls the recogniser whose
      contract TASK-913 settles, and both tasks edit the same two modules.
    - All ten findings triaged in scope for this feature; nothing deferred. The two forward-looking
      ones are fenced in the bodies instead: FEAT-903's three kinds each declare their own
      applicability predicate as they land (ADR-880 second amendment already reads all three against
      the test), and a view tag inside a *sub-entity* body stays out of scope until FEAT-907 seeds
      tags from creation templates.
    - US8's acceptance is corrected in TASK-913 ST6 rather than rewritten silently — it keeps its
      ruling and loses the sentence collapsing a view's *name* (not type-scoped) with a subentity
      source's *applicability* (type-scoped).
    - `sq check` clean. @manager both ready for dispatch in that order; I hold the Draft to Ready
      gate.
- [2026-09-03T14:38:16Z] Catherine Manager:
  - Closed. The tag mechanism ships: a marker-safe placement verb (insert/remove, idempotent, anchored at the body region end), read-time expansion at the single body-read boundary so every surface inherits it, sq check learning the unpaired sq:view family by shape with error-level findings for a target that cannot resolve, and source applicability as a type-decidable precondition rather than a read-time raise. reject_markers gained no hole. The tag stays unpaired -- no close_marker counterpart, so no span exists to materialise rendered content into.
  - Carried forward, not lost: five verification doubts the reviewer named but could not close himself (the bulk importer write seams never driven through a real sq import; the skew guard accepted on reading; the real sq ui never launched by human eyes; a retype between two types hosting the same kind, unbuildable on the bundled spec; and a second reader wanted on his own narration held-list). QA takes these against the shipped feature in parallel with FEAT-903.
- [2026-09-03T14:52:08Z] Mara Tester:
  - Closed REV-912's five carried-forward QA doubts against the shipped feature. All driven in a throwaway squad nested under scratch, removed after; this tree untouched (only concurrent tech-lead edits under squads/, not mine).
  - 1. Bulk importer's two write seams (_import.py:584/608) — driven. Real 'sq import' with body+sub-body ops against a pre-existing target, inside its already-open transaction: updated_at bumps to the event's own 'at' on each write, chained body/sub-body edits on the same item across events read each other's prior write with no false skew, markdown mtime < index mtime on every apply (files-then-index order holds), and a second body write without --force is refused in the pre-pass with nothing written (mtimes/content untouched) — not a silent no-op. No defect.
  - 2. Skewed placement — driven. Hand-diverged an item's on-disk title from the index (the same technique the skew-guard suite itself uses), then drove both 'view add' and 'view rm' into it: both refuse with ensure_no_skew's own message, exit 1, no write (mtimes unchanged). 'sq repair' clears it and 'view add' then succeeds normally. ensure_no_skew is genuinely wired into the new placement seam, both directions. No defect.
  - 3. sq ui by human eyes — driven. Launched the real SquadsApp.run() (the exact call _cli/_ui.py makes, headless+auto_pilot instead of a real TTY, not App.run_test()/Pilot), navigated the browse tree with real keypresses, exported a real screenshot. Visual: TASK carrying a placed subentity... er ref-sourced milestone_rollup tag renders its expansion cleanly inline in the reader's Body tab (Delivered/Outstanding/Settled groups) below the authored prose, no crash, no garbling, no hang. Only artifact is missing Nerd Font glyphs in my headless capture environment — a font-availability quirk of the screenshot pipeline, not the app. No defect.
  - 4. Retype between two types hosting the same subentity kind (hosting-preserved case) — driven, via a synthetic .overrides/workflow.toml declaring a second type ('chore') with subentity_kind='subtask' (same as task) plus a subentity-source view+template. Placed the tag on a 0-subtask task (source applies, empty is not a failure), retyped task->chore: body region bytes identical before/after (verified byte-for-byte), 'sq check' clean, 'show --raw' and '--json' both exit 0 with the view still expanding ('(no subtasks)') since chore also hosts subtask. The mechanism generalizes correctly because applicability is a pure function of (view, spec, item.type) on both sides of the retype. No defect.
  - 5. Second reader on the F9 held-list, applying the stranger test myself: _views.py:551 ('every existing catcher of that base class keeps working unchanged') — agree, hold. Self-contained substitutability/Liskov property, present tense, no before needed, someone introducing this subtype fresh today writes exactly this sentence.
  - 5 (cont). _validators.py:11 — partial disagreement. The scoping clause itself ('sole source of ... per-item and squad-global issues ... not of sq check's issues as a whole') is durable and should stay — it's reinforced by the very next paragraph naming the second tier, so it's independently checkable without any history. But 'despite an earlier version of this sentence' specifically is narration by the test: unlike the two corpus precedents it's patterned on (_sections.py:84, _maintenance.py:273), which both NAME the old false claim before refuting it with a driven fact, this one only gestures at 'an earlier version' without saying what it claimed — a stranger gets nothing checkable from that clause alone, and nobody writing this docstring fresh today (no prior sentence to correct) would write it. Not filing this as anything — a documentation nit, not a defect, and the call was explicitly invited.
  - Nothing left open from this pass; all five gaps closed with driven evidence.
- [2026-09-03T14:52:17Z] Mara Tester:
  - @manager all five REV-912 doubts closed above, none reopened; nothing further pending from QA on FEAT-905.
<!-- sq:discussion:end -->

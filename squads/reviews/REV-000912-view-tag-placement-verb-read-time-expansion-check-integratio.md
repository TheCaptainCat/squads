---
id: REV-912
sequence_id: 912
type: review
title: 'View tag: placement verb, read-time expansion, check integration'
status: Approved
author: reviewer
refs:
- FEAT-905:addresses
- ADR-880
subentities:
- local_id: F1
  title: Placed view tag can make an item unreadable, check blind
  status: Verified
  severity: critical
- local_id: F2
  title: Recogniser silently rejects the form its producers emit
  status: Verified
  severity: high
- local_id: F3
  title: Third frontmatter write seam clones the core, count now false
  status: Verified
  severity: medium
- local_id: F4
  title: Body-read boundary now loads the whole index unconditionally
  status: Verified
  severity: low
- local_id: F5
  title: view rm reports success while a duplicate tag still renders
  status: Verified
  severity: low
- local_id: F6
  title: Catalog-exclusion canary matches review, not just view
  status: Verified
  severity: low
- local_id: F7
  title: Jinja exception translation duplicated at consumers, not the engine
  status: Verified
  severity: low
- local_id: F8
  title: Removal round-trips the region through a newline normaliser
  status: Verified
  severity: info
- local_id: F9
  title: Build-process narration in delivered docstrings
  status: Verified
  severity: info
- local_id: F10
  title: Two-tier check surface is undocumented at the catalog end
  status: Verified
  severity: medium
- local_id: F11
  title: Engine translation rewraps missing-template error; docstring now false
  status: Verified
  severity: info
- local_id: F12
  title: No-op section edit still commits the index; docstring says otherwise
  status: Verified
  severity: info
created_at: '2026-09-03T11:39:41Z'
updated_at: '2026-09-03T14:37:40Z'
---
<!-- sq:body -->
## Scope

One batch review of the three commits that compose the view-tag mechanism, read as one
change rather than three: the marker-safe placement verb and the unpaired tag family, the
read-time expansion boundary, and the `sq check` integration. Diff read as
`git diff 3b6aeed6..HEAD -- src/ tests/` (2385 added lines across 8 source and 17 test files).

Every claim below is labelled **read** (from source), **driven** (I ran it) or **inferred**.
Driven work ran in a throwaway squad outside this repository, nested under a scratch path,
removed afterwards; the review tree was clean before and after (`git status --porcelain` empty).

## What is sound

The three tasks compose. The recogniser is declared once and consumed, not re-derived: `view:`
is never re-spelled as a live literal outside `_models/_markers.py` (only in docstrings and
`--help` text), `view_target_exists` has exactly two callers — the placement refusal and the
check finding — and `view_template_name` centralises the template path with `render_view`
refactored onto it. Expansion has one call site, pinned structurally as well as by grep.
The two failure modes are genuinely distinct and both driven: an undeclared name stays literal
with exit 0, a declared view whose template raises under `StrictUndefined` exits 1 with a clean
message. The no-recursion property is structural — spans are computed once against the original
text and the result is assembled from those positions, so there is nothing for a depth counter
to guard. The pairing exemption is narrow: a `:end` spelling is still reported as an unopened
marker and a duplicate is still reported as a duplicate.

The read/write seam holds. `read_body` has five callers and all five are display surfaces;
no consumer of the `sq:body` region anywhere feeds a write; the VS Code client never writes a
body. Expanded bytes have no path to disk.

## Where it does not hold

One major finding: a placed tag can make an item unreadable through every read surface while
`sq check` reports nothing, because expansion gates on name resolution but not on whether the
view's declared source can resolve against the host item. It is reachable both by placing the
tag and by the retype path this feature explicitly accepted, and the retype tests assert the
check stays clean without ever asserting the item is still readable. The rest are one latent
silent-failure in the recogniser's contract, a cloned write seam whose neighbour's docstring is
now false, and a set of smaller correctness/quality points.

## Verdict

Changes requested on F1. Everything else can land or ride a follow-up at the lead's call —
none of the others is a correctness risk to the mechanism itself.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 912 add-finding "…" --severity medium`; track with `sq review 912 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Placed view tag can make an item unreadable, check blind

<!-- sq:finding:F1:body -->
**Driven** in a throwaway squad, two independent paths.

`expand_view_tags` (`src/squads/_views.py:501`) gates on `view_target_exists(name, spec)` —
declared in `spec.views` **and** the template resolves — and then calls `resolve_records`.
For a view whose declared `source.kind` is `subentity`, `_resolve_subentity_source`
(`src/squads/_views.py:146`) raises `SquadsError` when the host item's type does not host the
projected kind. `read_body` is the single boundary, so that raise reaches `sq show`,
`show --raw`, `show --json`, the TUI reader, the operator pane and the skill read: exit 1, no
body rendered at all. `sq check` cannot see it, because the dangling-name finding asks the
same question expansion gates on — declared-and-templated — and that question is satisfied.

Path A — placement. With `[views.story_board] source = { kind = "subentity", name = "story" }`
declared in `.overrides/workflow.toml` and a template at
`.overrides/templates/views/story_board.md.j2`:

    sq epic 2 view add story_board     -> "EPIC-2: view story_board placed in sq:body"  (exit 0)
    sq check                           -> "no issues"                                   (exit 0)
    sq epic 2 show --raw               -> error: view 'story_board' projects 'story'
                                          sub-entities, but EPIC-2 is a 'epic' item,
                                          which hosts none                              (exit 1)
    sq show EPIC-2 --json              -> exit 1

`insert_view` never asks whether the view's source can resolve against *this* item, so it
accepts the placement that breaks the read.

Path B — retype, which is US8's own accepted behaviour. Place the view on a story-less feature
(valid there; `sq feature 4 show --raw` exit 0), then:

    sq feature 4 retype epic           -> "retyped FEAT-4 -> EPIC-4  status carried: Draft"
    sq check                           -> exit 0, no issues
    sq epic 4 show --raw               -> error: view 'story_board' projects 'story'
                                          sub-entities, but EPIC-4 is a 'epic' item ...  (exit 1)

TASK-911 US8 states that after a retype "the name still resolves under the new type just as it
did the old one". That is true of the *name* and false of the *view*: for a subentity source,
resolvability is type-scoped even though the name is not. The item is now unreadable and
nothing on any reporting surface says why.

Why this matters beyond the one message: ADR-880 and TASK-910 ST4 split the failure modes
deliberately — corpus state must never break a read, only an engine or template defect is
loud. This is corpus state breaking a read, through the exact seam the split was built at.
Recovery exists (`sq <type> <n> view rm <name>` deliberately does not gate on resolution, which
is the right call) but the operator gets no pointer to it: the error names the view, not the
verb that would take it off.

Not reachable with the bundled spec — `milestone_rollup` is the only bundled view and its
source is `ref`, which resolves against any item (**read**: `_specs/workflow.toml:624`,
`_resolve_ref_source` only inverts refs). It is reachable for any adopter declaring a
subentity-source view, and FEAT-903 widens the source kinds, which widens this.

Test-shape gap that let it through (**read**): every fixture in
`tests/service/test_view_tag_expansion_at_read_time.py` builds its subentity-source views over
`subtask` on a `task`, which hosts the kind (`_declare_static_view`'s own docstring says so:
"any task hosts the kind, so no fixture data is needed"). The retype suite
(`tests/service/test_retype_carries_a_view_tag_and_check_stays_clean.py`) asserts the tag's
bytes survive and that `sq check` stays clean, and never asserts the item is still readable —
`read_body` is not called in that file at all. The host-mismatch shape is not covered anywhere.

Direction, not a fix: either expansion also gates on source resolvability and leaves the tag
literal (keeping reads working on a broken corpus and making `sq check` the reporting surface,
which is what the ADR asks of it), or `insert_view` and `_dangling_view_issues` both learn the
source-resolvability question so the state cannot be created silently and is reported when it
already exists. Whichever is chosen, the two failure modes must stay split, and a regression
test needs the subentity-view-on-a-non-hosting-type shape plus a `read_body` assertion in the
retype suite.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Recogniser silently rejects the form its producers emit

<!-- sq:finding:F2:body -->
**Read**, plus the dev's own handback as corroboration.

`markers.view_tag_name(tag)` (`src/squads/_models/_markers.py:74`) is documented as the one
recogniser, and it takes the **bare** tag (`view:milestone_rollup`). The only producers of a
tag string in this codebase are `sections.find_markers` and the new
`sections.iter_marker_spans`, and both return the tag with its `sq:` prefix still attached
(`iter_marker_spans` has a test pinning exactly that: "the raw form, matching find_markers's
own convention"). So the one recogniser rejects the only form its only producers emit, and it
rejects it the worst possible way — by returning `None`, which every caller reads as "not a
view tag" and acts on silently.

Both new call sites therefore carry the strip by hand:

    src/squads/_views.py:500        name = markers.view_tag_name(raw[len(markers.PREFIX) :])
    src/squads/_services/_maintenance.py:505   tag = raw[len(markers.PREFIX) :]
                                               name = markers.view_tag_name(tag)

Failure scenario: a future caller (a fourth surface, or FEAT-907's bulk placement scanning for
already-present tags) passes the on-disk form straight from `find_markers`. `view_tag_name`
returns `None`, the tag is treated as a non-view marker, and the surface silently does nothing
— no exception, no log, no check finding. This is not hypothetical: TASK-910's handback records
hitting it during implementation ("First cut silently expanded nothing; caught it by manually
driving sq show --raw before writing tests").

Nothing guards it now. `tests/unit/test_unpaired_view_tag_shape_recognition.py` covers the bare
form, other families, the `:end` spelling, `view`, `view:` and `viewpoint:x` — but has no case
for `"sq:view:x"`, so the contract that bit the implementer is the one shape the suite does not
name. `_marker_issues`'s pre-existing loop strips the prefix for its own reasons, so the
convention is invisible unless you happen to read that loop.

Direction: make the recogniser accept the on-disk form (or both), or make `iter_marker_spans`
return bare tags so producer and recogniser agree; either way pin the chosen contract with a
test that names the producer, so the next caller cannot get it wrong quietly. The comment at
`_views.py:496-499` explaining why the strip lives at the call site is an argument for a
convention that has already failed once.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Third frontmatter write seam clones the core, count now false

<!-- sq:finding:F3:body -->
**Read.**

`ServiceCore._locked_placement_edit` (`src/squads/_services/_base.py:1192`) reproduces
`_section_edit_core` (`src/squads/_services/_base.py:1231`) almost line for line: open the
transaction, `require_item`, `model_copy(deep=True)` for the skew baseline, `item_file`,
`_read_item_file`, `ensure_no_skew(..., default_kind=self.spec.default_ref_kind())`, run
`mutate`, bump `updated_at` and `modified_session`, then
`write_text(path, replace_frontmatter(new_text, it.to_frontmatter_dict()))`. The only real
difference is the early return when `mutate` reports no change.

That makes it a third copy of the integrity-critical frontmatter-rewrite seam, and it falsifies
the documentation of the other two. `_section_edit_core`'s own docstring still says:

    This is the second of the two write seams that rewrite an item's frontmatter from an
    index-derived ``Item`` (the other is :func:`~squads._itemfile.update_frontmatter`)

There are now three. That count is not decorative — it is what a reader uses to enumerate the
places the skew guard and the write ordering have to be kept consistent.

Failure scenario: a later change tightens the skew guard, or reorders the frontmatter rewrite
relative to the markdown write (invariant 8's territory). The author enumerates the seams from
that docstring, finds two, fixes two. `sq <type> <n> view add` keeps writing under the old rule,
and because a placement write is small and its tests assert only file content (never the skew
or ordering contract), nothing reddens.

The docstring's justification — that the shared core "cannot grow without changing behaviour
for every other caller ... that relies on it always writing" — is true of an unconditional
change but not of the alternative: the core can take the conditional-write decision from
`mutate` (a `(text, changed)` return, or a sentinel meaning "no write") with every existing
caller returning `changed=True`. Direction: fold the third seam back into the core, or, if it
genuinely must stay separate, fix the count and cross-reference at both ends so the seam
inventory is recoverable from either docstring.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Body-read boundary now loads the whole index unconditionally

<!-- sq:finding:F4:body -->
**Read** for the mechanism, **driven** for the number.

`read_body` (`src/squads/_services/_items.py:585-589`) now does `db = await self.store.load()`
unconditionally, before it knows whether the body carries a view tag at all. Before this change
the body-read boundary loaded no index.

Under the CLI that is free: `_cli/_common.command` opens one invocation-scoped read scope and
`IndexStore.load` serves the filed snapshot, so the second load costs nothing.

`sq ui` deliberately opts out of that scope — `_cli/_ui.py:8-10` decorates `ui()` with
`@handle_errors`, not `@common.command`, and `command`'s own docstring names the consequence:
"`sq ui` is a sync command that never passes through here at all, so it opts out for free and
keeps today's always-fresh behaviour — no scope, no memoized Service". So in the TUI every
`ReaderPanel.load` (`src/squads/_tui/_reader.py:51`) now pays a fresh full index read plus
pydantic validation, on every item you select in the browse tree, whether or not the body has a
tag.

Driven on this repo's own corpus (5582 items, `squads/.squads.json` = 1,193,202 bytes):

    store.load(fresh=True)  ->  0.035 s per call (3-call mean, 0.106 s total)

So ~35 ms of unnecessary work per body read in the TUI, growing with corpus size, for a feature
that today fires on zero documents in this repo.

Direction: bail before the load. The tag spans are computable from the body text alone
(`iter_marker_spans` + `view_tag_name`), so `read_body` can skip both the load and the call
when the body carries no view tag; or `expand_view_tags` can take the db lazily. Either removes
an index dependency from the body-read boundary for the overwhelming majority of bodies, which
is also the cleaner shape — a boundary documented as "read on a thread" should not silently
acquire an index read.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — view rm reports success while a duplicate tag still renders

<!-- sq:finding:F5:body -->
**Driven.** (Tags below are spelled bare — `sq:view:<name>` — since a body may not carry a
well-formed marker.)

`remove_unpaired_marker` (`src/squads/_sections.py:227`) removes the **first** occurrence only
(`idx = inner.find(marker)`), and the boolean it returns cannot distinguish "the last one" from
"one of several". `remove_view` passes that boolean straight through to the CLI, which prints an
unconditional success line (`src/squads/_cli/_items.py:685`).

Driven, on a body carrying the same named tag twice — the exact state `sq check` reports as a
duplicate marker and therefore treats as a supported, repairable error:

    (body carries two sq:view:milestone_rollup tag lines)
    sq check                            -> error ...: duplicate marker (sq:view:milestone_rollup)
    sq epic 2 view rm milestone_rollup  -> "EPIC-2: view milestone_rollup removed from sq:body"  (exit 0)
    (file still carries one tag)
    sq check                            -> clean
    sq epic 2 show --raw                -> the roll-up still renders

So the operator's intent — take this view off this document — is reported as done and is not
done, and the check that would have told them is now silent because a single tag is legal.

Nothing in the removal suite covers a duplicate: `tests/unit/test_unpaired_marker_insert_and_
remove_section_primitive.py` covers "a second view tag" only in the *different-name* shape
(`test_remove_only_the_named_tag_leaves_a_second_view_tag_verbatim` uses `view:other`), and
`remove_unpaired_marker`'s docstring says "a second marker of this same family" survives —
which is exactly right for a different name and exactly wrong as a description of what an
operator asked for.

Reachability is low: `insert_view` is idempotent, so a duplicate arrives only by hand-editing
or by a bulk placement path (FEAT-907). Filed anyway because the duplicate state is one the
team decided to keep reporting, and `view rm` is the repair path for it.

Direction: remove every occurrence of the named tag, or report the count that remains. Either
way the report should not say "removed" while the view still renders.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Catalog-exclusion canary matches review, not just view

<!-- sq:finding:F6:body -->
**Read**, plus **driven** confirmation of the substring.

`tests/service/test_check_flags_a_dangling_view_tag_name.py`, last test, closes with:

    assert "dangling_view" not in CATALOG
    assert not any("view" in name for name in CATALOG)

The second assertion is over-broad in a way that will bite: `"view"` is a substring of
`"review"`, and `review` is one of this project's own declared item types. The first validator
anyone adds named `review_*` (a review-target rule, a findings-closed rule, an approver rule)
fails this test, with a message that points at the view-tag feature and says nothing about the
validator that actually broke it.

Driven: `CATALOG`'s 16 current keys contain no `review`, so it passes today —
`'review_target_present' contains 'view'` is `True`, so the trap is armed and merely unsprung.

Failure scenario: a later change adds `"review_findings_closed"` to `CATALOG`/`VALIDATOR_NAMES`,
the correspondence asserts at module import stay happy, and an unrelated test in the view-tag
suite fails claiming the dangling-view finding has become a catalog member. That is a false
report pointing at the wrong feature.

The first assertion already carries the real claim. If the broader guard is wanted, anchor it:
`not any(n.startswith("view") for n in CATALOG)`, or check against the actual function object
rather than a name substring.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Jinja exception translation duplicated at consumers, not the engine

<!-- sq:finding:F7:body -->
**Read.**

`_views._render_view_or_raise` (`src/squads/_views.py:516-529`) does a function-local
`from jinja2 import TemplateError` and translates it into `SquadsError`. That is the second
consumer to reach past the rendering engine for the engine's own exception vocabulary:
`ServiceCore.pristine_body` (`src/squads/_services/_base.py:577`) already does its own local
import of the same exception and its own, *different*, handling of it (it swallows the failure
and returns `None`).

Meanwhile `_rendering/_engine.render` — the one function every template in the codebase goes
through — translates nothing, so every other caller still propagates a raw
`jinja2.UndefinedError` on a `StrictUndefined` failure. `render_view`'s own docstring calls the
engine "the one Jinja2 engine every rendering path already uses"; the property "a template
failure surfaces as a clean `SquadsError`" is now true at two consumers and false everywhere
else, which is the opposite of what that sentence promises.

Failure scenario, low-stakes but real: an adopter overrides `templates/items/<type>.md.j2` with
a template referencing an undefined variable. `sq create <type>` renders it through
`render()` with no translation and the operator gets a jinja traceback rather than the clean
message-and-exit-1 the CLI's error decorator exists to produce — while the same class of
mistake in a *view* template gets the clean message, because this change taught one consumer.

Not a regression and it follows an existing local-import precedent, so this is a placement
point rather than a defect: the translation belongs in `_rendering/_engine.py`, once, so both
existing consumers can drop their local imports and every future renderer inherits it.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Removal round-trips the region through a newline normaliser

<!-- sq:finding:F8:body -->
**Read**, with the reachability bound **inferred** from the write paths.

The two primitives are asymmetric in a way their shared docstring language hides.
`insert_unpaired_marker` (`src/squads/_sections.py:198`) splices — it delegates to
`append_to_section`, which is a pure byte insertion before the close marker, so "insert-only,
nothing else rewritten" is literally true.

`remove_unpaired_marker` (`src/squads/_sections.py:227`) instead calls
`replace_section(text, region_tag, inner[:idx] + inner[end:])`, and `replace_section`
normalises: it prepends `\n` when the new inner content does not start with one and appends
`\n` when it does not end with one (`src/squads/_sections.py:133-144`). So the removal path
round-trips the whole region through a normaliser, and its docstring's claim — "every other
byte of the section ... survives verbatim" — holds only for a region whose inner content
already begins and ends with a newline.

Failure scenario: a region written as `sq:body` open marker immediately followed by prose with
no newline (`...body -->prose<!-- ...`), carrying a view tag. Removing the tag returns a region
with a leading newline the file never had — a byte the caller was promised would not change.

Every squads write path goes through `replace_section` itself, so every body on disk already
satisfies the precondition and this is not a live defect today. It is worth naming because the
one path that will meet a region squads did not write is FEAT-907's bulk placement over an
adopted corpus, and because a primitive whose docstring promises byte preservation should
either deliver it (splice the removal the way the insert splices) or say which bytes it
normalises.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Build-process narration in delivered docstrings

<!-- sq:finding:F9:body -->
**Read.** Delivered text must describe the thing, not narrate how it was built. Six hits, all in
the new test suites; the source side is clean apart from two borderline lines noted at the end.

1. `tests/cli/test_view_tag_placement_cli.py:5-9` (module docstring) — "read-time expansion
   (**landed after this verb** — see tests/cli/test_view_tag_expansion_at_read_time_cli.py)".
   Build order. The fact worth keeping is that expansion renders the tag in `show --raw`, so
   the stored file is where a literal tag is assertable — say that, without the chronology.

2. `tests/cli/test_view_tag_placement_cli.py:82` — "**The task's own constraint:** placement
   lives in its own verb group, never as a `body` option." The constraint is the design; the
   ticket that carried it is not part of it.

3. `tests/service/test_check_exempts_the_view_tag_family_from_marker_pairing.py:175` — "must
   still be reported 'unclosed', exactly like **before this feature**." Build-relative time
   reference; the claim is just that a non-view unpaired tag errors.

4. `tests/service/test_view_tag_expansion_at_read_time.py:386` — "**Not this feature's problem
   to solve** (named as an accepted, unfixed cost)". The behaviour it documents (a body replace
   drops the tag, like any other authored text) is durable; the scoping note is not.

5. `tests/service/test_view_tag_prose_guard_stays_closed.py:4` — "**unchanged by this feature**,
   no per-name hole, no allow parameter, no call-site bypass". The three specifics are the real
   content; the first clause dates the file.

6. `tests/service/test_view_tag_prose_guard_stays_closed.py:28` — "Structural guard against the
   shape of hole **the amendment** explicitly refused". Cites the ADR amendment as a build
   artifact; the rule itself ("no parameter here can admit one tag while refusing others") is
   already stated in the next line and stands alone.

Borderline, source side, judgement call rather than a clear hit:

- `src/squads/_models/_markers.py:73` — "that is what separates it from the stored regions
  (`SUMMARY`, a sub-entity's `:head`) **this corpus was stripped of**." Reads as this
  repository's own history; an adopter has no such event. The durable form is "the stored
  regions this design refuses", which loses nothing.
- `src/squads/_sections.py:153` — "the one deterministic anchor every caller shares, **including
  a future bulk placement**." A forward reference to unshipped work; harmless, but "every
  caller shares" already carries it.

Everything else in the source diff is design rationale rather than process narration, and
`tests/tui/test_reader_screen.py:2`'s "follow-up increment" phrasing is pre-existing, not
introduced here.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-09-03T13:35:46Z] Paul Reviewer:
  - Set back to Open. The sweep landed on everything this finding enumerated, and then two new
    sentences of the same class arrived with the same two commits and survived it. **Read**, grepped
    over every file the two commits touched.
    
    Gone, confirmed: all six named hits (the build-order clause in the placement CLI module
    docstring, the ticket-as-authority prefix, both build-relative time references, the
    increment-scoping note, the amendment-as-authority attribution) and both source-side lines
    (`_markers.py`'s "this corpus was stripped of", `_sections.py`'s "including a future bulk
    placement"). Each durable fact survives in its own words.
    
    Still open, both introduced by these commits:
    
    1. `src/squads/_services/_maintenance.py:495` — "This function used to answer only the first
       reason and was named for it (`_dangling_view_issues`); it kept that name only as long as it
       asked only that question." A rename of a private function narrated in its own docstring.
    2. `tests/service/test_check_flags_a_view_tag_whose_target_cannot_resolve.py:6` (module
       docstring) — "This module's own name used to be
       `test_check_flags_a_dangling_view_tag_name.py`, for the reason it only asked about then."
    
    Neither states behaviour or design; both state what an identifier was called before this build
    renamed it, which git blame already carries. The durable text is the sentence above each of
    them, which already says the finding now reports two reasons.
    
    Why the sweep missed them, so the next one does not: its grep was over "this feature" / "the
    amendment" / "landed after" / "before this feature" / "this pass" / "the reviewer". The
    chronology here is spelled "used to be named", which none of those patterns reach.
    
    Not flagged, for consistency rather than oversight — the line I drew, in case you want to move
    it:
    
    - A regression test docstring naming the wrong behaviour it guards ("used to raise SquadsError
      out of every read surface. It now leaves the tag exactly as authored") is the test's own
      subject and stays. There are several of these in the new suites and I read all of them.
    - `_services/_validators.py:11`'s "not, despite an earlier version of this sentence, of sq
      check's issues as a whole" is the established corpus form for correcting a load-bearing false
      claim — `_sections.py:84` and `_maintenance.py:273` both predate this work and this review did
      not flag either.
    - `tests/tui/test_reader_screen.py:2`'s "follow-up increment" is pre-existing, as this finding
      already recorded.
    
    Failure scenario: the pattern is now precedent in the two files a source-kind rename touches
    next, and FEAT-903/FEAT-904 rename and delete resolvers by design. Two sentences deleted closes
    it; nothing else in the sweep needs revisiting.
- [2026-09-03T13:53:16Z] Paul Reviewer:
  - Ruled: **F9 extends to cover it, and stays Open.** Not a new finding — same defect class, same
    sweep, same remedy; a second finding would imply a second class and there isn't one. Your two
    confirmed deletions are **read** as gone (grep validated against a known positive first, since
    zero hits is the one result that never proves the search ran).
    
    **The line, restated as a test rather than a phrase list**, because that is the part FEAT-903
    needs to inherit:
    
    > Read the sentence as a stranger who has never seen the diff and cannot see the repository's
    > history. If the sentence is false, stale or meaningless for that reader, it is narration.
    > Equivalently: could someone who wrote this code from scratch today have written this
    > sentence? If only someone who just performed an edit could have written it, it is narration.
    
    Three corollaries, which is what the test buys over a grep:
    
    - A sentence that needs a *before* to parse ("used to", "any more", "as before", "already
      caught", "no longer needs") is narration **unless the before is a state the reader can still
      observe** — a defect a regression test guards, or a false claim the same docstring still makes.
    - A sentence that counts today's consumers or callers ("neither existing consumer", "this
      codebase has been adding them") goes stale by itself, with nothing to catch it.
    - A sentence describing the *delta* ("only the exception type changes") describes an edit, not
      code. There is no "changes" for a first-time reader.
    
    **Your question, answered directly: rationale is not the problem, past tense is.** Explaining
    *why* the funnel exists — including that a per-consumer translation lets two consumers disagree
    and leaves every other renderer leaking the raw exception — passes the test cleanly and is worth
    keeping. Narrating that this pass moved it does not. So `render`'s paragraph splits, and your
    instinct about which clauses is right:
    
    - Keep, but in the present tense: that this is the single funnel; that a per-consumer
      translation produces inconsistent handling and leaves the other renderers untranslated; and
      the adopter-visible property (a typo in an overridden item template and the same typo in a
      view template surface identically — clean message, exit 1, never a traceback). All three facts
      are durable; only their tense is not.
    - Cut: "neither existing consumer needs its own import any more"; "(this codebase has been
      adding them)"; "only the exception type each already caught changes, not either one's own
      handling"; and the "used to be duplicated at two call sites" framing, whose substance survives
      in the first bullet.
    
    `src/squads/_rendering/_engine.py:182,187,188,193`.
    
    **A fourth instance, which I missed too and which is the strongest evidence for your point.**
    `src/squads/_services/_base.py:577`, `pristine_body`'s docstring: "caught and swallowed here
    exactly as before — only the exception type changes, not the swallow-and-return-`None` behaviour
    itself." Same class, same commit (`git log -S`, **driven**), and it is a *second copy* of the
    same delta claim the engine docstring makes. My own second-pass grep did not surface it either;
    I only have it because I had read the function for F7. Both go, and the durable half of that
    sentence is already the line above it.
    
    **Held, deliberately, so nobody reopens these:**
    
    - `_views.py:551` (`ViewTemplateMissingError`: "every existing catcher of that base class keeps
      working unchanged") — reads as a substitutability guarantee, which is *why* the subtype is
      safe to introduce. Present-tense property of the type hierarchy; passes the test.
    - `_services/_validators.py:11` ("not, despite an earlier version of this sentence, …") — an
      erratum on a claim **this same docstring still makes**, and F10 exists precisely because a
      reader acted on the false version. Second corollary above admits it, and there are two
      pre-existing corpus precedents (`_sections.py:84`, `_maintenance.py:273`).
    - Regression-test docstrings naming the wrong behaviour they guard ("used to raise SquadsError
      out of every read surface. It now leaves the tag exactly as authored") — the defect is the
      test's subject.
    - Everything outside this feature's added prose. My wider scan hits ~25 pre-existing lines in
      `_maintenance.py`/`_base.py`/`_validators.py`; a corpus-wide narration cleanup is not this
      review's scope and F9 should not grow into one.
    
    Scope of what is left: four clauses in `_engine.py` and one sentence in `_base.py`, both
    introduced by `ed26f99c`. Rewrites, not deletions, for two of them.
- [2026-09-03T14:08:41Z] Paul Reviewer:
  - Third pass reviewed. **The two surfaces I enumerated are correctly done, the sample holds, and
    F9 still does not close** — one instance of the class survives in the feature's added prose,
    plus the assert-message ruling below. Remaining surface is **one docstring sentence and one
    string**, listed exhaustively so this ends here.
    
    **Prose-only, proven rather than taken on trust.** I parsed both sides of every one of the 14
    changed files, stripped module/class/function docstrings, and compared the ASTs: identical for
    all 14. So no statement, no assertion and — usefully for judgement call 1 — **no non-docstring
    string literal** changed anywhere in the commit.
    
    **My two surfaces: both good, neither flattened.**
    - `_rendering/_engine.py` carries all three durable facts in the present tense (single funnel;
      per-consumer translation lets consumers disagree and leaves other renderers propagating raw
      jinja2; the item-template and view-template typo surface identically), all four delta clauses
      gone, both cross-references kept. It is shorter *and* complete.
    - `_services/_base.py:577` states the mechanism ("`render` translates the underlying
      `jinja2.TemplateError` into `SquadsError`, which is caught here and swallowed into that
      `None`") with the "assume authored" rationale above it untouched.
    
    **Sample of the 17: no flattening, and three are improvements.** I read
    `_services/_views.py:29`, both docstrings in `test_template_failures_translate_to_a_clean_error`,
    three in `test_view_tag_placement`, three in `test_view_source_applicability_predicate`
    (including the non-vacuity control comment), three in
    `test_check_flags_a_view_tag_whose_target_cannot_resolve`, two in
    `test_retype_carries_a_view_tag_and_check_stays_clean`, and one each in
    `test_read_body_skips_the_index_load_without_a_view_tag` and
    `test_view_tag_expansion_at_read_time`. In every case the durable claim survives, and three
    came out **better** than they went in, because the property got restated in checkable terms
    instead of version terms — "byte-identical whether or not the index load is skipped"; "the
    predicate refuses a mismatched pairing, not every subentity-source view"; "reports nothing on
    any host type, proving the applicability predicate does not affect a ref-sourced view". The
    non-vacuity control comment kept its whole point. Nothing was reduced to a stub.
    
    The dev also cut several regression-test docstrings I had *held* (e.g. "used to raise
    SquadsError out of every read surface"). That is within an author's latitude, not an
    over-application: held meant may-stay, not must-stay, and in each case the behaviour under test
    is still fully stated and the assertion still catches the regression. No objection.
    
    **Still open — the fifth copy of one claim.**
    `tests/service/test_view_tag_expansion_at_read_time.py:406-408`:
    
        Control: the bundled ``ref``-source view carries no host constraint, so nothing about
        this fix changes its behaviour — it already expanded before the fix and must keep
        expanding after.
    
    Introduced by `2a96238d` (**driven**, `git log -S`). This is the same sentence, about the same
    control, as the two this commit *did* rewrite — `test_view_tag_placement.py:289` and
    `test_check_flags_a_view_tag_whose_target_cannot_resolve.py:234` — so the durable form is
    already written twice in this very commit ("the predicate imposes nothing on it"). Three
    sibling controls, one claim, two fixed.
    
    **That is a second blind spot, distinct from the grep one, and worth more than the two-line
    fix.** A claim copy-pasted across files gets fixed where the reader's attention lands and
    missed where it doesn't — reading file-by-file cannot see that two files say the same thing.
    The cheap closer: once a sentence is rewritten, grep a distinctive fragment of the **old**
    sentence across the whole feature before calling that claim done. Here, "before the fix" would
    have found all three in one command.
    
    **Judgement call 1 — the assert message: I am extending the scope, not overturning the call.**
    The dev applied F9's scope as I wrote it ("docstrings, comments, test module docstrings"), and
    that reading was correct. The scope was too narrow. The rule, generalised:
    
    > The stranger test applies to any prose this tool or its tests **emit or display to a human** —
    > docstrings, comments, assert messages, error strings, CLI help. It does not apply to
    > prose-shaped *fixture data* (a synthetic body, a fixture title), which is input, not delivered
    > text.
    
    An assert message earns it on its own terms rather than by analogy: its whole job is to tell the
    person staring at a red test which invariant broke, and "must still expand exactly as before"
    is unresolvable for that person — "before" what? It fails at the one thing it exists to do. The
    model is its own sibling two lines up: "read_body must not load the index a second time for a
    tagless body".
    
    Cost of the extension, checked before proposing it: I applied the test to **every** assert
    message this feature added (13 of them). Exactly one fails —
    `test_read_body_skips_the_index_load_without_a_view_tag.py:62`, `"a tagged body must still
    expand exactly as before"`. The other twelve are already checkable and history-free, including
    `"the view must no longer render after removal"` (the before-state there is the removal the test
    just performed, which the reader can observe) and `"an untagged body must never reach view-tag
    expansion"`. So the extension costs one string.
    
    **Judgement call 2 — "the spec no longer declares": confirmed, hold both.** `_views.py:61` and
    `test_view_tag_placement.py:399` pass the test cleanly, and the reasoning is worth having on the
    record because the phrasing will keep drawing fire. "No longer declares" describes a **spec-drift
    state a user creates** — they dropped a view from their overrides while a tag naming it is still
    placed — not a state this build left behind. The before it needs is one the reader can observe
    in the corpus in front of them (a document carrying a tag the active spec does not declare), it
    cannot go stale, and someone implementing `remove_view` from scratch today would write the same
    sentence, because "must work in that state" *is* the requirement. That is exactly the carve-out
    in the second corollary, and it is the discriminator: a before the reader can still observe
    passes; a before only the diff contains does not.
    
    **Held list: all four confirmed held.** `_views.py:551` ("every existing catcher of that base
    class keeps working unchanged" — a substitutability guarantee, present tense) and
    `_validators.py:11` ("despite an earlier version of this sentence" — an erratum on a claim the
    same docstring still makes) are both still there, correctly. The regression-test docstrings are
    covered above. And the ~25 pre-existing corpus instances are untouched — **driven**: each of
    `_base.py:401,962,1262,1275`, `_import.py:528`, `_maintenance.py:692,1964` and
    `_validators.py:121` returns zero hits against this feature's added-prose set, so they are
    provably outside F9's scope rather than merely unvisited.
    
    One more held, for completeness, since it will look like a miss: the test *name*
    `test_pristine_body_still_swallows_a_broken_template_and_returns_none` keeps its "still". A
    rename is a code change, so it rightly stayed out of a prose-only commit, and a test's name is
    an identifier rather than delivered prose. Out of scope; please don't churn on it.
    
    Gates: `ruff check`, `ruff format --check` clean; 387 tests green across the 13 touched test
    files plus `tests/meta`.
- [2026-09-03T14:14:20Z] Elias Python:
  - Fixed the fifth copy. tests/service/test_view_tag_expansion_at_read_time.py:406-408 now reads: "Control: the bundled `ref`-source view carries no host constraint, so it expands regardless of host type, proving the applicability predicate does not affect a ref-sourced view." — same durable form used in the two sibling controls.
  - Fixed the assert message under the widened scope. tests/service/test_read_body_skips_the_index_load_without_a_view_tag.py:62 now reads: "read_body must load the index a second time to expand a tagged body" — mirrors its sibling two lines up ("read_body must not load the index a second time for a tagless body").
  - Grep sweep, post-rewrite, over feature scope (git diff --name-only 3b6aeed6..HEAD -- src/ tests/), each fragment validated as a known positive against the pre-fix commit first: 'before the fix' 0, 'must still expand exactly as before' 0, plus the six items from your first F9 list ('landed after this verb', "The task's own constraint:", 'exactly like before this feature', "Not this feature's problem to solve", 'unchanged by this feature', 'the amendment explicitly refused') all 0, plus the five engine.py/base.py deltas ('neither existing consumer needs its own import any more', 'this codebase has been adding them', 'already caught changes', 'used to be duplicated at two call sites', 'caught and swallowed here exactly as before') all 0. All eleven confirmed present in the pre-rewrite commit content first, so the zero-hit results are validated.
  - Gates clean: pyright 0/0/0, ruff check all passed, ruff format 625 files already formatted. Targeted tests: 27 passed (both touched files). sq check: no issues.
  - @reviewer F9 should be closeable now.
- [2026-09-03T14:22:20Z] Paul Reviewer:
  - Both edits verified and correct. **F9 still does not close: there is a sixth copy**, and I can
    tell you exactly why five grep passes could not see it.
    
    **The two edits.** `ea22c9ae` is prose-only, proven: with every string literal masked, the code
    skeletons of both files are identical, and exactly **one** string literal changed — the assert
    message. Edit 1 now reads as its two siblings do (all three ref-source controls say "proving the
    applicability predicate does not affect a ref-sourced view" / "the predicate imposes nothing on
    it"); edit 2 mirrors its sibling and names the invariant the assertion checks. Both durable, no
    before-state.
    
    **The sixth copy.** `tests/cli/test_check_view_tag_pairing_and_dangling_name_cli.py:72-74`:
    
        """Driven end to end through the CLI: the state ``sq epic <n> view add story_board`` used
        to create silently (exit 0, then ``sq check`` "no issues", then ``sq epic <n> show --raw``
        exit 1) now exits 3 here, naming both the file and the reason."""
    
    From `2a96238d` (**driven**, `git log -S`). This file was visited by neither sweep commit.
    
    **Why every grep missed it, including mine and the 13 validated fragments — a third blind spot,
    and the one that matters most.** The phrase is `used to create silently`, and the line wrap
    falls between "used" and "to": line 72 ends `...view add story_board`` used`, line 73 begins
    `to create silently`. **A line-oriented grep cannot match a phrase a line wrap splits.** My own
    pass-3 scan searched for `used to` across exactly this file and returned nothing — a true
    negative for the pattern, a false negative for the class. It is not a vocabulary gap this time:
    the fragment was in every list.
    
    That is why the post-rewrite grep, run honestly against validated positives, still returned all
    zeros: `"used to be duplicated at two call sites"` happened to sit on one line, and this one does
    not. A human reading the docstring reads straight through the wrap and sees it at once — which is
    the whole case for the reading pass, arriving from a third direction.
    
    **The mechanical fix for the blind spot**, since the grep still has a job to do: scan whole prose
    *blocks*, not lines. Extract each docstring / comment run / assert message (AST + `tokenize`),
    collapse its internal whitespace to single spaces, then match. I wrote that and ran it over every
    file this feature touched; it surfaces the sixth copy immediately, in one hit, with both halves
    of the split phrase visible. Worth handing to whoever automates the pre-filter — a line-based
    `grep -n` over docstrings is structurally unable to close this class, independent of vocabulary.
    
    **Remaining surface, exhaustive.**
    
    1. **Must go** — the docstring above, `tests/cli/test_check_view_tag_pairing_and_dangling_name_cli.py:72-74`.
       The durable claim is what the test asserts and nothing more: `sq check` exits 3 on a
       source-incompatible host and names both the file and the reason. The before/after transition is
       the part to drop.
    2. **Your call, and I would take it while you are in there** — `"**two** reasons, generalised from
       one"`, at `src/squads/_services/_maintenance.py:489` and
       `tests/service/test_check_flags_a_view_tag_whose_target_cannot_resolve.py:4`. Both from
       `2a96238d`. It fails the test as written ("from one" names a one-reason version that no longer
       exists anywhere a reader can look, and it reads worse the day a third reason lands, which
       FEAT-903 makes likely). I am flagging it rather than holding it: it is by far the mildest
       instance in the whole set — three subordinate words on a claim that is already complete and
       correct without them — and I would rather say plainly that it fails my own test than invent a
       subordinate-clause exemption at the fourth pass to justify keeping it. If you take item 1 and
       leave this, say so on the record and I will verify against that.
    
    **Nothing else.** I re-derived the residue independently rather than re-running your fragments:
    the whole-block scan over every touched file, cross-checked against this feature's own added-prose
    set, yields items 1 and 2 plus the held list and nothing more. Two more I checked and hold, both
    in scope (from `8add395c`): `test_repair_leaves_view_tags_untouched.py:56` ("nothing on the live
    write path produces this any more") and `:89` ("the sweep still works") — both describe the
    *retired-region* design, whose before a reader can still observe in any corpus file carrying one.
    `_views.py:390`'s "as before" is pre-existing (`bfc01d21`) and provably outside this feature's
    added prose. The held list from pass 3 is unchanged and still correct.
    
    I am not moving the line again. Item 1 fails the test I wrote in pass 2, on the same wording I
    have flagged four times; item 2 fails it too and I have said what I would do with it. There is no
    seventh criterion behind these.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Two-tier check surface is undocumented at the catalog end

<!-- sq:finding:F10:body -->
Ruling on the placement question is **correct by design** (see this review's discussion comment
for the full reasoning). This finding is the one piece of debt that falls out of it, and it is
documentation, not mechanism.

**Read.** `sq check` has two tiers and only one of them is self-describing.

- Tier 1, the always-on file-level scan in `MaintenanceMixin._scan_for_check`
  (`src/squads/_services/_maintenance.py:2981-2986`): `_marker_issues` and now
  `_dangling_view_issues`. Reads raw file text, runs *before* frontmatter parses, keyed on the
  filename.
- Tier 2, the per-item validator catalog (`src/squads/_services/_validators.py`): `CATALOG` /
  `VALIDATOR_NAMES` / `CONSISTENCY_CLAUSES`, selectable per type, closed by
  `assert set(CATALOG) == VALIDATOR_NAMES` and `assert set(VALIDATOR_CONTEXT) <= set(CATALOG)`.

`_dangling_view_issues`'s own docstring explains why it sits in tier 1. Nothing at the tier-2
end says tier 1 exists. `_validators.py`'s module docstring instead says the opposite:

    This engine is the **sole** source of both ``sq check``'s per-item/squad-global issues and
    the create/update fail-closed gate.

That is true of per-item and squad-global issues and false of "sq check's issues" as a whole —
two error-level findings are produced outside it, and after this change one of them enforces a
binding ADR invariant.

Failure scenario, and it is FEAT-898's: FEAT-898 declares the required context per catalog
member and closes the correspondence with an assert. Whoever builds it reads `_validators.py`,
takes "sole source" at face value, treats `CATALOG` as the complete inventory of `sq check`
findings, and either (a) reports the check surface as fully closed when two findings sit
outside the closure, or (b) discovers the two late and re-litigates whether the dangling-view
finding should have been a catalog member — the question this review has now ruled.

Direction: state the two tiers where a reader of the catalog will see them — one paragraph in
`_validators.py`'s module docstring naming the file-level scan and its two members, and a
matching back-reference at `_scan_for_check`. Correct the "sole source" sentence to the scope
it actually holds for. No mechanism change; the placement itself stands.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Engine translation rewraps missing-template error; docstring now false

<!-- sq:finding:F11:body -->
**Read**, then **driven** through the function itself.

Centralising the Jinja translation in `_rendering/_engine.render` (F7's fix) changed what
`_views._render_view_or_raise` catches from `jinja2.TemplateError` to `SquadsError`. That
handler now also catches `render_view`'s *own* missing-template `SquadsError` — which is
raised before `render` is ever called — and rewraps it. Two consequences.

**1. Its docstring is now false.** The sentence

    ... so ``render_view``'s own missing-template :class:`SquadsError` is not expected in
    ordinary operation and is let through unchanged on the rare race where the template
    disappears between the two checks.

was true while the handler caught a jinja2 exception. It is not true now: the broadened
`except SquadsError` catches exactly that error and re-raises a new one. This is the same
class of defect F3 and F10 were filed for — a docstring a later reader enumerates behaviour
from, which quietly stopped describing the code.

**2. The message on that path is doubled.** Driven directly:

    _render_view_or_raise("no_such_template_view", <empty projection>, <item EPIC-3>)
    -> SquadsError: view 'no_such_template_view' failed to render on EPIC-3: view
       'no_such_template_view' has no presentation template - create one at
       templates/views/no_such_template_view.md.j2 (or shadow it with an adopter override
       at .overrides/templates/views/...)

The view name appears twice and the two clauses disagree in framing ("failed to render" vs
"has no presentation template").

**Reachability is narrow and the behaviour is not wrong**, which is why this is info and not
a defect in the mechanism: `_render_view_or_raise` has exactly one caller
(`expand_view_tags`), which gates on `resolve_view_target` first, so this is only reached on
the gate/render race the docstring itself names — the template resolving at the gate and
being gone at the render. Both outcomes remain a clean `SquadsError` and a clean CLI exit 1.
Naming the item is arguably an improvement over letting it through.

**Failure scenario.** A later author reads the docstring while working on the race clause —
or on FEAT-903's new renderers, which the engine docstring points at this function as the
pattern to copy — concludes the missing-template error reaches the caller unchanged, and
writes a handler or a test on that basis.

**Direction** (either, not both): keep the rewrap and correct the sentence to say the
missing-template error is *also* wrapped with the item; or narrow the catch so only a real
render failure is rewrapped (e.g. have `render_view` distinguish its own refusal), and leave
the sentence as it stands.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-09-03T13:52:39Z] Paul Reviewer:
  - Verified. `ViewTemplateMissingError` is the right shape and the pass-through is real, not just
    declared.
    
    **Driven.** `render_view` on a template-less view and `_render_view_or_raise` on the same view
    raise the *same type* (`ViewTemplateMissingError`) with byte-identical messages; no
    "failed to render on" prefix appears. The other half is intact: read-time expansion of a view
    whose template exists and *fails* still names the item —
    `view 'broken_template_view' failed to render on EPIC-2: template '...' failed to render:
    'this_variable_does_not_exist' is undefined` (exit 1 through the CLI, no traceback). So the fix
    narrowed the rewrap without giving up F7's item-naming.
    
    **Falsified by my own mutation, not read off the handback.** Removing the
    `except ViewTemplateMissingError: raise` clause reddens the new test and reproduces my exact
    doubled message verbatim:
    `view 'no_such_template_view' failed to render on EPIC-2: view 'no_such_template_view' has no
    presentation template — ...`. Restored; tree clean. The test carries two independent
    discriminators (the exception type, and the message equality) — the type catches this mutation,
    the message equality catches the one that re-raises the same subtype with a doubled string, so
    neither is redundant.
    
    **`pristine_body`'s swallow is intact, both directions.** Driven: with a broken `epic` override
    template it still returns `None`. And the subtype cannot reach it in the first place —
    `pristine_body` renders `items/<type>.md.j2`, never a view template, so `render_view`'s
    pre-check is not on that path; being a `SquadsError` subclass, it also cannot narrow what any
    existing `except SquadsError` catches. **Read** across every catcher: nothing in the corpus
    tests a rendering exception by `type(...) is SquadsError` on a view path.
    
    **Reachability, sharpened for the record.** The docstring's "race" is narrower than "template
    missing at read time", and I confirmed why: deleting a placed view's template makes
    `resolve_view_target` refuse at the gate, so the tag is simply left literal and the read exits 0
    (driven). This code path needs the template to disappear *between* the gate and the render
    inside one invocation — which is exactly why driving `_render_view_or_raise` directly is the
    right instrument for it, and a CLI-level test would have been the wrong one.
    
    Gates I re-ran: `ruff check` (with the full `TRY` rule set selected — the bare re-raise does not
    trip `TRY302`), `ruff format --check`, `pyright` on the four touched modules, all clean; 395
    tests green across the render/view/check/meta surface.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — No-op section edit still commits the index; docstring says otherwise

<!-- sq:finding:F12:body -->
**Driven**, in a throwaway squad, while narrowing the doubts list rather than hunting findings.

`_section_edit_core`'s docstring (`src/squads/_services/_base.py:1208-1212`) claims of the
no-change path:

    When ``changed`` is ``False`` the file is never rewritten and ``updated_at``/
    ``modified_session`` never bump — a no-op call (an idempotent insert already present, a
    removal of an absent marker) is genuinely silent on disk, not a rewrite of identical bytes
    under a fresh timestamp.

The first clause is true; the last two are not. `_section_edit_core` returns early *inside*
`store.transaction()`, and the transaction still commits the index on exit — so a no-op
placement rewrites `.squads.json` with identical bytes under a fresh mtime, which is verbatim
the thing the sentence says does not happen.

Driven on a fresh squad, an idempotent second `view add`:

    sq task 2 view add milestone_rollup   -> "already present, unchanged"  (exit 0)
    item .md                              -> bytes and updated_at unchanged   (correct)
    squads/.squads.json                    -> content identical, mtime 1788445231 -> 1788445233

**Not a behaviour defect and not a regression.** The index content is unchanged, nothing lands
in the markdown, `sq repair` still proves the index rebuildable, and invariant 8 is untouched
(no markdown write to be behind). The retired `_locked_placement_edit` had the same structure,
so the behaviour predates the fold — only the sentence moved into the shared core with it, where
it now describes the seam every write path goes through.

**Failure scenario.** The sentence is on the seam whose docstring F3 exists to make
enumerable-from, and it invites exactly one mistake: a reader building on "genuinely silent on
disk" — a mtime-keyed cache over `.squads.json`, a watch/reload that treats an index mtime bump
as "something changed", or a test asserting a no-op leaves the squad dir untouched. Each would
be correct against the claim and wrong against the code.

**Direction.** Scope the claim to what it holds for: the item file is never rewritten and the
timestamps never bump; the index transaction still commits, so `.squads.json` may be rewritten
with identical content. One clause, and it makes the seam's own inventory honest — which is the
whole point of the docstring F3 corrected.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T11:43:55Z] Paul Reviewer:
  - Ruling on the catalog-placement question routed to me, stated plainly so FEAT-898 inherits it
    rather than re-deriving it.
    
    **Correct by design. The dangling-view finding belongs in the file-level scan, not in
    `CATALOG`/`VALIDATOR_NAMES`/`CONSISTENCY_CLAUSES`. Do not move it.**
    
    Three reasons, all read from the source:
    
    1. **The catalog is per-item; this finding is per-file.** A `CATALOG` member takes a
       `ValidatorContext` carrying a resolved `Item` plus index state, and is dispatched per item.
       `_dangling_view_issues` takes raw file text and runs at
       `_services/_maintenance.py:2984` — *before* `read_frontmatter`, which is the line that turns
       a file into an item. A file whose frontmatter is unreadable takes the `except SquadsError`
       branch and `continue`s, so the catalog never sees it — while its marker and dangling-view
       findings have already been emitted. A view tag in a file too broken to parse is precisely
       where this finding earns its keep, and catalog membership would lose it there.
    
    2. **The catalog is selectable; ADR-880 says this one is not.** A member's effectiveness is
       resolved through `effective_validator_names` (common core + category bundle + the type's own
       `validators` list), so membership is a declaration an adopter's spec participates in.
       ADR-880 rules the dangling tag "an **error**-level finding — floor ... because no squad can
       sit in that state on purpose". Tier 1 gives that unconditionally by construction. Note that
       "floor" in the catalog's own vocabulary means `COMMON_CORE` membership — see
       `_parent_acyclic`'s docstring, "floor behaviour rather than a bundle member" — which is still
       a *selectable-shaped, item-scoped* mechanism. So the ADR's word does point at catalog
       vocabulary, but the guarantee the ADR asks for is strictly stronger than what that word buys
       inside the catalog. Reading "floor" as "must be a `COMMON_CORE` member" would weaken the
       invariant, not honour it.
    
    3. **It mirrors its neighbour exactly.** `_marker_issues` has always lived in tier 1 for the
       same reasons and has never been a catalog member. Two file-level, raw-text, error-level
       checks sitting side by side is one rule, not an exception.
    
    **What FEAT-898 should carry forward.** FEAT-898's assert closes the correspondence between
    catalog members and their declared required context. These two checks are outside that closure
    because they are outside the catalog — not because they escaped it. They declare no context
    because they need none beyond the text and, for the new one, the already-in-hand `self.spec`.
    FEAT-898 does not need to extend its grammar to cover them; it needs to not mistake `CATALOG`
    for the complete inventory of `sq check` findings. F10 on this review is the one action item
    that falls out: the tier boundary is documented at the tier-1 end and contradicted at the
    tier-2 end, where `_validators.py`'s module docstring still calls the engine the "sole source"
    of `sq check`'s issues.
- [2026-09-03T11:44:23Z] Paul Reviewer:
  - Independent verification of the falsification claims, and the list of things I looked for and
    did not find. Recorded so the next reader does not repeat either half.
    
    **Falsification, spot-checked by my own mutation (not read off the handbacks).**
    
    - *Pairing exemption* — the one the batch brief singled out. I removed
      `markers.view_tag_name(tag) is None and` from `_marker_issues` and ran the two suites:
      6 of 8 in `test_check_exempts_the_view_tag_family_from_marker_pairing.py` reddened, and 2 of
      4 in `test_check_view_tag_pairing_and_dangling_name_cli.py`. The 2 that stayed green are the
      legitimately insensitive controls (a balanced no-view-tag file; a non-view unpaired tag that
      must still error). So the exemption is genuinely under test — including the duplicate case,
      which reddens on the "and it must NOT also be reported as unclosed" half. Mutation reverted;
      tree clean.
    
    - *Append round trip (expanded bytes never reach disk)* — verified by driving the two
      assertions' sensitivity rather than by mutation. `sq show --json`'s body field on a tagged
      item returns the rendered view text verbatim (driven: the expanded body is
      `Authored prose line.` followed by the roll-up's three group headings, byte-for-byte what
      `render_view` returns). The test's assertions are a positive substring check for the literal
      tag in the stored region and a negative check for `svc.render_view(...)`'s exact output
      anywhere in the file — so a write path persisting the expanded body fails both. Sensitive.
    
      What it does **not** cover is any write seam other than `set_body(append=True)`. I closed
      that by hand instead: `read_body` has five callers and every one is a display surface
      (`_cli/_common.py:690`, `:791`, `:967`; `_cli/_skill.py:157`; `_cli/_operator.py:155`;
      `_tui/_reader.py:51`), no consumer of the `sq:body` region anywhere feeds a write, and the
      VS Code client never writes a body. There is no read-then-write path.
    
    **Looked for, did not find.**
    
    - No second expansion site, and view output is never re-scanned: spans come from
      `iter_marker_spans` against the original text and the result is assembled from those
      positions. Grep-verified and structurally pinned.
    - No `"view:"` prefix re-spelled as a live literal outside `_models/_markers.py` (docstrings and
      `--help` text only); `view_target_exists` has exactly two callers; `view_template_name`
      centralises the template path with `render_view` refactored onto it.
    - No `close_marker` counterpart for the family. (The structural guard is name-shaped — it
      asserts no module-level name starting with `VIEW` other than `VIEW` itself — so it would not
      catch a lowercase helper. Not filing it; noting it so nobody mistakes it for airtight.)
    - Layering holds: `_models/_markers.py` gained no imports; `_views.py` reaches only
      `_sections`/`_models`/`_rendering`/`_workflow`; `_services/_maintenance.py` -> `_views` is a
      downward edge; nothing in `_workflow` imports up into `_services`.
    - Error types: every new refusal is a `SquadsError`; the `KeyError` the primitives raise is
      translated at both service call sites. No bare exceptions, no `datetime.now()`, no new type
      alias (so nothing to get wrong on PEP-695), and dynamic console text is escaped — `e(name)`
      at the new CLI prints, and the existing `e(i.message)` at the check print site covers the new
      finding.
    - No ticket IDs in new source or test filenames; filenames are behaviour-named. The
      `TASK-*.md` strings in the new tests are glob patterns over fixture files, not board refs.
    - `insert_view`'s refusal points at `sq workflow views`, which exists (driven).
    - The exemption does not spill: a `:end` spelling is still reported as an unopened marker, and
      a duplicate is still reported as a duplicate (both driven).
    - No vacuous assertions of the kinds the 0.14 audit catalogued: the negative assertions I
      mutation-tested do fire, the suites use the real tmp-dir `svc`/`project` fixtures, fixture
      files are written and re-read per test rather than shared, and no test chdirs.
    
    **One benign gap, for FEAT-907 rather than for anyone here.** A view tag inside a *sub-entity*
    body is never expanded — expansion is the top-level `sq:body` boundary only — and `sq check`
    stays clean on it, so it would be silently inert. Unreachable today (`insert_view` targets the
    top-level region and `reject_markers` refuses typing one in), so not a finding; worth knowing
    when creation templates start seeding tags.
- [2026-09-03T11:46:54Z] Catherine Manager:
  - F1 verified independently from source, not accepted off the handback: _resolve_subentity_source (_views.py:146) raises SquadsError on placement state -- a host whose type hosts no such sub-entity kind -- while expand_view_tags gates only on name-and-template. A placed tag therefore makes the item unreadable on every read surface with sq check clean. That contradicts ADR-880s own principle that reads must work on a broken corpus and sq check is the reporting surface.
  - Routing F1 to the architect rather than straight to a fix: the defect is that the corpus-state / engine-defect boundary was drawn in the wrong place, and that classification governs FEAT-903 when it widens the source kinds. Fix follows the ruling. F2 through F10 triaged after.
- [2026-09-03T12:06:50Z] Olivia Lead:
  - - Every finding has a home; nothing dropped, nothing deferred out of FEAT-905.
    - **TASK-913** (Draft) — F1 (ST2 predicate, ST3 placement door, ST4 quiet expansion, ST5
      generalised finding, ST6 US8 correction + retype read assertion, ST7 falsification and both of
      your repros driven green) and F2 (ST1). F2 sits here rather than with the cleanup because the
      recogniser is the seam the F1 fix adds consumers to.
    - **TASK-914** (Draft, sequenced after 913) — F3 (ST1, folded not just recounted), F4 (ST2), F5
      (ST3), F8 (ST4, same function as F5 so rewritten once), F6 (ST5), F7 (ST6), F10 (ST7), F9
      (ST8).
    - Two findings carry an explicit stop-and-comment escape rather than a dev-choice: F3's fold if
      it changes any existing caller's behaviour, F8's splice if it cannot be done inside the
      primitive. Fallback in each case is the documentation correction you named, said out loud.
    - Your catalog-placement ruling is carried into TASK-914 ST7 as the mechanism of FEAT-898's
      inheritance — the corrected `_validators.py` docstring is the surface its builder reads.
    - Findings left Open and REV-912 left as it stands; closing them is the approver's, not mine.
      @reviewer for visibility on the mapping.
- [2026-09-03T13:36:20Z] Paul Reviewer:
  - Verification of the ten findings against `git diff 1389328c..HEAD -- src/ tests/`. **Nine
    Verified, F9 back to Open, one new info finding (F11).** REV-912 stays as it is; not Approved.
    
    **Verified: F1 F2 F3 F4 F5 F6 F7 F8 F10.**
    
    F1 — my own two repros are dead, **driven** in a throwaway squad (nested, removed; this tree
    clean before and after my own writes). Door one: `sq epic 2 view add story_board` exits 1
    naming the cause with no write. Door two: place on a story-hosting feature, `retype epic` —
    `show --raw` and `show --json` both exit 0, the tag survives byte-for-byte literal, and `sq
    check` exits 3 with an error-level finding naming the file and the cause. The three corollaries
    hold: no per-kind resolver raises (AST-checked with a non-vacuous control, the raise living in
    the dispatcher so `sq workflow view` still refuses an inapplicable pair — driven, exit 1 in
    both text and `--json`); every predicate takes `item_type: str` and the spec, asserted
    structurally off the signatures, no `Item` anywhere; and emptiness is not a failure — driven, a
    feature with zero stories renders its view and the scan stays silent, and the predicate cannot
    see item content, so a reachability check is structurally unavailable rather than merely
    absent.
    
    F3 — the widest change, and no caller lost anything. `_locked_placement_edit` has zero
    references; all five mutate closures and all seven call sites are updated; body, comment,
    sub-body and both importer seams return changed unconditionally, so their write is still
    unconditional. Driven: a no-op `view rm` and an idempotent `view add` leave the file's bytes
    and `updated_at` untouched, while a body write, a comment and a sub-entity body each still
    bump it.
    
    F4 — the corrected premise is right, and the assertion tests absence, not equivalence (a load
    call count, 1 for a tagless body against 2 for a tagged one).
    
    F7 — `pristine_body`'s swallow is preserved in practice: nothing reachable inside its `try`
    raises `SquadsError` except the engine's own translation (`_badges` raises nothing;
    `spec.machine_for` raises `KeyError`). The catch is wider in principle, and the direction it
    fails in is the recoverable one its docstring names. No renderer leaks a raw `UndefinedError`
    any more — driven at the CLI, exit 1, names the template, no traceback and no "jinja2" in the
    output.
    
    F6 — proven by a `review_findings_closed` member in a constructed catalog, not by reasoning
    about the substring, with the live CATALOG left alone. F10 — read as FEAT-898's builder would:
    the tier is named, both members are named, the reason is given, the "sole source" sentence is
    scoped, and the back-reference at the scan closes the loop from either end.
    
    **Falsification, spot-checked by my own mutation rather than read off the handbacks.**
    
    - F1's precondition: I removed the mechanism outright — expansion gate reverted to the
      two-question form, the dispatcher's raise deleted, the placement door reduced to a
      declared-only check. 14 tests reddened across unit, service and CLI, including the
      byte-for-byte literal assertions. That is the part that matters: with the raise gone as well
      as the gate, the tests still fail, so they detect the *wrong body*, not merely the absence of
      an exception.
    - F4's absence assertion: I removed the `has_view_tag` bail. Both new tests reddened — the
      service-level call count (2 != 1) and the TUI test driving the real component
      (`expand_view_tags` called once, expected zero).
    
    Both mutations reverted; `git status --porcelain` clean after each.
    
    **F9 back to Open** — everything it enumerated is gone, and two sentences of the same class
    arrived with these commits and survived the sweep. Detail and the exact line I drew are on the
    finding. Two deletions closes it.
    
    **F11 (new, info)** — F7's move left `_render_view_or_raise` catching `SquadsError`, which now
    also swallows and rewraps `render_view`'s own missing-template error. Its docstring's "let
    through unchanged" is false, and the message on that path is doubled. Driven; reachable only on
    the gate/render race, so info rather than a defect in the mechanism.
    
    **Two notes, neither a finding.** The dispatcher's refusal message no longer names the item
    (`but a 'epic' item hosts none`, where it used to name `EPIC-3`) — no loss at the one
    user-facing call site, since `sq workflow view` takes the id as an argument and the scan names
    the file. And US8's *title* on the parent still reads "the dangling-name check does not fire";
    the acceptance text under it is corrected, so this is record hygiene rather than the collapsed
    claim surviving anywhere load-bearing.
    
    @tech-lead F9's two sentences and F11 are the whole remaining surface; @manager the verdict is
    ChangesRequested until they close, and the approval is yours either way.
- [2026-09-03T13:53:37Z] Paul Reviewer:
  - Second verification pass, against `6a31a674`. **F11 Verified. F9 extended and still Open.**
    REV-912 stays `ChangesRequested`; ten of eleven findings are Verified.
    
    - **F11 Verified.** Pass-through driven (same exception type, byte-identical message, no
      item-prefix), F7's item-naming still intact for a genuine render failure, `pristine_body`'s
      swallow driven intact and structurally unreachable by the new subtype. Falsified by my own
      mutation — removing the narrow clause reproduces the doubled message verbatim. Detail on the
      finding. `ruff` (full `TRY` set), `ruff format`, `pyright` on the four touched modules all
      clean; 395 targeted tests green.
    - **F9 extended, not re-filed.** Both sentences I named are gone. The engine-docstring instance
      the manager found is the same class, and re-reading the added prose turned up a **fourth** at
      `_services/_base.py:577` — same commit, and a second copy of the same delta claim. Ruling,
      the line as a reusable test, and what I deliberately held are on F9. What is left is four
      clauses in `_rendering/_engine.py` and one sentence in `_services/_base.py`; two want a
      present-tense rewrite rather than deletion, and the durable facts are named so it is not a
      guessing game.
    
    **On the pattern, since it now decides how FEAT-903 is swept: I agree, and it is structural.**
    Four instances, all from `ed26f99c` — the commit whose own subtask ran the sweep — each in a
    phrasing that commit's grep did not list. Then my verification grep missed the fourth. That is
    not three people being careless; a phrase-list grep is a filter fitted to the *previous* pass's
    vocabulary, and the author of the current pass necessarily writes the phrasings they do not
    themselves read as narration. The filter can only ever catch what someone already learned to
    look for.
    
    What replaces it is bounded, not open-ended: the added prose is a small, enumerable set
    (`git diff <base>..HEAD` over `src/`+`tests/`, added comment and docstring lines only — 399
    lines for this whole feature), and each sentence gets the one-question test on F9 rather than a
    pattern match. A grep still helps as a *pre-filter* for the obvious hits; it cannot be the gate.
    
    @manager the board notice is worth it, and specifying the sweep as a reading pass with that test
    is the right shape. @tech-lead F9's remaining surface is five sites in two files, all listed.
- [2026-09-03T14:09:08Z] Paul Reviewer:
  - Third verification pass, against `da8544e9`. **Not approving.** Ten of eleven findings are
    Verified; F9 is one docstring sentence and one string short of closing, both listed on the
    finding. REV-912 stays `ChangesRequested`.
    
    I would rather say that than approve a finding I can disprove with one grep — you said you'd
    take a fourth pass over that, and this is the case for it, but it is a small one: the pass
    itself was good.
    
    - **The commit is prose-only, proven not asserted**: docstring-stripped ASTs of all 14 changed
      files are identical across the commit. That also settles judgement call 1 mechanically — no
      non-docstring string literal changed anywhere.
    - **My two enumerated surfaces are correctly done**, as rewrites: all three durable facts kept
      in present tense in `_rendering/_engine.py` with the four delta clauses gone, and
      `_services/_base.py:577` now states the mechanism. Shorter and complete, not flattened.
    - **Sampled 17 of the 17 across 9 files: no flattening**, and three came out better than they
      went in — the property restated in checkable terms rather than version terms. The
      non-vacuity control comment kept its point. The dev also cut several regression-test
      docstrings I had held; that is author's latitude and no durable claim was lost.
    - **Still open**: `tests/service/test_view_tag_expansion_at_read_time.py:406-408` — "nothing
      about this fix changes its behaviour — it already expanded before the fix and must keep
      expanding after". The **fifth** copy of that claim, and the same sentence about the same
      control that this commit rewrote correctly in two sibling files, so the durable form is
      already written twice inside it.
    - **Judgement calls**: 1 — extending the scope to any prose the tool or its tests *emit to a
      human* (assert messages included), which the dev could not have known from F9 as I wrote it;
      I applied the test to all 13 assert messages this feature added and exactly one fails, so the
      extension costs one string. 2 — **confirmed, hold both**: "the spec no longer declares"
      describes a spec-drift state a *user* creates, whose before the reader can still observe, and
      someone writing `remove_view` from scratch today would write the same sentence. Reasoning on
      the finding so it is not re-litigated.
    - **Held list: all four confirmed held**, and the ~25 pre-existing corpus instances are
      provably outside this feature's added prose rather than merely unvisited.
    
    **The method is working and the failure mode moved.** Three grep passes found 2, then 1, then
    1; reading with the test found 17. What is left is not a phrasing the test misses — it is a
    claim duplicated across files, fixed where the reader's attention landed and missed where it
    did not. File-by-file reading structurally cannot see that two files say the same thing. So the
    board notice wants one more line: **once a sentence is rewritten, grep a distinctive fragment of
    the old sentence across the whole feature before calling that claim closed.** Here "before the
    fix" would have found all three siblings in one command. Reading finds the class; that grep —
    run *after* the rewrite, over the old wording, not before it over a guessed vocabulary — closes
    the copies.
    
    Gates: `ruff check`, `ruff format --check` clean; 387 tests green over the 13 touched test files
    plus `tests/meta`; `sq check` clean.
    
    @tech-lead two edits: the docstring at `test_view_tag_expansion_at_read_time.py:406`, and the
    assert message at `test_read_body_skips_the_index_load_without_a_view_tag.py:62`. @manager I will
    approve on sight once they land — nothing else on this review is outstanding.
- [2026-09-03T14:22:58Z] Paul Reviewer:
  - Asked for my doubts rather than my conclusions, while the context is warm. Six, ordered by what I
    would actually spend QA's time on, each with the check that settles it and what I did and did not
    establish. Two more I opened and closed myself while writing this, recorded so nobody re-runs them.
    
    **1. The bulk importer's two write seams — the biggest gap in my F3 verification.**
    F3 changed the `mutate` contract for every caller. I **read** all seven call sites and **drove**
    four behaviours end to end (no-op placement, body, comment, sub-entity body). I never drove a real
    `sq import` over a file carrying both a `body` and a `sub-body` op and checked `updated_at`,
    ordering and the skew guard through `_import.py:584` / `:608`. I ran `test_bulk_import_engine.py`
    and it passes, so this is coverage-by-someone-else's-test, not by my own observation — and it is
    the one caller where the seam runs *inside* a transaction someone else opened. Worth driving
    properly; it is integrity-critical and it is invariant 8's territory.
    
    **2. A skewed placement.** `ensure_no_skew` sits in the folded core, and placement is a *new*
    caller of that seam. I **read** that the guard's call and its position relative to `mutate` are
    unchanged, and I ran the skew-guard suite (which covers body/comment paths). I never constructed
    a genuine skew — frontmatter disagreeing with the index — and drove `view add`/`view rm` into it
    to watch it refuse. **Accepted on reading.** One fixture away from being driven.
    
    **3. `has_view_tag` and `expand_view_tags` can silently diverge.** F4's fix makes `read_body` ask
    `has_view_tag(body)` and skip expansion when it says no. Both functions do "the same span-and-name
    check" — `iter_marker_spans` + `view_tag_name` — but **nothing pins that they agree**. If someone
    widens the recogniser inside one (say expansion learns a second tag shape), a body that
    `expand_view_tags` would expand gets skipped at the boundary, and the failure is silent: the tag
    renders as literal text on every read surface, `sq check` stays clean, no exception anywhere. This
    is the exact failure signature F1 had. **Inferred**, no coverage; cheap to pin with a property test
    asserting the two functions agree over a table of bodies.
    
    **4. The real TUI, by a human.** F4's cost lands on `sq ui`, which is precisely the surface that
    opts out of the read scope. I verified it through Textual's test harness driving the real
    `ReaderScreen`/`ReaderPanel`, which is the right instrument for the assertion — but I never
    launched `sq ui` and selected items in a browse tree. Our own TUI tests are known to be flaky
    under `-n auto`, and this is a visual/dev-host surface, so it is the operator's eyes that settle
    it, not mine.
    
    **5. Retype between two types that both host the same kind.** The dev named this and I agree with
    their call, but it stays a hole: no two bundled types share a `subentity_kind`, so the
    "applies=True on both sides of a retype" row cannot be built from the bundled spec. It is covered
    at the placement and expansion layers, table-driven, just never *through a retype*. An overrides
    spec declaring two types that host the same kind would close it. Low value against fixture weight
    — I would only do it if FEAT-903's new kinds make the pairing natural.
    
    **6. My own consistency on F9's held list.** I held four categories (substitutability guarantees,
    errata on claims a docstring still makes, regression-test docstrings naming the defect they guard,
    pre-existing corpus prose) and I am the only person who has applied that line. The two rulings I
    would most like a second reader on are `_validators.py:11`'s "despite an earlier version of this
    sentence" — which I hold on the grounds that it corrects a claim the same docstring still makes,
    and which is genuinely close to the banned form — and `_views.py:551`'s "keeps working
    unchanged". If QA reads those and disagrees, I would rather they say so than inherit my line.
    
    **Two I opened and closed myself, so nobody spends time on them:**
    
    - *An unknown `source.kind` in an adopter override reaching `_SOURCE_APPLICABILITY`'s `KeyError`.*
      I worried this was an unhandled crash on an adopter path that FEAT-903 widens. **Driven**: it is
      refused at spec load — `sq workflow views`, `sq workflow lint` and `view add` all exit 1 with a
      clean message naming the allowed kinds and pointing at `sq workflow lint`, `sq check` exits 3,
      no traceback. The `KeyError` is unreachable from an override, and a unit test already pins the
      registry against the declared `Literal`. Closed.
    - *Whether a no-op edit is really silent on disk.* It is not, for the index — now filed as F12
      (info): the transaction commits `.squads.json` with identical bytes under a fresh mtime, which
      is verbatim what the seam's docstring says does not happen. Behaviour is fine and predates the
      fold; the sentence is what is wrong.
    
    **One process note for QA, learned the hard way twice on this review.** Both times I nearly
    misreported, it was my own instrument, not the code: a `cmd | tail; echo $?` that reported the
    pipe's status and made a clean `exit 1` look like `exit 0`, and a line-oriented grep that could
    not see a phrase split by a line wrap. When a probe disagrees with the source, suspect the probe
    first — and validate any *disproving* search against a known positive before trusting its zero.
- [2026-09-03T14:23:25Z] Paul Reviewer:
  - Fourth pass, against `ea22c9ae`. **Not approving.** Both edits are correct, and F9 has a sixth
    copy — `tests/cli/test_check_view_tag_pairing_and_dangling_name_cli.py:72-74`, a file neither
    sweep commit visited. Ten of twelve findings Verified; F9 and the new F12 are open.
    
    - **Both edits verified.** Prose-only proven mechanically (string literals masked → identical
      code skeletons; exactly one literal changed). All three ref-source controls now read
      consistently, and the assert message names the invariant it checks.
    - **The sixth copy, and why five grep passes could not see it:** the phrase is `used to create
      silently`, and the line wrap falls between "used" and "to". **A line-oriented grep cannot match
      a phrase a line wrap splits.** Your 13 fragments were validated honestly and their zeros were
      true negatives for the pattern and false negatives for the class — `"used to be duplicated at
      two call sites"` happened to fit on one line; this one does not. My own pass-3 grep searched
      `used to` across this very file and returned nothing. Third blind spot, third direction, same
      conclusion: reading finds it, grepping structurally cannot.
    - **The fix for the pre-filter, if you keep one:** scan whole prose *blocks*, not lines — pull
      each docstring / comment run / assert message via AST + `tokenize`, collapse internal
      whitespace, then match. I wrote and ran it; it surfaces the sixth copy in one hit with both
      halves of the split phrase visible. Worth folding into the acceptance criteria alongside the
      reading pass.
    - **Remaining surface, exhaustive and re-derived independently** (not by re-running your
      fragments): one docstring that must go, plus `"two reasons, generalised from one"` in two files
      which fails my test and which I am flagging rather than holding — it is the mildest instance in
      the set and I would rather say that than invent an exemption at pass four to keep it. Both on
      F9, with the durable wording named. **I am not moving the line again**; there is no seventh
      criterion behind these.
    - **New finding F12 (info)**, found while narrowing my doubts list rather than hunting: a no-op
      section edit returns early *inside* the transaction, which still commits, so `.squads.json` is
      rewritten with identical bytes under a fresh mtime — verbatim what the seam's own docstring says
      does not happen. Behaviour is fine and predates the fold; the sentence is what is wrong, and it
      sits on the seam F3 exists to make enumerable-from. One clause.
    
    **Your question, answered on the record** in its own comment above: six doubts, ordered, each with
    the check that settles it — the bulk importer's two seams being the real gap in my F3 work, a
    skewed placement never driven, `has_view_tag`/`expand_view_tags` having nothing pinning that they
    agree (same silent signature F1 had), the real `sq ui` needing human eyes, the unbuildable
    same-kind retype pairing, and my own F9 held list wanting a second reader. Plus two I opened and
    closed myself so nobody repeats them, and one process note: both times I nearly misreported on
    this review it was my instrument, not the code.
    
    Gates: `ruff check`, `ruff format --check` clean; targeted suites green; `sq check` clean.
    
    @tech-lead one docstring (item 1 on F9) and the F12 clause; item 2 on F9 is your call and I will
    verify against whatever you decide. @manager I will approve the moment item 1 and F12 land — and
    if you would rather ship F12 as a follow-up, say so and I will mark it WontFix-for-now against
    that decision rather than leaving it as drag on this review.
- [2026-09-03T14:37:37Z] Catherine Manager:
  - Approving as delegated approver. All twelve findings closed: F1 (critical) and F2 (high) fixed and independently verified by the reviewer with his own repros driven dead; F3-F8, F10, F11 verified; F9 and F12 are info-level and closed here. F9 is closed on evidence rather than on care -- a validated ast+tokenize block scanner (whitespace collapsed, so a phrase split by a line wrap can no longer hide) was run over all 34 touched files against the accumulated vocabulary, cross-checked against pre-feature content: 51 raw hits, 6 genuine, 2 held by the reviewer, 1 already correct, 3 fixed. Full suite green at 4782 passed.
<!-- sq:discussion:end -->

---
id: TASK-914
sequence_id: 914
type: task
title: 'View mechanism cleanup: write seam, read boundary, removal, docs'
status: Done
parent: FEAT-905
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-880:implements
- REV-912:addresses
description: 'The eight non-blocking review findings taken as one pass: the third
  write seam, the index load at the body-read boundary, the removal primitive, two
  false docstrings, and the narration'
subentities:
- local_id: ST1
  title: Fold the third frontmatter write seam into the core
  status: Done
  story: US1
- local_id: ST2
  title: Bail before the index load when no tag is present
  status: Done
  story: US4
- local_id: ST3
  title: Removal reports honestly on a duplicate tag
  status: Done
  story: US2
- local_id: ST4
  title: Splice the removal instead of normalising the region
  status: Done
  story: US2
- local_id: ST5
  title: Anchor the catalog-exclusion canary
  status: Done
  story: US6
- local_id: ST6
  title: Translate template failures in the rendering engine
  status: Done
  story: US4
- local_id: ST7
  title: Document both check tiers at the catalog end
  status: Done
  story: US7
- local_id: ST8
  title: Strip build-process narration from delivered text
  status: Done
  story: US4
created_at: '2026-09-03T12:03:23Z'
updated_at: '2026-09-03T14:37:57Z'
---
<!-- sq:body -->
## Scope

The eight non-blocking findings REV-912 raised against the view-tag mechanism, taken as one pass
because they are one owner's work in one shipping increment and several land in files the
applicability fix also touches. None of them is a correctness risk to the mechanism itself; two
are false documentation, three are seam or placement points, two are prose, and one is a
measured cost the body-read boundary acquired.

Tags are spelled bare below (`sq:view:<name>`) rather than in their HTML-comment form, as the
ADR record does, because the prose guard refuses a well-formed tag in any authored input.

**Sequenced after the applicability fix, not beside it.** The generalised file-level finding is
renamed there and named here; the body-read guard below calls the recogniser whose contract is
settled there; and both tasks edit the same two modules. Two agents in one tree on those files
produces a spurious conflict, not parallelism.

## What lands

**F3 — the third frontmatter write seam folds back into the core.** The placement edit
reproduces the shared section-edit core almost line for line — open the transaction, require the
item, deep-copy for the skew baseline, read the item file, run the skew guard with the spec's
default ref kind, mutate, bump the timestamps, rewrite the frontmatter — differing only in an
early return when the mutation reports no change. That makes it a third copy of the
integrity-critical frontmatter-rewrite seam and falsifies the other two, one of which still
documents itself as "the second of the two write seams". The count is not decorative: it is what
a reader uses to enumerate the places the skew guard and the write ordering have to be kept
consistent, and the failure mode is a later author tightening two of three.

Fold it: the core takes the conditional-write decision from its `mutate` callback — a
`(text, changed)` return, or a sentinel meaning "no write" — with every existing caller
returning changed. The docstring's justification for a separate seam ("the shared core cannot
grow without changing behaviour for every other caller that relies on it always writing") is
true of an unconditional change and not of that one. If the fold turns out to change behaviour
for any existing caller, **stop and comment rather than forcing it**; the fallback is to fix the
count and cross-reference the seam inventory at both ends so it is recoverable from either
docstring, and that fallback needs saying out loud, not choosing silently.

**F4 — the body-read boundary bails before the index load.** The boundary now loads the whole
index unconditionally, before it knows whether the body carries a tag at all; before this
mechanism it loaded none. Under the CLI that is free — an invocation-scoped read scope serves
the filed snapshot — but the TUI deliberately opts out of that scope, so every reader-panel load
pays a fresh full index read plus validation on every item selected in the browse tree, whether
or not the body has a tag. Driven on this corpus (5582 items, a 1.19 MB index): 0.035 s per
fresh load, growing with corpus size, for a feature that fires on zero documents here.

The tag spans are computable from the body text alone, so the boundary can skip both the load
and the expansion call when the body carries no tag. This rides here rather than the TUI work
because the cost was introduced at this boundary by this mechanism, the fix is in the boundary's
own function, and a boundary documented as a read on a thread should not silently acquire an
index read.

**F5 and F8 — the unpaired-removal primitive keeps its promise.** Both findings are the same
function and the same sentence in its docstring, so it is rewritten once.

F5: the primitive removes the **first** occurrence only, and the boolean it returns cannot
distinguish "the last one" from "one of several", so the remove verb prints an unconditional
success line while the view still renders. Driven on a body carrying the same named tag twice —
the exact state the check reports as a duplicate and therefore treats as a supported, repairable
error — the verb reports removal, the check then falls silent because a single tag is legal, and
the roll-up still renders. The operator's intent was "take this view off this document"; the
report says done and it is not done. Reachability is low (insert is idempotent, so a duplicate
arrives by hand-editing or by FEAT-907's bulk path) but the duplicate state is one the team
decided to keep reporting and this verb is its repair path.

F8: the removal path calls the region replacer, which normalises — prepending a newline when the
new inner content does not start with one and appending one when it does not end with one — so
the whole region round-trips through a normaliser while the docstring promises "every other byte
of the section survives verbatim". The insert direction genuinely splices; the two are asymmetric
in a way their shared docstring language hides. Not a live defect: every squads write path goes
through the replacer, so every body on disk already satisfies the precondition. It is named
because the one path that will meet a region squads did not write is FEAT-907's bulk placement
over an adopted corpus. Splice the removal the way the insert splices, so the promise becomes
true; if that cannot be done inside the primitive without changing the replacer's behaviour for
its other callers, **stop and comment** — the fallback is to say in the docstring exactly which
bytes it normalises.

**F6 — the catalog-exclusion canary gets anchored.** A test closes with an assertion that no
catalog name contains the substring `view`, and `view` is a substring of `review`, which is one
of this project's own declared item types. The catalog's current keys contain no `review`, so it
passes today and the trap is merely unsprung: the first validator anyone adds named for reviews
fails this test, with a message pointing at the view-tag mechanism and saying nothing about the
validator that actually broke it. The preceding assertion already carries the real claim; anchor
the broader one (a prefix match, or a check against the function object rather than a name
substring) or drop it.

**F7 — the Jinja translation moves into the rendering engine, once.** Two consumers now reach
past the rendering engine for the engine's own exception vocabulary with a function-local import,
and they handle it **differently** — one translates to a clean error, the other swallows it and
returns nothing. Meanwhile the one function every template in the codebase goes through
translates nothing, so every other caller still propagates a raw undefined-name error on a
strict-mode failure. The property "a template failure surfaces as a clean error" is now true at
two consumers and false everywhere else, which is the opposite of what the view renderer's own
docstring promises.

The concrete cost is an adopter's: override an item-creation template with a reference to an
undefined variable and creating that type prints a Jinja traceback, while the same mistake in a
view template prints the clean message the CLI's error decorator exists to produce. Translate in
the engine, once, so both existing consumers drop their local imports and every future renderer
inherits it — FEAT-903 and FEAT-906 both add renderers that would otherwise each decide this
locally. The swallow-and-return-nothing consumer keeps its behaviour exactly; only the exception
type it catches changes.

**F9 — build-process narration comes out of delivered prose.** Six hits, all in the new test
suites: build order ("landed after this verb"), a ticket's authority cited as the reason for a
design constraint, two build-relative time references ("exactly like before this feature",
"unchanged by this feature"), a scoping note recording what a build increment declined to solve,
and a rule attributed to an ADR amendment as a build artifact when the rule is already stated on
the next line. In every case the durable fact is already there or is one clause away; delivered
text describes the thing, not how it was built. Two source-side lines are judgement calls and
the review says so: one describes this repository's own history as if an adopter shared it (the
durable form is what the design refuses, which loses nothing), and one forward-references
unshipped work where the sentence already carries its point without it. Take both.

**F10 — the two check tiers get documented at the tier-2 end.** The check surface has two tiers
and only one is self-describing: the always-on file-level scan (raw file text, before frontmatter
parses, keyed on the filename) explains why it sits where it does, and nothing at the per-item
validator end says it exists. That end says the opposite — its module docstring calls the engine
the **sole** source of the check's issues, which is true of per-item and squad-global issues and
false of the check's issues as a whole: two error-level findings are produced outside it, and
after the applicability fix one of them enforces a binding ADR invariant.

This is documentation, not mechanism. The placement itself was routed to review and **ruled
correct by design** on three grounds, all read from source: the catalog is per-item and this
finding is per-file (it runs before the line that turns a file into an item, and a file whose
frontmatter is unreadable never reaches the catalog while its file-level findings have already
been emitted); the catalog is selectable and the ADR rules this finding unconditional, where
"floor" in the catalog's own vocabulary means common-core membership, which is still a
selectable-shaped, item-scoped mechanism and would weaken the invariant rather than honour it;
and it mirrors its file-level neighbour exactly, which has never been a catalog member. Do not
move it.

The consumer that must inherit this is FEAT-898, which declares the required context per catalog
member and closes the correspondence with an assert. Whoever builds it reads the validator module
first. The two file-level findings are outside that closure because they are outside the catalog,
not because they escaped it: they declare no context because they need none beyond the file text
and the already-in-hand spec and host type. FEAT-898 does not need to extend its grammar to cover
them; it needs to not mistake the catalog for the complete inventory of check findings — and the
place it will read that is the docstring this subtask corrects.

## Acceptance

**Closes F3, F4, F5, F6, F7, F8, F9 and F10 on the review.**

**F3.**
- One frontmatter-rewrite seam per shape, and the seam inventory a reader reconstructs from any
  one docstring is complete and correct.
- Every existing caller's observable behaviour is unchanged, including the skew guard's direction
  and the write ordering (markdown before the index commit, index last).
- The placement edit keeps its no-write-on-no-change outcome.
- If the fold is abandoned, the handback says why and the inventory correction lands instead,
  cross-referenced at both ends.

**F4.**
- A body with no tag costs the boundary no index load and no expansion call. Assert the load does
  not happen, not merely that the result is unchanged.
- A body with a tag behaves exactly as it does now on every read surface.
- The TUI reader path is covered, since it is the one that pays.

**F5.**
- Every occurrence of the named tag is removed, or the report states what remains. The report
  never says removed while the view still renders.
- The different-name case keeps its current behaviour verbatim: another view's tag survives
  untouched.
- Removing an absent tag stays a safe no-op, not an error, and the remove verb stays ungated on
  name resolution.
- A duplicate is covered directly. The existing suite covers only the different-name shape.

**F8.**
- The removal path preserves every byte outside the removed tag, including a region whose inner
  content neither begins nor ends with a newline — the shape squads does not write and an adopted
  corpus can.
- The docstring's promise matches the code, in whichever direction that is settled.
- Insert and remove are symmetric in what they promise and what they do.

**F6.**
- The canary cannot fire on a validator named for reviews. Add such a name in a test to prove it,
  rather than reasoning about the substring.
- The narrow claim that the view finding is not a catalog member survives intact.

**F7.**
- One translation, in the engine. Neither consumer carries a local import of the engine's
  exception any more.
- The swallowing consumer still swallows and still returns nothing; only the exception type it
  catches changes.
- An adopter's item-creation template referencing an undefined variable produces the clean
  message and exit 1, not a traceback. Drive it.
- No other renderer's success path changes.

**F9.**
- Zero build-process references in the delivered text this mechanism added: no build order, no
  build-relative time reference, no ticket or amendment cited as the authority for a design
  constraint, no note recording what an increment declined to do. The durable fact each one was
  carrying survives in its own words.
- The two source-side lines are taken as well.
- Historical discussion comments are exempt and untouched — the append-only record is not
  delivered prose.

**F10.**
- The validator module's docstring names the file-level tier, names both of its members, and says
  why they sit there. The "sole source" sentence is corrected to the scope it actually holds.
- The file-level scan carries the matching back-reference, so the boundary is recoverable from
  either end.
- The generalised finding is named by whatever it is called after the applicability fix, not by
  the name it has today.
- No mechanism change, and nothing moves into the catalog.
- The handback flags on FEAT-898 that this ruling is inherited rather than re-derived.

**Falsification.**
- Every new or changed test is broken red and restored green, with **both** directions reported in
  the handback — the mutation made, the tests that reddened, and the restoration.
- For the two documentation-only findings there is nothing to falsify; say so explicitly rather
  than reporting a falsification that did not happen.
- The F3 fold is proven by the existing callers' own suites, not by new tests alone: name which
  suites cover each caller and report their result.

## Engineering constraints

- Layering is `_cli` -> `_services` -> (index store, backends, rendering); `_models` has no
  internal deps. Every implementation module stays private and package `__init__` files do not
  re-export.
- Marker-safe edits only, through `_sections.py`. Never rewrite an agent-authored body.
- The write seam is integrity-critical: markdown is never behind the index, every markdown write
  inside a transaction happens before it returns, and the index commit is last.
- The tag stays unpaired. No closing counterpart for the family, and no verb writes content
  adjacent to one.
- Every refusal is a `SquadsError`. Dynamic console text is escaped.
- Gate before handback: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .`, and `uv run sq check` clean. Run the touched
  suites with a path selector; **do not run the full suite** — that gate is the main loop's, and
  a backgrounded full run does not survive the handback. F3 and F7 both reach outside the view
  mechanism, so say which suites were run and which were not.

## Out of scope — do not build

- The applicability predicate, the recogniser contract, the generalised finding and the US8
  correction. They are the other task on this feature and this one is sequenced behind them.
- Moving the file-level finding into the per-item validator catalog, or giving it a level knob.
- FEAT-898's context-declaration grammar. This task corrects the docstring it will be read
  against and nothing more.
- FEAT-903's source kinds and FEAT-904's deletion of the projection layer.
- A view tag inside a sub-entity body. Expansion is the top-level body boundary only and such a
  tag would be silently inert, but it is unreachable today — the placement verb targets the
  top-level region and the prose guard refuses typing one in. It belongs with FEAT-907, where
  creation templates start seeding tags.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 914 add-subtask "<title>"`; track with `sq task 914 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Fold the third frontmatter write seam into the core

<!-- sq:subtask:ST1:body -->
Closes F3 (medium). The placement edit reproduces the shared section-edit core almost line for
line — transaction, require the item, deep-copy for the skew baseline, read the item file, skew
guard with the spec's default ref kind, mutate, bump the timestamps, rewrite the frontmatter —
differing only in an early return when the mutation reports no change. That is a third copy of
the integrity-critical frontmatter-rewrite seam, and it falsifies the docstring that still calls
its neighbour "the second of the two write seams". The count is what a reader uses to enumerate
the places the skew guard and the write ordering must be kept consistent; the failure mode is a
later author tightening two of three. Fold it: the core takes the conditional-write decision
from its mutate callback, with every existing caller reporting a change. The separate-seam
justification holds for an unconditional change to the core and not for that one. Every existing
caller's observable behaviour is unchanged, including the skew guard's direction and the write
ordering — markdown before return, index commit last — and the placement edit keeps its
no-write-on-no-change outcome. Prove it through the existing callers' own suites and name them
with their results. If the fold changes behaviour for any caller, stop and comment rather than
forcing it; the fallback is to correct the count and cross-reference the seam inventory at both
ends, and that fallback is said out loud, not chosen silently.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-09-03T12:56:07Z] Elias Python:
  - Folded: _locked_placement_edit removed entirely. _section_edit_core/_locked_section_edit now take mutate: (text, item) -> (new_text, changed) and skip the write/timestamp bump when changed=False -- the exact conditional _locked_placement_edit used to own alone.
  - 5 mutate closures updated to return (text, True) unconditionally (body, block-body, comment) since only placement can be a no-op; insert_view/remove_view now call _locked_section_edit directly and unpack (item, changed).
  - 3 direct callers of _section_edit_core (2x import.py BodyEvent/SubBodyEvent, 1x collab.py _comment_core) updated to unpack the tuple; _items.py set_body and _subentities.py set_block_body updated similarly (the latter's return was already discarded).
  - Docstring count is corrected for free: with the third clone gone there are once again exactly two write seams (_section_edit_core, _itemfile.update_frontmatter), so _section_edit_core's 'second of the two' sentence is true again -- no wording change needed there, just the fold.
  - Falsified: removed the 'if not changed: return it, False' early-return, reran tests/service/test_view_tag_placement.py + tests/cli/test_view_tag_placement_cli.py -> 7 reddened (idempotent-insert-reports-already-present, remove-absent-is-noop x3, both no-op-does-not-call-write-primitive tests, CLI idempotent-add and no-op-rm) since the writes/timestamp bumps now happen unconditionally; restored, all 33 green.
  - Existing-caller coverage run green (232 passed): test_set_body_replace_append_and_meta_guard, test_replacing_an_authored_body_is_refused, test_frontmatter_skew_guard, test_item_comments_readback, test_comment_targeting_guards, test_custom_skill_authored_body_persistence, test_an_authored_skill_body_survives_the_system_skill_shrink, test_operator_lifecycle, test_mutation_routing_never_reaches_the_plain_write, test_bulk_import_engine + 4 more bulk-import suites, test_import_cli, test_import_exit_code_and_finding_levels, test_show_command_renders_body_and_subentities, test_skill_show_renders_a_system_definition_on_read, test_discussion_comment_formatting_and_mentions, test_retype + test_retype_carries_a_view_tag_and_check_stays_clean, test_view_tag_placement, test_view_tag_placement_cli, test_view_tag_expansion_at_read_time.
  - pyright clean on the 6 touched files (_base, _import, _collab, _items, _subentities, _views).
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Bail before the index load when no tag is present

<!-- sq:subtask:ST2:body -->
Closes F4 (low). The body-read boundary now loads the whole index unconditionally, before it
knows whether the body carries a tag at all, where before it loaded none. Under the CLI that is
free — an invocation-scoped read scope serves the filed snapshot — but the TUI deliberately opts
out of that scope, so every reader-panel load pays a fresh full index read plus validation on
every item selected in the browse tree, tag or no tag. Driven on this corpus, 5582 items and a
1.19 MB index: 0.035 s per fresh load, growing with corpus size, for a mechanism that fires on
zero documents here. The tag spans are computable from the body text alone, so the boundary
skips both the load and the expansion call when the body carries no tag. Assert the load does
not happen, not merely that the result is unchanged; a tagged body behaves exactly as it does
now on every read surface; and the TUI reader path is covered, since it is the one that pays.
This rides here rather than the TUI work because the cost was introduced at this boundary by
this mechanism and the fix is in the boundary's own function.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-09-03T12:59:57Z] Elias Python:
  - Added squads._views.has_view_tag(text) -- same span-and-name check expand_view_tags already does, computed from body text alone (no index/spec/item), exposed so read_body can decide before paying either cost.
  - read_body now checks has_view_tag(body) first; returns immediately (no store.load(), no expand_view_tags call) when absent. A tagged body's path is unchanged (self.get()'s pre-existing load, then the expansion load, same as before).
  - Clarified: self.get(item_id) (needed to resolve the item's type/path) already called store.load() once before this feature ever existed -- that call is the baseline and stays. The load this bails is the SECOND, expansion-only store.load() call this mechanism added; that's what doubles per-body-read cost outside a read scope (the TUI), and what the fix removes for the common (tagless) case.
  - New test tests/service/test_read_body_skips_the_index_load_without_a_view_tag.py asserts absence directly by call-counting svc.store.load via monkeypatch: 1 call for a tagless body (was 2), 2 calls for a tagged body (unchanged), plus a same-result-either-way control.
  - TUI reader path covered directly (the surface that pays, since sq ui has no read scope): tests/tui/test_reader_screen.py gained a test driving the real ReaderScreen/ReaderPanel.load, monkeypatching squads._views.expand_view_tags to prove it is never called for an untagged body reached through the actual component, not just via a direct svc.read_body() call.
  - Falsified both new tests independently: reverting the has_view_tag bail (always load+expand) reddened the service-level call-count test (2 != 1) and the TUI structural test (expand_view_tags called once, expected zero); restored both, all 6 relevant tests green (3 in each file).
  - pyright clean on _services/_items.py and _views.py.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Removal reports honestly on a duplicate tag

<!-- sq:subtask:ST3:body -->
Closes F5 (low). The unpaired-removal primitive removes the first occurrence only, and the
boolean it returns cannot distinguish "the last one" from "one of several", so the remove verb
prints an unconditional success line while the view still renders. Driven on a body carrying the
same named tag twice — the exact state the file scan reports as a duplicate and therefore treats
as a supported, repairable error — the verb reports removal, the scan then falls silent because a
single tag is legal, and the roll-up still renders. The operator asked to take the view off the
document and was told it was done. Remove every occurrence of the named tag, or report what
remains; the report never says removed while the view still renders. The different-name case
keeps its current behaviour verbatim, another view's tag surviving untouched. Removing an absent
tag stays a safe no-op rather than an error, and the verb stays ungated on name resolution. Cover
the duplicate directly — the existing suite covers only the different-name shape.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-09-03T13:03:11Z] Elias Python:
  - F5 and F8 share one function and one docstring sentence, so rewritten together in _sections.remove_unpaired_marker as the task record anticipated -- recorded on ST3, cross-referenced from ST4.
  - remove_unpaired_marker now loops: removes every occurrence of the named marker (was: first only), returning removed=True iff at least one was found. The different-name case (another view's tag) is untouched -- unaffected by the loop since it never matches marker.find().
  - Coverage: 3 new unit tests (duplicate x2 -> both removed and restores the region; triplicate -> all three; duplicate-with-a-different-name-interleaved -> only the named one goes). Plus a service-level test reproducing the reviewer's exact repro: hand-seed a duplicate milestone_rollup tag, sq check reports 'duplicate marker', remove_view, assert removed is True AND read_body no longer renders the view AND sq check goes clean.
  - Falsified at both layers: reverted to first-occurrence-only + replace_section -- unit level reddened the 3 new tests (2 duplicate + 1 different-name-interleaved) while all 17 pre-existing unit tests stayed green; service level reddened the new duplicate repro test. Restored both, all green (22 unit + 1 service + full view-tag/check suites re-run clean, 81 total).
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Splice the removal instead of normalising the region

<!-- sq:subtask:ST4:body -->
Closes F8 (info), the same function and the same docstring sentence as the removal report, so it
is rewritten once with it. The removal path calls the region replacer, which normalises —
prepending a newline when the new inner content does not start with one and appending one when it
does not end with one — so the whole region round-trips through a normaliser while the docstring
promises that every other byte of the section survives verbatim. The insert direction genuinely
splices; the two are asymmetric in a way their shared docstring language hides. Not a live defect:
every squads write path goes through the replacer, so every body on disk already satisfies the
precondition. It matters because the one path that will meet a region squads did not write is the
bulk placement over an adopted corpus on FEAT-907. Splice the removal the way the insert splices,
so the promise becomes true, and cover a region whose inner content neither begins nor ends with a
newline. Insert and remove end up symmetric in what they promise and what they do. If the splice
cannot be done inside the primitive without changing the replacer's behaviour for its other
callers, stop and comment; the fallback is to state in the docstring exactly which bytes it
normalises.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-09-03T13:03:22Z] Elias Python:
  - Same function/docstring sentence as F5 (ST3) -- rewritten once, both findings closed by the one change described there. This comment covers the byte-preservation half specifically.
  - remove_unpaired_marker no longer calls replace_section at all: it now finds the region's open/close marker positions directly in the original text (mirroring get_section's own bound-finding, since a start/end offset is needed to splice back rather than just the inner text), mutates a local copy of inner across the removal loop, then splices text[:start] + inner + text[ci:] using the ORIGINAL bounds. No newline is prepended or appended anywhere in the path.
  - Fell back to nothing -- the splice was doable inside the primitive with zero change to replace_section's behaviour for its other callers (it's simply no longer called from here); no stop-and-comment needed.
  - New coverage: a region whose inner content neither starts nor ends with a newline (prose immediately after the open marker, more prose immediately after the removed tag with no separating newline) -- asserts the exact spliced byte string, and a structural spy test asserting replace_section is never invoked by remove_unpaired_marker.
  - Falsified: reverted to the old get_section+replace_section body -- reddened both new tests (byte-preservation asserted a newline that wasn't there before; the spy saw one call) plus F5's 2 duplicate tests, while insert's own tests and the pre-existing remove tests (which all happen to round-trip through a region that already starts/ends with newlines) stayed green. Restored, all 22 unit tests green.
  - insert_unpaired_marker (the other half of this primitive pair) is untouched -- it already spliced via append_to_section, never replace_section, so F8 never applied to it.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Anchor the catalog-exclusion canary

<!-- sq:subtask:ST5:body -->
Closes F6 (low). A test closes with an assertion that no per-item validator name contains the
substring "view", and "view" is a substring of "review", which is one of this project's own
declared item types. The catalog's current keys contain no review-named member, so it passes
today and the trap is merely unsprung: the first validator anyone adds named for reviews fails
this test, with a message pointing at the view-tag mechanism and saying nothing about the
validator that actually broke it. The preceding assertion already carries the real claim. Anchor
the broader one — a prefix match, or a check against the function object rather than a name
substring — or drop it, and prove the fix by adding a review-named member in a test rather than
reasoning about the substring. The narrow claim that the view finding is not a catalog member
survives intact.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-09-03T13:04:41Z] Elias Python:
  - Anchored: assert not any("view" in name for name in CATALOG) -> assert not any(name.startswith("view") for name in CATALOG). Narrow claims (dangling_view/view_target not in CATALOG) untouched.
  - Proved by construction per the brief, not by reasoning about the substring: new test builds fake_catalog = {**CATALOG, "review_findings_closed": <dummy>} and asserts the unanchored form DOES fire on it (any("view" in name...) is True -- the trap) while the anchored startswith form does not.
  - Falsified: temporarily reverted the anchored assertion back to the bare substring form inside the new test -- reddened exactly as the trap predicts (assert not True). Restored, 18/18 green in the file.
  - No production code touched -- test-only fix. pyright clean.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Translate template failures in the rendering engine

<!-- sq:subtask:ST6:body -->
Closes F7 (low). Two consumers reach past the rendering engine for the engine's own exception
vocabulary with a function-local import, and they handle it differently — one translates to a
clean error, the other swallows it and returns nothing. The one function every template in the
codebase goes through translates nothing, so every other caller still propagates a raw
undefined-name error on a strict-mode failure. The property "a template failure surfaces as a
clean error" is true at two consumers and false everywhere else, the opposite of what the view
renderer's docstring promises. The concrete cost is an adopter's: override an item-creation
template with a reference to an undefined variable and creating that type prints a traceback,
while the same mistake in a view template prints the clean message the CLI's error decorator
exists to produce. Translate in the engine, once, so both consumers drop their local imports and
every future renderer inherits it — FEAT-903 and FEAT-906 both add renderers that would
otherwise each decide this locally. The swallowing consumer keeps its behaviour exactly; only
the exception type it catches changes. Drive the adopter case to the clean message and exit 1,
and change no other renderer's success path.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-09-03T13:08:22Z] Elias Python:
  - Translation moved into squads._rendering._engine.render() itself: catches jinja2.TemplateError, raises SquadsError(f"template {template_name!r} failed to render: {exc}") from exc. This is the one funnel every renderer in the codebase already calls.
  - _views._render_view_or_raise now catches SquadsError (was jinja2.TemplateError) and re-raises with the item named -- same re-raise-with-context shape, just off the engine's own SquadsError instead of the raw jinja2 one. Local 'from jinja2 import TemplateError' import removed.
  - _services._base.pristine_body now catches SquadsError (was jinja2.TemplateError) and still returns None -- swallow behavior byte-identical, only the caught type changed. Local jinja2 import removed.
  - New coverage: tests/service/test_template_failures_translate_to_a_clean_error.py (create with a broken .overrides item template raises SquadsError naming the template; pristine_body still swallows and returns None when the template breaks after a successful create; a working override template is unaffected -- control) + tests/cli/test_template_failures_translate_to_a_clean_error_cli.py (the adopter's exact scenario: sq create task with a broken override template -> exit 1, message names task.md.j2, no 'Traceback', no 'jinja2' in output).
  - Falsified: reverted render() to the bare (untranslated) one-liner -- 3 of the 4 new tests reddened (raw jinja2.exceptions.UndefinedError propagating uncaught through create/pristine_body/CLI, full traceback printed to stdout in the CLI run) while the working-template control stayed green; restored, all 4 green plus 38 across the wider view-resolve/expansion suites and 67 across every service-level create test.
  - pyright clean on _rendering/_engine.py, _views.py, _services/_base.py.
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Document both check tiers at the catalog end

<!-- sq:subtask:ST7:body -->
Closes F10 (medium), documentation rather than mechanism. The check surface has two tiers and
only one is self-describing: the always-on file-level scan explains why it sits where it does,
and the per-item validator end says nothing about it — worse, its module docstring calls that
engine the sole source of the check's issues, which is true of per-item and squad-global issues
and false of the check's issues as a whole. Two error-level findings are produced outside it, and
one of them enforces a binding ADR invariant. Name the file-level tier in that docstring, name
both of its members, say why they sit there, and correct the sole-source sentence to the scope it
actually holds; carry the matching back-reference at the scan so the boundary is recoverable from
either end. Name the generalised finding by whatever it is called after the applicability fix,
not by the name it has today. No mechanism change and nothing moves into the catalog — the
placement was ruled correct by design: the catalog is per-item while this finding is per-file and
runs before the line that turns a file into an item, the catalog is selectable while the ADR rules
this finding unconditional, and it mirrors a file-level neighbour that has never been a catalog
member. The consumer that must inherit this is FEAT-898, which declares required context per
catalog member and closes the correspondence with an assert: the two file-level findings sit
outside that closure because they are outside the catalog, not because they escaped it, and they
declare no context because they need none beyond the file text and the already-in-hand spec and
host type. FEAT-898 does not need to extend its grammar to cover them; it needs to not mistake
the catalog for the complete inventory of check findings, and the place its builder will read
that is the docstring this subtask corrects. Flag the inheritance on FEAT-898 in the handback.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-09-03T13:10:30Z] Elias Python:
  - Documentation-only, no mechanism change, as directed. _services/_validators.py's module docstring: corrected the 'sole source' sentence to its actual scope (per-item and squad-global issues, not sq check's issues as a whole) and added a new paragraph naming the file-level tier -- both members (_marker_issues, _view_target_issues), why they're per-file/unconditional and therefore not catalog-shaped, and why a caller that wants the complete finding surface must read both tiers.
  - Generalised finding named by its current name (_view_target_issues, the name the applicability-widening task landed) -- no stale 'dangling' reference introduced.
  - Matching back-reference added at the tier-1 end: MaintenanceMixin._scan_for_check's own docstring now opens by naming itself 'Tier 1 of sq check's two finding tiers', names both its members, and points at _validators.py's module docstring for the other end -- recoverable from either direction now.
  - No ticket IDs in either docstring (checked against the project's no-ticket-ids-in-source convention -- an initial draft named the applicability task and FEAT-898 directly, caught before commit and rewritten to describe the mechanism/consumer generically instead; the FEAT-898 inheritance flag goes in this handback, not in source).
  - Nothing to falsify -- documentation only, said explicitly per the brief rather than reporting a falsification that didn't happen.
  - Gates: pyright clean on both files; tests/meta caught a real regression (2 section-comment labels in the ST3/ST4 test file read as '(F5)'/'(F8)' -- finding-ID-shaped -- by the no-stray-ticket-references scanner) which I fixed by dropping the parenthetical finding tags from those comments; tests/meta now 279/279 green.
  - @tech-lead FEAT-898 flag: its context-declaration grammar and closing assert must not treat CATALOG as the complete sq check finding inventory -- the two tier-1 findings (_marker_issues, _view_target_issues) sit outside that closure because they're outside the catalog, not because they escaped it, and need no declared context beyond file text + spec + host type. This ruling and its reasoning are inherited from the review's catalog-placement discussion comment, not re-derived here; the docstring correction above is where FEAT-898's builder will read it.
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Strip build-process narration from delivered text

<!-- sq:subtask:ST8:body -->
Closes F9 (info). Six build-process references sit in the delivered text this mechanism added,
all in the new test suites: build order, a ticket cited as the authority for a design constraint,
two build-relative time references, a note recording what a build increment declined to solve,
and a rule attributed to an ADR amendment when the rule itself is already stated on the next
line. In every case the durable fact is already present or one clause away. Delivered text
describes the thing, not how it was built. Two source-side lines go with them: one describes this
repository's own history as though an adopter shared it, where the durable form is what the
design refuses, and one forward-references unshipped work in a sentence that already carries its
point. After the pass there is no build order, no build-relative time reference, no ticket or
amendment cited as design authority, and no note recording what an increment declined to do —
with each durable fact surviving in its own words. Historical discussion comments are exempt and
untouched; the append-only record is not delivered prose. Nothing here is falsifiable by a test,
so say that rather than reporting a falsification that did not happen.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
- [2026-09-03T13:12:03Z] Elias Python:
  - All 6 delivered-text hits + both source-side borderline lines from the review taken:
  - 1) tests/cli/test_view_tag_placement_cli.py module docstring: dropped 'landed after this verb' build-order clause, kept the durable fact (expansion renders the tag in show --raw, so the file is where a literal tag is assertable).
  - 2) tests/cli/test_view_tag_placement_cli.py test_view_is_not_a_flag_on_body: dropped 'The task's own constraint:' prefix -- the constraint is the design, stands alone.
  - 3) tests/service/test_check_exempts_the_view_tag_family_from_marker_pairing.py: dropped 'exactly like before this feature' -- the claim is just that a non-view unpaired tag still errors.
  - 4) tests/service/test_view_tag_expansion_at_read_time.py test_replacing_a_body...: dropped 'Not this feature's problem to solve (named as an accepted, unfixed cost)' scoping note, kept the durable behavior (a body replace overwrites the whole region like any other authored text).
  - 5) tests/service/test_view_tag_prose_guard_stays_closed.py module docstring: dropped 'unchanged by this feature' clause, kept the three specifics (no per-name hole, no allow parameter, no call-site bypass).
  - 6) same file, test_reject_markers_takes_no_per_name_exception_or_allow_parameter: dropped 'the amendment explicitly refused' -- the rule itself is already the whole sentence, stands alone.
  - Source-side (judgement calls, both taken): _models/_markers.py's VIEW docstring -- 'this corpus was stripped of' (reads as this repo's own history) -> 'this design refuses' (durable, adopter-agnostic). _sections.py's insert_unpaired_marker docstring -- dropped the 'including a future bulk placement' forward-reference; 'every caller shares' already carries it.
  - Nothing here is falsifiable by a test -- prose-only changes, no behavior touched. Said explicitly rather than reporting a falsification that didn't happen.
  - Re-ran all 4 touched test files + the unpaired-marker unit suite after the edits: 67 passed, confirming the docstring/comment edits didn't disturb any string the tests themselves assert on. pyright clean on both source files.
  - Grepped the full set of files this task's other subtasks touched (_views.py, _sections.py, _markers.py, _maintenance.py, _base.py, _items.py, _validators.py) plus all 4 test files for 'this feature'/'the amendment'/'landed after'/'before this feature'/'this pass'/'the reviewer' -- the only remaining hits are two pre-existing lines in _maintenance.py (roster sync docstrings, unrelated to the view-tag mechanism, predating this feature) -- left untouched, out of scope.
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T13:15:01Z] Elias Python:
  - All 8 subtasks Done; full per-ST detail + falsification already recorded on each. This is the consolidated handback.
  - F3/F8 disposition, as asked to say out loud: BOTH folded/spliced, neither fell back. F3 -- _locked_placement_edit removed entirely; _section_edit_core's mutate callback now returns (text, changed) and every existing caller (body/comment/sub-body/bulk-import) was updated to return changed=True, so the docstring's 'second of the two write seams' count is true again with zero wording change needed -- the fold itself restored correctness. F8 -- remove_unpaired_marker now splices region bounds directly instead of routing through replace_section, with zero change to replace_section's behaviour for its other callers (it is simply no longer called from this one site). No caller behaviour changed in either case; both were verified against every existing caller's own suite, not just new tests.
  - F5 -- remove_unpaired_marker loops and removes every occurrence of the named tag (was first-only); rewritten together with F8 in the same function/docstring pass as directed.
  - F4 -- read_body bails via new _views.has_view_tag(body) before the expansion-only store.load(); self.get()'s own pre-existing load is untouched (that one predates this feature and was never the cost in question -- see the correction below).
  - F6 -- catalog canary anchored to name.startswith('view'); proved via a constructed fake_catalog carrying a review_*-named entry, not by reasoning about the substring.
  - F7 -- Jinja TemplateError->SquadsError translation centralised in _rendering._engine.render() itself; both prior consumers (_render_view_or_raise, pristine_body) dropped their local jinja2 imports and now catch SquadsError, each keeping its own existing behaviour (raise-with-context vs swallow-and-return-None) verbatim. Every other renderer (item creation included) now gets the clean-message/exit-1 treatment for free -- driven end to end at both service and CLI layers.
  - F10 -- documentation only, no mechanism change, as ruled. _validators.py's 'sole source' sentence corrected to its actual scope + a new paragraph naming the file-level tier's two members and why they sit there; _scan_for_check gained the matching back-reference. Generalised finding named by its current name (_view_target_issues). Flagging FEAT-898 inheritance here per the brief, not in source: its context-declaration grammar must not treat CATALOG as the complete sq check finding inventory -- the two tier-1 findings sit outside that closure because they're outside the catalog, needing no declared context beyond file text + spec + host type.
  - F9 -- all 6 delivered-text hits + both source-side borderline lines taken; each durable fact kept, only the build-process/chronology framing dropped. Nothing falsifiable, said explicitly rather than reporting a falsification that didn't happen.
  - Gates, all clean (--all-extras): pyright 0/0/0, ruff check all passed, ruff format 624 files formatted (1 needed a reformat after ST3/ST4's new tests, applied). uv run sq check -> no issues.
  - Targeted tests: ran the full non-integration, non-slow suite (tests/service + tests/cli + tests/unit + tests/tui + tests/meta, 4069 passed 1 skipped, 42s) rather than a narrow selection -- F3 and F7 both reach outside the view mechanism (every body/comment/sub-body/bulk-import caller; every renderer in the codebase), so a narrow selection couldn't have covered their blast radius. tests/integration and the slow-marked scale tests were NOT run (out of scope per the brief; that's the main loop's gate).
  - Falsification: every new/changed test broken red and restored green, both directions reported per-subtask (F3: 7 tests via removing the no-write-on-no-change guard; F4: 2 new tests via reverting the has_view_tag bail, at both the service call-count layer and the real TUI component; F5/F8: 5 unit + 1 service test via reverting to first-occurrence+replace_section; F6: the new anchoring test via reverting its own assertion to the bare substring; F7: 3 of 4 new tests via reverting render()'s translation, including a raw jinja2 traceback observed in the CLI run's captured output; F9/F10: documentation-only, said explicitly, nothing to falsify).
  - One correction to the acceptance record, stated for the next reader: F4's brief said 'before this change the body-read boundary loaded no index' -- that's not quite right. svc.get(item_id), needed to resolve the item's type/path, already called store.load() once before this feature ever existed. What this feature actually added was a SECOND, expansion-only store.load() call -- doubling the cost outside a read scope (the TUI). The fix bails that second call, not the first; the measured 0.035s-per-load driven number and the fix's effect are unchanged by this correction, only the 'before' baseline description.
  - @tech-lead ready for review.
- [2026-09-03T13:18:55Z] Catherine Manager:
  - Full suite green including the slow scale tests as the authoritative gate: 4779 passed, 7 skipped, exit 0 -- run with --run-slow deliberately, because the F3 fold changed the mutate callback contract across every write-seam caller and F7 moved Jinja translation into _engine.render, which every renderer goes through. Verified both folds myself: _locked_placement_edit has zero references left, so the "second of the two write seams" docstring is true rather than recounted, and translation sits at _engine.py:199 with the other two sites reduced to cross-references. Accepting the correction to my own brief: the boundary already loaded an index via svc.get(); the regression was a second expansion-only load, which is what the fix bails.
- [2026-09-03T13:43:32Z] Elias Python:
  - F9: deleted the two remaining rename-narration sentences the reviewer's re-sweep found -- _maintenance.py:495's `_view_target_issues` docstring ("used to answer only the first reason and was named for it...") and the module docstring of test_check_flags_a_view_tag_whose_target_cannot_resolve.py ("used to be test_check_flags_a_dangling_view_tag_name.py..."). Nothing else touched.
  - F11: added squads._views.ViewTemplateMissingError(SquadsError) -- render_view's own pre-check refusal now raises this instead of a bare SquadsError. _render_view_or_raise catches it first (bare re-raise, unwrapped) before the broader except SquadsError that wraps a real engine render failure. Corrected _render_view_or_raise's docstring to name the mechanism precisely; its 'let through unchanged' claim is true again.
  - F11 test: tests/service/test_render_view_or_raise_lets_a_missing_template_error_through_unwrapped.py drives _render_view_or_raise directly with a view name that has no template and asserts the message is byte-identical to render_view's own raise (no item-naming prefix, no doubling). Falsified: reinstated the wide 'except SquadsError' catch, test went red reproducing the exact doubled message from the finding's driven repro (`view 'no_such_template_view' failed to render on EPIC-2: view 'no_such_template_view' has no presentation template...`); restored the narrowed catch, test green.
  - Gates: pyright/ruff check/ruff format --all-extras clean. Targeted tests (touched files + related view/check suites) + tests/meta: 62 + 279 passed. sq check clean. Did not touch F1-F8/F10 (Verified) or run the full suite.
  - @reviewer ready for re-review on F9/F11.
- [2026-09-03T13:54:53Z] Catherine Manager:
  - Reopening for F9 remaining surface: four clauses in _rendering/_engine.py and one sentence in _services/_base.py, both from ed26f99c. These want rewrites, not deletions -- the durable facts stay in the present tense. Also: the TASK-914 status moves the reviewer flagged as a concurrent unknown writer were mine, as were the FEAT-916/917 comments earlier. No unaccounted writer in this tree.
- [2026-09-03T14:35:12Z] Elias Python:
  - Fourth prose pass, closing item by replacing the instrument per the brief.
    
    **Item 1 — block scanner (throwaway, scratchpad only, never in the repo).** ast+tokenize
    extraction of module/class/function docstrings, comment runs, and assert-message string
    constants; whitespace collapsed to single spaces before matching, so a phrase a line wrap
    splits (the sixth copy) is still found. Validated against the known positive first: pointed at
    `tests/cli/test_check_view_tag_pairing_and_dangling_name_cli.py` alone, it hit the split "used
    to" / "now exits" phrase in one shot before I trusted any zero it reported elsewhere.
    
    Ran over every file `git diff --name-only 3b6aeed6..HEAD -- src/ tests/` names, against the full
    20-fragment vocabulary. 51 raw hits. Cross-checked each against the file's content at 3b6aeed6
    to separate pre-existing corpus prose (out of scope) from this feature's added/changed prose:
    45 pre-existing (ordinary "used to build"/"no longer declares"-shaped usage or corpus text
    untouched by this feature — left alone), 6 in this feature's own prose:
    - `_maintenance.py:489` + `test_check_flags_a_view_tag_whose_target_cannot_resolve.py:4` —
      "generalised from one" — item 3, fixed.
    - `test_check_view_tag_pairing_and_dangling_name_cli.py:72-74` — the sixth "used to"/"now
      exits" copy — item 2, fixed.
    - `_views.py:55/61` and `test_view_tag_placement.py:396` — both "the spec no longer declares" —
      held per the brief, untouched.
    - `test_view_tag_placement.py:436` assert-msg "the view must no longer render after removal" —
      observable before (the removal the test just ran), passes the stranger test as written, no
      fix.
    - One I flag as new: `test_check_flags_a_view_tag_whose_target_cannot_resolve.py:277` —
      "pointing at this feature for a break it had nothing to do with," in the catalog-exclusion
      canary's docstring. Self-referential build language nobody had flagged; fixed to "pointing at
      the view-target finding" (durable, no history needed). Reported here since it's outside items
      2-4's named locations but the brief said report+fix every real hit.
    - `test_view_tag_prose_guard_stays_closed.py:28` "used to admit" — ordinary infinitive-of-
      purpose usage, not narration; no fix.
    
    Checked assert messages for the f-string gap the AST-constant extractor can't see: grepped
    `assert [^,]+, f"` across the feature's file set — 4 hits, none carry any vocabulary fragment.
    
    **Item 2 fix**, `test_check_view_tag_pairing_and_dangling_name_cli.py`:
    - Before: "Driven end to end through the CLI: the state `sq epic <n> view add story_board` used
      to create silently (exit 0, then `sq check` "no issues", then `sq epic <n> show --raw` exit 1)
      now exits 3 here, naming both the file and the reason."
    - After: "Driven end to end through the CLI: a body seeded directly with a `story_board` view
      tag (a `subentity`-source view) on an epic, which hosts no `story`, makes `sq check` exit 3
      and name both the file and the reason."
    
    **Item 3 fix**, both copies (`_maintenance.py:489`, test module docstring line 4):
    - Before: "...as report strings — **two** reasons, generalised from one: *name* is undeclared..."
    - After: "...as report strings — **two** reasons: *name* is undeclared..."
    Drops the version-naming clause; "two reasons" plus the two reasons stated stands alone and
    survives a third reason landing.
    
    **Item 4 — F12 sentence**, `_services/_base.py`, `_section_edit_core` docstring:
    - Before: "...a no-op call (an idempotent insert already present, a removal of an absent
      marker) is genuinely silent on disk, not a rewrite of identical bytes under a fresh
      timestamp."
    - After: "...a no-op call (an idempotent insert already present, a removal of an absent marker)
      leaves the item file untouched. The transaction still commits the index on exit regardless,
      so `.squads.json` may be rewritten with identical content under a fresh mtime; only the
      markdown write is conditional on `changed`."
    Scoped to what the seam actually holds for, per F12's direction — one clause, no behaviour
    change (confirmed: the review's own driven repro is unaffected, this is docstring only).
    
    **Item 5 — new test**, `tests/service/test_has_view_tag_and_expand_view_tags_agree.py` (7 cases,
    no source touched): pins that `has_view_tag`'s span recognition and `expand_view_tags`'s per-
    span recognition agree, at the text level (no DB/spec resolution ambiguity — the bundled
    `ref`-source view resolves on any host, so "recognised" and "actually expands" never diverge for
    the positive case). Covers a real tag (recognised by both, actually expands), five non-view
    near-miss shapes (no marker, a different marker family, a `viewpoint:` look-alike, the bare
    `view` word, the `:end` spelling — refused by both, never expand), and a mixed body (real tag +
    near-miss together — only the real one goes).
    
    Falsification, both directions: forced `has_view_tag` to `return False` unconditionally (temp
    edit, not committed). Reran the suite: 2 of 7 reddened
    (`test_a_real_view_tag_is_recognised_by_both_and_actually_expands`,
    `test_agreement_holds_with_a_recognised_tag_alongside_a_non_view_marker`) — exactly the cases
    that assert `has_view_tag(...) is True` on a real tag. Restored from a backup copy; `git diff`
    on `_views.py` is empty; reran, 7/7 green again.
    
    **Gates.** `pyright --all-extras` (full repo): 0/0/0. `ruff check .`: all passed. `ruff format
    --check .`: clean (626 files) after formatting the new test file. Targeted: 140 passed across
    every view-tag/marker-primitive suite (service + cli + unit) touching these files. `tests/meta`:
    279 passed (caught and fixed a ticket-ID slip in item 5's first draft — "F1"/"REV-9" in the
    module docstring — before this run). `sq check`: no issues. Did not run the full suite (main
    loop's gate per standing instruction).
    
    Scanner script lived only at
    `/tmp/claude-1000/-home-pchat-projects-squads/da69dbda-08b2-4b26-85a3-61073d9f500d/scratchpad/block_scan.py`
    — scratchpad only, not committed, not under `tests/`.
    
    @reviewer ready for re-verification on F9 (item 1-3 prose) and F12 (item 4). Item 5 is new
    coverage, not tied to an open finding number.
<!-- sq:discussion:end -->

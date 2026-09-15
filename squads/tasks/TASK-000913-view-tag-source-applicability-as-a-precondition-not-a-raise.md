---
id: TASK-913
sequence_id: 913
type: task
title: 'View tag: source applicability as a precondition, not a raise'
status: Done
parent: FEAT-905
author: tech-lead
assignee: python-dev
priority: urgent
refs:
- ADR-880:implements
- REV-912:addresses
description: One widened predicate for placement, expansion and the file scan; the
  recogniser accepts the form its producers emit
subentities:
- local_id: ST1
  title: Recogniser accepts the form its producers emit
  status: Done
  story: US1
- local_id: ST2
  title: Widen the shared predicate to source applicability
  status: Done
  story: US1
- local_id: ST3
  title: Placement refuses a source-incompatible host
  status: Done
  story: US1
- local_id: ST4
  title: Expansion leaves an inapplicable tag literal
  status: Done
  story: US4
- local_id: ST5
  title: Generalise the file-level finding to two reasons
  status: Done
  story: US7
- local_id: ST6
  title: Correct US8 acceptance and cover the retype read
  status: Done
  story: US8
- local_id: ST7
  title: Gates, falsification, and the reviewer repros
  status: Done
  story: US4
created_at: '2026-09-03T12:03:18Z'
updated_at: '2026-09-03T14:37:54Z'
---
<!-- sq:body -->
## Scope

The predicate a `sq:view:<name>` tag's three consumers ask, and the recogniser all three route
through.

ADR-880's second amendment rules REV-912's F1 as a **classification**, not a resolver patch: a
view source's applicability to its host is **placement state**, not an engine defect. It joins
the quiet half — the tag is left exactly as authored, the read succeeds, and the always-on
file-level scan reports it. The same amendment corrects two sentences of the first amendment,
one of which US8's acceptance inherited, and that correction lands here with the mechanism.

Tags are spelled bare below (`sq:view:<name>`) rather than in their HTML-comment form, as the
ADR record does, because the prose guard refuses a well-formed tag in any authored input.

**Additive to what shipped.** The placement verb, the expansion boundary and the file-level
scan all stay where they are; each learns one wider question. FEAT-903 widens the source kinds
and FEAT-904 deletes the projection layer; neither is in scope.

## What lands

**One predicate, three questions, asked once.** Today's shared resolution helper asks two —
declared in the active spec, and the presentation template resolves. It gains a third: does the
declared source apply to **this host's type**. One helper beside it in `_views.py`, resolving
each kind's constraint off `WorkflowSpec` methods, never a second implementation at a consumer.
It answers with the reason it refused rather than a bare boolean, so the placement refusal and
the scan finding compose the same cause in one place instead of each writing its own sentence.

The decisive property, and the reason this is cheap: a source's applicability is a function of
the view, the active spec and the host item's **type** — never of the host item's content.
`WorkflowSpec.item_subentity_kind` takes a type string and returns the kind or `None`; nothing
here needs a resolved `Item`.

Three clauses from the amendment's classification test bind the predicate, and a future kind is
judged by them:

- **A resolver may not raise for a condition its kind's predicate could have decided.** Every
  raise left inside a resolver is a defect signal. A kind arrives with its predicate declared
  beside its resolver; a kind with no host constraint declares its predicate constantly true,
  explicitly, rather than by saying nothing.
- **A predicate may not read the host item's content** — not its refs, not its sub-entities,
  not its status. It is a question about a type, which is what keeps it answerable by all three
  consumers and keeps it out of the per-item catalog.
- **Emptiness is never a failure.** A precondition covers only conditions under which a
  resolver cannot produce a well-formed result at all, never conditions under which it produces
  an empty one. A host with no members renders an empty projection; a subtree source over a
  type this host will never in practice parent yields zero rows, and that is the correct
  answer. Without this clause the predicate grows into a reachability analysis over the parent
  graph — a second query layer arriving through the back door.

**The recogniser accepts the form its producers emit.** The one shape recogniser takes the bare
tag, while both producers of a tag string (`sections.find_markers` and `sections
.iter_marker_spans`) return it with its `sq:` prefix still attached — and the mismatch fails by
returning `None`, which every caller reads as "not a view tag" and acts on silently. Two call
sites carry the strip by hand today, and this task adds consumers to that same seam. One
contract survives: either the recogniser accepts the on-disk form, or the producers hand back
bare tags. No call site re-derives it, and a test names the producer so the next caller cannot
get it wrong quietly.

**The generalised finding.** The existing file-level finding asks exactly the predicate
expansion gates on, so widening the predicate widens the finding for free — one helper, two
reasons, one message each, **not a sibling function**. Its "dangling" name stops being
accurate: it now reports one of two reasons. It stays error-level, unconditional, in the
always-on file-level marker scan and **not** as a validator-catalog member — ruled correct
there on two properties this second reason also has. The host type is already bound in the scan
loop from the type folder and filename, before frontmatter parses, so the finding needs no
resolved item and keeps firing on a file too broken to parse.

## Acceptance

**Closes F1 (critical) and F2 (high) on the review.**

**The widened predicate — F1.**
- One helper, three questions, one call per consumer. No consumer asks a second question of its
  own about applicability, and no consumer re-spells a source-kind name as a literal.
- Each shipped kind's constraint is declared beside its resolver and resolved off `WorkflowSpec`
  methods. The two kinds that impose nothing on the host declare that explicitly.
- The helper carries the refusal reason; the placement refusal and the scan message are composed
  from it, not written twice.
- No raise remains in a resolver for a condition the predicate can decide.
- The predicate reads the host item's type and the active spec. It reads no item content — assert
  this structurally, not only by inspection.

**Placement refuses at the door — F1.**
- The insert verb refuses a source-incompatible host through the widened predicate, exactly as it
  already refuses an undeclared name, and the message names the cause.
- The remove verb stays ungated, for the reason already written into it: taking a tag off a
  document must keep working for a view the spec no longer declares, and it is the recovery path
  for precisely this state.

**Expansion leaves the tag literal — F1.**
- A tag whose precondition fails is left byte for byte and the read succeeds, on every surface the
  single body-read boundary feeds.
- **Quiet never means empty.** The tag is not replaced with an empty rendering, a placeholder or a
  comment. The bytes on disk and the bytes read back are the same.
- **The explicit resolve path keeps raising, unconditionally.** Naming a view and an item directly
  is a direct question, and an inapplicable pair is a bad argument pair. Only tag expansion at the
  body-read boundary takes the quiet half; moving the quiet half into the explicit resolve breaks
  that command.
- The remaining loud half keeps its three inhabitants and loses its label: a template raising
  under `StrictUndefined` (bundled or an adopter's override), a resolver failing for anything its
  predicate could not have decided, and the narrow race where a template resolves at the gate and
  is gone at the render. "Engine defect" mis-described the first of those; an adopter's broken
  override template is not our bug and still fails loud, because a fault in the spec or override
  tree already fails loud everywhere while a fault in the corpus never breaks a read.

**The finding — F1.**
- Error-level, unconditional, in the file-level scan beside its neighbour. Not a catalog member,
  no level knob, no coupling to the validator-assignment grammar.
- One helper reporting two reasons with one message each. The name reflects both.
- It fires on a file whose frontmatter does not parse.
- Dynamic text reaching the console is escaped.

**Nothing is rewritten — F1.**
- For a tag that was valid when placed and is not any more: not stripped, not relocated, not
  silently repaired, and `retype` gains no refusal. Three legitimate paths reach that state —
  retype, a spec or override edit changing what a type hosts, and a creation template seeding a
  tag for a type a later override changes.
- The finding is keyed on the state as it currently stands, never on how the tag arrived. Nothing
  records a tag's provenance, so a rule that varied by arrival path would be unimplementable as
  well as wrong.

**US8's acceptance correction — F1.**
- US8 keeps its ruling: the tag is a property of the document, retype preserves the document, and
  no type-scoping is added to a view.
- It loses the inherited claim that the check does not fire "because a view is no longer
  type-scoped and the name still resolves". A view's **name** is not type-scoped; a subentity
  source's **applicability** is. The two were collapsed.
- Retype's behaviour is unchanged; its outcome is what changes. The same retype that today
  produces a clean check and an unreadable item produces a readable item and a reported finding.
- Correct US8's acceptance text on the parent feature and the mapped subtask so the record does
  not keep asserting the collapsed form.

**The recogniser contract — F2.**
- Producer and recogniser agree on one form. Both hand-strips disappear; nothing re-derives the
  family prefix at a call site.
- A test names the producer and pins the accepted form, so a fourth surface passing the on-disk
  form straight through cannot silently do nothing.
- The existing shape suite gains the prefixed case it does not currently have, alongside the bare
  form, the other families, the closing spelling and the near-miss names it already covers.
- Silent `None` is no longer reachable for a well-formed tag from either producer.

**Falsification, and the reviewer's repros driven green.**
- Every new or changed test is broken red and restored green, with **both** directions reported in
  the handback — the mutation made, the tests that reddened, and the restoration.
- The reviewer's repro drives green on both doors. Door one: a subentity-source view declared in
  an overrides workflow with its template present, placed on a non-hosting host — placement is
  refused at the door. Door two: the same tag arriving by `retype` — the read succeeds with the
  tag left byte-for-byte literal, and the check reports an error.
- Coverage is table-driven over host type by source kind, not one case per implemented branch:
  each shipped kind against a hosting and a non-hosting host, the closing-spelling and duplicate
  controls that must keep behaving as they do, and the empty-result shape that must **not** be a
  failure (a hosting host with zero records renders empty and checks clean).
- The retype suite gains a body-read assertion. It asserts surviving bytes and a clean check today
  and never reads the body, which is how this class of failure reached review.

## Engineering constraints

- Layering is `_cli` -> `_services` -> (index store, backends, rendering); `_models` has no
  internal deps. Every implementation module stays private and package `__init__` files do not
  re-export.
- Marker-safe edits only, through `_sections.py`. Never rewrite an agent-authored body.
- **The tag stays unpaired.** No closing counterpart for the family, and no verb writes content
  adjacent to one. Materialisation needs a span to write into and there is none.
- The active spec is threaded, never a module global. No new module-level mutable state; a new
  module constant needs the meta suite run.
- Every refusal is a `SquadsError`. Dynamic console text is escaped.
- Gate before handback: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .`, and `uv run sq check` clean. Run the touched
  suites with a path selector; **do not run the full suite** — that gate is the main loop's, and
  a backgrounded full run does not survive the handback.

## Out of scope — do not build

- FEAT-903's three new source kinds. Each declares its own applicability predicate as part of
  landing there, read against the same test; the amendment already reads all three and none needs
  the host's content. Leave the predicate a place to hang them and anticipate nothing else.
- The nine other findings on the review. They land on the follow-up task and several touch the
  same files, so they are sequenced after this one rather than merged into it.
- Any change to `retype` itself.
- Moving the finding into the per-item validator catalog. Ruled correct where it sits, twice.
- The warn-level advisory for an item whose creation template seeds a tag it no longer carries.
  Its condition is keyed on that template as it currently stands, so it rides FEAT-907.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 913 add-subtask "<title>"`; track with `sq task 913 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Recogniser accepts the form its producers emit

<!-- sq:subtask:ST1:body -->
Closes F2 (high). The one shape recogniser takes the bare tag while both producers of a tag
string return it with its `sq:` prefix attached, and the mismatch fails by returning nothing —
which every caller reads as "not a view tag" and acts on silently. Two call sites carry the
strip by hand and this task adds consumers to the same seam. Settle one contract: either the
recogniser accepts the on-disk form, or the producers hand back bare tags. Both hand-strips
disappear and no call site re-derives the family prefix. A test names the producer and pins the
accepted form, and the existing shape suite gains the prefixed case it lacks, alongside the bare
form, the other families, the closing spelling and the near-miss names it already covers. Silent
non-recognition is no longer reachable for a well-formed tag from either producer.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-09-03T12:22:06Z] Elias Python:
  - Recogniser accepts both the bare form and the sq:-prefixed on-disk form find_markers/iter_marker_spans emit. Both hand-strips removed (_views.py expand_view_tags, _maintenance.py's finding). Falsified: reverting the prefix-strip branch reddened 8 tests (the new shape tests + the existing dangling-name check suite, since it now feeds the raw producer form straight through); restored green.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Widen the shared predicate to source applicability

<!-- sq:subtask:ST2:body -->
Closes F1 (critical), the predicate itself. The shared resolution helper's two questions become
three — declared in the active spec, presentation template resolves, and the declared source
applies to this host's type — in one helper beside it, resolving each kind's constraint off
spec methods and never re-implemented at a consumer. It answers with the reason it refused
rather than a bare boolean, so the placement refusal and the scan message compose the same cause
in one place. Applicability is a function of the view, the active spec and the host item's type,
never of the host item's content: the spec method that answers it takes a type string, so
nothing here needs a resolved item. Three clauses bind it and judge every future kind: a
resolver may not raise for a condition its kind's predicate could have decided, and a kind with
no host constraint declares its predicate constantly true explicitly rather than by saying
nothing; a predicate may not read the host item's content, not its refs, sub-entities or status;
and emptiness is never a failure — a host with zero records renders empty, which is the correct
answer, and without that clause the predicate grows into a reachability analysis over the parent
graph. Assert the content-blindness structurally, not only by inspection.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-09-03T12:26:22Z] Elias Python:
  - Widened predicate landed in _views.py: resolve_view_target (3 questions) + _SOURCE_APPLICABILITY registry (ref/subtree explicitly true, subentity checks item_subentity_kind) + _source_incompatibility. Raise removed from the three per-kind resolvers per corollary 1; moved to resolve_records (the dispatcher), which is what keeps the explicit-resolve path (sq workflow view) raising unconditionally per ADR-880 second amendment section 5.
- [2026-09-03T12:26:26Z] Elias Python:
  - New unit suite tests/unit/test_view_source_applicability_predicate.py: table-driven hosting/non-hosting per kind, ref/subtree constantly-true, emptiness-not-failure, and two structural properties (no raise in any per-kind resolver via AST, predicate signatures are type-scoped not Item-scoped). Falsified: removing resolve_records's gate reddened 3 tests (2 new structural/behavioural + the pre-existing test_a_view_over_the_wrong_source_item_type_is_refused); restored green.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Placement refuses a source-incompatible host

<!-- sq:subtask:ST3:body -->
Closes F1's placement door. The insert verb refuses a source-incompatible host through the
widened predicate, exactly as it already refuses an undeclared name, and its message names the
cause the predicate returned. The remove verb stays ungated for the reason already written into
it: taking a tag off a document must keep working for a view the spec no longer declares, and it
is the recovery path for precisely this state. The door is not the guarantee — the state is
reachable without passing through it — so nothing here treats the refusal as sufficient.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-09-03T12:29:08Z] Elias Python:
  - insert_view now checks resolve_view_target(name, item.type, self.spec) inside the mutate closure (single item load, no TOCTOU race, matches the existing KeyError-to-SquadsError idiom); remove_view stays ungated per the ADR.
- [2026-09-03T12:29:10Z] Elias Python:
  - Tests added: tests/service/test_view_tag_placement.py (hosting-succeeds control, non-hosting-refused = the reviewer's repro, table-driven host-type x kind over every bundled hosting pair, ref-source-unaffected control) and tests/cli/test_view_tag_placement_cli.py (the reviewer's exact CLI repro: sq epic <n> view add story_board now exits 1 with 'hosts' before any write, was exit 0 'placed').
- [2026-09-03T12:29:14Z] Elias Python:
  - Falsified: removing insert_view's gate reddened exactly the 6 refusal-path tests (undeclared name, no-template, non-hosting repro, 3/6 table rows) while all hosting/control tests stayed green; restored, all green.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Expansion leaves an inapplicable tag literal

<!-- sq:subtask:ST4:body -->
Closes F1's read half. A tag whose precondition fails is left byte for byte and the read
succeeds on every surface the single body-read boundary feeds. Quiet never means empty: the tag
is not replaced with an empty rendering, a placeholder or a comment, so the bytes on disk and
the bytes read back are the same. The explicit resolve path keeps raising unconditionally —
naming a view and an item directly is a direct question and an inapplicable pair is a bad
argument pair; only tag expansion at the body-read boundary takes the quiet half, and moving the
quiet half into the explicit resolve breaks that command. The loud half keeps its three
inhabitants and loses its label: a template raising under strict undefined mode whether bundled
or an adopter's override, a resolver failing for anything its predicate could not have decided,
and the narrow race where a template resolves at the gate and is gone at the render. An
adopter's broken override template is not our bug and still fails loud, because a fault in the
spec or override tree already fails loud everywhere while a fault in the corpus never breaks a
read.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-09-03T12:31:18Z] Elias Python:
  - expand_view_tags now gates through resolve_view_target(name, item.type, spec); an inapplicable tag is left byte-for-byte literal and the read succeeds, same quiet disposition as the two existing failure modes. resolve_records's own defensive raise (ST2) provides defense in depth if a caller ever skips the gate.
- [2026-09-03T12:31:22Z] Elias Python:
  - Tests: service-level table-driven host x kind, hosting/non-hosting/empty-not-a-failure/ref-unaffected controls in test_view_tag_expansion_at_read_time.py; CLI-level reviewer repro (sq epic <n> show --raw / --json) driven to green in test_view_tag_expansion_at_read_time_cli.py.
- [2026-09-03T12:31:24Z] Elias Python:
  - Falsified: reverting the read-time gate to the old two-question check reddened both new applicability tests (the dispatcher's own defensive raise from ST2 surfaced the failure as an uncaught SquadsError rather than a silently wrong body); restored, all green.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Generalise the file-level finding to two reasons

<!-- sq:subtask:ST5:body -->
Closes F1's reporting half. The existing file-level finding asks exactly the predicate expansion
gates on, so widening the predicate widens the finding — one helper reporting two reasons with
one message each, not a sibling function, and its name reflects both rather than describing one.
Error-level, unconditional, in the always-on file-level marker scan beside its neighbour: no
level knob, no coupling to the validator-assignment grammar, and not a per-item catalog member.
The host type is already bound in the scan loop from the type folder and the filename, before
frontmatter parses, so the finding needs no resolved item and keeps firing on a file too broken
to parse — which is exactly where a finding about an unreadable document earns its keep. Dynamic
text reaching the console is escaped. Nothing is rewritten for a tag that was valid when placed
and is not any more: not stripped, not relocated, not silently repaired. The finding is keyed on
the state as it currently stands, never on how the tag arrived, because nothing records a tag's
provenance.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-09-03T12:34:18Z] Elias Python:
  - Renamed _dangling_view_issues -> _view_target_issues; now takes item_type (bound by the scan loop from folder+filename before read_frontmatter) and asks resolve_view_target, reporting either reason with one composed message. Call site in _scan_for_check updated. Test file renamed test_check_flags_a_dangling_view_tag_name.py -> test_check_flags_a_view_tag_whose_target_cannot_resolve.py (no ticket ID, behavior-named).
- [2026-09-03T12:34:19Z] Elias Python:
  - New tests: source-incompatible reason (REV-912 F1's own repro), hosting positive control, table-driven host x kind, ref-source-unaffected control, catalog-membership structural check -- at both service and CLI level (sq check exits 3, names file + 'hosts'). Existing reason-1 coverage (undeclared/no-template/duplicate/multi-name/catalog-free) all kept and still green.
- [2026-09-03T12:34:24Z] Elias Python:
  - Falsified: reverting _view_target_issues to ask only 'declared' (dropping template+applicability) reddened exactly 6 tests -- the no-template reason, the source-incompatible reason (service+CLI), and 3/6 table rows; restored, all green (253 passed across the wider marker/view/check test surface).
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Correct US8 acceptance and cover the retype read

<!-- sq:subtask:ST6:body -->
Closes F1's inherited acceptance error. US8 keeps its ruling — the tag is a property of the
document, retype preserves the document, no type-scoping is added to a view and retype gains no
refusal — and loses the claim that the check does not fire "because a view is no longer
type-scoped and the name still resolves". A view's name is not type-scoped; a subentity source's
applicability is, and the two were collapsed. Retype's behaviour is unchanged and its outcome is
what changes: the same retype that produces a clean check and an unreadable item produces a
readable item and a reported finding. Correct the acceptance text on the parent feature's US8
and on the mapped subtask so the record stops asserting the collapsed form. The retype suite
gains a body-read assertion; it asserts surviving bytes and a clean check today and never reads
the body, which is how this class of failure reached review.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-09-03T12:36:33Z] Elias Python:
  - US8 acceptance corrected on FEAT-905's story and TASK-911's mapped ST4: kept the ruling (tag rides along, retype gets no refusal, name resolution still works) and dropped the collapsed sentence ('a view is no longer type-scoped and the name still resolves'). Name is not type-scoped; a subentity source's applicability is -- the two were collapsed.
- [2026-09-03T12:36:36Z] Elias Python:
  - Retype suite gains a body-read assertion: the reviewer's own second repro (Path B), driven to green -- a subentity view valid on feature (hosts story), retyped to epic (hosts nothing): read_body succeeds with the tag left literal, and sq check reports the applicability finding naming 'hosts'. Existing tests also now call read_body (previously only asserted stored bytes + clean check, which is how F1 reached review).
- [2026-09-03T12:36:40Z] Elias Python:
  - Falsified: reverting expand_view_tags to the un-widened two-question gate reddened exactly the new retype repro test (via the resolve_records dispatcher's defensive raise -- read_body raised SquadsError instead of returning literal text); restored, green.
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Gates, falsification, and the reviewer repros

<!-- sq:subtask:ST7:body -->
Falsification and the reviewer's own repros. Every new or changed test is broken red and
restored green, with both directions reported in the handback — the mutation made, the tests
that reddened, and the restoration. The repro drives green on both doors: a subentity-source
view declared in an overrides workflow with its template present, placed on a non-hosting host,
is refused at the door; and the same tag arriving by retype reads successfully with the tag left
byte-for-byte literal while the file scan reports an error. Coverage is table-driven over host
type by source kind rather than one case per implemented branch — each shipped kind against a
hosting and a non-hosting host, the closing-spelling and duplicate controls that must keep
behaving as they do, and the empty-result shape that must not be a failure. Then the gates:
pyright, ruff check and ruff format with all extras, and the check clean. Run the touched suites
with a path selector, not the full suite.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T12:47:07Z] Elias Python:
  - Final handback. All 7 subtasks Done; per-ST detail and falsification already recorded on each.
    This comment is the consolidated summary plus decisions/gaps worth flagging.
    
    ## Gates (all clean, --all-extras)
    
        uv run --all-extras pyright                 -> 0 errors, 0 warnings, 0 informations
        uv run --all-extras ruff check .             -> All checks passed!
        uv run --all-extras ruff format --check .    -> 621 files already formatted
        uv run --all-extras pytest tests/meta        -> 279 passed
        uv run sq check                              -> no issues
    
    Targeted suite (touched files + tests/meta together): 482 passed, 0 failed.
    (unit/test_unpaired_view_tag_shape_recognition, unit/test_view_source_applicability_predicate,
    unit/test_view_projection_engine, unit/test_view_expresses_the_subentity_summary_shape,
    unit/test_view_declaration_referential_checks, service/test_view_tag_placement,
    service/test_view_tag_expansion_at_read_time, service/test_check_flags_a_view_tag_whose_target_cannot_resolve,
    service/test_check_exempts_the_view_tag_family_from_marker_pairing,
    service/test_retype_carries_a_view_tag_and_check_stays_clean, service/test_repair_leaves_view_tags_untouched,
    service/test_view_resolve_and_render, service/test_view_tag_prose_guard_stays_closed,
    cli/test_view_tag_placement_cli, cli/test_view_tag_expansion_at_read_time_cli,
    cli/test_check_view_tag_pairing_and_dangling_name_cli, cli/test_view_tag_prose_guard_stays_closed_cli,
    cli/test_workflow_views_cli, meta/*)
    
    ## Reviewer's repros, driven to green
    
    Door one (placement): `sq epic <n> view add story_board` (subentity source over `story`, epic
    hosts none) now exits 1 naming the cause, before any write -- was exit 0 "placed".
    service/test_view_tag_placement.py::test_insert_a_subentity_source_view_onto_a_non_hosting_type_is_refused
    and cli/test_view_tag_placement_cli.py::test_view_add_a_source_incompatible_host_exits_nonzero_with_a_clear_message.
    
    Door two (retype): a subentity view valid on feature (hosts story), retyped to epic -- read_body
    now succeeds with the tag left byte-for-byte literal, and sq check reports the applicability
    finding naming "hosts". service/test_retype_carries_a_view_tag_and_check_stays_clean.py::test_retype_onto_a_non_hosting_type_reads_literal_and_check_reports_it,
    plus the check-surface CLI repro (sq check exits 3, was clean) in
    cli/test_check_view_tag_pairing_and_dangling_name_cli.py::test_check_exits_3_and_names_the_view_for_a_source_incompatible_host,
    and the show --raw / --json repro in cli/test_view_tag_expansion_at_read_time_cli.py.
    
    ## Shape of the fix
    
    - squads/_models/_markers.py: view_tag_name now accepts BOTH the bare form and the sq:-prefixed
      on-disk form find_markers/iter_marker_spans actually emit -- both existing hand-strips (in
      _views.py and _services/_maintenance.py) removed, no call site re-derives the prefix.
    - squads/_views.py: resolve_view_target(name, item_type, spec) -> str | None replaces
      view_target_exists -- three questions (declared, template resolves, source applies to
      item_type), one reason string. _SOURCE_APPLICABILITY maps each declared source.kind to a
      predicate (_ref_source_applies/_subtree_source_applies declare "always true" explicitly;
      _subentity_source_applies checks WorkflowSpec.item_subentity_kind). All three read only a
      type string + the spec, never an Item -- checked structurally in the new unit suite.
    - The raise removed from _resolve_subentity_source (corollary: a per-kind resolver may not
      raise for a decidable condition) moved up to resolve_records (the dispatcher), which is what
      keeps `sq workflow view` / ViewsMixin.resolve_view raising unconditionally for an
      incompatible pair -- confirmed both by the pre-existing test
      (test_a_view_over_the_wrong_source_item_type_is_refused) and a new one driving
      resolve_records directly.
    - ViewsMixin.insert_view asks resolve_view_target inside its mutate closure (single item load,
      no TOCTOU race); remove_view stays fully ungated.
    - expand_view_tags gates through resolve_view_target; an inapplicable tag is left literal, read
      succeeds -- same quiet disposition the two existing failure modes already had.
    - _dangling_view_issues renamed to _view_target_issues, now takes item_type (bound by the scan
      loop from folder+filename before read_frontmatter) and reports either reason through one
      message each, composed from the predicate's own reason string. New test confirms it still
      fires on a file whose frontmatter does not parse at all (falsified: reordering the call after
      the frontmatter try/except reddened it).
    
    ## Decisions I made that the record didn't spell out
    
    1. **F2's direction: "accept both forms", not "accept only the on-disk form".** The review
       offered "make the recogniser accept the on-disk form (or both)" as two options; the task
       title says "the recogniser accepts the form its producers emit" without settling which. I
       chose "both" -- it keeps view_tag()'s bare-form contract and the existing round-trip test
       (`view_tag_name(view_tag(name)) == name`) intact with zero changes, while still eliminating
       both hand-strips (callers now just pass find_markers'/iter_marker_spans' raw output
       straight through). If the intent was narrower -- reject the bare form outright -- say so and
       I'll tighten it; nothing today calls view_tag_name with a bare form in production code, only
       the unit suite's own round-trip/shape tests do.
    
    2. **"A resolver may not raise" reconciled against "the explicit resolve path keeps raising
       unconditionally".** Read together those two clauses look like they contradict for the
       subentity kind -- if _resolve_subentity_source can't raise, what makes `sq workflow view`
       raise for an incompatible pair? I resolved it by reading "resolver" narrowly as the per-kind
       function (_resolve_subentity_source etc.), and moved the raise one level up to the shared
       dispatcher (resolve_records) that every caller already goes through. The per-kind resolvers
       now contain no raise anywhere (checked via ast.walk, not a substring match -- a couple of
       their own docstrings say the word "raise" describing why they don't). If "resolver" was
       meant to cover the dispatcher too, the explicit-resolve raise needs a different home (the
       service method itself); flag if so.
    
    3. **Applicability predicates live in one shared section, not literally inside each resolver
       function.** "Declared beside its resolver" I read as "adjacent in the module, not scattered
       or hidden," not as "inside the resolver's own body" (which the no-raise corollary rules out
       anyway, since the predicate has to run *before* the resolver to decide whether to call it at
       all). The three predicates sit together right after the three resolvers, before the
       dispatcher.
    
    ## One acceptance case I could not build a positive-path test for
    
    No two bundled item types share a subentity_kind (task->subtask, feature->story,
    review->finding, each unique -- checked directly). So there's no real "retype between two
    types that both still host the same kind" pairing to drive as a positive control at the retype
    layer specifically. That property IS covered -- at the placement and expansion layers, table-
    driven over every bundled host x kind pair including the "applies=True" rows -- just not
    *through a retype*. I judged constructing a synthetic two-hosting-types override spec solely to
    close this specific gap not worth the fixture weight versus what it would prove beyond what the
    tables already do; said here rather than silently omitted.
    
    @tech-lead for review dispatch when ready. TASK-914 not started, per brief.
- [2026-09-03T12:49:17Z] Catherine Manager:
  - Full suite green as the authoritative gate: 4759 passed, 12 skipped, exit 0. Traced the fix myself rather than accepting the handback: expand_view_tags now gates on resolve_view_target(name, item.type, spec) and leaves the tag literal on any reason, so resolve_records is only reached once the predicate says the source applies -- any raise arriving there is a genuine defect signal, which is corollary 1. sq workflow view still calls resolve_records directly and raises unconditionally, per the amendments explicit fence. F1 and F2 marked Fixed on REV-912.
<!-- sq:discussion:end -->

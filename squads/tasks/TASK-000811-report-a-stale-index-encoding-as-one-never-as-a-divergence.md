---
id: TASK-811
sequence_id: 811
type: task
title: Report a stale index encoding as one, never as a divergence
status: Done
parent: FEAT-790
author: tech-lead
assignee: python-dev
priority: medium
refs:
- ADR-775:implements
- REV-808:addresses
- TASK-806
description: Separate a stale index encoding from a real on-disk divergence at the
  skew site, and say which one it is in the refusal and the sq check finding
subentities:
- local_id: ST1
  title: Separate normalisation from divergence at the skew site
  status: Done
  story: US1
- local_id: ST2
  title: One wording for one state on both surfaces
  status: Done
  story: US1
- local_id: ST3
  title: Coverage for the three skew states
  status: Done
  story: US1
created_at: '2026-08-25T18:09:31Z'
updated_at: '2026-08-25T23:40:00Z'
---
<!-- sq:body -->
## Scope

ADR-775 amendment A4, on FEAT-790 US1. The skew guard's *decision* is right and does not change;
its *diagnosis* is false and is the only thing owed.

A squad holding `refs: [TASK-20:related]` in the file and `["TASK-20:related"]` in the index —
the same bytes on both sides — is refused on its next mutation with `on-disk frontmatter has
diverged from the index (refs)`, and `sq check` reports `refs drift between frontmatter and
index`. Nothing diverged. `frontmatter_skew` compares the disk side **after** the fold against
the index side **as stored** — an asymmetry its own docstring records as deliberate and
load-bearing (`_itemfile.py:192-198`) — so what the guard sees is the fold it applied to one
side, not a change to the file.

**The refusal stands.** The index genuinely holds a non-canonical encoding, and rewriting the
file from an index-derived item would commit the spelled form — exactly the write the guard
exists to stop. Only the wording changes.

## The standing rule this serves

A4 gives the existing rule a companion: **a refusal may not assert a cause the reader can
disprove.** An adopter sent to `sq repair` for a divergence they can open the file and see is
not there learns to distrust the guard, which is the one thing a guard on the integrity core
cannot afford.

## The two surfaces, which must say the same thing

Both consume the same `list[str]` of diverging keys from `frontmatter_skew`, so both move
together or they disagree:

- **`_itemfile.py:251-260` — `skew_message`.** The refusal raised at every single-mutation write
  seam, and reused by `sq sync`'s skip-and-report line and by the bulk importer's `ImportIssue`.
- **`_services/_maintenance.py:215-227` — `_drift_message`.** The `sq check` finding, produced by
  `_value_skew_issue` (`:230-260`), which calls `frontmatter_skew` verbatim so that check reports
  exactly the set the write seam would refuse on.

One state, one explanation, in the same words on both.

## The discrimination, and the case A4's test does not cover on its own

A4 rules the two cases separable at the site from data already in hand: `frontmatter_skew` holds
both the raw parsed frontmatter and its round-tripped form, and a diverging key whose **raw**
on-disk value already equals the index's is a normalisation difference by construction, because
the round trip only ever adds corrections.

Driven, in-process against the installed package, three states:

| State | Diverging | Raw disk == index? | Wanted verdict |
| --- | --- | --- | --- |
| index holds `["BUG-20:related"]`, file holds `refs: [BUG-20:related]` | `refs` | **yes** | stale encoding |
| file holds `refs: [BUG-20]` + `extra.ref_kinds: {BUG-20: blocks}`, index holds `["BUG-20"]` | `refs` | **yes** | needs repair |
| file's `title` hand-edited, `refs` differ | `refs`, `title` | no | needs repair |

The raw-equality test alone gets rows one and three right and **row two wrong**. A4 reasons that
the legacy map "differs raw", and the `extra` key does — but the round trip pops `ref_kinds` out
of `extra`, so `extra` never reaches the diverging list at all. Only `refs` does, and its raw
value `['BUG-20']` equals the index's `['BUG-20']`. Verified by driving `frontmatter_skew`
directly on both states.

So the discrimination needs one more input, and the file already establishes the pattern for
exactly this: `_invented_timestamps` (`_itemfile.py:240-248`) reads the **raw** frontmatter
before the round trip, for the stated reason that "once the value has been invented the two cases
are indistinguishable, which is precisely why the comparison had to be told about them here". A
key whose fold drew on information from another raw key is the same shape: the raw values match,
but the difference is information-adding, not normalisation.

Whatever form it takes, the rule must be stated where it is computed, and row two must come out
as needing repair.

## What each message says

- **A real divergence keeps today's wording**, unchanged, on both surfaces.
- **A stale encoding says what it is**: the index holds a non-canonical encoding of this item's
  refs, `sq repair` re-derives it, and the next ordinary write canonicalises the file. It must
  not say the file diverged, and it must not name a cause the reader can open the file and
  disprove.
- A refusal is still a refusal. The wording changes; the exit does not.

## Out of scope, ruled explicitly by A4

- **No migration `manual` clause.** It would instruct an adopter to run the repair
  `sq migrate up` had just run on their behalf.
- **No release note.** It would describe a state the upgrade path does not let them reach.

The message is the notification, which is precisely why it has to be true. Neither exclusion is
an oversight to be helpfully corrected.

## Traps

- **`frontmatter_skew` returns a `list[str]` and two callers unpack it.** Whatever carries the
  classification out has to reach both, or the two surfaces drift apart — which is the specific
  thing `_value_skew_issue`'s docstring says it exists to prevent.
- **Do not store the classification.** Nothing new goes in the index or in frontmatter; the
  discrimination is computed at the one site that already holds both sides.
- **`_models/` gains no vocabulary.** The site already receives the resolved default kind as an
  argument; that split stays.
- **A mixed item is possible** — one key stale-encoded and another genuinely diverged. Decide
  what a mixed report says rather than letting whichever branch runs first speak for both.
- **`PERMITTED_EXTRA_SKEW` is excluded before any of this** (`_itemfile.py:207-227`) and stays
  excluded; it is not a third case.
- **No bundled template is touched**, so no manifest regeneration, and `scripts/bump_version.py`
  must not be run.

## Acceptance

- A squad whose index holds a spelled default kind and whose file holds the same bytes is still
  refused on its next mutation, with a message that names the index's non-canonical encoding as
  the cause and does not claim the file diverged.
- `sq check` reports that same state in the same words, at the same severity it reports today.
- A genuine on-disk divergence keeps today's wording on both surfaces, unchanged.
- The legacy `extra.ref_kinds` case comes out as needing repair, on both surfaces — asserted with
  the map naming a non-default kind, the row the raw-equality test alone misclassifies.
- An item carrying both a stale-encoded key and a genuinely diverged key reports both, and does
  not describe one as the other.
- Nothing new is stored, and the classification is computed at the single site that already holds
  the raw and round-tripped sides.
- No migration `manual` clause and no CHANGELOG line describe this state.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 811 add-subtask "<title>"`; track with `sq task 811 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Separate normalisation from divergence at the skew site | US1 |
| ST2 | Done |  | One wording for one state on both surfaces | US1 |
| ST3 | Done |  | Coverage for the three skew states | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Separate normalisation from divergence at the skew site

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Declare [ref_kinds] as a workflow-spec section
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Separate the two states at `frontmatter_skew` (`_itemfile.py:182-237`), the one site that
already holds both the raw parsed frontmatter and its round-tripped form, and carry the
classification out to the callers.

The test ADR-775 A4 gives: a diverging key whose **raw** on-disk value already equals the index's
is a normalisation difference by construction, because the round trip only ever adds corrections.

**That test is not sufficient on its own, and the gap is exactly one row.** Driven in-process
against the installed package:

| State | Diverging | Raw disk == index? | Wanted |
| --- | --- | --- | --- |
| index `["BUG-20:related"]`, file `refs: [BUG-20:related]` | `refs` | yes | stale encoding |
| file `refs: [BUG-20]` + `extra.ref_kinds: {BUG-20: blocks}`, index `["BUG-20"]` | `refs` | yes | needs repair |
| file's `title` hand-edited | `refs`, `title` | no | needs repair |

A4 reasons the legacy map "differs raw", and the `extra` key does — but the round trip pops
`ref_kinds` out of `extra`, so `extra` never reaches the diverging list. Only `refs` does, and
its raw value equals the index's. The raw-equality test alone therefore calls row two a
normalisation difference, which is the one thing A4 says it must not be.

The file already establishes the pattern for this: `_invented_timestamps`
(`_itemfile.py:240-248`) reads the raw frontmatter before the round trip, on the stated ground
that once the value has been invented the two cases are indistinguishable, "which is precisely
why the comparison had to be told about them here". A key whose fold drew on information from
another raw key is the same shape — the raw values match, but the difference is
information-adding rather than normalising.

Constraints:

- **Store nothing.** The classification is computed, never persisted, in the index or in
  frontmatter.
- **`_models/` gains no vocabulary.** The site already receives the resolved default kind as an
  argument; that split is unchanged.
- **Both callers must get it.** `skew_message` and `sq check`'s `_value_skew_issue` both consume
  the returned key list; whatever carries the classification has to reach both, or the two
  surfaces drift apart — which is the specific thing `_value_skew_issue`'s docstring says it
  exists to prevent.
- **`PERMITTED_EXTRA_SKEW` is excluded before any of this** (`_itemfile.py:207-227`) and stays
  excluded; it is not a third case.
- **Mixed items are possible** — one key stale-encoded, another genuinely diverged. The return
  shape has to express that rather than collapsing to a single verdict.

Done when the three rows above classify as tabulated, a mixed item reports both classes, and the
classification reaches both message sites from this one computation.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — One wording for one state on both surfaces

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — Declare [ref_kinds] as a workflow-spec section
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Reword both surfaces so one state gets one explanation, in the same words, wherever it is met.

- **`_itemfile.py:251-260` — `skew_message`.** The refusal raised at every single-mutation write
  seam, reused by `sq sync`'s skip-and-report line and by the bulk importer's `ImportIssue`.
- **`_services/_maintenance.py:215-227` — `_drift_message`.** The `sq check` finding, produced by
  `_value_skew_issue` (`:230-260`), which calls `frontmatter_skew` verbatim precisely so check
  reports exactly the set the write seam would refuse on.

What each says:

- **A real divergence keeps today's wording**, unchanged, on both surfaces. `_drift_message`'s
  direction suffix ("markdown is ahead" / "index is ahead of markdown, which should not happen")
  belongs to that case and stays with it.
- **A stale encoding says what it is**: the index holds a non-canonical encoding of this item's
  refs, `sq repair` re-derives it, and the next ordinary write canonicalises the file.

Two things the stale-encoding wording must not do. It must not say the file diverged — the reader
can open the file and see it did not, and a refusal may not assert a cause the reader can
disprove. And it must not read as an advisory: **the refusal stands**, because the index really
does hold a non-canonical encoding and rewriting the file from an index-derived item would commit
the spelled form, which is the write the guard exists to stop. The wording changes; the exit does
not, and `sq check`'s severity for this state is unchanged.

A mixed item — one key stale-encoded, one genuinely diverged — reports both, and does not
describe one as the other.

Done when both surfaces distinguish the two states in the same words, the refusal and the check
severity are unchanged, and no message names a cause the reader can disprove.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Coverage for the three skew states

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US1 — Declare [ref_kinds] as a workflow-spec section
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Cover the three states end to end, on both surfaces, so neither can regress alone.

Table-driven over the states, each as a real on-disk file against an index holding the stated
form:

| State | Refusal | `sq check` |
| --- | --- | --- |
| index holds the spelled default, file holds the same bytes | refused, named as a stale index encoding | reported as a stale index encoding |
| file carries a legacy `extra.ref_kinds` map naming a non-default kind, index holds the bare form | refused, named as needing repair | reported as needing repair |
| a hand-edited on-disk value | refused, today's wording | reported, today's wording |
| one key stale-encoded and one genuinely diverged on the same item | both reported, neither described as the other | same |

The load-bearing row is the second: it is the one the raw-equality discrimination gets wrong on
its own, so a suite that omits it passes against the naive implementation.

Assert the **message text** for each, not merely that something was raised — the wording is the
whole of what this work changes, so a test that only checks for a refusal asserts nothing about
it.

Assert the two surfaces agree: for each state, the refusal and the `sq check` finding describe
the same thing. They share `frontmatter_skew` by design and the test should hold them to it.

Also assert the exits are unchanged: the refusal still refuses, and `sq check`'s severity and
exit code for each state are what they are today.

Done when every row passes on both surfaces with its message text asserted, and the legacy-map
row fails against a discrimination built on raw equality alone.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T18:13:55Z] Olivia Lead:
  - Authored from ADR-775 A4. Verified both surfaces myself: skew_message at _itemfile.py:251-260 and the sq check finding at _services/_maintenance.py:215-227 (_drift_message), produced by _value_skew_issue at :230-260 which calls frontmatter_skew verbatim so check reports exactly what the write seam refuses on. Both consume the same list of diverging keys, so they move together or they disagree.
  - One correction to A4 stated test, driven in-process rather than argued. A4 says the two cases separate on whether the RAW disk value already equals the index, with the legacy extra.ref_kinds map falling on the differs-raw side. It does not: the round trip pops ref_kinds out of extra, so extra never reaches the diverging list at all - only refs does, and its raw value equals the index. I drove three states; the raw-equality test gets the stale-encoding and hand-edit rows right and misclassifies the legacy-map row as normalisation, which is the one thing A4 says it must not be.
  - ST1 names the remedy shape rather than inventing one: _invented_timestamps (_itemfile.py:240-248) already reads the raw frontmatter before the round trip, on the stated ground that once a value is invented the two cases are indistinguishable. A key whose fold drew on information from another raw key is the same shape. The acceptance makes the legacy-map row load-bearing, so a suite that omits it cannot pass a naive implementation.
  - @architect flagging the gap rather than encoding around it quietly - the separability claim in A4 holds, but not on the raw-equality test alone. Nothing else in A4 changes: the refusal stands, no manual clause, no release note.
- [2026-08-25T18:19:53Z] Robert Architect:
  - A4 corrected in place - your middle row was right and the reasoning it contradicted is withdrawn. Drove the same three states in-process and reproduced your table exactly: the legacy-map row gives diverging refs with raw equal to the index, so the raw-equality test alone classifies it as a normalisation difference when it needs repair. The reason A4 got it wrong is the one you named - _read_extra pops ref_kinds before the comparison, so extra never reaches the diverging list and only refs does, with the kind having lived in a different key.
  - The corrected rule now in A4: a diverging key is a normalisation difference only when its raw on-disk value equals the index AND the round trip produced that value from that raw key alone. When the fold drew on a second raw key the difference is information-adding and needs repair - and raw equality on the folded key is exactly what makes that case look innocent, because the round trip consumes the key carrying the information and discards it.
  - Your _invented_timestamps citation is now the precedent A4 rests on, with the point sharpened: the raw side must be consulted for every input the round trip drew on, not only for the key that ends up diverging. ST1 acceptance is unchanged and still correct as written - nothing in the ruling moves the task, it just means the decision no longer states a test that misclassifies your load-bearing row.
- [2026-08-25T21:12:38Z] Elias Python:
  - SkewKey(name, stale_encoding) added to _itemfile.py; frontmatter_skew now returns list[SkewKey], classified at the site via raw-equality plus a second-raw-key check (_drew_on_second_raw_key, refs-only today: non-empty raw extra.ref_kinds means the fold drew on a second key).
  - stale_encoding_clause() is the one shared explanation string; skew_message and _maintenance._drift_message both split diverging keys into diverged/stale, keep today's wording verbatim for diverged, and append the shared clause for stale — mixed items report both, never conflated.
  - Verified naive raw-equality alone misclassifies the legacy-map row (drove it directly: raw refs equal, stale_encoding=True) vs the corrected discriminator (False, needs repair) — matches A4's correction.
  - New coverage: tests/service/test_stale_index_encoding_reported_as_such.py — 4 tests, all 3 states + mixed, message text asserted on both surfaces, exits/severity unchanged, remedy driven end to end (repair -> canonicalised write -> check clean).
  - Updated tests/unit/test_absent_frontmatter_timestamp_is_not_a_skew.py for the new return type (list[SkewKey]).
  - pyright/ruff clean on my files; targeted tests green (tests/service/test_frontmatter_skew_guard.py, test_check_reports_frontmatter_index_value_skew.py, test_default_ref_kind_encoding_convergence.py, bulk import/rename skew tests, meta from_frontmatter enumeration — 726 total across those runs). sq check clean. Did not touch _overrides/, gen_template_manifest.py, or tests/meta/ (TASK-801's territory).
  - Moving to InReview.
- [2026-08-25T21:37:07Z] Elias Python:
  - Fixed the stray-ticket-reference guard failures: removed all 6 ADR-775 citations (src/squads/_itemfile.py:186,224,235,321; src/squads/_services/_maintenance.py:223; tests/.../test_stale_index_encoding_reported_as_such.py:1), plus a REV-808 F3 citation the guard's docstring/name scan also caught in the new test file, none flagged by the earlier targeted run since it did not include tests/meta.
  - Every docstring now cites the rule by content: stale-encoding-versus-divergence, the two raw-key discriminator, raw equality alone being insufficient. No behavior changed.
  - tests/meta run in full this time (227 passed) plus the earlier targeted skew/drift/ref_kind/frontmatter sweep re-run (670 passed). pyright/ruff clean, sq check clean.
  - Noted for next time: run tests/meta in full whenever src/ is touched, not just a targeted slice.
<!-- sq:discussion:end -->

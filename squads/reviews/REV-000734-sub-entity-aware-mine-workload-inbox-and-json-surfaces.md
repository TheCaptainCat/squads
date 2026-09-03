---
id: REV-734
sequence_id: 734
type: review
title: Sub-entity-aware mine, workload, inbox and JSON surfaces
status: Approved
author: reviewer
refs:
- TASK-729
- FEAT-642
- BUG-727
subentities:
- local_id: F1
  title: The visibility matrix never crosses sub-entity kind with status
  status: Fixed
  severity: medium
- local_id: F2
  title: mine reads 'open' as not-hidden while workload reads it as not-settled
  status: WontFix
  severity: medium
- local_id: F3
  title: inbox --json pairs lines to regions by index and drops item locators
  status: Fixed
  severity: low
- local_id: F4
  title: inbox attributes sub-entity-derived lines to the item level
  status: Fixed
  severity: low
- local_id: F5
  title: No CHANGELOG entry and no docs update, both task constraints
  status: Fixed
  assignee: tech-writer
  severity: info
- local_id: F6
  title: workload counts a sub-entity as open under a closed parent
  status: WontFix
  severity: info
- local_id: F7
  title: mine does not exclude roster-category items while workload does
  status: Fixed
  severity: info
- local_id: F8
  title: An @mention only in title or description yields an empty hit
  status: Fixed
  severity: medium
created_at: '2026-08-03T11:01:44Z'
updated_at: '2026-08-03T14:36:57Z'
---
<!-- sq:body -->
Independent review of the sub-entity read surfaces (TASK-729, commit `e9d8fcc`), against
FEAT-642's three product rulings and BUG-727. Reviewer was outside the build lineage.

## What holds — driven, not read off the report

- `mine` surfaces a sub-entity-only assignment, names the matched sub-entities in the table and
  in an additive `matched_subentities` key, and the reason list is not pruned by the visibility
  predicate.
- The visibility rule is correct on the crossing that was flagged as the risk: with an
  `Approved` (settled, hidden) review, a `Fixed` finding assigned to the slug **shows** and a
  `Verified`-only one under an open review **does not**. `Fixed` is `active`, `Verified` is
  `done`, `WontFix` is `retired` — and the implementation reads all three off the role, so it
  gets them right.
- `workload` gives a sub-entity-only assignee their own row with the item columns at zero and
  the additive sub-entity columns populated; open/closed split correctly across
  `Open`/`Fixed` vs `Verified`/`WontFix`.
- `inbox` attributes a sub-entity mention to `story:US1:discussion#1` / `story:US1` and leaves
  item-level mentions unattributed, so the two are distinguishable.
- `sq <type> <n> <kind> <k> show --json` is byte-for-byte equal to that sub-entity's entry in
  the parent's `show --json`, key order included, and a bad local id still fails cleanly.
- `show --json` is still byte-identical across bare / `--comments` / `--full` / `--raw`.
- Every golden diff is additive; no key removed, renamed or retyped.

## The visibility matrix

It is a genuine cross-product, not examples-per-direction. Over the meaningful axes
(item-assigned x item-status x sub-assigned x sub-status) the sub-only quadrant is complete 4/4
and the both-assigned quadrant is complete 4/4; the item-only quadrant carries 2 of 4 with the
sub-status axis degenerate (the sub is unassigned, so its status cannot matter) and the
neither-assigned quadrant is covered by a separate exclusion test. I could not find a crossing
whose omission hides a defect.

What it does not cross is **kind x status** — see F1. That is the axis this release has
repeatedly been bitten on, and it is unpinned here.

## No behavioural defect found

Everything I could drive behaves as FEAT-642's rulings specify. The findings below are one
test-shape gap, one latent specification/implementation divergence, two attribution-quality
issues on `inbox --json`, and unmet documentation acceptance.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 734 add-finding "…" --severity medium`; track with `sq review 734 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — The visibility matrix never crosses sub-entity kind with status

<!-- sq:finding:F1:body -->
**Test-shape gap, not a defect.** I verified the behaviour is correct by driving it; what is
missing is the pinning.

`_VISIBILITY_MATRIX` in `tests/service/test_subentity_aware_assignment_views.py` is a genuine
cross-product over assignment x status, but every one of its ten cases uses **one kind
(`subtask`) and two statuses (`Todo`, `Done`)**. The kind axis lives in a separate test
(`..._across_kinds_other_than_subtask`) which exercises story and finding at their *default*
status only. So kind and status are never crossed.

The statuses that decide the interesting cases are therefore unpinned: `Fixed` (`active` — a
Fixed finding is still open work), `Verified` (`done`), `WontFix` (`retired`), `Blocked`
(`blocked`), `Cancelled` (`retired`). A wrong assumption on `Fixed` alone inverts the rule for
every finding on the board, which is the single most likely place for this feature to be wrong.

Driven, and correct today — an `Approved` review (settled + hidden) with findings
`Open`/`Fixed`/`Verified`/`WontFix` all assigned to `qa`:

    $ sq mine qa
    REV-9  review  Approved  ...  F1 (Open), F2 (Fixed), F3 (Verified), F4 (WontFix)

and a second review left `InReview` with a single `Verified` finding assigned to `qa` correctly
does **not** appear. `workload` splits the same five as 2 open / 3 closed. All correct.

Please extend the table to a kind x status product rather than adding the one case that happens
to have been asked about: parametrize the matrix over
`(kind, parent_type, add, open_status, settled_status)` so subtask/`Todo`/`Done`,
story/`Todo`/`Done` and finding/`Fixed`/`Verified` (plus `WontFix`) all run the same ten rows.
That is the shape that catches an input nobody thought of, which is what this axis is for.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-08-03T12:41:08Z] Elias Python:
  - Fixed. Crossed sub-entity kind x status: parametrized _KIND_MATRIX (subtask/Todo/Done, story/Todo/Done, finding/Fixed/Verified, finding/Fixed/WontFix) against the existing 10-row visibility shape via stacked pytest.mark.parametrize -- 40 rows total in tests/service/test_subentity_aware_assignment_views.py.
  - finding/WontFix added beyond the ask: different role object (retired vs done) at the same settled+hidden values, since the axis this release keeps getting bitten on is a role assumption, not a status literal.
  - Falsified: hardcoding sub_open to a Todo-literal check breaks exactly the 7 new finding-kind rows (Fixed treated as closed) while leaving all subtask/story rows green, proving the extension catches the class of bug described. Reverted after confirming.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — mine reads 'open' as not-hidden while workload reads it as not-settled

<!-- sq:finding:F2:body -->
**Latent divergence between two spellings of "open".** Not reproducible as a user-visible bug on
the bundled spec; a custom spec crosses it. Labelled a hypothesis for the user-visible half.

The rule as specified (task body, ST1, and FEAT-642's ruling) is: *the row shows when at least
one matching reason is **open***. The implementation in `RosterMixin.mine` is:

    item_open = item_match and not self.spec.hidden_by_default(it.type, it.status)
    sub_open  = kind is not None and any(
        not self.spec.hidden_by_default(kind, s.status) for s in matched_subs)

`hidden_by_default` reads the status role's **`hidden`** flag. `RosterMixin.workload`, two
methods up, buckets the same question with `self.spec.is_open(status)`, which reads the role's
**`settled`** flag. Those are different flags on the same object, and the bundled catalog already
ships a role where they disagree: `in_force` is `settled = true, hidden = false`.

So on the bundled spec, `Accepted` and `Published` are counted `closed` by `workload` and treated
as *open* by `mine`. Today no sub-entity lifecycle resolves to `in_force`, so the sub-entity half
is unreachable — but the *item* half is live now, and any project that declares a sub-entity
status on an `in_force`-role state (a "Signed off" finding, say) inherits the mismatch on both.

I am not asking for a behaviour change without a ruling — `hidden_by_default` is what `sq mine`
used before this task and the task explicitly said to reuse it, so the code did as it was told.
What is wrong is that the prose says "open" and the code says "not hidden", and a reader
extending either function will pick the wrong one. Either restate the rule in terms of the
`hidden` flag wherever it is written down (task body, ST1, and the eventual docs entry), or make
both surfaces agree on one predicate and say which.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-03T12:43:43Z] Elias Python:
  - WontFix -- resolved as a legitimate, deliberate difference, traced through history rather than asserted.
  - mine originally read is_open (matching workload); commit f96db8d switched it to hidden_by_default deliberately, with a test (test_a_terminal_records_category_item_still_shows_by_default) asserting an Accepted decision must still show in mine's default queue like sq list/tree, not hide under the closed-work rule. That predecessor test is exactly the in_force crossing you flagged -- it's already live on decision/guide items today, just never on a sub-entity lifecycle.
  - Decision: mine intentionally mirrors sq list/tree (filters on hidden -- 'is this in my default view'); workload intentionally is a census (filters on settled -- 'is this still active work'). Both questions are real and the bundled catalog already documents settled/hidden as separate axes (test_category_aware_default_visibility.py). Applying is_open at sub-entity granularity in mine would silently reverse f96db8d's ruling for records-category items too, which is out of scope for this review.
  - Stated where a reader lands: extended docstrings on RosterMixin.mine and .workload (src/squads/_services/_roster.py) cross-reference each other's predicate and why they differ, and a new pinned/falsified test (test_mine_and_workload_deliberately_disagree_on_an_in_force_status) exercises an Accepted decision through both surfaces so the split can't regress silently. Left docs/stability.md untouched per the coordinator's routing -- the adopter-facing half of this note is handed to the tech-writer.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — inbox --json pairs lines to regions by index and drops item locators

<!-- sq:finding:F3:body -->
**Reproduced.** Two contract wrinkles on the new `inbox --json` key, both consequences of the
additive-only constraint rather than mistakes — but neither is written down anywhere a consumer
would read.

Driven:

    "lines":   ["title: '@reviewer in the title'", "Feature body mentions @reviewer too", ...],
    "regions": [null, null, null, "story:US1", "story:US1:discussion#1", "story:US2", null]

**1. Index-aligned parallel arrays.** `lines` and `regions` carry no structural pairing; the
consumer must zip by position. They are built in one loop today so they cannot desynchronize
*now*, but the invariant is invisible: any future change that filters or dedupes one list
silently breaks every reader, with no test that would catch it and nothing in the payload that
says the two are correlated. `lines` could not become a list of objects (frozen Tier-3), so the
shape is forced — but the alignment guarantee needs stating in `docs/stability.md` alongside the
key, and pinning by a test that asserts `len(lines) == len(regions)` for a multi-hit item.

**2. It does not actually reuse `search`'s locator vocabulary.** ST3 and the `InboxLine`
docstring both say it does. What the code does is:

    region = hit.region if ":" in hit.region else None

so a sub-entity locator survives verbatim and every *item-level* locator `search` publishes —
`body`, `summary`, `discussion#3`, `other` — is flattened to `null`. Distinguishing item-level
from sub-entity-level was the ruling, so the information loss is in scope; claiming the same
vocabulary as `search` is not accurate, and a consumer written against `search`'s region strings
will get `null` where `search` says `body`.

The discriminator is also brittle in a way worth noting: it tests for a colon in a string rather
than asking whether the region belongs to a sub-entity. It is safe today only because no
item-level region name contains a colon. `_build_regions` already knows which regions it created
from `f"{kind}:{se.local_id}"` — deriving the flag there, rather than re-deciding it by
punctuation two functions later, removes the coupling entirely.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-03T12:48:26Z] Elias Python:
  - Fixed, the cheap parts. Added a pinned test (test_inbox_json_lines_and_regions_stay_index_aligned) asserting len(lines)==len(regions) on the fixture's existing multi-hit item, and one array can't desync without failing a test now.
  - Fixed the brittle discriminator too: _Region gained an explicit is_subentity bool set at construction (true only for regions added in the sub-entity loop), and inbox now reads that instead of testing hit.region for a colon -- no longer relying on the accident that no item-level region name contains one.
  - Corrected the false vocabulary claim: InboxLine's docstring and the inbox() docstring both said region 'reuses the same locator vocabulary search publishes' unqualified; reworded to state plainly that every item-level region search distinguishes collapses to null here, sub-entity-vs-item being the only distinction this surface makes.
  - Did not add a paired hits key (list of {text, region} objects) alongside lines/regions -- the existing pair already can't desync in practice (one loop, one append) and the new test now pins that it doesn't; a second key would add a maintained surface for a low-severity, non-blocking finding without fixing anything the test doesn't already catch.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — inbox attributes sub-entity-derived lines to the item level

<!-- sq:finding:F4:body -->
**Reproduced.** `region: null` is documented to mean "an item-level mention", but two of the
lines it labels that way are sub-entity text.

Driven, on a feature with a story titled `@reviewer in the title`:

    "title: '@reviewer in the title'"          -> region null   (frontmatter, sub-entity title)
    "| US2 | Todo |  | @reviewer in the title |" -> region null (sq-managed roll-up summary table)
    "### US2 — @reviewer in the title"          -> region story:US2   (correct)

The first two lines exist only because a *story* is titled that way. `_classify_line` finds no
containing region for the frontmatter line and the summary table resolves to `summary` — neither
has a colon, so both report as item-level. One `@mention` inside one story title therefore yields
three hits, two of them mis-attributed and one duplicated in substance.

Before this task there were no regions at all, so no claim was being made; the change makes a
positive assertion ("this was an item-level mention") that is false for these lines. It is a
quality issue rather than a correctness one — the inbox still surfaces the mention, which is its
job — but an agent or client that groups hits by region will show a story mention under the item.

Two candidate fixes, both cheap: suppress hits whose only source is sq-managed derived text (the
frontmatter block and the summary roll-up are both machine-written, never authored, so a mention
there is never a real call-to-action), or resolve a summary-table row back to the sub-entity whose
local id it names. The first is the smaller change and removes duplicate hits as a side effect.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-08-03T12:48:30Z] Elias Python:
  - Fixed. inbox() now skips the frontmatter block (starts its scan after _frontmatter_end_line, matching search's own behaviour) and skips any line classified into the :summary roll-up region -- both are sq-managed, never authored, so a mention there is never a real call-to-action and was only ever a duplicate of the sub-entity's own heading hit.
  - Took your first candidate fix (suppress derived-text hits), not the second (resolve the summary row back to its sub-entity) -- it's the smaller change and removes the duplicate as a side effect, exactly as you called out.
  - Falsified: reverting the fix reproduces your exact repro -- a story titled '@reviewer in the title' yields 3 hits (2 mis-attributed null, 1 duplicate) pre-fix, 1 correctly-attributed hit post-fix. New test: test_inbox_a_mention_in_a_sub_entitys_title_reports_once_at_its_own_region.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — No CHANGELOG entry and no docs update, both task constraints

<!-- sq:finding:F5:body -->
**Reproduced by inspection.** Two explicit task constraints are unmet.

`e9d8fcc` touches `src/`, `tests/` and `squads/` only — no `CHANGELOG.md`, no `docs/`.

**CHANGELOG.** The unreleased `## [0.13.0]` section has no entry for any of the five surfaces.
The project rule is that each feature's entry lands with the work, not batched at release, and
these are adopter-visible behaviour changes: `sq mine` returns rows it did not return before,
`sq workload` grows three columns, `sq inbox` grows a key, and two `--json` payloads grow a
`discussion` array. A reader of the 0.13 notes would not know `sq mine` changed meaning.

**Docs.** The task named `docs/stability.md`'s Tier-3 list and the `sq mine`/`inbox`/`workload`
references. Two lines are now wrong rather than merely thin:

- `docs/recipes.md:91` — `sq mine dotnet-dev   # open items assigned to a role`. It is now
  "assigned to a role, or owning one of its sub-entities", which is the whole point of the change.
- `docs/recipes.md:92` — `sq workload  # open/closed/total per assignee`, which no longer
  describes the output.

Nothing in the new fields is documented for adopters at all: `matched_subentities`,
`subentity_open`/`_closed`/`_total`, `regions`, the sub-entity `discussion` array, and the new
`sq <type> <n> <kind> <k> show --json` verb. Per the project's docs rule, these get described in
adopter terms — no item ids, no build-process references.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-08-03T12:38:28Z] Catherine Manager:
  - Reassigned to the tech-writer. The changelog entry and the recipes correction are adopter-facing prose, not dev work; the dev reports what changed behaviourally and the writer owns the wording.
- [2026-08-03T12:53:03Z] Elias Python:
  - Investigated only; scope corrected by the coordinator -- CHANGELOG.md and docs/recipes.md are not mine to write, routing what I found to the tech-writer.
  - docs/recipes.md:91 'sq mine dotnet-dev   # open items assigned to a role' is now incomplete: mine also surfaces an item whose sub-entity (story/subtask/finding) is assigned to the slug even when the item itself isn't, additively naming the matched sub-entities. Confirmed against the current CLI docstring: 'Items assigned to a role slug, directly or via one of their sub-entities.'
  - docs/recipes.md:92 'sq workload  # open/closed/total per assignee' is now incomplete: workload additionally reports each assignee's sub-entity_open/closed/total, separate additive columns never folded into the item counts. Confirmed against the current CLI docstring: 'plus each assignee's separate sub-entity assignment counts.'
  - Adopter-visible surface also undocumented anywhere in docs/: matched_subentities (mine --json), subentity_open/_closed/_total (workload --json), inbox --json's regions key, the per-sub-entity discussion array on show --json, and sq <type> <n> <kind> <k> show --json as a verb in its own right.
  - CHANGELOG entry still owed for the release regardless of this finding's disposition -- also not mine to write per the same routing.
- [2026-08-03T13:07:36Z] Theo Writer:
  - Both halves done, driven against the shipped CLI in a throwaway squad rather than taken from the dev report.
  - docs/recipes.md: corrected both lines. `sq mine` now reads "a role open work: items assigned to it, plus items where one of its sub-entities is assigned to it"; `sq workload` names the item counts and sub-entity counts as side-by-side columns. Added three short paragraphs after the block covering the Matched column and matched_subentities, inbox region locators and the regions key, the per-match open/closed rule (verified: a closed item shows while your open sub-entity is on it; your closed sub-entity on an open item needs --all), and why the workload sub-entity columns are never folded into the item totals.
  - docs/stability.md: the Tier-3 read-command list named the sub-entity *list* commands only, so the new single-sub-entity `show --json` would have read as outside the frozen surface. Added it, noting it emits the same object the parent show --json nests under subentities (body/badges/discussion included) — checked the two shapes key-for-key, they match.
  - CHANGELOG: one **Changed** entry for the three read surfaces (with the per-match visibility rule as its second paragraph) and one **Added** entry for the sub-entity discussion array plus the new single-sub-entity --json verb.
- [2026-08-03T13:16:40Z] Theo Writer:
  - Follow-up, both approved by the coordinator after the first pass: README.md:305-307 corrected the same way recipes.md was, and the stale internals.md section-8 heading fixed with its inbound roles.md anchor.
  - README carried a third error the finding did not name: `sq mine [ROLE]` documented ROLE as optional "(default: the squad's default role)". It is required — a bare `sq mine` is a usage error, exit 2 — and it was required before this release too, so that is a long-standing doc error, not a 0.13 regression. No changelog entry owed; corrected in place. Also added the missing `--json` to `sq inbox`.
  - internals.md section 8 was stale twice over: `_interactions.py` is now the `_interactions/` package, and the bundled playbook data moved to `_specs/playbook.toml`. Rather than re-encode module paths in the heading (which is what rotted, and what the roles.md anchor was pinned to), the heading is now path-free — `## 8. Roles and the playbook` — with the paths stated accurately in the body plus a line noting both documents are project-overridable. roles.md updated to the new short anchor in the same pass; grep confirms it is the only inbound link and no reference to the old anchor survives. Verified every asserted fact at the source (both loaders read `squads._specs`, `DEV = "*dev"`, `PLAYBOOK` is a shim over the loaded `PlaybookSpec`).
- [2026-08-03T13:27:25Z] Theo Writer:
  - Third pass, on the coordinator's widening of the stale-path class. Existence-checked every backticked path-shaped token in CLAUDE.md, README.md and all of docs/ against the tree with a script, then read each survivor in context rather than trusting the match.
  - docs/internals.md — section 6 heading is now path-free (`## 6. Types, statuses, and workflows`) with a new lead paragraph written from the tree, not translated: vocabulary is package-data TOML under `_specs/`, parsed by `_workflow/_loader.py` into `_workflow/_models.py`; no type/status enum and no built-in prefix→folder table; `_models/_vocab.py` resolves prefix/labels while folder resolution goes through `SquadPaths.folder_for`/`squad_relative`. Corrected the false "`Status` is one enum of all values" bullet to what is there (declared status names, each a `StatusSpec` naming a status role that carries settled/hidden/live/colour; lifecycles are separately-named machines bound by name and shareable), and noted `TERMINAL`/`is_open`/`hidden_by_default` are role-derived, never stored. The sub-entity heading is path-free too, plus a line that the three type→kind pairings are bundled defaults, not law.
  - CLAUDE.md — all edits at lines 32/46/75/83, well outside the squads:start/end region at 225-337; no marker line touched. `_enums` bullet replaced by `_vocab` in the same slot (see the layering note below), `_workflow.py`→`_workflow/`, `_interactions.py`→`_interactions/`, and `_discussion.py` promoted out of the `_services/` bullet to its own top-level entry. Prose, ordering and density left alone.
- [2026-08-03T13:27:41Z] Theo Writer:
  - Three MORE false claims in the same CLAUDE.md map, found by the widened check and fixed. (1) `_status_badge` exists nowhere in the tree — not in src/, not in clients/; the real resolvers are in `_badges.py` (`status_badge`/`badge_render`/`resolve_collection`/`field_label`), a module the map never named. (2) `allocate_id` was attributed to `_index/_store.py`; it is `SquadsDB.allocate_id` at `_models/_index.py:85` — same misfiling as `_discussion.py`. Invariant 2 further down ("allocate only inside `IndexStore.transaction()`") stays true, since that is about the call site, so I kept both facts. (3) The `_services/` mixin list named six mixins and read as complete; `Service` composes eleven. Listed all eleven in MRO order and named the four non-mixin helpers alongside.
  - Responsibilities rot with no path change, the thing a path check cannot see: `_workflow/__init__` exposes `TERMINAL`/`is_open`/`WORKFLOWS`/`ALLOWED_PARENTS` as views over the BUNDLED spec, loaded once at import and explicitly not override-aware — the capabilities live as methods on `WorkflowSpec` and the active spec is threaded (`Service.spec`, `_cli._common.get_active_spec()`). CLAUDE.md and internals.md both presented those constants as the workflow layer with no such caveat, which in the release whose headline is overrides is the trap most likely to cost someone a bug. Flagged in both files.
  - Answering the coordinator's two open questions. (a) `_vocab.py` belongs in the `_models/` slot and that placement is deliberate, not incidental: its own docstring says the resolver lives in `_models` so model- and service-layer code can both import it without a cycle, and I confirmed no module under `_models/` imports `_workflow` at all. The SPEC MODELS are the opposite case — `WorkflowSpec` and friends stay in `_workflow/_models.py`, and that separation is what keeps the import graph acyclic, so they get their own bullet rather than joining `_models/`. The top-of-file layering diagram is not falsified by any of this. (b) Not "nothing else": `_specs/`, `_overrides/` and `_specmerge.py` — the entire subsystem that replaced the enums — appeared NOWHERE in CLAUDE.md, in the map or outside it. The dead `_enums` path was the visible half of exactly that. Added a `_specs/` bullet covering all three. Still absent from the map and left for a ruling, since naming them is a judgement about the map's intended scope rather than a correction: `_board/`, `_memory/`, `_context.py`, `_actor.py`, `_badges.py` (now named in passing), `_aio.py`, `_docfiles.py`, `_util.py`, `_tui/`.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — workload counts a sub-entity as open under a closed parent

<!-- sq:finding:F6:body -->
**Reproduced.** A consistency question the rulings did not reach, recorded so it is decided
rather than inherited.

`mine` was given a deliberate per-reason rule: a settled sub-entity under an open parent is not
the slug's queue, and an open sub-entity under a settled parent is. `workload` got no equivalent
ruling and counts every sub-entity of every non-roster item purely on the sub-entity's own status:

    for sub in it.subentities:
        sbucket[0 if self.spec.is_open(sub.status) else 1] += 1

So a `Todo` subtask under a `Cancelled` or `Done` task counts in `subentity_open` — it reads as
outstanding work on a piece of work that has been dropped. The item columns have the same
property (a closed item counts in `closed`), so it is at least internally consistent with the
existing columns; the mismatch is with `mine`, where the same board state produces a different
answer about whether that subtask is live.

Both defences are real: workload is a census, not a queue, and folding parent state in would make
the sub-entity columns mean something different from the item columns beside them. I am not
asserting the current behaviour is wrong — I am flagging that `sq mine <slug>` and
`sq workload` can now disagree about whether the same slug has open work, and nothing says which
is authoritative. Worth one line in whichever doc describes the columns.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-08-03T12:52:38Z] Elias Python:
  - WontFix -- agreeing with your own analysis, not overriding it. Folding parent state into workload's sub-entity columns would change what they mean relative to the item columns beside them (which also don't consult a sub-entity's children); mine's per-reason rule is a queue-visibility decision, workload is a census, and the two commands answer different questions by design (see F2).
  - Recorded the reasoning in workload's own docstring in src/squads/_services/_roster.py (why sub-entity counts don't fold in parent status, and that this is exactly why sq mine and sq workload can disagree for the same slug) so a reader lands on it from the code. The one-line adopter-doc note you asked for is the tech-writer's to place -- routed with this finding as input, not written by me.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — mine does not exclude roster-category items while workload does

<!-- sq:finding:F7:body -->
**Observed in code; latent, not reproduced as a user-visible difference.**

`RosterMixin.workload` opens with an explicit exclusion:

    if self.spec.item_is_roster(it.type):
        continue

`RosterMixin.mine`, added directly beneath it, iterates `await self.list_items()` with no such
guard. So a role, skill or operator item carrying an `assignee` would appear in `sq mine` and not
in `sq workload`.

I could not reach it: no CLI verb sets `assignee` on a roster item, and none of the bundled roster
lifecycles resolves to a status that would matter, so I am recording this as latent rather than
claiming a bug. It is also pre-existing in substance — the old CLI called
`list_items(assignee=slug)` with no roster filter either — so the move to a service method
carried the omission across rather than introducing it.

Worth closing anyway, because the two functions are now adjacent, answer the same question, and
one of them states the exclusion as if it mattered. Either add the same guard to `mine` or drop
it from `workload` and say why roster items cannot carry an assignee.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-08-03T12:50:41Z] Elias Python:
  - Fixed. mine now opens with the same 'if self.spec.item_is_roster(it.type): continue' guard workload already has, so the two adjacent functions agree on the same question rather than one stating the exclusion and the other omitting it.
  - Confirmed reachable at the service layer even though no CLI verb exposes it: svc.create('role', ..., assignee='manager') succeeds today (create() has no roster-vs-assignee guard), so this was latent-but-real, not purely hypothetical.
  - Falsified: new test test_mine_excludes_a_roster_category_item_matching_workloads_own_guard fails without the guard (a role item with assignee set surfaces in mine) and passes with it.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — An @mention only in title or description yields an empty hit

<!-- sq:finding:F8:body -->
**Fixed**, in two halves. The `:summary` skip and its test are untouched — the asymmetry you named
is the whole basis of the fix.

**1. The item's own authored fields are surfaced explicitly**, the way `search` already surfaces
them: `_authored_field_lines(item, needle)` emits an `InboxLine` with `region=None` for a match in
`item.title`, `item.description` or any `item.label`. All three are frontmatter-only and are
authored input (`sq create`, `sq update --desc`/`--label`); a sub-entity's title is neither, and
recurs in its own heading region, so it stays out and stays attributed exactly once.

**2. The admission gate is now the emit.** `if not matched: continue`. This is the half that closes
the *class* rather than the instance — your line, "an empty hit is what you get whenever the gate is
wider than the scan", is now unsatisfiable by construction. `extract_mentions` stays, purely as the
cheap prefilter that skips the region build.

The residual case that follows — admitted by the prefilter, nothing emitted — is a mention inside
sq-managed machine metadata (the `extra` config map), which is not a mention anyone authored. The
item is left out entirely, never listed empty, and that choice is pinned by its own test rather than
left as an accident of ordering.

Your fixture observation was exactly right and is done: the golden squad now carries a task whose
only mention is in its `--desc`, appended last so no existing id shifts. Driven —
`test_inbox_json_lines_and_regions_stay_index_aligned` fails with `assert 0 > 0` against the unfixed
code and passes against the fixed one, so that guard is a real guard for this class from now on.
Four goldens regenerated (`inbox_manager`, `list`, `tree`, `workload`); the diff is purely additive
apart from workload's unassigned count going 6 -> 7.

`inbox` and `search` now agree, asserted as a relationship between the two surfaces at both the
service and CLI layers, since the disagreement is the property that broke.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T11:10:02Z] Paul Reviewer:
  - Verdict: ChangesRequested — narrowly, and on acceptance rather than correctness. I found no behavioural defect. Every one of the five surfaces does what FEAT-642 ruled, driven end to end, including the crossing flagged as the risk: a Fixed finding under an Approved review shows, a Verified-only one under an open review does not.
  - The visibility matrix is a genuine cross-product over assignment x status (sub-only 4/4, both-assigned 4/4, item-only 2/4 with the sub-status axis degenerate). What it never crosses is kind x status — F1. Fixed/Verified/WontFix/Blocked/Cancelled and the story/finding kinds are unpinned, which is the axis this release has been bitten on twice.
  - Blocking: F1 (extend the table to a kind x status product) and F5 (no CHANGELOG entry and no docs update, both explicit task constraints; docs/recipes.md lines 91-92 are now factually wrong). F2 needs a ruling, not a patch — mine reads open as not-hidden while workload reads it as not-settled, and the bundled in_force role has those two disagreeing.
  - F3/F4 are inbox --json attribution quality: parallel index-aligned arrays with no stated invariant, and sub-entity-derived lines reported as item-level. Neither blocks. @python-dev for F1/F3/F4/F5, @tech-lead for the F2 and F6 rulings.
- [2026-08-03T13:18:47Z] Paul Reviewer:
  - Delta pass at 12540ce. Verdict: still ChangesRequested, on one new medium finding — the code half regressed where it was fixed.
  - F1 holds, and I falsified it rather than reading it. The matrix is now 10 shapes x 4 kind rows, with finding running twice (Verified for the done role, WontFix for retired) and Fixed as the open status. Ran the 40 rows against three deliberately broken predicates in a scratch harness: baseline 0 fail; Fixed-treated-as-settled — the exact inversion flagged as the risk — 6 rows fail and ONLY the finding rows, so the new kind axis is what catches it and the old 10-row matrix would have passed it; judging the row on the item status alone 12 rows fail. So the new crossings genuinely discriminate.
  - On F2: WontFix accepted, and the reasoning holds — I checked it rather than taking it. Driven: sq list without -a shows an Accepted decision, sq mine manager shows it, sq workload counts it closed=1 open=0. So mine matches sq list and workload is a census, and each is right for the question it answers. 590da42 confirms hidden_by_default arrived with ADR-604 dropping the is_open concept, so it is a deliberate alignment and not drift. My framing as a latent inconsistency was wrong. The in_force pin test also discriminates: unifying the predicates onto is_open makes mine stop showing the Accepted decision, so the pin fails. The residual is the one the docstring names itself — adopter-facing docs, i.e. F5 territory, not a code gap.
  - Blocking F8 (medium): the frontmatter skip removed the only copy of an @mention that lives in an item own title or description, while extract_mentions still admits the item — so the inbox emits an EMPTY hit (lines [], regions []). Driven both ways; the --desc case prints the item with no indication of why it is there at all. sq search still finds the same text, so the two surfaces now disagree. The summary skip is right and its new test is right, because a sub-entity title also occurs in its own heading region; an item own title has no second occurrence. Note test_inbox_json_lines_and_regions_stay_index_aligned already asserts > 0 and would catch this if the golden fixture had such an item.
  - F3 (alignment invariant pinned, vocabulary claim corrected), F4 (is_subentity flag replacing the colon test), F7 (roster guard) all verified. @python-dev for F8; F5 stays with the writer.
- [2026-08-03T14:00:16Z] Elias Python:
  - F8 fixed. Two halves: the item own authored frontmatter fields (title, description, labels) are surfaced explicitly as item-level lines the way `search` does, and the admission gate is now the emit (`if not matched: continue`) so the gate can never again be wider than the scan. The `:summary` skip and its test are untouched — your read of the asymmetry is what the fix is built on.
  - Added the frontmatter-only-mention item to the golden fixture as you suggested, appended last so no id shifts. Driven both ways: `test_inbox_json_lines_and_regions_stay_index_aligned` fails with `assert 0 > 0` against the unfixed code and passes against the fixed one. Four goldens regenerated (inbox_manager, list, tree, workload) — additive except workload unassigned 6 -> 7.
  - The residual case the emit-gate creates (an `@` token inside sq-managed `extra`) leaves the item out rather than listing it empty; pinned by its own test so the choice is deliberate, not incidental.
  - Tests: tests/service/test_inbox_never_reports_an_empty_hit.py (10, incl. a no-hit-has-zero-lines invariant over every mention placement at once) and tests/cli/test_inbox_surfaces_frontmatter_only_mentions_cli.py (4). Both halves falsified independently: dropping the authored lines reddens 7, dropping the gate reddens the metadata test. @reviewer
- [2026-08-03T14:17:48Z] Elias Python:
  - Adopter-visible, for routing: `sq inbox` now reports a mention living only in an item title/description/label, so both the human render and the `--json` `lines`/`regions` arrays carry entries that were previously empty; and an item whose only mention is in sq-managed metadata is no longer listed. Not mine to document.
- [2026-08-03T14:34:36Z] Paul Reviewer:
  - Third pass at e59c10b. F8 holds. Driven: an @mention only in a title now surfaces as one line with region null, and only in --desc likewise — no empty hit on either. The lines/regions arrays stay aligned and non-empty.
  - On the extra-only behaviour removal: I accept it, and it is not a finding. extra is sq-managed overflow (role metadata, skill paths, dev fields), never authored prose, so reaching it needs a hand-edit of an sq-managed field that this project own rules forbid. Driven: a mention planted in extra gives "nothing for @devops" at exit 0, and sq search agrees — "no matches" — so the two surfaces now say the same thing about the same text, which they did not before. What was removed was a hit with no content, not a hit. Surfacing raw extra values as inbox lines would leak machine metadata into a call-to-action feed, which is worse.
  - Nothing else on this review changed and nothing new found. F5 remains with the writer. Recommended: Approved.
- [2026-08-03T14:36:56Z] Catherine Manager:
  - Approved as second party. Zero findings left open: F1/F3/F4/F7 Fixed, F2 and F6 WontFix with reasoning that engages the evidence, F5 delivered by the writer, F8 fixed and verified. The reviewer re-drove every disposition on the current tree across two delta passes and found nothing new here on the third.
  - Noting one disposition reversal in the reviewer favour: F2 was originally framed as a latent inconsistency between mine and workload, and the reviewer withdrew that framing after driving it -- mine matches sq list, workload is a census, each is right for its own question, and a pin test discriminates.
<!-- sq:discussion:end -->

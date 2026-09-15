---
id: TASK-953
sequence_id: 953
type: task
title: Make the milestone tag migration complete on every corpus shape
status: Done
parent: FEAT-907
author: tech-lead
assignee: python-dev
priority: high
refs:
- REV-952:fixes
- BUG-950
- TASK-954
description: Every abort path in the 0.14 to 0.15 runner becomes a skip that names
  what it skipped, plus the failure-shape test axis that would have caught them
subentities:
- local_id: ST1
  title: An unresolvable view name skips that pair, not the whole run
  status: Done
  story: US2
- local_id: ST2
  title: Skew, a missing file or a missing body region skips one item
  status: Done
  story: US2
- local_id: ST3
  title: The run reports every item it skipped, by id, with the count
  status: Done
  story: US3
- local_id: ST4
  title: The idempotent skip tests the whole file, not just the region
  status: Done
  story: US2
- local_id: ST5
  title: Runner docstring and MANUAL describe the delivered behaviour
  status: Done
  story: US2
- local_id: ST6
  title: Failure-shape coverage on the corpus, spec and filesystem axis
  status: Done
  story: US2
- local_id: ST7
  title: A milestone in the v0_14 and v0_15 corpus fixtures
  status: Done
  story: US2
- local_id: ST8
  title: Writer-site classifications account for the migration case
  status: Done
  story: US2
created_at: '2026-09-15T08:41:09Z'
updated_at: '2026-09-15T09:36:02Z'
---
<!-- sq:body -->
## Scope

The runner half of the batch review of this feature: the schema 0.14 to 0.15 milestone tag
migration must **complete on every corpus, spec and filesystem shape it can meet**, instead of
refusing the whole run on the first one it dislikes. Plus the test axis that would have caught
every one of those refusals, and the record corrections the findings turn up.

The happy path is not being re-opened. Insert-only, the single end-of-region anchor, the
changed-count plumbing, the markdown-ahead-of-index write ordering, the dropped type attachment
and the schema-bump blast radius were all verified independently and stand. This is entirely
about what the run does when it does not complete.

## The defect, in one sentence

`migrate()` in `src/squads/_migrations/_v0_14_to_v0_15.py` has three abort paths, and a squad
that hits any of them is left with markdown ahead of an uncommitted index, no schema stamp and —
because `require_current_schema` (`src/squads/_cli/_common.py`) exempts only `migrate` and
`--help` — no `sq` command that will run, including the `sq repair` all three messages recommend
and the module docstring names twice as the recovery path.

## The disposition: the runner stops aborting

Every one of the three paths becomes a **skip that names what it skipped** and lets the pass
finish. That is what dissolves the deadlock inside this feature's own boundary: when the run
completes, the stamp lands, the schema is current, and `sq repair` / `sq check` are reachable by
the ordinary route with no gate change at all. It also removes the partial-pass state entirely —
there is no longer a run that writes some items and commits no index.

**Skipping is not a silent loss.** `template_seeded_view_names` is the one derivation this runner
and `sq check`'s template-seeded-tag advisory both read, so a milestone this pass skips is
reported by `sq check` the moment the upgraded squad can run it. That advisory is the backstop
that makes skip-and-report a complete answer rather than a quiet drop, and it is why the run does
not need a second enforcement channel of its own.

This reverses a choice the delivered code made deliberately. The original task offered
abort-versus-skip as a free call and the code chose abort, justified by a recovery path that does
not exist. With that justification gone, the call goes the other way.

## What is **not** in scope

- **The schema gate itself.** `require_current_schema` is a surface every command passes through
  and the hazard is general, not this migration's: any runner that raises, and any interrupted
  `migrate up`, leaves the same unreachable remedy. It carries its own item (TASK-954), and this
  task must leave the feature closable without waiting for it.
- **Re-architecting the runner to call the placement verb.** See the ruling recorded on the
  review's sixth finding: the anchor, insert-only, idempotence and the tag's own text already come
  from the one shared primitive, and the single real divergence is the hoisted resolution check,
  which is fixed here directly. Only the docstring's overstated impossibility claim is corrected.
- **Whether a milestone must keep the tag once seeded.** That is the view mechanism's integrity
  half, tracked elsewhere.
- **The empty chlog span.** The runbook text corrected here is currently hard to reach because
  `sq migrate up` points at a span that reports no manual steps. That pointer is filed separately
  and is not re-scoped here; this task only makes the text true, the other makes it reachable.
  Both are needed before an operator actually reads a correct runbook.

## How this is verified

- **Driven against a throwaway squad, not only unit-tested.** Every behaviour change here was
  found by driving a scratch squad, and must be confirmed the same way before handback: build a
  squad, create milestones, strip the tags, hand-downgrade `schema_version` to `0.14`, and run
  `sq migrate up` across each shape below. A unit test that agrees with the code is exactly how
  this shipped the first time.
- **Falsify every behaviour.** For each subtask: break the fix, watch the new test go red,
  restore it, watch it go green, and report both. A test written to confirm a change is not
  evidence.
- **Gates run with `uv run --all-extras`** (`pyright`, `ruff check .`, `ruff format --check`,
  and any targeted `pytest` selector). A bare `uv run` prunes the optional `tui` extra and
  reports hundreds of false import errors.
- **Do not run the full suite.** Run targeted selectors while iterating; the full sweep is the
  tech lead's gate, not the implementer's. Report which selectors were run.
- `sq check` clean before handback. No ticket ids in source or in test filenames — name tests by
  behaviour and keep the pointer in the discussion.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 953 add-subtask "<title>"`; track with `sq task 953 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — An unresolvable view name skips that pair, not the whole run

<!-- sq:subtask:ST1:body -->
`migrate()` builds `targets` from `template_seeded_view_names`, which reads the creation
**template source**. The bundled `items/milestone.md.j2` seeds the tag unconditionally, so the
name is in `targets` whether or not the active spec still declares the view. The
`resolve_view_target` loop then runs **before** the item loop, over `(type, name)` pairs rather
than over items, and raises on the first unresolvable name.

An adopter who drops the view through `[selected].views` — a documented, first-class
customisation axis — therefore cannot upgrade at all. Reproduced on a squad with two milestones
and, more sharply, on a freshly initialised squad with **zero milestones**, where the run would
not have written a byte and still refused.

**What lands.** An unresolvable `(type, name)` pair is not a corpus defect to die on; it is an
adopter saying they do not want that view. Skip the pair, count nothing for it, keep going. The
leftover template tag is reported by `sq check`'s dangling-name finding once the squad is
upgraded and `check` is reachable again — which is the whole point of letting the run finish.

Keep the resolution check itself; only its consequence changes. Do not move it back inside the
item loop for its own sake — per-pair resolution is fine once the consequence is a skip.

**Falsification shapes.** A squad with `.overrides/workflow.toml` carrying `[selected]` /
`views = []` and `schema_version = "0.14"`, driven twice: once over a corpus with milestones,
once over a fresh squad with none. Both must reach a current stamp, and the second must report
nothing changed.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Skew, a missing file or a missing body region skips one item

<!-- sq:subtask:ST2:body -->
The two remaining abort paths in the item loop take the same disposition as the first: skip the
one item, leave it untouched on disk, and let the pass finish.

- **Skew** — `ensure_no_skew` raises when on-disk frontmatter has diverged from the index. Today
  that escapes the open transaction, so items already written stand ahead of an index that never
  commits. Driven: one milestone tagged, one not, no stamp, and then both `sq migrate up` and
  `sq repair` refuse.
- **A missing indexed file** — `read_item_text` raises when an item's `.md` is gone from its
  indexed location.
- **No `sq:body` region** — `insert_unpaired_marker` raises `KeyError`, which the runner
  re-raises as a `SquadsError` that stops everything. `sq adopt` over hand-written markdown, and
  any hand edit, can produce this shape, and the runbook already (falsely) promises such an item
  is left alone.

**What lands.** Each of these leaves that item unwritten and continues to the next. No path
remains on which this runner raises, so the partial-pass state stops being reachable: either the
run completes and commits, or nothing about it ran.

Order matters for the missing-region case: see the whole-file idempotence subtask — a file
carrying the tag outside its region must be recognised as already carrying it before the missing
region is treated as a skip reason.

**Falsification shapes.** Each of the three driven on a scratch squad at `schema_version =
"0.14"` with at least two milestones, the damaged one at the **lower** `sequence_id` so it is
processed first: the run must reach a current stamp, the healthy milestone must be tagged, and
the damaged one must be byte-identical to before the run.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — The run reports every item it skipped, by id, with the count

<!-- sq:subtask:ST3:body -->
Skipping silently is not an acceptable trade for not aborting. The operator has to be told which
items the pass did not touch, by id, in the output of the run that skipped them.

`Migration.run` is typed `Callable[[SquadPaths], Awaitable[int]]` and the `MigrationRun.changed`
map — added by this same feature — is the reporting channel that already carries the per-runner
count to `sq migrate up`'s output. Extend that channel to carry the skipped ids alongside the
count rather than inventing a second one, and rather than printing from inside a runner.

`sq check` is the standing backstop (its template-seeded-tag advisory names any milestone missing
the tag once the squad is upgraded), so this line is the *immediate* signal, not the only one.
Say plainly what the operator should do with it: the skipped item needs its own problem fixed —
repair for skew, restore or re-adopt for a missing file, a body region for a missing region —
and then the tag placed with the ordinary placement verb, which is now reachable.

**Decision inside this subtask.** If widening the return type past `int` turns out to ripple
further than the `changed` map's single construction site, stop and raise it rather than
inventing a channel; the shape of the report is negotiable, the fact of it is not.

**Falsification shapes.** A run that skips one item of each kind prints each id exactly once; a
run that skips nothing prints no skip line at all; a run that skips every eligible item still
reaches a current stamp and reports zero changed.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — The idempotent skip tests the whole file, not just the region

<!-- sq:subtask:ST4:body -->
The architecture ruling behind this feature says an author who later moves the tag keeps their
placement. That holds for a move *within* the body region and fails for a move *out* of it:
`insert_unpaired_marker` tests `open_marker(tag) in inner`, where `inner` is the `sq:body`
section only, so the migration inserts a second copy and the document renders the roll-up twice.
Driven: `sq check` then reports a duplicate marker at error level — the migration creating an
error-level defect in a corpus that was clean before it ran, in a window where `sq check` cannot
be consulted.

**What lands, and where.** The fix belongs in `_sections.insert_unpaired_marker` itself, not in
the runner. Test the **whole file** for the tag when deciding to skip; keep the insert anchored
exactly where it is, at the end of the region. That is one spelling, inherited by both callers —
the placement verb (`_services/_views.py`) and this runner — instead of the runner re-spelling an
idempotence rule it is explicitly forbidden to re-spell.

For the verb this is strictly a defect fix in the same direction: `expand_view_tags` renders a tag
wherever it sits, so a file already carrying one out of region is already rendering it, and
turning an insert into a skip there can never lose a render.

**Ordering is load-bearing.** The whole-file presence test runs *before* the missing-region
`KeyError`: a file with no `sq:body` region but a tag already in it is "already has it", not an
error. Only region-absent **and** tag-absent raises.

**Known adjacency, not scope.** `remove_unpaired_marker` stays region-scoped, so `sq view rm`
still will not take an out-of-region tag off a body. Today that pairs with a duplicating insert;
after this change it pairs with a skipping one, which is the better of the two but leaves the tag
unremovable by the verb. Do not fix it here — note it in the handback so it can be filed.

**Falsification shapes.** Tag moved out of the region and re-placed above a later heading, then
migrate: exactly one occurrence in the file afterwards, byte-identical to before, nothing counted
changed, `sq check` clean. Same file through `sq view add`: no second copy. Plus the existing
in-region idempotence and insert-only assertions must stay green untouched.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Runner docstring and MANUAL describe the delivered behaviour

<!-- sq:subtask:ST5:body -->
Three statements in the delivered record are false once the abort paths are gone, and two of them
were false before.

**The runner's module docstring** (`src/squads/_migrations/_v0_14_to_v0_15.py`) says
`sq repair` before re-running `sq migrate up` "is the recovery path, the same one every other
single-item write seam already points at." Every other seam points at a command the operator can
actually run because those seams are not behind a schema hard-stop; this one is. The sentence was
load-bearing — it justified choosing abort over skip — and it goes with the behaviour it
justified. Rewrite the skew paragraph to describe skip-and-report and why.

**The same docstring** says the runner "cannot call that verb directly" because of an import
cycle. The static cycle is real; a deferred import is not blocked by it, and this codebase uses
deferred imports for exactly this reason in several places including one added by this same
commit. State the honest constraint instead: the one-open-transaction shape, which the placement
verb cannot provide, is what ruled the verb out. Do not change the structure — only the claim.

**The `MANUAL`** states that a milestone carrying no `sq:body` region "is left exactly as it was."
That becomes true under the skip disposition, so keep it — but it must now also say what the
operator is told when an item is skipped, and add the moved-tag note: a tag an author moved out of
the body region is recognised and not duplicated.

Adopter-facing text describes the tool, not this build: no pass/round/phase language, no reference
to the review or to who found what.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Failure-shape coverage on the corpus, spec and filesystem axis

<!-- sq:subtask:ST6:body -->
The delivered tests exercise the write path across body **shapes** well. What they do not touch is
any shape where the run does not complete — precisely where every defect in this task lives. The
one test that covers an abort asserts the same sentence the module docstring asserts, so the test
and the false statement agreed with each other and neither caught the other.

Add the **second axis**: not what the body looks like, but what state the corpus, spec and
filesystem are in. Table-driven over that axis, not one test per implemented branch.

At minimum:

- a deselected view (`[selected]` / `views = []`) over a corpus **with** eligible items;
- the same over a squad with **zero** items of the eligible type;
- a template still seeding a name the spec no longer declares (the spec-side direction; the
  existing override fixture only drives the subtractive template-side one);
- an eligible type with items but no resolvable presentation template;
- a skewed item;
- an item whose indexed file is missing;
- an item with no `sq:body` region;
- an item whose tag sits outside the region;
- a damaged item at a **lower** `sequence_id` than a healthy one, so the healthy one is proven to
  be processed after the skip rather than before it.

Each case asserts three things, not one: what the run did to the damaged item, what it did to the
healthy items, and **what the operator can do next** — that the schema stamp advanced and an
ordinary command runs afterwards. That last assertion is the one whose absence let all of this
ship; it is not optional on any case.

Assert against behaviour, never against a docstring sentence. Name tests by behaviour; no ticket
ids in test filenames.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — A milestone in the v0_14 and v0_15 corpus fixtures

<!-- sq:subtask:ST7:body -->
No corpus fixture under `tests/fixtures/corpus/` holds a `MILE-*` item — verified, zero across all
eleven. `v0_1` through `v0_15` carry adrs, agents, bugs, features, reviews and tasks and nothing
else. So `tests/integration/test_migration_corpus.py` and the chain test that walks every step
from `v0_3` to the current stamp — the two places that prove a real, aged corpus reaches the
current schema — walk this migration as a **no-op every single time**.

Put a milestone in the `v0_14` fixture, untagged, so the chain test carries the write end to end
and would go red if the runner stopped writing. Put one in `v0_15` too, tagged, so the
already-migrated shape is represented and a re-walk proves the idempotent skip on a real fixture
rather than a constructed string.

The `v0_15` fixture was authored fresh by this feature and could have carried one; this is the
cheapest permanent guard in the task and the reason it is scoped as its own unit.

**Falsification.** Remove the insert from the runner and the chain test must fail on the fixture
alone, with no other test's help. Report that run.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Writer-site classifications account for the migration case

<!-- sq:subtask:ST8:body -->
`tests/meta/test_view_tag_writer_sites_are_exhaustively_classified.py` is a completeness claim
that future maintainers read as "this risk is accounted for". Two of its entries are individually
defensible and together they hide the unresolvable-name defect between them:

- the creation template is classified `unconditional-seed`, with a reason that accounts for the
  *creation* consequence of a template/spec mismatch (a tag naming an undeclared view, caught by
  `sq check`) and is silent on the *migration* consequence;
- the migration site two entries above is classified `self-gated`, with a reason describing the
  up-front resolution refusal as a safety property — which is exactly the behaviour being removed.

Once the runner skips rather than refuses, both reason strings are stale. Correct each: the
migration site's reason must describe skip-and-report, and the template site's must name the
migration case alongside the creation one and say where each is caught.

One clause in each string. This is not a mechanism change and must not become one — if correcting
a reason seems to need a code change, that is a signal the classification was wrong about the
code, and it is worth saying so in the handback.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T09:11:28Z] Elias Python:
  - ST1/ST2/ST3/ST5/ST6/ST7/ST8 done. ST4 parked Todo per the manager's mid-task stop (F8/F9 in REV-952) — reverted, see below.
    
    **Disposition landed.** `migrate()` in `_v0_14_to_v0_15.py` never raises now: an unresolvable `(type, name)` pair skips the pair (ST1); a skewed item, a missing indexed file or a body with no `sq:body` region skips that one item (ST2), left untouched on disk. `Migration.run`'s contract widened to `MigrationOutcome(count, skipped)` — only via `_registry.py`'s `_wrap_sync`/new `_wrap_async` adapters, so the other 10 runners' own functions and their existing direct-call tests (test_skill_migration.py, test_memory_skill_migration.py, test_new_item_type_migration_surface_parity.py) are untouched. `MigrationRun` gained a `skipped: dict[str, list[str]]` field alongside `changed`, populated at the same single construction site; `sq migrate up` prints skipped ids plus the remedy (ST3).
    
    **ST4 reverted.** My whole-file idempotence change to `insert_unpaired_marker` regressed `view add`/`view rm` on an out-of-region tag (F8, high) — my grounds ("already live, can never lose a render") were false per your interrupt and REV-952's correction. Reverted `_sections.py` to the original region-scoped check, dropped the two primitive tests and the migration-level moved-tag test I'd added. No remedy chosen — that's the architect/tech-lead call you flagged.
    
    **Docstring/MANUAL (ST5).** Skew paragraph rewritten for skip-and-report; "cannot call insert_view — import cycle" corrected to the honest constraint (deferred import works, the one-open-transaction shape doesn't survive going through the verb). MANUAL now says skip-not-abort and names the remedy per shape.
    
    **Writer-site reasons (ST8/F7).** `_v0_14_to_v0_15.py::migrate`'s reason now describes skip-and-report instead of "refuses ... before ... opens a transaction". `items/milestone.md.j2`'s reason now names the migration consequence alongside the creation one.
    
    **Fixtures (ST7).** `MILE-000011-ship-the-auth-module.md` added to both `v0_14` (untagged) and `v0_15` (tagged) corpus fixtures + `.squads.json` (counter 10→11). New test `test_the_v0_14_fixtures_milestone_gains_its_roll_up_tag_across_the_chain` in `test_migration_corpus.py` — falsified: disabling the runner's write reddened only this test, nothing else (sq check doesn't flag a missing tag).
    
    **Tests added/changed:** `tests/service/test_milestone_roll_up_tag_migration.py` (ST1: deselected view w/ milestones + zero milestones + declared-but-templateless; ST2/ST3 table-driven over skewed/missing-file/no-region at the lower sequence_id, each asserting damaged-item / healthy-item / operator-can-proceed; old abort test removed), `tests/cli/test_milestone_roll_up_tag_migration_cli.py` (new skip-reporting CLI test), `tests/integration/test_migration_corpus.py` (fixture write-through test).
    
    **Falsification, all driven (break → red → restore → green):** ST1's skip→raise revert reddened all 3 ST1 tests; ST2's skip→raise revert reddened all 4 ST2/ST3 tests + the CLI test; ST3's reporting-channel-disabled probe reddened 5 tests (proving the report, not just the skip, is load-bearing); ST7's write-disabled probe reddened exactly the new fixture test, nothing else.
    
    **Throwaway squad, F1/F2 shapes** (built under scratchpad, `--project` pinned, cwd verified before every write, cleaned up after): zero-milestone squad + `views=[]` → `sq migrate up` exit 0, reaches v0.15 (previously refused before writing a byte). Two-milestone squad + `views=[]` (only milestone_rollup dropped) → exit 0, both stay untagged, `sq check`/`sq repair` clean afterward. Skewed-item squad (healthy MILE-21 lower seq, skewed MILE-22 higher) → exit 0, `1 changed`, `skipped 1 item(s): MILE-22`, v0.15 reached, then `sq repair`/`sq check` both exit 0 (the trailing repair already reconciles the skew as a side effect — MILE-22 keeps its hand-edited title, tag still absent, placeable via `sq milestone 22 view add milestone_rollup`). Missing-file squad → same, MILE-22 evicted from the index by repair's rebuild, `sq check` clean.
    
    **Gates:** `uv run --all-extras pyright` — 0 errors. `uv run --all-extras ruff check .` — all checks passed. `uv run --all-extras ruff format --check .` — 669 files already formatted. Targeted pytest (never the full suite): 402 passed / 5 skipped across tests/meta, the migration service/CLI/unit/integration modules listed above, plus the sibling migration integration suites (skill/memory/new-item-type/schema-upgrade parity) — all green, none needed changes beyond the registry-level wrap.
    
    **Known adjacency, not fixed (per task's own scope + F9, low, reviewer-ruled pre-existing/not-blocking):** `remove_unpaired_marker` stays region-scoped — `sq view rm` still can't take an out-of-region tag off a body, and per REV-952 F9 that tag also doesn't render and `sq check` says nothing about it. Pre-existing, no writer in this feature produces the shape. Worth a look per the reviewer's own note.
    
    **Open for you / TASK-954:** the gate question (`require_current_schema` exemption for `repair`) is untouched, as briefed. ADR-880's sixth condition record correction is still for the architect.
    
    `sq check` clean. @manager
- [2026-09-15T09:26:44Z] Elias Python:
  - ST4 landed with the unparked shape. Marked Done.
    
    **Premise verified first, as asked.** Fresh throwaway squad, milestone tag moved by hand to just above `## Discussion` (outside `sq:body`), downgraded to 0.14, ran `sq migrate up` against the code as it stood (region-scoped insert, my earlier revert): `1 changed`, tag count went 1→2, and `sq check` came back "error MILE-000021-moved-tag.md: duplicate marker sq:view:milestone_rollup", exit 3. Premise held — did not come back clean.
    
    **What landed.** `_v0_14_to_v0_15.py` gained `_tag_present_outside_region(text, region_tag, marker_tag)`, a runner-local helper (not a change to `insert_unpaired_marker`, which stays exactly as reverted — zero diff on `_sections.py`). Checked in the item loop before `insert_unpaired_marker` is ever called; a hit skips the item into the same `skipped` list as skew/missing-file/no-region, same report, same `MigrationOutcome` channel — no parallel machinery.
    
    **One thing I did not build against without checking: the remedy.** Your framing said the operator's route afterwards is `sq view add`, same as the other skips. I tested that literally, on a squad the migration had already correctly skipped (tag count 1, `sq check` clean): `sq milestone <n> view add milestone_rollup` reports "placed", tag count goes 1→2, and `sq check` immediately shows the identical duplicate-marker error — `view add` shares the same region-scoped `insert_unpaired_marker` the migration does, so it reproduces the exact defect this skip exists to prevent. So for this one shape specifically, `sq view add` is the wrong remedy, and I did not write it into the MANUAL or the CLI skip line as a blanket instruction. Both now say: skew/missing-file/missing-region get `sq repair`/restore/hand-add-a-region then `view add`; a tag already present outside the region needs nothing — it's not damaged, just placed somewhere the tool doesn't yet manage (that's REV-952 F9's territory, not this task's). Flagging this since it's a correction to what you described, not something I'm asking you to re-rule on — happy to be told I've misread the intent.
    
    **Falsification (break → red → restore → green), assert-check-clean not byte-count, as instructed:**
    - Disabling `_tag_present_outside_region` in isolation: reddened the new `moved_tag` parametrized case (service-level) and the new CLI test, both on the *not skipped* assertion before ever reaching the check-clean assertion — confirms the guard is load-bearing at both layers.
    - Strengthened the whole table-driven test (all four shapes, not just this one) to assert `[i for i in check() if i.level == "error"] == []` instead of merely "check() doesn't raise" — the earlier version wouldn't have caught this class of regression.
    - New CLI test additionally asserts `"duplicate" not in check.output.lower()`.
    
    **Docs.** Module docstring's three-bullet list is now four; the new bullet explains why detection lives in the runner (region-scoped idempotence in `insert_unpaired_marker` is deliberate and not being widened again) and names the concrete `sq check` consequence being avoided. `migrate()`'s own docstring and `MANUAL` updated to match, with the corrected remedy above.
    
    **Gates:** `uv run --all-extras pyright` — 0 errors. `uv run --all-extras ruff check .` — all checks passed. `uv run --all-extras ruff format --check .` — 669 files already formatted. Targeted pytest (no full suite): 442 passed, 5 skipped across the migration service/CLI/unit/integration modules + `tests/meta` (ticket-id hygiene included, clean). `sq check` on this repo: clean.
    
    Everything from the first handoff still stands unchanged. `git status` now additionally shows `src/squads/_migrations/_v0_14_to_v0_15.py`, `src/squads/_cli/_migrate.py`, `tests/service/test_milestone_roll_up_tag_migration.py`, `tests/cli/test_milestone_roll_up_tag_migration_cli.py` with this shape's diff on top of the prior landing; `_sections.py` and its primitive test remain at zero diff. @manager
<!-- sq:discussion:end -->

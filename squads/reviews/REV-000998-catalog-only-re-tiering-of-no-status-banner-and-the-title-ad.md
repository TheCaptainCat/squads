---
id: REV-998
sequence_id: 998
type: review
title: Catalog-only re-tiering of no_status_banner and the title advisory
status: Approved
author: reviewer
assignee: reviewer
refs:
- FEAT-899:addresses
- TASK-996:addresses
- MILE-934:targets
description: Review of the branch that moves both checks to catalog-only and selects
  them in this project override
subentities:
- local_id: F1
  title: Whole-squad test fails at the version bump on the override stamp
  status: Verified
  severity: medium
- local_id: F2
  title: Whole-squad comparison breaks on any later selection in the override
  status: Verified
  severity: medium
- local_id: F3
  title: Repository override guards compare check names, not levels
  status: Verified
  severity: low
- local_id: F4
  title: Other-type-only title row never checks the unselecting type
  status: Verified
  severity: low
- local_id: F5
  title: Stale and history-narrating text in the new and rewritten tests
  status: Verified
  severity: low
created_at: '2026-10-11T22:14:20Z'
updated_at: '2026-10-12T05:17:26Z'
---
<!-- sq:body -->
## Scope

Review of the branch `worktree-agent-a240571530eba5b43` (four work commits and a merge of
`release/0.16`): `no_status_banner` leaves the floor, `subentity_title_max` leaves the `work`
bundle, the `add-<kind>` title advisory follows the same selection, and this repository
selects both in `squads/.overrides/workflow.toml`. Covers stories 1 to 3 of the feature;
documentation is a separate task.

## What was covered

**Read:** the whole diff of `src/` and the override file; the eight new test files and the
nine rewritten ones; the engine paths the change runs through (`effective_validator_names`,
the consistency clauses, `ValidatorEngine.gate` and `report`, `_add_block_core`, the import
apply pass). Both callers of `WorkflowSpec.item_subentity_title_max` handle `None`; nothing
else in `src/` reads the resolver or a type's `validators` list for rendering.

**Driven, in scratch squads built with the released 0.15.0 tool and then checked with both
builds** (same schema, so the released tool is the "before"):

- A default squad with a body banner and a description banner on nine types and over-long
  sub-entity titles on the three hosting types: the new build reports none of the banner or
  title findings and keeps the others.
- The same squad with this repository's override: `sq check --json` from the new build is
  byte-identical to the released tool's without the file; `sq workflow lint` and
  `sq override list` exit 0, state `current`.
- A copy of this repository's board with 21 planted findings (16 banners over nine types, 3
  titles, 2 unwritten bodies on the same items): byte-identical again, and the released tool
  reports the same with and without the file. `sq sync` from the new build writes the same
  files with and without the override.
- The effective validator set of all twelve bundled types, as (name, parameter, level): the
  new build with the override equals the released build without it on every type; without the
  override the difference is exactly the two names.
- Upgrade shapes, each loaded and checked by both builds: types already naming a check with a
  number or a level (`:80`, `:40@warn`, `@error`); `epic`, `skill` and `task` lists replacing
  the bundled one without the splat; a declared `work` type hosting a kind and a declared
  `records` type; `review` moved to `records` naming the title check alone, and naming another
  sub-entity check; a declared `records` type hosting a kind with `:40@error`; `review` moved
  to `records` naming nothing (refused by both, same message). Every explicit selection reports
  the same findings before and after; only unselected findings disappear.
- The gate with both checks at `@error`: create with a description banner, body banner,
  `add-<kind>`, sub-entity retitle, item `status` and `update`, and `sq import` (apply, and
  the pre-pass refusing a `status` after an over-long `add-subtask`). The new build and the
  released tool behave the same on every door.

**Mutated, in a scratch copy of the branch** (never in the worktree): each subtask's
falsification was reproduced (name back in the floor, name back in the bundle, advisory
compared against the constant), and four further mutations back the findings below.

## Not covered

`tests/tui`, the VS Code client, the full suite (run by the manager), `docs/` and the
changelog (separate task), and the roster types' banner path on the board copy (no verb to
set a role, skill or operator description there; covered by the effective-set comparison
and the branch's own whole-squad test).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 998 add-finding "…" --severity medium`; track with `sq review 998 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Whole-squad test fails at the version bump on the override stamp

<!-- sq:finding:F1:body -->
**Where:** `tests/integration/test_a_squad_selecting_both_checks_reports_what_the_floor_reported.py:129`,
in `_with_repo_override`:

```python
assert text.startswith(f"# squads:override-base:{__version__}\n")
```

**Input shape:** the package version moves to 0.16.0 while
`squads/.overrides/workflow.toml` keeps its `0.15.0` stamp.

**What happens:** the test fails on that line, whatever the bundled `workflow.toml` holds.
The tool itself does not ask for a restamp in that state: drift is content-gated
(`_overrides/_service.py::_workflow_state`, `_workflow/_loader.py::workflow_stamp_finding`),
so an older stamp over an unchanged bundled file is `current` and owes nothing. The task's
release-preparation list says the same (restamp only if the bundled file changed). The
assertion makes the restamp unconditional and ties a comparison about two checks to the
version number.

**Demonstrated:** in a scratch copy of the branch, `__version__` set to `"0.16.0"`, then the
three test files that read the repository override: 1 failed (this test, on line 129), 42
passed. `test_override_list_shows_workflow_as_current` stays green in that state, which is
the content-gated answer.

**Fix:** drop the assertion. The copied file does not need the running version's stamp to
load, and the stamp's standing is already asserted where it belongs, by the `sq override list`
test.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-11T22:21:50Z] Elias Python:
  - Dropped the stamp assertion; the sq override list test holds the stamp's standing.
- [2026-10-11T22:29:15Z] Paul Reviewer:
  - Verified on d7bad7bf: the stamp assertion is gone, and with `__version__` set to 0.16.0 in a scratch copy the three files that read the override pass (43 passed).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Whole-squad comparison breaks on any later selection in the override

<!-- sq:finding:F2:body -->
**Where:** `tests/integration/test_a_squad_selecting_both_checks_reports_what_the_floor_reported.py:141`:

```python
assert _report(await selecting.check()) == EXPECTED
```

`selecting` runs under the live `squads/.overrides/workflow.toml`, and the comparison is over
the whole `check()` list.

**Input shape:** the repository override gains any selection that fires on the fixture squad.
The next feature in line does exactly that: its ninth story has this project select
`body_written` and `item_title_max` in the same file, and the fixture holds a dozen items with
no written body (every "description banner" item).

**What happens:** the test goes red for a selection that has nothing to do with the two checks
it pins. The test follows its subtask as written; the consequence for the next selection was
not weighed there. The `tests/meta` table has the matching limit in a milder form: its
`SELECTIONS` value is a fixed pair (banner, title number), so "a later selection adds its row
here" needs a new column, not a row.

**Demonstrated:** in a scratch copy of the branch, `"parent_present@warn"` added to
`[items.task]` in the override: this test fails (four "task requires a parent" warnings join
the list), the other 42 tests of the three files pass.

**Fix:** compare only the two members' findings (filter the report on the banner and the title
messages before the equality), so the list stays the record of these two checks under whatever
else the override selects. Alternatively run the comparison under a selection written in the
test and leave the live file to the `tests/meta` guard.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-11T22:21:59Z] Elias Python:
  - The whole-squad test now compares only the two members' findings; checked at 0.16.0 with an extra selection (green) and with either member or the number changed (red).
- [2026-10-11T22:29:22Z] Paul Reviewer:
  - Verified on d7bad7bf: with `parent_present@warn` added to `[items.task]` (alone, and together with the 0.16.0 version) the comparison passes (43 passed); with that selection still present, a banner reported twice, a title finding at `error` and a banner missing on `review` each turn it red, so the filter hides none of the three.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Repository override guards compare check names, not levels

<!-- sq:finding:F3:body -->
**Where:** `tests/meta/test_this_repositorys_workflow_override_keeps_what_the_bundled_spec_turns_on.py:35-38`
(`_effective` keeps `parse_validator_entry(n)[0]`, the bare name) and `:67-74` (presence and
the title number only).

**Input shape:** an entry of the repository override that keeps a name and changes its level.

**What happens:** nothing fails. The story asks for both checks "at today's strength" and for
each type's other bundled validators to be kept; the guards hold the names and the title
number, not the levels. The whole-squad comparison sees a level only on a type whose fixture
holds an offender, and it has no banner item on `review` and no epic with a parent.

**Demonstrated:** in a scratch copy of the branch, the override changed to

```toml
[items.epic]
validators = [
  "no_parent@warn",
  "no_status_banner",
  "subentity_title_max:120@error",
]
```

(no splat, the bundled `no_parent` demoted from `error` to `warn`) and `"no_status_banner@error"`
on `review`: all 43 tests of the three files that read the override pass.

**Fix:** compare (name, parameter, resolved level) in the containment test, with the level
taken from the entry or from `DEFAULT_VALIDATOR_LEVEL`, and carry the expected level in the
table. A banner offender on a `review` item in the whole-squad fixture closes the other half.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-11T22:22:11Z] Elias Python:
  - The override guard compares name, parameter and level with a level column in the table, and a review banner offender joins the fixture.
- [2026-10-11T22:29:31Z] Paul Reviewer:
  - Verified on d7bad7bf: the evasion (epic list without the splat, `no_parent@warn`, `:120@error`, `no_status_banner@error` on review) now fails the containment row for epic, the table rows for epic and review, and the whole-squad test; `no_parent@warn` alone fails the epic containment row.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Other-type-only title row never checks the unselecting type

<!-- sq:finding:F4:body -->
**Where:** `tests/service/test_title_advisory_follows_the_selection.py:98-102`,
`test_selecting_the_check_on_another_type_leaves_this_type_as_it_was`. Its body ends with
`await _drive(svc, other, 80, "warn")`: only the selecting type is driven. `row`, the type
the name is about, is never given a sub-entity.

**Input shape:** the "selected on a different type only" column of the selection table, for
`subentity_title_max`. The task asks for "the selecting type reports and advises, this one
does neither". The banner twin of this test asserts both halves; this one asserts the first.

**Demonstrated:** in a scratch copy of the branch, `WorkflowSpec.item_subentity_title_max`
changed so that a type which does not select the check returns another type's number. The
three rows of this test stay green, and no test that adds a sub-entity or runs `check()`
fails. The only failures (7) are in the `tests/meta` table over the repository override, on
types that host no kind, which is a catch by coincidence.

**Fix:** add `await _drive(svc, row, None, None)` to the test, so the unselecting hosting type
is shown to get neither the advisory nor the finding at 119, 120 and 121 characters.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-11T22:22:20Z] Elias Python:
  - The other-type row now drives the unselecting type too; the leak mutation turns its three rows red.
- [2026-10-11T22:29:41Z] Paul Reviewer:
  - Verified on d7bad7bf: with the resolver leaking another type's number, the three rows of `test_selecting_the_check_on_another_type_leaves_this_type_silent` fail (feature, task, review), beside the seven `tests/meta` rows that failed before.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Stale and history-narrating text in the new and rewritten tests

<!-- sq:finding:F5:body -->
Text in the new and rewritten tests that is false after the change, or that describes how the
code got here instead of what it does. All read, none affects a result.

- `tests/service/test_subentity_title_max_threshold_is_spec_resolved.py:5-6`, module docstring:
  "a type that does not override it reproduces today's 120-character default exactly". A type
  that does not select the check now gets nothing; the two tests below it were rewritten and
  the docstring was not.
- `tests/integration/test_a_squad_selecting_both_checks_reports_what_the_floor_reported.py`:
  the file name and lines 6-7 of the docstring ("the list the engine produced before either
  check became selectable") name the test by what an earlier engine did. Name it by what it
  pins: a squad selecting both checks reports each offender once, at `warn`, with this text.
- `tests/_selection_table.py:27-31`, `TypeRow` docstring: describes a `roster` attribute the
  class does not have, and leaves `slug` and `body_authorable` undescribed.
- `tests/_selection_table.py:21`: `TITLE_MESSAGE` is defined and never used.
- `tests/unit/test_validator_engine_scaffold.py:68`: `assert "no_status_banner" not in COMMON_CORE`
  restates the set equality four lines above it.

**Fix:** correct the first three, and delete the unused constant and the redundant assert.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-11T22:22:34Z] Elias Python:
  - Docstrings corrected, file renamed to what it pins, unused constant and redundant assert removed.
- [2026-10-11T22:29:51Z] Paul Reviewer:
  - Reopened on d7bad7bf: four of the five items are done (the threshold test's module docstring, the integration file's name and docstring, `TITLE_MESSAGE`, the redundant assert). One is not: the `TypeRow` docstring in `tests/_selection_table.py` (lines 25-31) is unchanged and still describes a `roster` attribute the class does not have, with `slug` and `body_authorable` undescribed. A docstring edit, nothing else.
- [2026-10-12T04:49:33Z] Elias Python:
  - TypeRow docstring corrected in the commit after d7bad7bf (Corrected the TypeRow docstring to describe its real attributes); the other four items were already committed in d7bad7bf.
- [2026-10-12T05:17:11Z] Paul Reviewer:
  - Verified on 4b23b04c: the `TypeRow` docstring now describes `declaration`, `keep`, `kind`, `slug` and `body_authorable`, the attributes the class has, and the commit changes nothing else (two lines of `tests/_selection_table.py`).
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-11T22:15:37Z] Paul Reviewer:
  - 2026-10-12: verdict ChangesRequested, on the tests only. The product change is sound and I ask for no change in `src/`. @manager @python-dev
    
    - **To fix before the merge:** F1 and F2 (medium) are two lines in the whole-squad comparison that will turn the suite red later for reasons the test does not protect: the version bump, and the next selection this project adds to its override (the next validator feature selects `body_written`, which fires on that fixture). F4 (low) is a one-line addition. F3 and F5 (low) can ride along.
    - **Equivalence for this repository holds.** The new build with `squads/.overrides/workflow.toml` gives a byte-identical `sq check --json` to the released tool without it, on a scratch squad and on a copy of this board with 21 planted findings; the effective set of all twelve types matches as (name, parameter, level). Not covered by that comparison: the order of findings in `sq import` output (it is not sorted, and the two checks now run after the bundle members), and levels in the guards (F3).
    - **Upgrade shapes held.** Every shape I drove loads under both builds and keeps each explicit selection's findings; only unselected banner and title findings disappear. No squad that loaded before is refused now.
    - **The gate is unchanged from the released tool.** With `subentity_title_max:80@error`, `add-<kind>`, a sub-entity retitle and `sq import` accept an over-long title (import exits 3), and every `status` or `update` on the parent is then refused until the title is shortened. `no_status_banner@error` never refuses a write, including a description banner at create. Both match the subtask text and `docs/overrides.md`.
    - **The three drafting choices:** I agree with all three. No migration step exists for this release and the schema does not move, so there is nothing to attach a note to. Refusing a hosting type that names the title check alone would break overrides that load today. Reading this repository's override from `tests/meta` is sound, since nothing else can report a dropped bundled entry; the cost is in the integration comparison (F1, F2), not in the guard.
    - **For the tech writer, outside the task:** `docs/overrides.md`, validators section: "Two checks are not selected for you anywhere in the bundled spec" is now four; "Declare no parameter and the type gets the bundled default" must say a type that does not name the check runs nothing and a bare name gives 120; the sentence that neither the core nor a bundle can be subtracted from should say these two are no longer in either. Hand-written `CLAUDE.md`: the `sq check` gate section and the "No status/lifecycle prose in bodies" rule should say both rules are this project's selections in its override. No generated skill, template or playbook text describes either rule as a default.
- [2026-10-11T22:30:07Z] Paul Reviewer:
  - 2026-10-12, second pass, on commit d7bad7bf (six files, all under `tests/`): F1 to F4 are Verified, F5 is back to Open for one leftover docstring, so the review stays at ChangesRequested. @manager @python-dev
    
    - **Is the branch clear to merge into release/0.16?** Functionally yes: nothing I found, in either pass, argues against merging the code or the override. What stands between this review and Approved is a single docstring in a test helper (`TypeRow` in `tests/_selection_table.py`, which names an attribute that does not exist). I would take that one edit on the branch first, since it is a minute's work; merging without it breaks nothing.
    - **Re-run in a scratch copy of d7bad7bf, never in the worktree:** the version bump to 0.16.0, the unrelated `parent_present@warn` selection, and both together (43 passed each time); the level evasion and three single-entry changes to the override (each red on the expected rows); the resolver leak (the renamed other-type test now fails on its three rows); and three regressions of the two members with an unrelated selection present (reported twice, wrong level, missing on one type), each red through the filter.
    - **Nothing new from the commit.** The comparison's filter keys on message text (`status/lifecycle banner`, `(threshold:`), so a future check whose message carries `(threshold:` joins the compared list when it fires on the fixture; the comparison is over the exact list, so that shows as a red test, not as a hidden finding.
    - **Not re-run:** the full suite and the gates (the manager's run on d7bad7bf stands), `tests/tui`.
- [2026-10-12T05:17:26Z] Paul Reviewer:
  - 2026-10-12: Approved at branch tip 4b23b04c (`worktree-agent-a240571530eba5b43`). All five findings are Verified and the branch is clear to merge into release/0.16. @manager
    
    - 4b23b04c is a docstring-only commit: `git diff --stat d7bad7bf..4b23b04c` lists `tests/_selection_table.py`, 2 insertions and 2 deletions, and the worktree is clean at that tip.
    - Read only on this pass, no probe round: the mutations of the second pass were run on d7bad7bf, and nothing they exercise moved since.
    - The approval covers stories 1 to 3 of the feature as built on that tip. Documentation and the changelog are the tech writer's task, with the list in my first comment here.
<!-- sq:discussion:end -->

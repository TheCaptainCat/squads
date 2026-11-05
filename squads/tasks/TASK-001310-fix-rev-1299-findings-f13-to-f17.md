---
id: TASK-1310
sequence_id: 1310
type: task
title: Fix REV-1299 findings F13 to F17
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
refs:
- REV-1299:addresses
- ADR-1172
- ADR-1274
description: Override-tree coverage, custom-type help, pull report counters, then
  test fixes
subentities:
- local_id: ST1
  title: Drop the completion options from custom type groups
  status: Done
  assignee: python-dev
- local_id: ST2
  title: Require every test squad's tree in the coverage guard
  status: Done
  assignee: python-dev
- local_id: ST3
  title: Count every pulled issue in exactly one counter
  status: Done
  assignee: python-dev
- local_id: ST4
  title: Split the twin-holder case and compare whole objects
  status: Done
  assignee: python-dev
- local_id: ST5
  title: Replace substring asserts; fold two check cases
  status: Done
  assignee: python-dev
created_at: '2026-11-05T04:27:13Z'
updated_at: '2026-11-05T06:17:57Z'
priority: high
---
<!-- sq:body -->
## Goal

Fix REV-1299's findings F13 to F17, so the 0.20 tests follow ADR-1172 as corrected on 2026-11-05 (rule 3, every test squad's tree) and the pull report follows ADR-1274 §14, "The pull report's counters".

## Rounds

1. ST1 (F14), then ST2 (F13). ST1 is a product bug; ST2 makes the guard walk the override squad's tree, which surfaces the pairs ST1 removes and the cases still missing.
2. ST3 (F15): the pull report's counters.
3. ST4 (F16) and ST5 (F17): test-only fixes on modules ST2 and ST3 have settled.

## Overlap with TASK-1309

TASK-1309 (python-dev, InProgress) has uncommitted changes in `src/squads/_services/_base.py`, `_items.py`, `_subentities.py`, `_validators.py`, `_workflow/_validator_names.py`, `_cli/_render/_rows.py`, `tests/check/test_subentity_rules.py`, `tests/cli/test_create.py`, `test_import.py`, `test_item_verbs.py`, `test_show.py`, `test_source_pull.py`, `test_subentity_verbs.py`, `CHANGELOG.md` and `docs/overrides.md`.

- ST1: the fix (`_cli/_app.py`, `_cli/_create.py`) is clear; its cases go in `test_create.py` and `test_item_verbs.py`, so they wait.
- ST2: the guard and fixture (`tests/meta/`, `tests/_cli_surface.py`, `tests/conftest.py`) are clear; the new cases (`test_subentity_verbs.py` at least) wait.
- ST3: waits (`test_source_pull.py`, `CHANGELOG.md`).
- ST4: waits (`test_source_pull.py`, `test_item_verbs.py`).
- ST5: waits (`test_item_verbs.py`, `test_show.py`; `tests/check/test_source_rules.py` is another file in the directory TASK-1309 gates on).

Dispatch after TASK-1309 is committed. Starting earlier is possible only for the clear parts of ST1 and ST2.

## Tests

CLI surface cases per ADR-1172, run on both test squads. Expected count: about +5 test functions in all.

- ST1: +2 (one per command).
- ST2: +1 to +3, one per pair the override tree adds that no case declares; report the list.
- ST3: none new; re-pin the existing cases.
- ST4: +1 (the field-skipped case).
- ST5: -2 (the two check cases fold into breach cases).

Falsify each new or re-pinned case: break the fix, watch it go red, restore it.

## Gates

`uv run --all-extras pyright`, `ruff check` and `ruff format --check` clean on touched files; `tests/meta`, `tests/check` and the touched `tests/cli` modules pass on the bundled squad and with `--squad override`; `~/.local/bin/sq check` clean. The main loop runs the full suite. Comments and docstrings: one or two sentences, no versions, ticket IDs or history.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1310 add-subtask "<title>"`; track with `sq task 1310 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Drop the completion options from custom type groups

<!-- sq:subtask:ST1:body -->
REV-1299 F14. On a squad whose workflow override declares its own types, `sq <type> --help` and `sq create <type> --help` list Typer's `--install-completion` and `--show-completion`; bundled types do not. Reproduced on the override test squad (`sq job --help`, `sq create job --help`).

Likely sites (inferred, trace before fixing):

- `src/squads/_cli/_app.py:258`: the custom type group is built with `typer.main.get_command(type_app)` straight on the Typer `build_item_app` returns, while bundled groups go through `_group_command`, whose host is `typer.Typer(add_completion=False)`.
- `src/squads/_cli/_create.py:148`: `_build_create_cmd` uses `typer.Typer()`, which keeps `add_completion=True`.

Fix: build both with `add_completion=False`, like the bundled ones.

Regression test, two cases on both squads, through `profile.ref` (`job`, a custom type, on the override squad; `task` on the bundled one): the full option lines of `sq <type> --help` (in `test_item_verbs.py`) and of `sq create <type> --help` (in `test_create.py`), compared whole. On the override squad they hold the bug; on the bundled squad they hold the same surface. QA was asked to file the bug on REV-1299: ref it here once it exists.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Require every test squad's tree in the coverage guard

<!-- sq:subtask:ST2:body -->
REV-1299 F13. ADR-1172 rule 3, as corrected on 2026-11-05: the coverage guard requires every pair of each test squad's tree, each tree built with its squad's spec bound. A pair one squad's tree alone has is still declared once and checked against the squad that has it. A marker is stale only when no test squad's tree has its pair or key. The `invoke` teardown checks a marker against the tree of the squad the run uses, and skips a pair only the other squad has.

The code follows the retracted wording:

- `_surface()` (`tests/meta/test_every_cli_parameter_is_declared_by_a_covering_test.py:112`) builds the surface from the bundled tree and treats `squad_known() - bundled.known` as known, not required.
- `squad_known()` (`tests/_cli_surface.py:342`) adds only the `--<attribute:map>` derivation; it never walks the override tree.

Fix:

- The guard builds the override squad's tree with its spec bound, beside the bundled one, and requires the union of their pairs and leaves.
- `squad_known` goes away.
- The `invoke` teardown (`tests/conftest.py`) and `check_json`'s teardown (`tests/check/conftest.py`) where it checks pairs, resolve a marker against the run's squad tree; a pair only the other tree has is skipped, not reported unreached or stale.
- Add a case for each pair the override tree adds that no case declares. Known: `<type> <kind> update --no-<field>`, from a kind field that is not required (`test_subentity_verbs.py`). `--install-completion` / `--show-completion` must not appear once ST1 is in.

Falsify the guard: remove one override-only marker and watch the guard name the pair; add a marker for a pair neither tree has and watch it reported stale.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Count every pulled issue in exactly one counter

<!-- sq:subtask:ST3:body -->
REV-1299 F15, ruled in ADR-1274 §14, "The pull report's counters" (product-owner, 2026-11-05). Every issue a pull sees lands in exactly one counter, and the counters sum to the issues seen. A counter counts issues, not items. A zero counter is not printed.

Code:

- `SourcePullReport` (`src/squads/_api/_dto/_sources.py:61`): add `gone`, `dropped` and `held_elsewhere`. Each counter's docstring states its ADR definition, and the class docstring states the exactly-one rule.
- Summary line (`src/squads/_cli/_render/_sources.py`): print the counters in the ADR's order, zero ones left out.
- Gone (`src/squads/_services/_pull.py:599-609`): the gone path emits its event but increments nothing; count it as `gone` only.
- Dropped: the import pre-pass (`_without_failing_issues`, `_pull.py:640-680`) discards `created` and leaves `refreshed`; an issue whose every event was dropped counts as `dropped`, never created or refreshed. An issue with some events applied stays refreshed.
- Held elsewhere (`_triage`, `src/squads/_services/_fetch.py:95-116`): an issue an item of another source of the tracker holds, with no item of this source, is `held_elsewhere`; `filtered_out` then means no item of any source holds it.
- An issue two items of one source hold counts once.

Re-pin the counts round 3 pinned from observed output, to the ruled values: the filter-lost case (`test_source_pull.py`, about `:737`), the dropped-event and dropped-link cases (about `:1276` and `:1305`; measure whether the second pull of the dropped-link case writes anything), and the two split sources (about `:520-583`). Update the expected-output helper `tests/cli/_output.py`.

Delivered text: `docs/sources.md` (the summary line, the paragraph on what the line counts, the `--json` key list), `docs/stability.md:1415` (the report's `--json` keys), and one CHANGELOG line under the unreleased section. These are the tech writer's: report the counter facts and the new keys in a comment to @tech-writer, who writes them.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Split the twin-holder case and compare whole objects

<!-- sq:subtask:ST4:body -->
REV-1299 F16, ADR-1172 Scope and rule 5.

`test_two_items_holding_one_issue_are_both_refreshed_and_no_third_is_made` (`tests/cli/test_source_pull.py`, about `:814-860`) creates the twin as `profile.host`, then branches its expected lines on `profile.host_has_badge`: only the override run asserts the "<badge> skipped" line.

Fix:

- Make the twin `profile.ref`, so both squads expect the same lines, compared whole.
- Give the field-skipped line its own case, named for it, through a profile entry (`tests/_profile.py`) for a type that lacks the badge field on both squads. The profile guard (`tests/meta/test_every_profile_entry_resolves_against_its_squads_spec.py`) checks the new entry.
- If `host_has_badge` has no reader left, remove it.

Fold in the leftover partial JSON checks, comparing the whole object: `test_source_pull.py` about `:858` (`(twin_row["title"], twin_row["source"])`) and `:1044` (`first["source"]`), `test_source_credential.py:59` (`removed["removed"]`), and `test_item_verbs.py:1811-1827` (the map attribute values). Line numbers are at 9955faac; ST3 moves them.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Replace substring asserts; fold two check cases

<!-- sq:subtask:ST5:body -->
REV-1299 F17, ADR-1172 rule 5 (whole lines, never a substring) and CONTRIBUTING's check-rule rule (each case declares `breaches`).

84 `in` / `not in` / `startswith` / `endswith` asserts in 0.20 tests added after the first audit (973058e5..9955faac), outside TASK-1300: `test_role.py` 31, `test_migrate.py` 13, `test_item_verbs.py` 13, `test_skill.py` 9, `test_init.py` 6, `test_sync.py` 5, `test_repair.py` 4, `test_show.py` 3. The reviewer's list of sites is in `/home/pchat/.cache/sq-review-1172/later_substr.txt`.

- Positive containment asserts compare whole lines or whole documents.
- Absence checks stay (a secret, an escape code, a stripped region that must not appear).
- Report the count rewritten and kept per module.

Two check-rule cases with no `breaches` marker, each running the report once: `tests/check/test_source_rules.py:657` (`test_prose_that_names_the_attribute_tag_is_not_an_attribute_line`) and `:682` (`test_a_body_example_naming_an_undeclared_source_author_is_not_a_comment`). Fold each into the `comment_attributes_valid` and `source_author_declared` breach cases, as a sibling item that must not be reported.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T04:27:36Z] `tech-lead` Olivia Lead:
  - Planned in Draft: rounds ST1 (F14) then ST2 (F13); ST3 (F15); ST4 (F16) and ST5 (F17).
  - Every subtask touches a file in TASK-1309's uncommitted diff (test_create, test_item_verbs, test_show, test_source_pull, test_subentity_verbs, CHANGELOG); dispatch after TASK-1309 is committed. @manager
- [2026-11-05T04:35:40Z] `manager` Catherine Manager:
  - Also in this task's last round: REV-1307 F6 (role update --title must go through require_title and refuse a line break like every other title write) and F7 (a pull's report names the refusal without the --title flag, since a pull has no flag; the CHANGELOG quotes the messages as each command prints them).
- [2026-11-05T04:41:52Z] `python-dev` Elias Python:
  - Round 1 (ST1, ST2) done, uncommitted.
    
    - ST1 (F14) cause: two sites, both confirmed by fixing one at a time. build_item_app made its Typer with the default add_completion=True, and typer.main.get_command(type_app) in the custom type group (_cli/_app.py) adds the completion options for a callback group; _build_create_cmd in _cli/_create.py did the same. Both now pass add_completion=False (fix in _cli/_items.py and _cli/_create.py).
    - ST1 tests: +2 through profile.ref (group help panel compared whole; create help option list), profile gains create_flags with a guard row.
    - ST2 (F13): the guard requires the union of the bundled tree and the override squad's tree built from a real override squad dir with its spec bound; squad_known is gone; the invoke teardown checks a marker against the trees of the squads the test's calls ran on. check_json does not check pairs, so it is unchanged.
    - ST2 newly required: only <type> <kind> update --no-<field>. It is declared on the existing optional-field clear case. No completion pairs appear.
    - Gates: pyright, ruff check and format clean; bundled run 2307 passed, 4 skipped; override run 1985 passed, 171 skipped; sq check clean.
    - Mutations: reverted each ST1 fix (help cases red); removed the new marker (guard names the pair); added a ghost marker (reported stale); dropped the teardown filter (a temporary bundled case declaring the override-only pair errors).
- [2026-11-05T05:01:59Z] `python-dev` Elias Python:
  - Round 2 (ST3, F15) done, uncommitted. @tech-writer, the facts for docs/sources.md, docs/stability.md and the CHANGELOG follow.
    
    Counter facts (ADR-1274, "The pull report's counters"):
    - New `--json` keys on each source's report: `dropped`, `gone`, `held_elsewhere`, all integers, always present (0 when none). Key order: created, refreshed, unchanged, left_out, lines, failed, dropped, gone, restricted, held_elsewhere, filtered_out, skipped_no_type.
    - Summary line prints, in this order, only the non-zero counters: created N (ids), refreshed, unchanged, dropped, gone, restricted, held elsewhere, filtered out, skipped N (no type). A zero counter is left out, including created, refreshed and unchanged (the line used to always print those three). When every counter is zero the line reads `<name>: no issues`.
    - Every issue a pull sees is in exactly one counter; they sum to the listed issues plus each held item's issue the listing did not return. A counter counts issues, not items: an issue two items of one source hold counts once, as refreshed if either item changed.
    - dropped: the squad refused every event compiled for the issue (so nothing written), whether or not an item holds it; the issue is not counted as created or refreshed and the next pull retries. An issue with some events applied (for example only a link dropped) stays refreshed.
    - gone: an item holds it and the tracker neither lists it nor returns it by ID (deleted, or now restricted); counts here only. An item already gone and unchanged counts as unchanged.
    - held_elsewhere: an item of another source of the tracker holds it and this source has none; named on a held-by line only when the filter accepts it.
    - restricted: now only restricted issues no item holds (a held one is gone).
    - filtered_out: the filter rejects it and no item of any source holds it. skipped_no_type now also counts an issue mapping to two types (its line is kept).
    - Cost: the connector exposes the restricted issue IDs; no `--json` change for that.
    
    Open points for the coordinator:
    - A listed, unheld issue the tracker stops returning while it is read ("skipped, the tracker stopped returning it") is counted nowhere, so the sum is short by that case.
    - In one unnamed pull, an issue the filter rejects that a source compiled earlier in the same pull creates still counts as filtered_out (triage runs before the creation).
    - ADR says held_elsewhere is named on a held-by line; a filter-rejected one is counted but not named, as before.
- [2026-11-05T05:04:11Z] `manager` Catherine Manager:
  - The two counting edge cases in the round 2 handback (an issue the tracker stops returning mid-read; a filter-rejected issue another source creates later in the same unnamed pull) are accepted as known gaps of the exactly-one rule for this release.
- [2026-11-05T05:07:53Z] `tech-writer` Theo Writer:
  - - Pull report counters documented, uncommitted. @manager
    - docs/sources.md: summary example now shows gone and held elsewhere; the counting paragraph is replaced by the exactly-one rule, a counter table in print order, zero counters not printed and `<name>: no issues`; the `--json` list adds `dropped`, `gone`, `held_elsewhere` (always present, 0 when none). Also aligned: the type map (two types count as skipped), restricted issues (only unheld ones; a held one counts as gone) and the held-by paragraph (now counts as held elsewhere instead of no count).
    - docs/stability.md: the pull report's key list follows the DTO order.
    - CHANGELOG 0.20 (Added): the pull entry's example and key list corrected, plus one new bullet for the counters.
    - Verified on the dev build with the gitlab fixture routes served by the tracker harness on a scratch squad: `created 2 (...)`, `unchanged 2`, `unchanged 1, gone 1`, an already-gone unchanged item counts as unchanged, an empty listing prints `platform: no issues`; `--json` key order matches.
    - tests/meta: 748 passed.
- [2026-11-05T05:42:17Z] `python-dev` Elias Python:
  - Round 3 (ST4, ST5, REV-1307 F6 and F7) done, uncommitted. Facts for @tech-writer (CHANGELOG, docs):
    
    - F7 refusal wording: the service no longer names the flag. Every title refusal reads `title must not be empty`, `title must be a single line` or the marker refusal with `title`, on every surface: `update --title` (item and sub-entity), a pull's retitle, `role update --title`, create and add. Before, `update --title` printed `error: --title must be ...`; the CHANGELOG line that quotes `error: title must be a single line` for every surface is now true as written, and any line quoting `error: --title must ...` needs the flag dropped.
    - A pull's report line reads `platform/api#13: dropped, title must not be empty` (or `title must be a single line`), with no flag.
    - F6: `sq role <slug> update --title` now refuses a line break or a marker tag with `error: title must be a single line`; the role is not changed. A blank name keeps its own message, `a role's name cannot be blank`.
- [2026-11-05T05:52:56Z] `tech-writer` Theo Writer:
  - Title refusal wording documented, uncommitted. CHANGELOG 0.20 title line now lists role update --title; docs/overrides.md (title_single_line, role rename) and docs/roles.md state the single-line and blank-name refusals. No old --title wording was quoted anywhere. Verified on a scratch squad (item, sub-entity, role, create); tests/meta 748 passed.
- [2026-11-05T06:02:01Z] `python-dev` Elias Python:
  - Reopened F15 and F17 fixed, uncommitted. F15: item 2's issue compiles a record event (kept at the stored time, so it writes nothing) plus the dangling link event, which is refused; since not every event is refused it is not dropped, and since nothing is written it is unchanged. The pre-pass now counts an issue whose surviving events are only records equal to the stored ones as unchanged. The case pins unchanged=1, dropped=1 on both pulls: the unchanged is issue 12, the dropped is issue 13 (blank title), two issues. F17: test_role.py membership now on before.splitlines().
- [2026-11-05T06:12:37Z] `python-dev` Elias Python:
  - F19 fixed, uncommitted. The refreshed/unchanged count is now made once, after the pre-pass: a held issue (not dropped) with a surviving event is refreshed, else unchanged. _keeping_stored_time drops a source event whose kept record equals the stored one. Removed: Compiled.refreshed_labels, the refreshed/unchanged restore in attempt(), the refreshed half of uncount() (gone stays), the per-path increments in issue(), the changed return of refresh(), _count_unwritten_as_unchanged and _is_stored_record. Added: held_labels, _count_held, and a dry-run case pinning refreshed 1, unchanged 1, dropped 1 equal to the real pull. No existing pull counter case changed.
<!-- sq:discussion:end -->

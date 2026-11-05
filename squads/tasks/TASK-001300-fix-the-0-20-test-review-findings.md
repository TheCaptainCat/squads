---
id: TASK-1300
sequence_id: 1300
type: task
title: Fix the 0.20 test review findings
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
refs:
- REV-1299:addresses
- ADR-1172
description: Override-squad and Windows CI fixes first, then the REV-1299 findings
  against ADR-1172
subentities:
- local_id: ST1
  title: Source CLI tests run on the override squad
  status: Done
  assignee: python-dev
- local_id: ST2
  title: Coverage teardown passes over a skipped test
  status: Done
  assignee: python-dev
- local_id: ST3
  title: Arrange and read source states through the CLI
  status: Done
  assignee: python-dev
- local_id: ST4
  title: Load refusals in tests/check, markers name their parameter
  status: Done
  assignee: python-dev
- local_id: ST5
  title: 'CONTRIBUTING: one case per load-rule message'
  status: Done
  assignee: python-dev
- local_id: ST6
  title: One case per refusal, named for it
  status: Done
  assignee: python-dev
- local_id: ST7
  title: Whole message lines and whole JSON objects
  status: Done
  assignee: python-dev
- local_id: ST8
  title: Check-rule cases follow the breach-test rules
  status: Done
  assignee: python-dev
- local_id: ST9
  title: Stored-view helper merges into the override
  status: Done
  assignee: python-dev
- local_id: ST10
  title: Each case in its command group's module
  status: Done
  assignee: python-dev
created_at: '2026-11-04T23:33:24Z'
updated_at: '2026-11-05T04:11:06Z'
priority: high
---
<!-- sq:body -->
## Goal

Fix the REV-1299 findings, so the 0.20 tests follow ADR-1172 as amended on 2026-11-04 (op-pierre's ruling 5673927 on REV-1299: leaf modules for a large group, credential reads, `sources.toml` load refusals), and the release PR's CI goes green.

Four CI jobs on the release PR fail because of these tests (run 41932646293):

- `override-squad` and `remote-mode-override`: the `tests/cli/test_source*.py` modules spell bundled vocabulary (F1).
- `test (windows-latest)` and `remote-mode (windows-latest)`: three errors at teardown, `covers declares pairs no call reached`, on the credential cases that skip on Windows (ST2).

## Rounds

Each round leaves the fast gates green; the main loop runs the full suite and commits before the next round. Brief each round with its subtask IDs and "stay out of the later subtasks".

| Round | Subtasks | Why this order |
|---|---|---|
| 1 | ST1, ST2 | The two red CI jobs: the override squad and Windows |
| 2 | ST3, ST4, ST5 | CLI-only arrangement and reads; load refusals move to `tests/check` under the rule CONTRIBUTING then states |
| 3 | ST6, ST7 | One case per refusal, then whole lines and whole JSON objects |
| 4 | ST8, ST9 | Check-rule cases and the stored-view helper |
| 5 | ST10 | Move cases into their groups' modules last, once their content is settled |

## Overlap with TASK-1295

TASK-1295's python-dev edits these files now (round 3 of that task): `tests/cli/test_board.py`, `test_init.py`, `test_item_verbs.py`, `test_memory.py`, `test_role.py`, `test_show.py`, `test_skill.py`, `test_sync.py`, `test_workflow.py` and `tests/check/test_corpus_integrity_rules.py`.

- Rounds 1 and 2 touch none of them.
- ST7 edits `tests/cli/test_workflow.py`.
- ST8 edits `tests/check/test_corpus_integrity_rules.py`.
- ST9 edits `tests/cli/test_item_verbs.py` and `test_show.py`.
- ST10 moves cases into `tests/cli/test_item_verbs.py`, `test_show.py`, `test_role.py` and `test_workflow.py`, among others.

Dispatch this task after the current TASK-1295 round is committed, and run rounds 3 to 5 only between TASK-1295 rounds, never beside one.

## Gates

- Fast gates: `uv run --all-extras pyright`, `ruff check`, `ruff format --check`, and `uv run --all-extras pytest -n 4` on the touched modules plus `tests/meta`.
- Every round runs the touched modules on both squads: `--squad override` as well as the default.
- Falsify each fix: break the case's subject, see it go red, restore it.
- `~/.local/bin/sq check` clean. No commit.
- Mark each finding Fixed on REV-1299 as its subtask lands, with a finding comment naming the change.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1300 add-subtask "<title>"`; track with `sq task 1300 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Source CLI tests run on the override squad

<!-- sq:subtask:ST1:body -->
REV-1299 F1. Round 1.

- In the eleven `tests/cli/test_source*.py` modules, build every name the cases spell from the `profile` fixture, as `test_item_verbs.py` does: the `maps.types` targets (`issue = "task"`, `bug = "task"`, `Story = "task"`), the field maps (`maps.fields.priority`, from a badge field of the profile and its values), and every address (`["task", "2", "show", ...]`, `create task`, `TASK-2`, `retype bug` at `test_source_ownership.py:124`, `[items.task.attributes]` at `test_source_identities.py:112`), through `P.ref` and `P.ref_prefix`.
- Give `bundled_only` with a reason only to a case that is about the bundled squad's own spelling.
- Change nothing else in the cases: whole-line asserts, markers and module moves are ST4, ST6, ST7 and ST10.
- Done when `uv run --all-extras pytest -n 4 --squad override tests/cli` passes, in local mode and with `SQUADS_TEST_MODE=remote` (the CI jobs at `.github/workflows/test.yml:109` and `:252`), and the default squad still passes.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Coverage teardown passes over a skipped test

<!-- sq:subtask:ST2:body -->
Round 1. The `test (windows-latest)` and `remote-mode (windows-latest)` failures, three errors at teardown: `test_credential_set_reads_each_value_from_stdin_and_stores_it_privately`, `test_credential_set_ignores_what_a_crash_left_and_tightens_an_open_directory` and `test_a_store_other_users_can_read_is_refused_naming_chmod`.

**Cause.** `_posix_modes_only()` in `tests/cli/test_source.py` calls `pytest.skip` inside the test body. The `invoke` fixture is already set up, no command runs, and its teardown fails the test with `covers declares pairs no call reached`.

**Fix: the teardown passes over a skipped test**, not a `skipif` mark. A mark fixes these three cases only. Any case whose skip condition is known only at run time hits the same teardown: `tests/cli/test_sync.py:146` skips when a shell is not installed, `tests/cli/test_daemon.py:207` when the platform refuses a link.

- `tests/conftest.py`: a `pytest_runtest_makereport` hookwrapper stores each phase's report on the item (`item.stash`); the `invoke` teardown skips its pair check when the call phase was skipped. A failed or passed call keeps the check.
- `tests/check/conftest.py`: the `check_json` teardown follows the same rule through the same stored report.
- Leave `_posix_modes_only()` as it is: it is the case Windows CI runs.
- CONTRIBUTING.md:245 and `:274`: the two teardown sentences say a skipped test is not checked.
- Falsify on Linux: make `_posix_modes_only()` skip unconditionally. Before the fix the three cases error at teardown; after it they are skipped. Do the same with a temporary skip in one `tests/check` breach test. Restore both.
- Mention @architect in the handoff: ADR-1172's teardown sentence ("At teardown it fails the test when a declared key or pair is not among them") may need the same exception.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Arrange and read source states through the CLI

<!-- sq:subtask:ST3:body -->
REV-1299 F3, F4 and F5. Round 2.

- **F3.** `tests/cli/test_source_record.py:59-73`: drop the assertion on the rebuilt `.squads.json`'s key set. The `after == before` comparison of `show --json` already proves the rebuild.
- **F4.** Arrange through the tracker harness (`tests/_tracker_harness.py`) and `sq source pull`, then read through `show --json` and `comments --json`:
  - `test_source_record.py:52-73`: the valid record `_mirror` writes by hand;
  - `test_source_record.py:93-107`: the `source:platform` comment header (a pull writes it, `test_source_pull.py:610`);
  - `test_source_comments.py:184-186`: the renamed `author_name`, from a tracker note whose author name changes with `updated_at` bumped. If the pull does not refresh author attributes by design, keep the hand edit and say so in the test's docstring.
  - Keep the hand-written states no command writes (the list under F4 "Legitimate, keep").
- **F5**, per op-pierre's ruling 5673927: read stored credentials back through `sq source credential … --json`. Open the store file only for what no command shows (its `0600`/`0700` modes, the secret gone after `remove`), with the path from the test's own `credentials_home` fixture layout. No `CredentialStore` import from `src` in `tests/cli/test_source.py` (`:13`, `:46`, `:161-229`) or `tests/daemon/test_the_credential_verbs.py` (`:10`, `:49`, `:76`). The expected `path` in `_written` comes from the fixture too, so a wrong store location fails.

Files: `tests/cli/test_source_record.py`, `test_source_comments.py`, `test_source.py`, `tests/daemon/test_the_credential_verbs.py`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Load refusals in tests/check, markers name their parameter

<!-- sq:subtask:ST4:body -->
REV-1299 F6 and F7. Round 2, with ST5.

Per op-pierre's ruling 5673927 and ADR-1172 as amended:

- **`sources.toml` load and grammar refusals** move to `tests/check/test_source_rules.py`, one case per distinct message, each declared `breaches("sources_loads")`. `tests/cli` keeps one case showing that a command refuses when `sources.toml` does not load.
  - From `tests/cli/test_source.py:89, 105, 117, 129`, `test_source_connectors.py:385, 403`, and the 16 cases of `test_source_scope.py` (`:39-307`) with their tables (`:141-321`).
  - One row per distinct message. Drop the rows that repeat a message at another position or with another character (F7 lists them).
  - Drop `test_source_scope.py:236`: it duplicates the `sources_loads` breach test.
- **Author-name escapes**, `test_source_comments.py:121-138`: one case whose name carries a quote and a control character, plus the empty-name case if its output differs.
- **Markers name the parameter the assertion is about:**
  - `test_source_ownership.py:50`: the priority refusal declares the derived field option's pair, not `--title`;
  - `test_source_identities.py:108`: the `--links` effect declares the derived map option's pair, not `--set`.

Files: `tests/cli/test_source.py`, `test_source_connectors.py`, `test_source_scope.py`, `test_source_comments.py`, `test_source_ownership.py`, `test_source_identities.py`, `tests/check/test_source_rules.py`.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — CONTRIBUTING: one case per load-rule message

<!-- sq:subtask:ST5:body -->
Round 2, with ST4. The line the architect flagged on REV-1299 (comment 58b769c).

- CONTRIBUTING.md:255 ("`tests/check/` has one breach test per rule `sq check` reports"): add that a load rule, such as `sources_loads`, has one case per distinct message, as ADR-1172 now says.
- One sentence, in the section's existing voice. No other CONTRIBUTING change.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — One case per refusal, named for it

<!-- sq:subtask:ST6:body -->
REV-1299 F9. Round 3.

- `tests/cli/test_source_links.py:244` (`…_and_more`): one case per refusal (a record still held, not sourced, the wrong source, a key already held, a malformed key). Each is named for its refusal and declares the parameter it is about.
- `test_source_links.py:214`: the marker becomes the `--json` pair plus one argument pair.
- `test_source_links.py:403, 422, 441, 654, 690`: `covers(key, "source")` and `covers(key, "issue")` as separate markers, each only where its effect is asserted.
- `test_source_ownership.py:50, 83`: one case per batched refusal.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Whole message lines and whole JSON objects

<!-- sq:subtask:ST7:body -->
REV-1299 F2 and F10. Round 3.

- **F2, whole message lines.** Compare `(exit_code, output)` with the whole expected text at the sites F2 lists, including `tests/cli/test_migrate.py:358-359`. Normalise the tracker's port as `_checked` does (`test_source_check.py:45-48`). Drop the `" ".join(output.split())` rewrapping, so line breaks are asserted too. Keep the negative containment checks that the secret never leaks.
- **F10, whole JSON objects.** Compare the whole `--json` document at the sites F10 lists, including `tests/cli/test_workflow.py` (`test_views_json_marks_a_view_that_keeps_a_stored_body`). Normalise only what varies by run (tracker address, `etag`), as `_shown` does. Build the expected document with a small helper per module, like `issue(...)` in `tests/check/_arrange.py`.

Overlap: `tests/cli/test_workflow.py` is a TASK-1295 file.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Check-rule cases follow the breach-test rules

<!-- sq:subtask:ST8:body -->
REV-1299 F11. Round 4.

- `tests/check/test_prose_rules.py:166`: declare `breaches("body_written")` and assert the clean state before the breach, or fold the stored-pair boundary into the existing `body_written` case as a sibling item that must not be reported.
- `tests/check/test_source_rules.py:86-123`: split `source_declared` into a disabled case and an undeclared case.
- `test_source_rules.py:261-284` (`comment_attributes_valid`) and `tests/check/test_corpus_integrity_rules.py:480-499`: assert the whole array built with `issue(...)`. Normalise the timestamp only if the frozen clock does not fix it.
- `test_source_rules.py:134`: drop the extra partial assertion.

Overlap: `tests/check/test_corpus_integrity_rules.py` is a TASK-1295 file.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Stored-view helper merges into the override

<!-- sq:subtask:ST9:body -->
REV-1299 F12. Round 4.

- `tests/_stored_view.py:20-27`: `declare_stored_view` adds its `[views.<name>]` table to the squad's existing `.overrides/workflow.toml` instead of overwriting it, so the override squad keeps its vocabulary.
- Drop the nine `bundled_only("the stored view is declared by an override")` markers: `tests/cli/test_item_verbs.py:1323, 1340, 1360, 1372, 1400, 1415`, `tests/cli/test_show.py:289, 317`, `tests/cli/test_repair.py:297`.
- `test_repair.py:297` spells `task 3`: address it through the profile.
- The nine cases pass with `--squad override`.

Overlap: `tests/cli/test_item_verbs.py` and `test_show.py` are TASK-1295 files.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — Each case in its command group's module

<!-- sq:subtask:ST10:body -->
REV-1299 F8. Round 5, last, so the earlier subtasks edit the cases where F1-F12 locate them.

Per op-pierre's ruling 5673927 and ADR-1172 rule 6 as amended:

- `source` is a large group: one module per leaf (`test_source_pull.py`, `test_source_check.py`, `test_source_credential.py`, …). Each case lives in the module of the command its marker declares.
- Cases of other groups move to those groups' modules (the sites F8 lists): `<type> show`, `<type> update`, `<type> body`, `<type> retype`, `<type> source unlink|relink`, `<host> comment`/`comments`, `inbox`, `operator update`, `role add`, `check`, `repair`, `import`, `override scaffold`, `workflow view`.
- The feature modules with no leaf (`test_source_comments.py`, `_connectors`, `_converters`, `_identities`, `_links`, `_ownership`, `_record`, `_scope`) are emptied and deleted.
- A move changes no case: compare the collected test count before and after (`pytest --collect-only`), and the `tests/meta` coverage guard stays green.

Overlap: the destinations include `tests/cli/test_item_verbs.py`, `test_show.py`, `test_role.py` and `test_workflow.py`, all TASK-1295 files.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T23:37:58Z] `tech-lead` Olivia Lead:
  - Authored for REV-1299 (ten subtasks, five rounds). Round 1 is ST1 (F1, the override-squad jobs) and ST2 (the Windows teardown errors, fixed in the coverage teardown so any test that skips at run time passes it). Rounds 3 to 5 touch files TASK-1295's python-dev is editing (`test_workflow.py`, `test_corpus_integrity_rules.py`, `test_item_verbs.py`, `test_show.py`, `test_role.py`): run them between TASK-1295 rounds. Parented to FEAT-1173 as TASK-1199 was for REV-1198; FEAT-1173 is Done and should reopen when this task is dispatched. Left in Draft. @manager
- [2026-11-04T23:57:03Z] `python-dev` Elias Python:
  - Round 1 done (ST1, ST2 Done); nothing committed.
  - ST1: the eleven tests/cli/test_source*.py modules build type maps, field maps, addresses and ids from the profile. Profile gained host_folder/host_path (guard row added). The override squad fixture now selects the source_description view, which a pull needs. Two cases adapted: the scaffolded worked example is bundled_only; the scaffold-list assert filters to the sources entry.
  - ST2: a pytest_runtest_makereport wrapper stashes each phase report; the invoke and check_json teardowns skip their check when the call was skipped. CONTRIBUTING updated. Falsified with a forced skip (3 credential cases and one tests/check case): error at teardown before, skipped after.
  - Gates: bundled 2210 passed, 2 skipped; override tests/cli 1022 passed, 179 skipped, local and remote mode; pyright, ruff clean.
  - @architect: ADR-1172 teardown sentence ("At teardown it fails the test when a declared key or pair is not among them") needs the same exception: a test that skipped itself is not checked.
- [2026-11-05T01:40:23Z] `python-dev` Elias Python:
  - Round 2 handback. ST3 (F3, F4, F5) and ST5 Done; ST4 (F6, F7) stays InProgress: F7 Fixed, F6 partly. Open: the --links effect in test_source_identities has no declarable pair (no map-option derivation in tests/_cli_surface.derived_names, so a --links marker is stale in the coverage guard); needs an architect ruling. test_source_ownership:50 still declares --title and --<field> together until ST6 splits it. Gates: pyright/ruff/format clean; tests/meta cli check daemon regressions 2236 passed 2 skipped; --squad override cli check 1185 passed 179 skipped, 0 failed. Logs in /home/pchat/.cache/sq-loop/r2-*.log. sq check clean.
- [2026-11-05T01:43:01Z] `manager` Catherine Manager:
  - F6 --links: the override squad's workflow override declares one map attribute on its reference type and its profile names it, and tests/_cli_surface gains the --<attribute:map> derivation like the str/list/date ones, so the derived option exists in that squad's tree and a marker can declare it. Goes into the ST6 round; the architect records the derivation in ADR-1172 rule 3.
- [2026-11-05T03:39:23Z] `python-dev` Elias Python:
  - - Round 3 handback. ST4, ST6, ST7 Done; REV-1299 F2, F6, F9, F10 Fixed. Nothing committed; `tests/cli/_pulled.py` is a new untracked file.
    - **F6 map option.** Derivation named `--<attribute:map>`: a settable `kind = "map"` attribute of a non-roster type, derived on `<type> update` (`tests/_cli_surface.derived_names`). The override squad's workflow declares `links = { kind = "map" }` on `job`; the profile gains `map_type`/`map_attr`. The bundled tree has no such option, so `_cli_surface.squad_known()` adds `(<type> update, --<attribute:map>)` to the pairs a marker may name; the coverage guard and the `invoke` teardown use it (`Surface.other_squads`). The case that reaches it declares the attribute in its own override on the bundled squad. The architect records the derivation in ADR-1172 rule 3. Side effect: `job update --help` now lists `--links`, so one help line in `test_subentity_verbs` moved.
    - **F9.** Five relink refusals, ownership title/field/desc, comment edit/remove and `--as`/import are one case each; effect markers reduced to `--json`+`source`, refusals declare `source` or `issue`.
    - **F2/F10.** About 250 assert statements in 11 source modules plus `test_migrate` and `test_workflow` replaced by whole-line or whole-object compares. Helpers: `tests/cli/_pulled.py` (item, shown_item, without_digests), `tests/cli/_output.py` (pull_report, pull_document, alice_document, MANAGER_ROW, without_hashes). Profile gained fields the whole documents need (badge_shown*, host_has_badge, host_author_warning, map_*).
    - **Set aside / kept picked, by design.** Comment content digest (`hash`, `short_hash`; prefix pair checked), tracker address, etag. Kept as picked: ids of `list` rows (membership claim), the `source` record of items 4 and 5 in the filter-lost case, the stamp line of the scaffolded `sources.toml`.
    - **Gates.** pyright, ruff check, ruff format clean. `tests/meta tests/cli tests/check tests/daemon tests/regressions tests/cross_process -n 4`: 2284 passed, 4 skipped. `--squad override tests/cli tests/check -n 4`: 1205 passed, 180 skipped, 0 failures. Source modules also pass in remote mode on both squads. Logs: `/home/pchat/.cache/sq-loop/r3-main2.log`, `r3-override.log`.
    - **Spot checks** (product string changed, case red, restored): relink "still holds", relink "was not created", map "not --set", pull "each is refreshed", comment "via", Jira "authenticated as", map option derivation, `restricted` count, "just now" age (28 reds). `sq check` clean.
    - @manager
- [2026-11-05T03:43:17Z] `architect` Robert Architect:
  - ADR-1172 rule 3 now records the `--<attribute:map>` derivation (ST6/F6) and the skipped-call teardown exception (ST2). @manager
- [2026-11-05T03:59:34Z] `python-dev` Elias Python:
  - Round 4 handback. ST8 and ST9 Done; REV-1299 F11, F12 Fixed. Nothing committed. Gates: pyright, ruff, format clean; main set 2287 passed, 4 skipped; --squad override tests/cli tests/check 1217 passed, 171 skipped, 0 failures. Mutations: source_declared and markers_balanced messages changed (2 reds), sq:attrs wording changed (1 red), helper reverted to overwrite (9 failed + 9 errors on override); all restored. @manager
- [2026-11-05T04:11:06Z] `python-dev` Elias Python:
  - - Round 5 handback. ST10 Done, REV-1299 F8 Fixed, TASK-1300 Done. Nothing committed.
    - Layout: each case sits in the module of the command it declares. source leaves: test_source_pull, test_source_check, test_source_list, test_source_credential; test_item_source for `<type> source unlink|relink`; the rest moved into test_show, test_operator, test_item_verbs, test_comment_verbs, test_inbox_mine, test_import, test_check, test_repair, test_role, test_override, test_workflow. The nine other test_source_* modules are gone; shared arrangements are in tests/cli/_source_*.py.
    - Counts: 1388 collected on bundled and on override, before and after, identical ids.
    - Gates: pyright, ruff check, ruff format clean; main set 2287 passed, 4 skipped; --squad override tests/cli tests/check 1217 passed, 171 skipped, 0 failures. Logs in /home/pchat/.cache/sq-loop/r5-*.log.
    - @reviewer: REV-1299 is ready for re-review.
<!-- sq:discussion:end -->

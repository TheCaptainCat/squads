---
id: REV-1198
sequence_id: 1198
type: review
title: 'Review FEAT-1173: CLI surface test suite'
status: Approved
parent: FEAT-1173
author: reviewer
refs:
- ADR-1172
description: Harness, guards and tests/cli against ADR-1172; seeded-defect and mutation
  spot checks.
subentities:
- local_id: F1
  title: Hand-written create guide is folded onto create <type>; its options can break
    with the suite green
  status: Verified
  severity: high
- local_id: F2
  title: Hidden commands are invisible to the coverage and parity guards
  status: Verified
  severity: medium
- local_id: F3
  title: A covers marker on a skipped or uncollected test satisfies the coverage guard
  status: Verified
  severity: medium
- local_id: F4
  title: reached_pairs counts absent arguments and options after --help as reached
  status: Verified
  severity: low
- local_id: F5
  title: Parity guard compares parameter names only; per-type attribute drift passes
  status: Verified
  severity: medium
- local_id: F6
  title: Shared roster verbs and comments listing are not folded; one registration
    tested per host
  status: Verified
  severity: medium
- local_id: F7
  title: 'repair test pins BUG-1191: a duplicate-number item vanishes with exit 0'
  status: Verified
  severity: medium
- local_id: F8
  title: 'memory search test pins BUG-1197: the doubled hit line'
  status: Verified
  severity: medium
- local_id: F9
  title: init and adopt expected panel paths use '/' where the product prints native
    paths
  status: Verified
  severity: medium
- local_id: F10
  title: 'Generated files read without encoding: breaks on Windows, negative asserts
    go vacuous'
  status: Verified
  severity: medium
- local_id: F11
  title: test_docs_ui imports the TUI app at module top; collection fails without
    the tui extra
  status: Verified
  severity: low
- local_id: F12
  title: Prefix-only output assertions remain against rule 5
  status: Verified
  severity: low
- local_id: F13
  title: Seven pairs are declared only by refusal cases; the bundled-spec limit is
    not recorded
  status: Noted
  severity: low
- local_id: F14
  title: 'File reads beyond rule 5''s init/sync exception: adopt, roster pointers,
    override files'
  status: Verified
  severity: low
- local_id: F15
  title: Dead owner() in tests/_cli_surface.py, with a process-word docstring
  status: Verified
  severity: info
- local_id: F16
  title: Multi-parameter covers markers used for non-interactions, against rule 3
  status: Verified
  severity: info
- local_id: F17
  title: Two handback observations were not filed as bugs
  status: Noted
  severity: info
- local_id: F18
  title: 'import refusal test pins a stray '': '' and pydantic''s wording as the message'
  status: Verified
  severity: low
- local_id: F19
  title: Roster fold leaves operator and skill addressing of the shared verbs untested
  status: Verified
  severity: low
created_at: '2026-10-27T23:47:47Z'
updated_at: '2026-10-28T00:33:22Z'
---
<!-- sq:body -->
## Scope

The CLI surface suite of FEAT-1173 against ADR-1172, as one batch over TASK-1174 to TASK-1182: `git diff 579f1554^..HEAD -- tests pyproject.toml` (harness `tests/_cli_surface.py`, the `invoke` cross-check in `tests/conftest.py`, `tests/cli/**`, and the coverage, cross-check and parity guards in `tests/meta`). Production code is unchanged.

## Method

- Harness attacked by seeding defects and reverting each one: a hidden command with an option, every test of one key skipped, parameter attributes changed on one type's verbs, and argument lists with missing arguments or `--help` passed to `reached_pairs`.
- `invoke` instrumented for one run of `tests/cli` to log each call's reached pairs and exit code, so declared pairs could be checked against successful calls, and `--as` attribution could be broken suite-wide.
- Dev mutation claims spot-checked by breaking `src`, running the named module, and restoring (`git diff src` empty after each).

## Re-verified mutation claims

All went red as claimed: reflog `--since` inclusive bound (test_reflog), label add/rm order with rm winning (test_item_verbs), `check` printing only the first issue (test_check), `create --desc` dropped on the built create (test_create). `--as` attribution dropped while validation stays: 37 tests red across item, sub-entity, role, skill, operator and dev modules, and every `--as` pair routed through `apply_edit_actor` had at least one red test.

## Verdict

Request changes. The suite is in good shape: no cross products, whole-line asserts almost everywhere, honest refusals, and fast (788 CLI tests in about 13 s with `-n 3`). But the fold onto `create <type>` hides a separate hand-written `create guide`, whose effects can break with the whole suite green. The coverage guard also cannot see hidden commands or tests that never run. Findings below.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1198 add-finding "…" --severity medium`; track with `sq review 1198 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Hand-written create guide is folded onto create <type>; its options can break with the suite green

<!-- sq:finding:F1:body -->
`sq create guide` is a separate hand-written command (`create_guide` in `src/squads/_cli/_create.py`), not the built create every other type uses. But `fold_path` folds it onto `create <type>`, so every `create <type>` pair counts as covered by a test on `task`, and only `--tag` and `--tech` are ever run on guide.

Seeded (then reverted): in `create_guide`, `description=""`, `parent=None`, `assignee=None`, and the `--json` branch disabled. `pytest tests/cli tests/meta -n 3` gives `1363 passed`. `--desc`, `--parent`, `--assignee` and `--json` on guide can all break with the suite green.

ADR rule 2 folds a registration that one builder mounts on several hosts. `create guide` is a second implementation, so the fold hides exactly the divergence the rule assumes cannot exist. The parity guard does not close the gap: for a command whose class differs, `create_problems` checks only that the `CREATE_CORE` names are present.

Fix: either give the hand-written create its own key (e.g. keep `create guide` unfolded, so its pairs are required in their own right), or have the harness fold only commands built by the builder (e.g. by command class, as `create_problems` already tells them apart).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-28T00:09:21Z, edited 2026-10-28T00:09:51Z] `python-dev` Elias Python:
  - create guide has its own key (create_guide is not folded onto create <type>, told apart by command class); 13 tests in test_create.py cover its pairs; the parity guard compares the hand-written create core by signature.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Hidden commands are invisible to the coverage and parity guards

<!-- sq:finding:F2:body -->
`_help_tree.command_nodes()` skips every hidden command except `_addr`, and both the coverage guard and the parity guard read the tree through it. ADR-1172 counts hidden parameters as pairs, and asks for every leaf to be declared. A hidden command and all its parameters are outside both guards.

Seeded (then reverted): `@app.command(name="wipe", hidden=True)` with a `--everything` option in `_cli/_main.py`. The coverage and parity guards give `29 passed`.

Existing case: `role|skill|operator <slug> rm` (hidden, with `--purge` and `--as`) is not declared and not tested. The hidden type aliases (`t`, `b`, `create t`, …) are harmless because they fold to the same keys. But that is also the reason to include hidden commands: an alias walk would fold for free, and a hidden non-alias command would then be required.

Fix: walk hidden commands in the surface (fold aliases as today), and name any deliberate exclusion in `EXCLUDED_PARAMS` with its reason.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-28T00:09:23Z] `python-dev` Elias Python:
  - The surface and parity guards walk hidden commands (command_nodes include_hidden); aliases fold and are held to the signatures of the command they name; role rm is tested for --purge and --as.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — A covers marker on a skipped or uncollected test satisfies the coverage guard

<!-- sq:finding:F3:body -->
The coverage guard reads markers with `ast` from anywhere in a `tests/cli/test_*.py` file. The `invoke` cross-check runs only when the test runs. So a marker on a test that is skipped, xfailed, deselected by default (the `slow` marker is skipped without `--run-slow`), or on a function pytest does not collect (a helper not named `test_*`), counts as coverage, and nothing ever checks it.

Seeded (then reverted): `@pytest.mark.skip` added under each of the three `@pytest.mark.covers("sync")` markers in `test_sync.py`. `pytest tests/cli/test_sync.py tests/meta/test_every_cli_parameter_is_declared_by_a_covering_test.py` gives `19 passed, 3 skipped`, so the guard is green and `sq sync` is not tested.

Fix: in the guard, accept a marker only on a `test_*` function (or a module-level `pytestmark`) with no skip, skipif, xfail or slow marker. Or refuse `covers` together with those markers at collection, in the conftest hook.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-28T00:09:25Z] `python-dev` Elias Python:
  - A covers marker counts only on a collected test with no skip, skipif, xfail or slow mark; any other marker is reported by the guard.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — reached_pairs counts absent arguments and options after --help as reached

<!-- sq:finding:F4:body -->
`reached_pairs` records `(key, param)` when `p.name in given`. Click's parser always puts every declared argument in `given`, with `None` when the argument is absent. So an argument is reached whether or not the call supplied it. Probed: `["search"]` reaches `("search", "TEXT")`, `["create", "task"]` reaches `("create <type>", "TITLE")`, `["task"]` reaches `("<type>", "N")`, and `["role", "comment"]` reaches `("role", "<slug|id|n>")` with `comment` taken as the slug.

Likewise `--help` stops the command before it runs, but the options after it still count: `["task", "3", "update", "--help", "--title", "x"]` reaches `("<type> update", "--title")`.

No current test relies on either. Tightened (then reverted) so that an argument counts only when its value is not `None`/`()`, `pytest tests/cli -n 3` gives `788 passed`. So the fix costs nothing. `test_a_covers_marker_is_checked_against_the_pairs_a_call_reaches.py` has no case with a missing argument, which is why it did not show.

Fix: count an argument only when it has a value, end the walk at an eager `--help`, and add both shapes to the cross-check's meta cases.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-28T00:09:27Z] `python-dev` Elias Python:
  - reached_pairs counts an argument only with a value and ends at an eager --help; new cross-check cases hold both shapes.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Parity guard compares parameter names only; per-type attribute drift passes

<!-- sq:finding:F5:body -->
`Tree.of` reduces each command to `frozenset(param_name(p) …)`, so `differences` compares names only. Seeded on the live tree (scratch script, no repo edit): on `bug show`, `--json` made required, non-flag, multiple and hidden; on `bug status`, `--force` defaulted to `True`. `item_verb_problems` returns `[]`.

The fold sends every non-reference type's verbs to the reference type's single test. So a per-type difference in required, flag-ness, multiplicity, hidden or default is covered by nothing. ADR-1172 only promises equal names, so this is a gap in the ADR's design as much as in the guard. A builder conditional on the type, which the parity guard exists to catch, would show up as a changed attribute just as often as a missing name.

Fix: compare a parameter signature (kind, `required`, `is_flag`, `multiple`, `nargs`, `hidden`, default) rather than the name. Exclude only what the spec legitimately varies, such as the choices of a field option.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-28T00:09:29Z] `python-dev` Elias Python:
  - The parity guard compares kind, required, is_flag, multiple, nargs, hidden and default per parameter; spec-declared options match any signature.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Shared roster verbs and comments listing are not folded; one registration tested per host

<!-- sq:finding:F6:body -->
`register_status_verb`, `register_body_verb`, `register_remove_verb` and the `comments` listing of `register_comment_verbs` are mounted on `role`, `skill` and `operator` (`comments` on every item type too). `fold_path` folds none of them, because `comments` is not `comment` and roster hosts keep their literal names. The coverage guard therefore forces one copy of each case per host.

Counted: `role|skill|operator body` (`--message`, `--file`, `--append`, `--force`, `--as`), `status` (`STATUS`, `--force`, `--unlink`, `--as`) and `remove` (`--purge`, `--as`). That is about 30 near-identical tests, three times over. `comments --json` is asserted in test_item_verbs, test_role, test_skill and test_operator. ADR-1172 rule 2 says a verb set one registrar mounts on several hosts is tested on one host, with the rest held by a guard. The parity guard holds the comment group, but not these roster verbs.

Fix: fold the shared roster verbs onto one key (e.g. `<roster> status`, `<host> comments`), keep one host's tests, and extend the parity guard over the roster hosts. Where one host differs (`refresh_managed=True` on role and operator `remove`), test that difference by name.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-28T00:09:32Z] `python-dev` Elias Python:
  - role is the reference roster host (its remove also re-renders the managed roster section); body, remove, rm, status fold onto it and comments onto <host> comments; duplicate tests deleted on skill and operator; parity guard extended over the roster hosts.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — repair test pins BUG-1191: a duplicate-number item vanishes with exit 0

<!-- sq:finding:F7:body -->
`test_repair_without_renumber_reports_a_shared_number_through_check` (test_repair.py) asserts `(0, "rebuilt index: 4 items, counter=4\n")` while five item files exist. That is the silent drop BUG-1191 records: an item vanishes from the index, exit 0, and no warning. A fix that warns or exits non-zero turns this test red, so the test defends the bug. ADR-1172 and the task ground rules say not to pin buggy behaviour.

The `sq check` half of the test is sound and should stay. For the repair line, assert only what is correct today (the `numbers_unique` report through `check`), or mark the repair-output assertion with `xfail(strict=True)` referencing the behaviour, until BUG-1191 is fixed.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-28T00:17:56Z] `python-dev` Elias Python:
  - The repair-output assertion is dropped; the test (renamed for the check report) keeps the numbers_unique half.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — memory search test pins BUG-1197: the doubled hit line

<!-- sq:finding:F8:body -->
`test_search_prints_each_matching_memory_with_the_lines_that_matched` (test_memory.py) expects `"tooling  Prefer uv over pip\n    Prefer uv over pip\n    Prefer uv over pip\n"`: the hit line printed twice when the body equals the summary. That is exactly BUG-1197's reproduction (filed from this work). The test locks the bug in, against the ADR's rule not to pin buggy behaviour.

Fix: give the memory a distinct body, as `test_search_reads_the_body_as_well_as_the_summary` already does, so the case asserts the intended single hit. Leave the equal-body shape to the regression test that comes with BUG-1197's fix.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-28T00:17:58Z] `python-dev` Elias Python:
  - The memory has a body distinct from its summary; the case asserts the single hit.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — init and adopt expected panel paths use '/' where the product prints native paths

<!-- sq:finding:F9:body -->
`_created` in test_init.py builds `f"{root}/{folder}"` and `f"…index:{squad}/.squads.json"`, and test_adopt.py:46 builds `f"…squad:{root}/{folder}…"`. The product prints `sp.squad_dir` / `sp.index_path`, which are `Path` objects (`_cli/_main.py` around lines 398 and 452). On Windows these print with backslashes, so every `init` and `adopt` panel assertion fails there. The panel is flattened by `flat()`, which strips whitespace but not separators.

Not run on Windows here; inferred from the code. The product messages elsewhere use `as_posix()` (e.g. the numbers_unique report), so the expected strings in these two helpers are the outlier.

Fix: build the expected path with `str(root / folder)` and `str(root / folder / ".squads.json")`.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-28T00:18:00Z] `python-dev` Elias Python:
  - Expected init and adopt panel paths are built from Path objects (str(root / folder), str(root / folder / ".squads.json")).
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Generated files read without encoding: breaks on Windows, negative asserts go vacuous

<!-- sq:finding:F10:body -->
Several helpers read generated UTF-8 files with `read_text()` and no encoding: `_claude_md` (test_role.py:53), `_roster_lines` (test_operator.py:29), the pointer reads in test_dev.py:35/97, test_skill.py:582/629/667, and test_role.py:144/202/307/864/882/929/1032. CI does not set `PYTHONUTF8` (checked `.github/workflows`, the root `conftest.py` and `pyproject.toml`). Python 3.14 on Windows still decodes with the locale code page, so the em dash in the managed CLAUDE.md lines (`— architect`) decodes as mojibake.

Effect on Windows: the positive asserts fail, and the negative ones go vacuous, e.g. `assert "- **Robert Architect** — architect (`architect`)" not in _claude_md(project)` (test_role.py:645) passes whatever the file holds. Inferred, not run on Windows.

Fix: pass `encoding="utf-8"` everywhere, as the squad-wide helpers already do. Optionally turn on `-W error::EncodingWarning` in the test run, so this cannot come back.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-28T00:18:02Z] `python-dev` Elias Python:
  - Every read_text, write_text and open in tests/cli passes encoding="utf-8"; tests/cli also passes under PYTHONWARNDEFAULTENCODING=1 with -W error::EncodingWarning.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — test_docs_ui imports the TUI app at module top; collection fails without the tui extra

<!-- sq:finding:F11:body -->
test_docs_ui.py imports `from squads._tui._app import SquadsApp` at module top, and `_tui/_app.py` imports `textual` at module top. Without the optional `tui` extra (a bare `uv run pytest`, or an adopter's plain install), collecting the module fails. That takes the four `docs` tests down with the two `ui` tests.

Fix: import inside the two `ui` tests, after `pytest.importorskip("textual")`, or monkeypatch by dotted string (`"squads._tui._app.SquadsApp.run"`) so the module never imports it at collection.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-28T00:18:04Z] `python-dev` Elias Python:
  - test_docs_ui imports the app through a fixture that skips without textual; the module collects with textual blocked (5 passed, 2 skipped).
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Prefix-only output assertions remain against rule 5

<!-- sq:finding:F12:body -->
ADR-1172 rule 5 asks for the whole message line, not a substring that would survive a wrong message. Prefix-only assertions remain:
- test_skill.py:381 and :899: `result.output.startswith("error: SKILL-2's body renders through its declared")`. The rest of the refusal (the remedy text) is unasserted, though test_role.py asserts the same refusal whole as `VIEW_REFUSAL`.
- test_import.py:161: `splitlines()[0].startswith("line 2: ")`. The refusal reason for line 2 is unasserted.
- test_init.py:241 and :255: `result.output.startswith(…)`. Whatever follows the prompts (the init panel) is unasserted.

Fix: assert the whole output, reusing the module constants that exist, or `flat()` for the init panel.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-28T00:15:04Z] `python-dev` Elias Python:
  - Whole-output asserts replace the prefixes in test_skill (shared refusal constant), test_import, test_init (prompts exact, panel through flat()) and test_comment_verbs.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Seven pairs are declared only by refusal cases; the bundled-spec limit is not recorded

<!-- sq:finding:F13:body -->
Seven pairs are declared only by tests in which no call naming them succeeds (from an instrumented run of tests/cli): `role|skill|operator status --force` (each "does not lift a status the lifecycle lacks"), `role view add --as`, and `role view disable NAME` and `--as`. The removed `--dir` and `scaffold --new` are refusal-only by design.

The handback explains why: under the bundled spec, the roster lifecycle gives `--force` nothing to lift, and the declared role_definition view refuses every view edit. So the effect is unreachable with the bundled vocabulary. That is a legitimate limit, but nothing records it. Only the comment in TASK-1179 says so, and the guard reads these pairs as covered with an effect case.

Fix: state the limit where a reader finds it, in a one-line docstring on each test ("no effect is reachable under the bundled spec; the refusal is the case"). Or add these pairs to a named constant beside `EXCLUDED_PARAMS`, listing pairs whose effect the bundled spec cannot reach, each with its reason, so the later override-backed run knows to cover them.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-28T00:15:08Z] `python-dev` Elias Python:
  - One-line docstrings on the refusal-only cases (role status --force, role view add --as, role view disable NAME and --as, root --dir, override scaffold --new); the skill and operator status --force cases are gone with the roster fold.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — File reads beyond rule 5's init/sync exception: adopt, roster pointers, override files

<!-- sq:finding:F14:body -->
Rule 5 says the generated agent-facing files of `init` and `sync` are the only files a CLI test reads. The suite also reads:
- the `adopt` pointers and regions (test_adopt.py);
- the `role`, `dev` and `skill` pointers after update/regen/link (test_role.py, test_dev.py, test_skill.py);
- the override files `scaffold` and `update` write (test_override.py).

As setup, it also edits item files and `.squads.json` (test_repair.py, test_check.py, test_sync.py, and test_migrate.py's config). The setup edits are unavoidable for repair/check, and the reads cover outputs the user does receive and that have no CLI view.

Fix: amend ADR-1172 rule 5 (architect) to name the generated files of any command that writes them, the override files, and corruption setup for repair/check/migrate. Or, where a CLI view exists (e.g. `override diff --json` for a scaffolded override), read through it.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-27T23:51:07Z] `architect` Robert Architect:
  - Fixed by the ADR-1172 rule 5 amendment.
- [2026-10-27T23:51:43Z] `architect` Robert Architect:
  - ADR-1172 rule 5 also allows direct item/index writes only to arrange states no CLI path can produce (repair, check, migrate, adopt, renumber); assertions stay on the CLI.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Dead owner() in tests/_cli_surface.py, with a process-word docstring

<!-- sq:finding:F15:body -->
`owner(key)` in `tests/_cli_surface.py` is referenced nowhere in the tree (grep across tests/ and src/), now that the per-task pending list is gone. Its docstring ("The group of keys a surface task owns") also names the build process, which the test-prose rules forbid.

Fix: delete it. `KIND_SEGMENTS` stays, because the parity guard uses it.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-28T00:09:34Z] `python-dev` Elias Python:
  - owner() deleted.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — Multi-parameter covers markers used for non-interactions, against rule 3

<!-- sq:finding:F16:body -->
ADR-1172 rule 3: "One marker, several parameters, is only for an interaction (rule 1)." 171 markers carry two or more parameters, and many are not interactions. Examples: `covers("board post", "--message", "--as")` sits on every `post` test, including `test_post_until_hides_the_notice_after_that_date`; `covers("role update", "--title", "--as")` sits on the unknown-slug refusal.

The coverage guard does not care. But the convention exists so that a reader can tell an interaction test from the marker. As written, a multi-parameter marker no longer signals one.

Fix: use one marker per asserted parameter (`@covers(k, "--as")` alone on an `--as` case). Keep multi-parameter markers for the named interaction tests (parent/no-parent, add-label/rm-label, onto/by, …).
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-10-28T00:15:06Z] `python-dev` Elias Python:
  - One covers marker per asserted parameter; 22 multi-parameter markers remain, each on a test named for an interaction (message/file, parent/no-parent, add-label/rm-label, set/unset, onto/by, in/out, ...).
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Two handback observations were not filed as bugs

<!-- sq:finding:F17:body -->
Two observations from the TASK-1180 handback were not filed, while the others became BUG-1183 to BUG-1197:
- `migrate up`: the in-command "newer than this squads … upgrade the squads package" branch is unreachable, because the root schema gate refuses first. The dev reports that mutating it leaves every test green, so it is dead code.
- `migrate rename-status task Nope Draft` (an OLD status outside the lifecycle) exits 0 with "0 item(s) renamed", while an unknown NEW status is refused.

Fix: QA files both (or the tech lead routes the dead branch as a cleanup), so they do not live only in a task comment.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — import refusal test pins a stray ': ' and pydantic's wording as the message

<!-- sq:finding:F18:body -->
`test_a_refused_line_leaves_the_valid_events_before_it_unapplied` (test_import.py) now asserts this line verbatim: `line 2: : Input tag 'nope' found using 'op' does not match any of the expected tags: 'create', …`.

The doubled `: ` is a product defect. `_services/_import_model.py` (around line 365) formats a validation error as `f"{loc}: {first['msg']}"`, and for a discriminator-tag error pydantic's `loc` is empty, so the message starts with `: `. Everything after the second colon is pydantic's own wording. The test pins both the stray separator and a third-party library's phrasing as the contract, so a fix to either one turns it red. That is the "do not pin buggy behaviour" rule again.

Fix: QA files the product bug: drop the separator when `loc` is empty, and preferably name the unknown `op` in squads' own words, listing the valid ops. Until it is fixed, assert the stable parts as whole lines (line 3, the summary line, nothing applied), and either leave line 2 out or mark its assertion `xfail(strict=True)` pointing at the behaviour.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-10-28T00:28:24Z] `qa` Mara Tester:
  - Product bug filed: BUG-1200.
- [2026-10-28T00:30:04Z] `python-dev` Elias Python:
  - The import refusal test no longer asserts line 2; it asserts the other lines, the exit code and that nothing was applied.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — Roster fold leaves operator and skill addressing of the shared verbs untested

<!-- sq:finding:F19:body -->
With `body`, `remove`, `rm` and `status` folded onto `role`, the roster parity guard checks that skill and operator have the same parameters. But each host passes its own address callback to the shared registrar (`register_body_verb(_addr, lambda ctx: ctx.obj["id"])` in `_cli/_operator.py`, likewise in `_skill.py`), and no test exercises the callback on a non-reference host.

Seeded (then reverted): operator's `register_body_verb` callback returning `"ROLE-1"`, so `sq operator <slug> body` writes the manager role's body. `pytest tests/cli tests/meta -n 3` gives `1382 passed`. The same seed on skill's body, operator's remove, or operator's status went red only through unrelated setup or listing tests, not through a case aimed at the address.

The comment verbs already handle this (the verbs are tested on one host, and addressing once on each of the others). Fix: one addressing case per non-reference roster host for the shared verbs, e.g. `operator <slug> body -m …` read back through `operator <slug> show --json`, and the same for skill. The cases need no `covers` marker beyond what the fold already declares.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
- [2026-10-28T00:30:06Z] `python-dev` Elias Python:
  - One addressing case each on operator and skill (body, status, remove); the seed redirecting each shared verb callback to ROLE-1 turns them red (6 of 6).
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T23:48:36Z] `reviewer` Paul Reviewer:
  - Batch review of FEAT-1173 filed: 17 findings (1 high, 8 medium, 5 low, 3 info), verdict request changes. The high one: the hand-written create guide is folded onto create <type>, so its --desc, --parent, --assignee and --json can break with all 1363 tests green.
  - Re-verified dev mutation claims, all red as claimed: reflog --since bound, label add/rm order, check first-issue-only, create --desc, and --as attribution suite-wide (37 red). Review left in its initial status for the approver.
  - @tech-lead to route fixes: F1-F6, F9-F16 are test and harness changes for python-dev, F14 also needs an ADR-1172 amendment from the architect, and F17 goes to QA.
- [2026-10-27T23:49:32Z, edited 2026-10-27T23:49:50Z] `manager` Catherine Manager:
  - Triage under the operator delegation to drive FEAT-1173 (op-pierre, 2026-10-27):
  - Fix: F1 (create guide gets its own key and tests), F2 (guards see hidden commands; test roster rm), F3 (markers count only on runnable tests), F4 (arguments reached only when supplied, nothing after --help), F5 (parity compares parameter attributes, not names only), F6 (roster shared verbs fold onto one key, duplicate tests removed, parity extended to roster hosts), F7 and F8 (drop the assertions that pin BUG-1191 and BUG-1197), F9, F10, F11, F12, F15, F16 (one covers marker per parameter outside interactions).
  - F13: keep refusal-only cases; each test docstring states the bundled spec cannot reach the effect. No guard change. Mark Noted.
  - F14: ADR-1172 rule 5 is widened to the files a command under test produces as its output (generated agent files, override files); architect to amend. Mark Fixed when the amendment lands.
  - F17: rename-status on an old status outside the lifecycle is by design (QA, during the bug filing). The unreachable migrate up branch is production dead code, outside this feature (no production changes); this finding is its record. Mark Noted.
  - @tech-lead: one fix task under FEAT-1173 with subtasks per finding group.
- [2026-10-28T00:27:00Z] `reviewer` Paul Reviewer:
  - Verified commit 177f5509: I re-applied each original seed and broke src for the new tests, saw red, and reverted. Guide create breakage: 4 red in test_create. Hidden wipe command: guard red. Skip on the sync tests: guard red. Absent arguments and --help: no longer reached. Attribute drift on bug show/status and on skill/operator status/body: parity red. Shared roster status ignoring --unlink: role and skill tests red. textual blocked: docs_ui collects, ui tests skip. F1-F12, F14-F16 moved to Verified; F13 and F17 stay Noted.
  - New: F18 (import test pins a stray colon and pydantic wording) and F19 (operator/skill addressing of the folded roster verbs untested). Both low. The review stays ChangesRequested until they are treated. One gap I left unfiled: a skip applied through an alias (from pytest import mark; @mark.skip) is not seen by the not-run filter.
  - @tech-lead F18 and F19 go back to python-dev (F18 also needs a QA bug for the import message).
- [2026-10-28T00:32:43Z] `reviewer` Paul Reviewer:
  - Verified commit 928e73ef. F18: the import test no longer asserts line 2, only lines 3 and 4 and that nothing was applied; the message defect is tracked as BUG-1200. F19: pointed each address callback at ROLE-1 in turn (operator and skill; body, status and remove). All six seeds turned the new addressing tests red, and each was reverted. Both moved to Verified.
- [2026-10-28T00:33:22Z] `manager` Catherine Manager:
  - Approved: all 19 findings Verified or Noted (F13, F17), verified by the reviewer on the original seeds; the reviewer does not approve a review they authored.
<!-- sq:discussion:end -->

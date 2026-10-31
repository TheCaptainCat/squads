---
id: TASK-1177
sequence_id: 1177
type: task
title: 'CLI tests: sub-entity and comment verbs'
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
refs:
- TASK-1174:depends-on
subentities:
- local_id: ST1
  title: Sub-entity verbs on task subtask
  status: Done
  assignee: python-dev
  maps_to: US4
- local_id: ST2
  title: Finding-only options on review
  status: Done
  assignee: python-dev
  maps_to: US4
- local_id: ST3
  title: Comment verbs and host addressing
  status: Done
  assignee: python-dev
  maps_to: US4
created_at: '2026-10-27T21:35:10Z'
updated_at: '2026-10-28T01:02:41Z'
---
<!-- sq:body -->
## Scope

FEAT-1173 US4, two modules (ADR-1172 rules 2-3, 6):

- `tests/cli/test_subentity_verbs.py`, on `task subtask`: `add-<kind>`, `<kinds>`, the `<kind>` group's `LOCAL-ID`, and its `show`, `update`, `body`, `remove`, every option of each. `--story`/`--no-story` resolved against the parent feature's stories (a rule 1 "reads the other's value" case). `--severity` and `--deferred-to` on `review finding` and `review add-finding`, the only host that carries them.
- `tests/cli/test_comment_verbs.py`, on the `task` host: the `<host> comment` group (`-m`, `--file`, `--as`, the `HASH` argument) and its `show`, `edit`, `remove`, every option of each. Plus one addressing case each for the sub-entity, role, skill and operator hosts; those cases cover the address only, not the verb parameters again.

## Acceptance

- Every sub-entity pair is declared under the `<kind>` keys and every comment pair under the `<host>` keys.
- `-m` with `--file` has its own named exclusion test on each verb that takes both.
- `comment edit` and `comment remove` are refused for a comment authored by someone else, whole error line asserted.

## Ground rules (every CLI surface task)

- Rulebook: ADR-1172. Read it before starting; the rules are cited here, not restated.
- In-process only: Typer `CliRunner` through the `runner`/`invoke` fixtures, on a squad copied per test (`copy_squad` and the builders in `tests/_squads.py`), under the frozen clock. No subprocess (ADR-1172 rule 4).
- One case per (command, parameter) pair where the value takes effect, plus its boundary refusals; combinations only for a genuine interaction, named for the interaction (rule 1). No cross-product or per-type parametrised tables (rules 1-2).
- Assert the exit code and the whole message line or JSON object, never a substring. Read state back through the CLI (`sq <type> <n> show --json` or the command's `--json` form); never open an item file or `.squads.json` (rule 5).
- Declare coverage with `@pytest.mark.covers("<key>", "<param>", ...)`, literal strings, keyed as ADR-1172 rule 3 says; an option is named by its first long flag, so `-m` is declared as `--message`. Hidden parameters are pairs too, each with a refusal test; `--as` is covered on every write command and `--json` on every command that declares it (op-pierre ruling on ADR-1172).
- Mutation-check each test when written: break the parameter's effect, see the test red, restore it. Record in the handback which effect you broke for each test.
- Names state the behaviour; no ticket IDs or process vocabulary in module, function or fixture names (the naming guards in `tests/meta` apply). Docstrings 1-2 sentences, present tense, no versions or history.

## Gate

`uv run --all-extras pyright`, `uv run --all-extras ruff check .` and `uv run --all-extras ruff format --check .` clean; `uv run --all-extras pytest tests/meta tests/cli -n 4` green; `~/.local/bin/sq check` clean for this task. The full suite is run by the main loop.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1177 add-subtask "<title>"`; track with `sq task 1177 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Sub-entity verbs on task subtask

<!-- sq:subtask:ST1:body -->
add-subtask, subtasks, subtask LOCAL-ID and its show/update/body/remove with every option; --story and --no-story resolved against the parent feature stories, with the refusal for an unknown story.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Finding-only options on review

<!-- sq:subtask:ST2:body -->
The --severity and --deferred-to options of review add-finding and review finding update, each with its out-of-set refusal.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Comment verbs and host addressing

<!-- sq:subtask:ST3:body -->
The comment group on the task host (-m, --file, --as, HASH) and its show/edit/remove with every option; edit and remove refused for another author; one addressing case each for the sub-entity, role, skill and operator hosts.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T22:31:26Z] `python-dev` Elias Python:
  - @manager Handback: all three subtasks Done; gate green. `uv run --all-extras pytest tests/meta tests/cli -n 3`: `822 passed in 26.19s`; pyright 0 errors; ruff check and format clean; sq check clean. No production code changed (`git diff src/` empty); nothing committed.
    
    Files
    - tests/cli/test_subentity_verbs.py (72 tests): `<kind>` group LOCAL-ID, `<kinds>` --json, show --json, add-<kind> (TITLE, --message, --file, --status, --assignee, --story, --json, --as, --severity, --deferred-to), update (--title, --status, --force, --assignee, --clear-assignee, --story, --no-story, --as, --severity, --deferred-to), body (--message, --file, --append, --force, --as), remove (--yes, --json, --as). Host is `task subtask`; --severity/--deferred-to on `review add-finding` / `review finding update`.
    - tests/cli/test_comment_verbs.py (43 tests): `<host> comment` (--message, --file, --as, HASH), show (--json, --raw), edit (--message, --file, --as, --json), remove (--yes, --json, --as) on `task`; one addressing case each for subtask, role, skill, operator.
    - tests/meta/test_every_cli_parameter_is_declared_by_a_covering_test.py: removed `"<kind>"` and `"<host>"` from PENDING (guard passes; 31 owners remain).
    - Interaction tests named for the interaction: assignee/clear-assignee, story/no-story, message/file (add, body, comment, edit), story resolved against the parent feature of the task it is added to (second feature with one story). Edit/remove refused for another author, whole line asserted. --raw is observed by forcing Rich's is_terminal in the test (monkeypatch on Console), since plain output is identical otherwise.
    
    Mutation proofs (each broke src, saw the named tests red, restored; driver kept in scratchpad, src diff empty after)
    - Sub-entity: local_id_for digit mapping dropped (group LOCAL-ID); _find message (unknown local id, remove-then-show); list_sub/show/add `json_out` forced off (listing json, show json, add --json); Table pad_edge (table); print_subentity label (show text); add title "" (TITLE); add body=None (add --message/--file/stdin); resolve_body_optional exclusion off (add + body -m/--file); _read_source_file message (missing file, add+body); add initial_status ignoring --status; parse_status message (add+update unknown status); add assignee=None; resolve_slug_or_raise message (every ghost refusal incl. --as); add story=None; story-not-found and no-feature-parent messages (add + update, incl. the second-feature case); apply_edit_actor removed from add/update/body/remove (each --as test); field default dropped (--severity, default medium); parse_badge_code message; _resolve_deferred_to returning None (add/update --deferred-to + carrier refusals); carrier/invalid-id/no-item messages; update title/status/assignee/story/severity assignment removed (each effect test); force=False; transition message; clear_assignee/clear_story branches off; "no assignee to clear" message; assignee/clear and story/no-story exclusion raises removed; nothing-to-update message; body: message/file dropped, append=False, force=True, no-text and overwrite messages; remove: `if not yes` forced, abort=False, json key renamed, remove_block skipped.
    - Comment: messages[:1]; file content replaced; read-file message; exclusion off; no-text message; empty-file raise removed; author fixed to manager (--as); require_as message; ghost message; reserved-slug message; hash min length 40; not-a-hash, missing-verb, no-comment, after-the-verb messages; show json off, where line removed, --raw ignored; edit text replaced, `changed` forced, author guard off (both refusals) and always-on (both own-comment tests); edit/remove json off; remove `if not yes` forced, abort=False, removed list emptied, remove_comment skipped; sub=None (subtask addressing); id_from_ctx replaced by a fixed id (role, skill, operator addressing).
    
    Product bugs found (not fixed)
    1. `sq task 3 add-subtask` with no TITLE exits 0 and adds ST3 with an empty title (`subtask 3 show --json` has `"title": ""`). Expected a refusal like a missing required argument. The TITLE pair is covered by the effect case only.
    2. `sq task 3 subtask 9 comment -m x --as manager` (ST9 does not exist) fails with `error: no discussion section 'subtask:ST9:discussion' in TASK-3 (was it scaffolded?)`. Expected `error: no subtask ST9 in TASK-3` as `subtask 9 show` gives.
<!-- sq:discussion:end -->

---
id: REV-1211
sequence_id: 1211
type: review
title: Check rule test harness and first rule modules
status: Approved
parent: FEAT-1202
author: reviewer
refs:
- TASK-1203
- TASK-1204
- TASK-1205
- ADR-1201
description: Review of the check rule harness, breaches guard and the parent, ref,
  sub-entity and prose rule modules
subentities:
- local_id: F1
  title: rule:param is honoured by selection alone, with no report and even after
    the selection was overwritten
  status: Verified
  severity: high
- local_id: F2
  title: 'select_validators cannot select a member the bundled list already names:
    duplicate entry, spec fails to load'
  status: Verified
  severity: high
- local_id: F3
  title: select_validators overwrites on each call, clobbers overrides, and cannot
    carry ref_rules or other keys
  status: Verified
  severity: medium
- local_id: F4
  title: Marker reader counts tests skipped at class level and shadowed redefinitions;
    residual blind spots undeclared
  status: Verified
  severity: medium
- local_id: F5
  title: Guard and teardown do not enforce ADR-1201 §2 shapes for required-param and
    multi-selection members
  status: Verified
  severity: medium
- local_id: F6
  title: ref_rule_target_present requires a param at load but is missing from REQUIRED_PARAM_VALIDATOR_NAMES
  status: Verified
  severity: low
- local_id: F7
  title: Teardown accepts a rule reported in the pre-state run; the clean pre-state
    rests on each test body
  status: Verified
  severity: low
- local_id: F8
  title: File write plus repair used for breaches the CLI can arrange (ref rm, update
    --title/--desc, body)
  status: Verified
  severity: medium
- local_id: F9
  title: Two diverging helper patterns, hard-coded ids and paths tied to the minimal
    squad counter
  status: Verified
  severity: medium
- local_id: F10
  title: covers_arguments duplicates _marker_ast.string_arguments verbatim after the
    extraction
  status: Verified
  severity: low
- local_id: F11
  title: Missing-param refusal for ref_rule_target_present splits across two sites
    via a literal-name early return
  status: Verified
  severity: low
created_at: '2026-10-28T09:04:13Z'
updated_at: '2026-10-28T10:19:16Z'
---
<!-- sq:body -->
## Scope

The check rule test foundation against ADR-1201:
- the harness: `tests/check/conftest.py`, `tests/check/_arrange.py`, `tests/check/test_baseline.py`;
- the guard: `tests/_check_surface.py`, `tests/_marker_ast.py`, `tests/meta/test_every_check_rule_is_declared_by_a_breach_test.py`, and the covers guard refactor (`tests/_cli_surface.py`, `tests/meta/test_every_cli_parameter_is_declared_by_a_covering_test.py`);
- the first rule modules: `test_parent_rules.py`, `test_ref_rules.py` (TASK-1204), `test_subentity_rules.py`, `test_prose_rules.py` (TASK-1205).

## Method

- `uv run --all-extras pytest -n 3 tests/check tests/meta` on the main tree at 1b563dc9: 694 passed.
- Guard discovery probed through `read_declarations` with suppression shapes.
- Teardown, `select_validators` and the CLI routes for each file-written breach driven in a throwaway worktree with probe tests. The worktree was removed afterwards.

## Verdict basis

The derivation matches ADR-1201 §2 on the tables as written: 69 breach declarations, 7 param cases and 34 level cases, with floors and selectable squad-wide members handled correctly. Every derived name exists in the tree. The holes are in what the per-test check accepts and in what `select_validators` can express, and two of them block upcoming rule modules: `type_has_live_author@error` cannot be selected at all. Fix F1, F2, F3 and F9 before the next rule module is built, since every later module copies the helper API.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1211 add-finding "…" --severity medium`; track with `sq review 1211 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — rule:param is honoured by selection alone, with no report and even after the selection was overwritten

<!-- sq:finding:F1:body -->
**Where.** `tests/check/conftest.py`, `_unhonoured`: a `rule:param` declaration is honoured when `observed.selected` holds an entry for the member with a param. Nothing ties it to a report.

**Failure scenario (driven).** A probe test declared `item_title_max:param`, called `select_validators("item_title_max:5", on="task")` and then `select_validators("body_written", on="task")`, which overwrites the override file and drops the first selection. It created a task with a 19-character title and asserted that no `item_title_max` issue appeared. The test passed: the teardown accepted a param case where the member was not in effect and never reported. A param case whose param value does not change the verdict, which ADR-1201 §2 and §6 exist to prevent, is invisible to the per-test check. Only the manual falsification step catches it, and that step is not repeatable.

**Suggested fix.** Honour `rule:param` only when (a) the member was selected with a param that is still in the override when the run happens, and (b) the rule was reported by a run made after that selection. Record selections with a run counter, or snapshot the effective selection when each run happens. ADR-1201 §4 spells the weaker condition, so this needs a one-line amendment by the architect alongside the harness change.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-28T09:21:37Z] `python-dev` Elias Python:
  - Teardown records each run with the params in the override on disk; rule:param needs a honouring run with the param selected.
- [2026-10-28T09:29:52Z] `reviewer` Paul Reviewer:
  - Verified on 0a60a22e. A rule:param run now needs the param in the on-disk override at run time (read back per run), plus a report after a pre-state run that did not report the rule. Matches amended ADR-1201 §4.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — select_validators cannot select a member the bundled list already names: duplicate entry, spec fails to load

<!-- sq:finding:F2:body -->
**Where.** `tests/check/conftest.py`, `select_validators`: it always splats the bundled list (`"$(*items.<type>.validators)"` / `"$(*squad.validators)"`) and appends the entries.

**Failure scenario (driven).** When the member is already in the bundled list, the override names it twice, the spec refuses to load, and `sq check` reports `workflow_loads` instead of the rule. Both shapes were reproduced:
- `select_validators("subentities_settled_with_parent@error", on="review")` gives exit 3 and "validator 'subentities_settled_with_parent' is selected more than once".
- `select_validators("type_has_live_author@error")` gives exit 3 and "squad validators entry 'type_has_live_author@error' repeats type_has_live_author".

This has already pushed two level cases off the type that ships the member: `no_parent@warn` was tested on decision instead of epic, and `subentities_settled_with_parent@error` on task instead of review. The squad-wide case has no workaround: `type_has_live_author@error` (work policy rules) can only be selected in `[squad]`, and it is bundled there. `item_skill_shadowed@error` on skill is the same shape.

On the question raised with TASK-1205: yes, the helper should handle it. Raising a bundled member's level on the type that ships it is exactly what an adopter does, and an adopter does it by writing the list without the splat and with the entry replaced. The test on task proves level resolution for an added member only.

**Suggested fix.** When an entry's selection key (`validator_selection_key`) matches a bundled entry, write the bundled list out explicitly with that entry substituted, and no splat. Otherwise keep the splat. Move the epic and review level cases back onto their shipping types.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-28T09:21:40Z] `python-dev` Elias Python:
  - select_validators writes the bundled list out with a replaced entry, no splat; level cases back on epic and review, type_has_live_author@error selectable.
- [2026-10-28T09:29:54Z] `reviewer` Paul Reviewer:
  - Verified. A bundled key is substituted in the written-out list with no splat. no_parent@warn is back on epic and subentities_settled_with_parent@error on review. Residual edge, not reopened: when the squad already ships an override whose list holds a splat, an entry matching a bundled member is appended, which is again a duplicate. Today no test starts from such an override.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — select_validators overwrites on each call, clobbers overrides, and cannot carry ref_rules or other keys

<!-- sq:finding:F3:body -->
**Where.** `tests/check/conftest.py`, `select_validators`, and `tests/check/test_ref_rules.py::test_each_selected_target_type_is_resolved_and_the_selections_are_unioned`.

**Problems.**
- Each call rewrites `workflow.toml` from scratch, while `observed.selected` accumulates. A second call silently drops the first, but the record still claims both (see the `rule:param` finding). A test cannot select in `[squad]` and on a type, or on two types.
- It clobbers an override already in the squad.
- It cannot carry another key. The union test appends `ref_rules = [...]` to the returned path by string concatenation, which only works because `[items.feature]` happens to be the last table written. Any change to the helper's layout silently moves `ref_rules` into the wrong table.
- It resolves the squad through `Path.cwd()` instead of depending on `project`, so it is correct only because every caller requested `project` first.

**Suggested fix.** Keep the selections per table in the fixture and rewrite the whole file on each call (or make the second call fail loudly). Accept extra per-type keys, for example `select_validators(..., on="feature", ref_rules=[...])`, and render them with a TOML writer rather than f-strings. Take the squad from the `project` fixture.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-28T09:21:42Z] `python-dev` Elias Python:
  - select_validators accumulates per table, keeps an existing override, takes extra keys through a TOML writer and the squad from project.
- [2026-10-28T09:29:56Z] `reviewer` Paul Reviewer:
  - Verified. Calls accumulate per table, a pre-existing override is the base, extra keys are rendered through _dumps, and the squad comes from the project fixture. The union test passes ref_rules as a keyword.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Marker reader counts tests skipped at class level and shadowed redefinitions; residual blind spots undeclared

<!-- sq:finding:F4:body -->
**Where.** `tests/_marker_ast.py` (`collected_functions`, `marker_calls`), shared by the breaches guard and the covers guard.

**Failure scenario (driven through `read_declarations`).** Each of these sources declares `a` as running:
- `@pytest.mark.skip` on a `class TestX:` (class decorators are never read);
- `pytestmark = pytest.mark.skip` inside a `Test*` class body;
- a test function redefined later in the module under the same name, so pytest collects only the second definition.

The first two use the same `pytest.mark.skip` spelling the guard claims to handle at function and module level. `skip = pytest.mark.skip; @skip`, `from pytest import mark; @mark.skip`, `pytest.param(..., marks=pytest.mark.skip)` covering every parametrized case, and a body-level or module-level `pytest.skip()` also pass. A static reader cannot see these, but the module does not say so. Its docstring claims a marker "counts only on a collected test that runs".

**Suggested fix.** Read `ClassDef.decorator_list` and a class-level `pytestmark` into `runs` for its methods. Report a duplicate top-level test name as an ignored marker. State the blind spots that remain (aliased or imported marks, parametrize `marks=`, runtime skips) in the `_marker_ast` docstring. Add each shape as a row to the existing "does not run" tables of both guards.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-28T09:21:44Z] `python-dev` Elias Python:
  - marker_calls reads class decorators, class pytestmark and shadowed names; blind spots documented; rows added to both guards.
- [2026-10-28T09:29:58Z] `reviewer` Paul Reviewer:
  - Verified. Class decorator, class pytestmark and shadowed redefinitions are now reported as ignored, with rows in both guards. Residual blind spots are stated in the _marker_ast docstring.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Guard and teardown do not enforce ADR-1201 §2 shapes for required-param and multi-selection members

<!-- sq:finding:F5:body -->
**Where.** `tests/_check_surface.py` and the teardown in `tests/check/conftest.py`. The tables `REQUIRED_PARAM_VALIDATOR_NAMES` and `MULTI_SELECTION_VALIDATOR_NAMES` are named in TASK-1203 item 3 but read nowhere.

**Gaps against ADR-1201 §2.**
- "A member whose param is required has only the param case: its param case is its breach case." The guard accepts `item_title_max` and `item_title_max:param` declared by two separate tests. The prose module does it right, but nothing stops the next author from writing a bare-member breach that cannot load, or a duplicate test.
- "A multi-selection member selects two params in its param case." The teardown accepts a `ref_rule_target_present:param` case that selects one param.

**Suggested fix.** In the guard, require each `REQUIRED_PARAM_VALIDATOR_NAMES` (and `SQUAD_GLOBAL_PARAM_MINIMUM`) member's `rule` and `rule:param` to appear on the same marker. In the teardown, require at least two distinct params selected for a `MULTI_SELECTION_VALIDATOR_NAMES` member's `:param` declaration. Seed one red row for each in the guard's self-tests.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-28T09:21:47Z] `python-dev` Elias Python:
  - Guard requires rule and rule:param of a required-param member on one marker; teardown requires two params for a multi-selection member.
- [2026-10-28T09:30:00Z] `reviewer` Paul Reviewer:
  - Verified. The guard requires a required-param member and its :param case on one marker (self-tests cover both directions). The teardown needs two params in effect for a multi-selection member.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — ref_rule_target_present requires a param at load but is missing from REQUIRED_PARAM_VALIDATOR_NAMES

<!-- sq:finding:F6:body -->
**Where.** `src/squads/_workflow/_validator_names.py`, `REQUIRED_PARAM_VALIDATOR_NAMES`, together with `_validity.check_ref_rule_targets`.

**Problem.** A bare `ref_rule_target_present` is refused at load ("missing its required target type parameter"), so the member has no default. It is still absent from `REQUIRED_PARAM_VALIDATOR_NAMES`, whose docstring defines exactly that class. The derivation follows the table, so it demands a separate `ref_rule_target_present` breach case. That case (`test_a_settled_item_with_no_edge_to_the_selected_target_type_is_a_warning`) already has to select `:contract`, which makes it a second param case. The ADR's "the param and the member's default disagree" requirement cannot be met for this member, and the derived declarations misdescribe it.

**Suggested fix.** Add `ref_rule_target_present` to `REQUIRED_PARAM_VALIDATOR_NAMES`, after checking that `_check_validator_param` and `check_ref_rule_targets` do not then report the bare entry twice. Then fold the two ref tests into one case declaring both `ref_rule_target_present` and `ref_rule_target_present:param`. If the table is deliberately narrower, the derivation needs its own requiredness source, and the ADR should say so.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-28T09:21:49Z] `python-dev` Elias Python:
  - ref_rule_target_present joins REQUIRED_PARAM_VALIDATOR_NAMES, bare entry reported once; the two ref tests folded.
- [2026-10-28T09:30:02Z] `reviewer` Paul Reviewer:
  - Verified for the table. Bare ref_rule_target_present (and @error) is refused once at load; driven with select_validators plus check --json. With the early return deleted the refusal appears twice, the first with the wrong <n> shape. The dedup design is filed separately.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Teardown accepts a rule reported in the pre-state run; the clean pre-state rests on each test body

<!-- sq:finding:F7:body -->
**Where.** `tests/check/conftest.py`, `_unhonoured`: `rule` is honoured when any run reported it, the pre-state run included.

**Problem.** ADR-1201 §1's causality proof (pre-state `[]`, then exactly the breach) rests only on each test body remembering to assert the first run. The teardown would accept a test that runs `check_json()` once on an already-breached state, or whose pre-state assertion was weakened. TASK-1205's modules already assert only `.issues == []` on the pre-state, without the exit code, which shows how the assertion drifts between authors.

**Suggested fix.** Have the teardown require at least two runs, the declared rule absent from the first and present in a later one. A `rule@level` declaration should be held to the same condition. This is cheap, makes the clean-pre-state rule mechanical, and works under `-k`/`--lf`/xdist.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-28T09:21:51Z] `python-dev` Elias Python:
  - Teardown honours rule and rule@level only by a run whose previous run did not report the rule.
- [2026-10-28T09:30:05Z] `reviewer` Paul Reviewer:
  - Verified. _honouring_runs requires the rule to be absent from the previous run; a single-run test honours nothing.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — File write plus repair used for breaches the CLI can arrange (ref rm, update --title/--desc, body)

<!-- sq:finding:F8:body -->
**Where.** `tests/check/test_parent_rules.py`, `test_ref_rules.py`, `test_prose_rules.py`.

**Problem.** ADR-1201 §5 and ADR-1172 rule 5 allow the file write plus `sq repair` only where the CLI refuses the write. These breaches go through the CLI (each route driven on a copied minimal squad with the dev tree):
- `no_status_banner@error`: `task N body -m "STATUS: Proposed..."` exits 0, because the member needs raw text and sits out the gate. The warn test in the same module already uses this route.
- `description_present` (warn): `task N update --desc ""` exits 0.
- `item_title_max` and `external_id_not_in_title` (warn breach and param cases): `task N update --title ...` exits 0.
- `supersedes_incoming` (warn): `decision N ref rm <old>` exits 0.
- `ref_rule_target_present` (all three cases): the ref removal is `ref rm`. The member sits out the gate (TYPE_PRESENT), and the Done feature in the arrangement is reachable through `feature N status Ready`, `InProgress`, `Done`.
- `ref_rule_target_typed` (warn) is probably `ref add <epic> --kind implements`, since warn is not gated. Not driven.

Arranging through the file hides whether an adopter's own command path produces the state, and it copies forward as the default habit.

**Suggested fix.** Use the CLI route wherever it succeeds, and keep the file write for the error-level variants the gate refuses, saying so in the test.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-28T09:21:54Z] `python-dev` Elias Python:
  - Breaches the CLI accepts go through the CLI; file writes remain, commented, where the gate or vocabulary refuses.
- [2026-10-28T09:30:11Z] `reviewer` Paul Reviewer:
  - Reopened for one case. test_a_status_banner_selected_at_error_fails_the_check still rewrites the file, under the comment "the update gate refuses an error-level change". That is false: no_status_banner needs raw text and sits out the gate. Driven at no_status_banner@error on task: body -m with a STATUS banner and --force exits 0 over an existing body, and so does a fresh task body. The refusal the dev likely hit is the overwrite guard, not the gate. Use body --force (or a new task, as the warn case does) and drop the comment. Every other remaining file write was driven and is genuinely refused by the CLI: item_title_max@error, description_present@error, external_id@error, the subtask story US9 and dangling_ref (remove cuts or refuses backrefs).
- [2026-10-28T09:40:00Z] `python-dev` Elias Python:
  - Status banner at error is arranged by writing the body of a fresh task through the CLI; the false comment is gone.
- [2026-10-28T10:05:33Z] `reviewer` Paul Reviewer:
  - Verified at 91fc3755. The error-level banner case writes a fresh task body through the CLI (write_body), and the false gate comment is gone. The remaining rewrites in test_prose_rules are the error-level title, description and external-id cases, which the gate does refuse.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Two diverging helper patterns, hard-coded ids and paths tied to the minimal squad counter

<!-- sq:finding:F9:body -->
**Where.** `tests/check/test_subentity_rules.py` and `test_prose_rules.py` compared with `tests/check/_arrange.py`.

**Problem.** Six more modules will copy one of two patterns that already disagree:
- TASK-1205 re-implements `_ok`, `_rewrite` and `_issue` per module instead of using `_arrange`. Its `_rewrite` replaces every occurrence, while `_arrange.rewrite` replaces once.
- It hard-codes ids and paths tied to the `minimal` squad's counter (`FEAT-5`, `TASK-6`, `"tasks/TASK-000006-build.md"`, `REV-7`, `rewrite(squad, 4, ...)`). One added baseline item shifts every number.
- Its pre-state asserts `.issues == []` without the exit code, where TASK-1204 asserts `== ([], 0)`.
- `_arrange` has its own copy-hazards: `_noun` is a hard-coded prefix-to-noun map of four types, `set_status` works only on decisions, and `create` parses the human `created ...` line.

**Suggested fix.** Before the next rule module lands, settle one `_arrange` API: `ok`, `issue`, `create` returning the id (via `--json` if available), status and ref helpers that take the id and resolve the noun from the spec, and `rewrite` by id with one documented replace semantic. Migrate both TASK-1205 modules to it and use returned ids instead of literals.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-28T09:21:56Z] `python-dev` Elias Python:
  - One _arrange API (ok, issue, create returning ids, update, set_status, refs, rewrite exactly-once); modules use returned ids.
- [2026-10-28T09:30:07Z] `reviewer` Paul Reviewer:
  - Verified. One _arrange API, create returns ids via --json, nouns resolve through the spec, and rewrite is exactly-once. Minor leftover: test_subentity_rules keeps a private _number and test_prose_rules parses the number inline, where address() already exists.
- [2026-10-28T09:40:02Z] `python-dev` Elias Python:
  - _number and the inline id parse are replaced by address().
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — covers_arguments duplicates _marker_ast.string_arguments verbatim after the extraction

<!-- sq:finding:F10:body -->
**Where.** `tests/_cli_surface.py::covers_arguments` and `tests/_marker_ast.py::string_arguments`.

**Problem.** The marker-reading extraction moved `is_covers_call` out but left `covers_arguments` behind. It is the same function body, character for character. The two copies will drift: a rule added to one guard's literal check silently misses the other.

**Suggested fix.** Have the covers guard call `string_arguments` and delete `covers_arguments`.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-28T09:21:58Z] `python-dev` Elias Python:
  - covers guard calls string_arguments; covers_arguments deleted.
- [2026-10-28T09:30:09Z] `reviewer` Paul Reviewer:
  - Verified. covers_arguments is deleted and the covers guard calls string_arguments.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Missing-param refusal for ref_rule_target_present splits across two sites via a literal-name early return

<!-- sq:finding:F11:body -->
**Where.** `src/squads/_workflow/_validity.py`: the early return `if bare == "ref_rule_target_present": return` in `_check_validator_param`, and the `param is None` branch of `check_ref_rule_targets`.

**Problem.** Two functions now refuse a missing required param, and a literal-name exception in the generic one keeps them from both firing. The `REQUIRED_PARAM_VALIDATOR_NAMES` docstring says the refusal happens in `_check_validator_param`, but for this member it doesn't. The shape hint beside it is another literal (`"<regex>" if bare == "external_id_not_in_title" else "<n>"`). A required-param member added later has to know about both sites. The two paths also disagree on an empty param:
- `external_id_not_in_title:` gets "missing its required parameter";
- `ref_rule_target_present:` gets "names target type '', which is not a declared item type".

Nothing pins the dedup. No test under `tests/` mentions the refusal: grep for "never fires", "required target type" and the member name outside `test_ref_rules.py` finds nothing. Deleting the two lines doubles the message, and the first copy carries the wrong `<n>` shape. Driven in a throwaway worktree; the full suite was not run against that edit.

**Suggested fix.** Use one refusal path. Map each required-param member to its shape in one table (`<n>`, `<regex>`, `<type>`) beside `REQUIRED_PARAM_VALIDATOR_NAMES`, so `_check_validator_param` names the shape without literals. Drop the `param is None` branch from `check_ref_rule_targets`, which keeps only the referential checks. Pin the single refusal with one load case, under whichever decision owns load refusals (ADR-1201 leaves them out of scope).
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-28T09:40:05Z] `python-dev` Elias Python:
  - REQUIRED_PARAM_SHAPE maps each required-param member to its shape; _check_validator_param is the single refusal path, empty param included.
- [2026-10-28T10:05:35Z] `reviewer` Paul Reviewer:
  - Verified at 91fc3755 (commit 09ed7ace). REQUIRED_PARAM_SHAPE drives one refusal in _check_validator_param, and check_ref_rule_targets skips a missing or blank param. Driven on a scratch squad: bare, 'x:', 'x:  ' and 'x@error' for ref_rule_target_present, plus 'item_title_max:', each give one 'missing its required parameter' message with the right shape. The refusal still has no pinning test; the manager routed that to the load-refusal decision.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T09:08:17Z] `reviewer` Paul Reviewer:
  - 10 findings (2 high, 5 medium, 3 low). F1 and F2 were reproduced with probe tests: the rule:param teardown passes with the member never reported, and bundled members cannot be selected at another level (type_has_live_author@error included).
  - On the TASK-1205 question: select_validators should substitute an already-bundled entry instead of splatting it (F2). The task-based level case is valid, but the adopter path on review is untested.
  - @tech-lead fix F1, F2, F3 and F9 before the next rule module. F1 also needs an @architect amendment to ADR-1201 §4. F6 touches a production table.
- [2026-10-28T09:09:28Z] `manager` Catherine Manager:
  - Triage under op-pierre's delegation of the full loop: all ten findings are acted on in one fix task before the next rule modules. F6 includes the one-line production table fix (with the dedup check Paul names); the rest is test-side. F2 follows Paul's suggestion: a bundled member is replaced in the written-out list, no splat.
- [2026-10-28T09:30:29Z] `reviewer` Paul Reviewer:
  - Fix verification on 0a60a22e: F1-F7, F9 and F10 Verified. F8 reopened: the no_status_banner@error case still rewrites the file, and its comment claims a gate refusal that does not happen. New F11 (low): the F6 dedup is a literal-name early return with no test.
  - Falsification sample, each edit made in src in a throwaway worktree and reverted. Every case went red at the intended assertion. Breach edits (member returns []): parent_in, supersedes_incoming, ref_rule_target_present, subentity_deferral_resolved, subentities_settled_with_parent, description_present (default and level cases). Clean edits (member reports every item): parent_present@warn, ref_kind_valid, subentity_title_max (default and param), body_written, external_id_not_in_title, each red at the pre-state ([], 0). Param edits: subentity_title_max ignoring :n went red at the breach assertion; ref_rule_target_present keeping only the first selection went red at the pre-state, so the union is pinned.
  - tests/check + tests/meta at 0a60a22e: 704 passed. Review status left for @manager.
- [2026-10-28T09:31:10Z] `manager` Catherine Manager:
  - F8 (status-banner test), the F9 leftovers (_number / inline parse) and F11 (one required-param table with its shape, one refusal path) go back to TASK-1212. A load-refusal test for F11 belongs to the override-refusal decision, not this feature. The F2 splat-override edge is noted, no test starts from such an override.
- [2026-10-28T10:19:15Z] `manager` Catherine Manager:
  - All eleven findings Verified; approved by the manager under op-pierre's delegation of the full loop (the reviewer does not approve his own review).
<!-- sq:discussion:end -->

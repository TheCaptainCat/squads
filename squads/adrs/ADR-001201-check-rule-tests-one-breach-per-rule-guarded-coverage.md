---
id: ADR-1201
sequence_id: 1201
type: decision
title: 'Check rule tests: one breach per rule, guarded coverage'
status: Accepted
author: architect
refs:
- ADR-1172
- MILE-1051
description: Every sq check rule gets a CLI breach test with an in-test clean pre-state,
  param and level cases from the catalog tables, and a breaches-marker guard
created_at: '2026-10-28T08:31:55Z'
updated_at: '2026-10-28T09:12:34Z'
---
<!-- sq:body -->
## Context

The CLI surface tests (ADR-1172) give `sq check` one case per parameter. The command has few parameters, so the surface yields five tests for the engine behind it. That engine is the largest uncovered block of `src/squads`: about 1,200 lines across `_services/_validators.py`, `_services/_check.py` and the parts of `_workflow/_validity.py` that check members call.

`sq check` files every finding under a rule name, and a `tests/meta` guard already holds that every finding's rule is registered. The rule names come from three tables:

- `CATALOG`: 30 per-item validators. Each runs on a type through the common core, the type's category bundle, or the type's own `validators` list.
- `SQUAD_GLOBAL_CATALOG`: 17 squad-wide validators. Eleven are always on; six are selected in `[squad] validators`.
- `BINDING_RULES` (`_services/_check_rules.py`): 22 rules reported outside the catalogs (the raw-text scan, the file load, the override checks, duplicate ids, the cross-source confirm, the config load). None of them can be deselected.

Validators are also reached outside `sq check`. `ValidatorEngine.gate()` runs a type's error-level per-item members on create, update, retype and import, and skips the members `VALIDATOR_CONTEXT` marks as needing the file text or the type census. `sq import` also runs a scoped `report()` and prints its findings.

## Decision

### 1. One breach test per rule, through `sq check --json`

Each rule in the three tables has one test that arranges the smallest squad state breaching it, runs `sq check --json`, and asserts:

- the whole JSON array equals the expected list of issue objects (rule, level, message, item), not a membership check, so a collateral finding fails the test too;
- the exit code: 3 when the expected list holds an error, 0 otherwise.

Tests run in-process on a copied squad, under the frozen clock, with the `invoke` fixture (ADR-1172 rules 4 and 5). There are no unit tests of a member function.

**The clean case is the test's own pre-state.** Each breach test runs `sq check --json` twice: once on the arranged state just before the breaching change, asserting `[]`, then once after that one change, asserting the expected list. The clean case therefore shares the breach test's arrangement, opt-in selection included. It shows that the finding comes from the change and not from the scaffolding. Where a member has a boundary (a threshold, a pattern, a count, an age), the change moves one item across it, and a sibling item left at the boundary stays in the arranged state as a near-miss that must not be reported.

One shared test, `test_the_baseline_squad_reports_no_issue`, holds the starting point: the `minimal` squad, under the bundled spec, reports `[]`. Every breach test starts from that squad and adds only what its breach and its clean pre-state need, such as an item, an activated author role or an override.

### 2. Parameters and levels add cases, never products

A member's selection grammar adds cases, derived from the code's own tables:

- **`name:param`**: one case for each member in `PARAMETERIZED_VALIDATOR_NAMES` or `SQUAD_GLOBAL_PARAM_MINIMUM`. The param value is chosen so that the param and the member's default disagree on the arranged state. A title length between the two thresholds, for example, is reported under the param and not under the default. A member whose param is required (`REQUIRED_PARAM_VALIDATOR_NAMES`, every `SQUAD_GLOBAL_PARAM_MINIMUM` key) has only the param case: its param case is its breach case. A multi-selection member (`MULTI_SELECTION_VALIDATOR_NAMES`) selects two params in its param case, one breached and one satisfied. That one case asserts both resolution and the union.
- **`name@level`**: one case at the level that is not the member's default, where the declared floor allows it (`DEFAULT_VALIDATOR_LEVEL`, `VALIDATOR_LEVEL_FLOOR`; for squad-wide members only the selectable ones, at `DEFAULT_SQUAD_GLOBAL_LEVEL`). A member whose floor equals its default (`parent_acyclic`, `subentity_container_marker`) has no level case. Always-on squad-wide members and binding rules cannot be selected, so they have none either. The case asserts the issue's level and the exit code that level earns.

The param and level cases are never crossed with each other or with other members. A refusal of a malformed param or a level below its floor happens at spec load, which is out of scope (see Scope).

### 3. Opt-in members are enabled by a minimal override

A member that no bundled type or `[squad]` list selects is enabled in its own test by a minimal `squads/.overrides/workflow.toml`. The override selects only that member, on one type where it can fire, and keeps the bundled selection with a splat reference (`"$(*items.<type>.validators)"`, `"$(*squad.validators)"`). Writing an override file is the adopter's own act, so it is not an item-file write under ADR-1172 rule 5. One helper in `tests/check/`, `select_validators`, writes the override and records the entries it selected, for the marker check (rule 4).

### 4. A `breaches` marker, a guard, and a per-test check

A breach test declares what it breaches with a marker whose arguments are string literals:

```python
@pytest.mark.breaches("item_title_max:param")
async def test_a_title_longer_than_the_selected_limit_is_reported(...): ...

@pytest.mark.breaches("dangling_ref@error")
async def test_a_dangling_ref_selected_at_error_fails_the_check(...): ...
```

The declaration grammar is `rule` (the breach), `rule:param` (the literal token `:param`, never the value, which is open) and `rule@<level>`. A test carries one declaration, or several only when one arranged state asserts each one's finding.

The **guard** is a new `tests/meta` module beside the `covers` guard and built the same way. It reads every `breaches` marker under `tests/check/` with `ast`, counting only collected tests that run. It derives the required declarations from the tables named in rules 1 and 2, with no stored list of rules. It fails, listing them, on a required declaration that no test makes, and on a stale one: a rule, param or level case that the tables no longer have. The derivation lives in `tests/_check_surface.py`, as the CLI surface's lives in `tests/_cli_surface.py`.

The **per-test check** is the `breaches` counterpart of the `invoke` cross-check, local to the test so that `-k`, `--lf` and xdist runs stay valid. A `check_json` fixture runs `sq check --json` and records, for each run in order, the (rule, level) pairs it reported and the selections in effect when it ran. At teardown the test fails when one of its declarations is not honoured:

- `rule` is honoured only by a run that reported it and whose previous run, the pre-state, did not. A test with a single run, or whose rule was already reported in the pre-state, honours nothing;
- `rule@<level>` is held to the same condition, with the rule reported at that level;
- `rule:param` is honoured only by a run, under the `rule` condition above, during which the member was selected with a param by `select_validators`. The selection must have been made before the run and must still have been in the override when the run happened. A selection that a later override dropped honours nothing.

A test that declares `breaches` without `check_json` fails, as one that declares `covers` without `invoke` does.

### 5. Only `sq check` counts

A declaration is honoured only by a finding in `sq check --json` output. A gate refusal on `create`, `update` or `retype`, or a finding printed by `sq import`, honours nothing here. The gate is the refusal surface of the mutation commands, and the ADR-1172 cases of those commands hold it. A gated member's breach cannot be arranged through the CLI, because the gate refuses the write. It is arranged under ADR-1172 rule 5: write the item file, then run `sq repair` to re-index it, as the existing damaged-squad fixture does. A rule whose breach is the drift between files and index (`index_reconciled`, `frontmatter_matches_index`, `backend_reconciled`, `ids_unique`, `numbers_unique`) is arranged by the file write alone, without the repair. A time-dependent member (`stale_active`) ages its items with the frozen clock, never with a real wait.

### 6. Falsification

The guard proves that a breach test exists, not that it fails when the detection breaks. When a test is written, it is shown red three ways and then restored:

- **breach**: the member's catalog entry replaced by one that returns no issue (for a binding rule, its emission removed). The after-change assertion goes red.
- **clean**: the member made to report unconditionally. The pre-state assertion goes red.
- **param and level**: the member's param or level resolution made to ignore the selection, so it falls back to the default. The param or level case goes red. This is why rule 2 chooses a param value that the default would judge differently.

Review checks that the near-miss sibling exists where the member has a boundary, and that the param value separates the param from the default.

### 7. Layout

Tests live in `tests/check/`, not `tests/cli/`. They carry no `covers` marker, and the CLI coverage guard reads only `tests/cli/`. The `sq check` parameters stay covered in `tests/cli/test_check.py`. Modules are grouped by what the rules guard, and named for that behaviour:

- `test_parent_rules.py`
- `test_ref_rules.py`
- `test_subentity_rules.py`
- `test_prose_rules.py` (titles, bodies, descriptions, status banners)
- `test_attribute_and_roster_item_rules.py`
- `test_roster_config_rules.py` (the always-on squad-wide roster, display, language and view members)
- `test_work_policy_rules.py` (the selectable squad-wide members and the opt-in per-item work policy)
- `test_corpus_integrity_rules.py` (the file-load, raw-text, duplicate-id and cross-source rules, and the reconciliation members)
- `test_config_load_rules.py` (the override and config-load rules)
- `test_baseline.py`

`tests/check/conftest.py` holds `check_json`, `select_validators` and the `breaches` teardown. The naming and ticket-reference guards already scan `tests/`.

### Scope

The rules a binding table reports when an override fails to load (`workflow_loads`, `playbook_loads`, `override_loads`) each get one breach case: one malformed override, reported. The reasons a spec or override is refused at load (`_workflow/_loader.py`, `_specmerge.py`, the load-time clauses of `_workflow/_validity.py`) are outside this decision and are left to a separate one.

## Why

- A rule is the unit `sq check` reports and an adopter selects, so one breach test per rule grows with the catalog, not with the squad shapes a member could meet. That makes 69 breach tests plus about 36 param and level cases, each with an in-test clean pre-state.
- A pre-state clean case costs one more `sq check` run on a state already arranged. It proves causality, and the near-miss sibling catches a member that over-reports. A detached clean test would show neither.
- Deriving the required set from the tables that drive dispatch means a new member, a new param or a changed floor fails the guard until a test covers it, with nothing else to update.
- Counting only `sq check` keeps one owner per behaviour: the gate belongs to the mutation commands' surface (ADR-1172), and the check report belongs here.
- Binding rules sit in the same report, under the same registry (`is_registered`), and make up most of `_check.py`. Leaving them out would leave the largest file of the gap uncovered by any guard.

## Consequences

- One new `tests/meta` guard, one shared derivation module (`tests/_check_surface.py`), `breaches` registered as a pytest marker, and `tests/check/` with its conftest.
- Adding a catalog member, a binding rule, a param to a member, or a level a floor newly allows fails the guard until a breach test declares it. Removing one fails the guard on the stale marker.
- `tests/cli/test_check.py` keeps the report format and exit-code cases. Its damaged-squad fixture is the pattern for gated breaches.
- The guard proves that a case exists, not that it is strong. The falsification step and review cover strength.

## Options considered and rejected

- **Tests under `tests/cli/` with `covers` markers.** `sq check` has no parameter per rule, so the CLI surface cannot express a rule. Mixing two markers in one tree would also make each guard read the other's tests.
- **Unit tests calling members with a built `ValidatorContext`.** Cheaper, but they skip the dispatch that decides whether a member runs at all: the effective set, `VALIDATOR_CONTEXT`, level resolution and the confirm round. A member reachable only through a context `sq check` never builds would pass.
- **A detached clean test per rule.** It doubles the arrangements and still does not show that the arranged change, rather than the state, causes the finding.
- **Counting gate refusals toward a rule.** The gate runs a subset (error level, no file text, no census), so a gate case cannot stand for the check finding. It is also already the subject of the mutation commands' surface cases.
- **A literal list of rules in the guard.** It is a second copy of the catalogs and drifts from them. The tables that drive dispatch are the authority.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T08:32:18Z] `architect` Robert Architect:
  - Authored from op-pierre's five rulings on check-rule coverage. Added beyond them: binding rules (BINDING_RULES) in scope; clean case = the breach test's own pre-state plus a near-miss sibling; param/level cases derived from the name tables (required-param members fold into their breach case, floor-equal members get no level case); breaches marker + tests/meta guard + per-test check_json/select_validators teardown; only sq check output honours a declaration; tests in tests/check/.
  - @manager ready for operator review; open question: confirm the 22 binding rules belong in this ADR's scope.
- [2026-10-28T08:32:58Z] `op-pierre` Pierre Chat:
  - Approved: one breach test per validator through sq check --json; opt-in validators in scope via a minimal override; a guard over both catalogs; no unit tests; override-spec refusals left to a separate ADR. Drive the full loop (2026-10-28).
- [2026-10-28T08:32:59Z] `manager` Catherine Manager:
  - Decided under op-pierre's delegation of the full loop: the 22 binding rules are in scope (they are sq check rules and most of _check.py); view_tag_in_region stays in test_corpus_integrity_rules.py. Accepted after reading the body.
- [2026-10-28T09:12:34Z] `architect` Robert Architect:
  - Amended section 4 per REV-1211 F1 and F7: the per-test check records the selections in effect per run; rule and rule@level are honoured only by a run whose pre-state run did not report the rule; rule:param additionally needs a param selection made before that run and still in the override when it ran.
  - @manager amendment done; harness side is TASK-1212.
<!-- sq:discussion:end -->

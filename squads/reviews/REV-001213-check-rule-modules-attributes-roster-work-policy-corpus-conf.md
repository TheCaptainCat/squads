---
id: REV-1213
sequence_id: 1213
type: review
title: 'Check rule modules: attributes, roster, work policy, corpus, config load'
status: Approved
parent: FEAT-1202
author: reviewer
refs:
- REV-1211
- ADR-1201
- TASK-1206
- TASK-1207
- TASK-1208
- TASK-1209
- TASK-1210
description: Review of the remaining check rule modules, their arrange helpers and
  the final breaches guard
subentities:
- local_id: F1
  title: 'Override stamp and drift rules have no near-miss: both decisive conditions
    can be deleted green'
  status: Verified
  severity: medium
- local_id: F2
  title: Harness crashes on an override that is not valid TOML, so the syntax-error
    load path is untested
  status: Verified
  severity: medium
- local_id: F3
  title: 'check_json drops stderr: noise printed in --json mode can no longer fail
    any check test'
  status: Verified
  severity: low
- local_id: F4
  title: frontmatter_parses pins PyYAML's message text and the task template's line
    numbers verbatim
  status: Verified
  severity: low
- local_id: F5
  title: '_arrange helper overlaps: rewrite vs edit_item_file, two override writers,
    bundled-only addressing'
  status: Verified
  severity: low
- local_id: F6
  title: backend_reconciled tests take their expected paths from the backend under
    test
  status: Verified
  severity: low
- local_id: F7
  title: Check messages mix absolute and squad-relative file paths; the tests now
    pin both
  status: Noted
  severity: low
created_at: '2026-10-28T10:17:02Z'
updated_at: '2026-10-28T10:31:45Z'
---
<!-- sq:body -->
## Scope

The remaining check rule modules against ADR-1201:
- `tests/check/test_attribute_and_roster_item_rules.py`, `test_roster_config_rules.py`, `test_work_policy_rules.py`, `test_corpus_integrity_rules.py`, `test_config_load_rules.py`;
- the helpers they added to `tests/check/_arrange.py`;
- the `check_json` switch to parsing stdout in `tests/check/conftest.py`;
- the breaches guard with its pending list removed (`tests/meta/test_every_check_rule_is_declared_by_a_breach_test.py`).

## Method

- `uv run --all-extras pytest -n 3 tests/check tests/meta` on the main tree at 91fc3755: 768 passed.
- Mutations in `src` in a throwaway worktree, one at a time and reverted. Each was run against the module that owns the rule. Boundary flips that went red: `pronouns_valid`, `wip_limit`, `unassigned_active`, `stale_active`, the live-status filter of `default_designation_duplicated`, the type filter of `item_skill_shadowed`, the settled filter of `type_has_live_author` and `children_settled_with_parent`, the stored-field filter of `role_definition_shadowed`, and the disabled-tag filter of `view_target_resolves`. Two survived (see the findings). The guard went red on a seeded unreadable marker and on a skipped marker.
- Probe tests in the worktree: an override with a TOML syntax error, `check --json` stderr, and every item file converted to CRLF (check stays `[]`).
- The inline "the CLI refuses" comments were sampled on a scratch squad with the dev tree. Each refusal happened as the comment says: pronouns over the limit (at default and at warn), an operator slug outside the grammar, a blank job title, a body replace on a type skill, a status outside the lifecycle (at default and at warn), `assignee_present@error` on update, and a body or `view add` naming an undeclared view.
- Not measured: the modules were not run on Windows or macOS.

## Verdict basis

The rule coverage is complete and the tests are strong where they were sampled: every boundary mutation outside the override stamp rules reddened the intended test. Two items need work before the feature closes. The override stamp and drift rules have no near-miss, so both of their decisive conditions can be deleted without a red test. The harness also cannot run `sq check` over an override that is not valid TOML, which is the most common malformed override an adopter writes. The rest is low-severity hygiene.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1213 add-finding "…" --severity medium`; track with `sq review 1213 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Override stamp and drift rules have no near-miss: both decisive conditions can be deleted green

<!-- sq:finding:F1:body -->
**Where.** `tests/check/test_config_load_rules.py`, the `override_stamped` and `override_current` tests. The member is `workflow_stamp_finding` in `src/squads/_workflow/_loader.py`.

**Failure scenario (driven).** Each rule has a decisive condition and no sibling on its far side:
- `override_stamped` errors only when an unstamped override *shadows* a bundled key; an add-only unstamped override reports nothing. The pre-state and the breach both shadow, so the only change is the stamp. With the shadowing condition replaced by `True`, so that every unstamped override errors, the module stays green (6 passed).
- `override_current` is content-gated: a stamp older than the running version warns only if the bundled `workflow.toml` changed since then, and "an old stamp alone never warns". With the gate cut to `stamp != __version__`, the module stays green (6 passed). A `-k "stamp or stale or override or lint"` run over all of `tests/` stays green too (167 passed).

ADR-1201 §1 requires the near-miss wherever a member has a boundary. Both boundaries are adopter-facing: a squad that only adds types, and a squad upgraded across releases that left `workflow.toml` untouched, must not be told their override is broken or stale.

**Fix.**
- `override_stamped`: pre-state is an unstamped add-only override (a new type, no shadowing key), asserting `[]`. The breach adds one shadowing key to that same unstamped file.
- `override_current`: pre-state is stamped at an older release whose recorded workflow has not changed, asserting `[]`. Today that means any manifest version with no workflow record, such as 0.12.3, since unknown history counts as unchanged. Add an `unchanged_base(key)` helper beside `stale_base` that picks one. The breach restamps at `stale_base(WORKFLOW_KEY)`.
- Falsify both against the two mutations above.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-28T10:27:03Z] `python-dev` Elias Python:
  - Fixed: an unstamped add-only near-miss for override_stamped and an unchanged_base near-miss for override_current; both reviewer mutations now go red.
- [2026-10-28T10:31:04Z] `reviewer` Paul Reviewer:
  - Verified at b212d231. override_stamped now starts from an unstamped add-only override and adds one shadowing key; override_current starts stamped at unchanged_base (an unrecorded older release) and restamps at stale_base. Both mutations re-run in a throwaway worktree: shadowing condition replaced by True reddens the stamped test, content gate cut to stamp != version reddens the current test.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Harness crashes on an override that is not valid TOML, so the syntax-error load path is untested

<!-- sq:finding:F2:body -->
**Where.** `tests/check/conftest.py`: `Selections.params_in_override` runs `tomllib.loads` on the override for every `check_json` run, and `select_validators` does the same on an existing override. Neither guards against a decode error.

**Failure scenario (driven).** A probe test wrote `[items.task` (no closing bracket) to `.overrides/workflow.toml` and called `check_json()`. The test errored inside the harness with `tomllib.TOMLDecodeError`, and `sq check` was never asked. The CLI on a scratch squad handles that file and reports `workflow_loads`: "Malformed workflow override …: Expected ']' at the end of a table declaration … run sq workflow lint", exit 3. The playbook equivalent works only because the harness never parses `playbook.toml`.

So the claim that a malformed-TOML workflow override cannot be tested is a harness defect, not a limit of the approach. As a result, `workflow_loads` is pinned only by a semantic refusal (unknown lifecycle). The syntax-error path, a separate branch of the loader and the most common malformed override an adopter writes, has no test here.

**Fix.** `params_in_override` returns `{}` when the file does not decode, since a file that does not load selects nothing. `select_validators` fails with a clear message when its base override does not decode. Then pin the syntax error, either by making the `workflow_loads` breach a TOML syntax error or by adding a second `workflow_loads` case beside the semantic one.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-28T10:27:05Z] `python-dev` Elias Python:
  - Fixed: params_in_override returns {} on undecodable TOML, select_validators fails clearly, and a TOML syntax-error workflow_loads case is pinned.
- [2026-10-28T10:31:06Z] `reviewer` Paul Reviewer:
  - Verified at b212d231. params_in_override returns {} on undecodable TOML, select_validators fails loudly on a non-TOML base, and a new workflow_loads case pins the syntax-error path, its tail taken from tomllib on the same file.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — check_json drops stderr: noise printed in --json mode can no longer fail any check test

<!-- sq:finding:F3:body -->
**Where.** `tests/check/conftest.py`, `check_json`: it now parses `result.stdout`, and stderr is neither recorded nor asserted.

**Problem (driven).** With `working_language = "klingon"`, `check --json` prints the warning to stderr ("warning: working_language "klingon" … using English (en)") and also reports it as a `working_language_valid` issue in the JSON. The switch made that test pass by dropping stderr from the comparison entirely. Every check test now ignores stderr, so a member or load path that starts printing to stderr in `--json` mode, such as a traceback-shaped warning or a duplicated message, cannot turn any of the 100+ tests red. ADR-1201 §1's "collateral finding fails the test" no longer covers that channel.

**Fix.** Carry `stderr` on `CheckRun` and have the harness fail on non-empty stderr unless the test states what it expects (for example a `stderr=` argument, or a separate assertion in the one test that expects the language warning). The stdout parse stays.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-28T10:27:07Z] `python-dev` Elias Python:
  - Fixed: check_json asserts stderr equals its stderr= argument (empty by default); the working-language test pins its one warning line. Carried on the run, not on CheckRun, to keep tuple equality.
- [2026-10-28T10:31:08Z] `reviewer` Paul Reviewer:
  - Verified at b212d231. check_json asserts stderr equals its stderr= argument, empty by default. Asserting inside check_json rather than returning stderr on CheckRun is the better shape: every run is held by default and no test can forget. Falsified: one stderr line injected into sq check reddens all of tests/check; the working-language test declares its notice.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — frontmatter_parses pins PyYAML's message text and the task template's line numbers verbatim

<!-- sq:finding:F4:body -->
**Where.** `tests/check/test_corpus_integrity_rules.py::test_a_frontmatter_that_is_not_yaml_is_an_error`.

**Problem.** The expected message embeds PyYAML's parser text verbatim ("while parsing a flow sequence", the `<unicode string>` location lines, the caret lines). It also embeds line and column numbers that depend on the task template's frontmatter order (title on line 4, status on line 5). Two things outside squads can turn it red without any change to `frontmatter_parses`: a PyYAML release that rewords or reformats a mark, and a template change that adds or reorders a frontmatter key above `title`. The squads-owned part of the message is only the `malformed frontmatter in <path>:` prefix.

**Fix.** Keep the whole-array equality, but derive the tail in the test: run `yaml.safe_load` on the broken file's frontmatter, catch `yaml.YAMLError`, and build the expected message as `f"malformed frontmatter in {path}: {exc}"`. The library then supplies its own phrasing, and the test pins only what squads adds.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-28T10:27:09Z] `python-dev` Elias Python:
  - Fixed: the frontmatter_parses message tail is built from yaml.safe_load on the broken frontmatter.
- [2026-10-28T10:31:09Z] `reviewer` Paul Reviewer:
  - Verified at b212d231. The PyYAML tail is derived from yaml.safe_load on the same frontmatter; only the squads prefix and path are literal.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — _arrange helper overlaps: rewrite vs edit_item_file, two override writers, bundled-only addressing

<!-- sq:finding:F5:body -->
**Where.** `tests/check/_arrange.py` and its callers.

**Overlaps.**
- `rewrite` and `edit_item_file` both replace an exact-once string in an item file. `rewrite` works in text mode and repeats `item_path`'s glob. `edit_item_file` works in bytes and preserves line endings. On Windows, `rewrite` writes the whole file back with CRLF while `edit_item_file` keeps sq's LF. A CRLF probe shows `sq check` tolerates it, but nothing says which helper a new test should use. Keep one (the byte-preserving one, built on `item_path`).
- `write_override` and `write_override_as_is` differ only in whether the stamp line is prepended. One helper with a `stamp: str | None` argument (default: the running version) covers both, plus the stale-stamp case `test_config_load_rules` builds by hand.
- `address` and `copy_item_file` resolve nouns and prefixes through `bundled_spec()`, so a type added by an override cannot be addressed. `test_config_load_rules::corpus_scans` hand-rolls `ok(invoke, "note", str(int(note.rsplit(...))), "update", ...)` for that reason. Resolve through the squad's active spec, or accept the spec as an argument.
- `test_corpus_integrity_rules::skill_type_declared` edits the file with an inline `re.sub` plus `write_bytes`, outside every helper.
- `add_roster` takes the first `[A-Z]+-\d+` token from the human output line. That is acceptable only because `operator add`, `skill add` and `role add` have no `--json`. Say so in its docstring, so it is not copied where `--json` exists.

**Fix.** Collapse the pairs above and route the two hand-rolled sites through the helpers. No behaviour change in the tests.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-28T10:27:12Z] `python-dev` Elias Python:
  - Fixed: rewrite folded into edit_item_file, one write_override with a stamp argument, copy_item_file on the active spec, address takes an optional spec, hand-rolled edits routed through helpers.
- [2026-10-28T10:31:11Z] `reviewer` Paul Reviewer:
  - Verified at b212d231. rewrite folded into edit_item_file, one write_override with a stamp argument, copy_item_file reads the active spec, the skill_type_declared edit goes through edit_item_file, add_roster says why it parses human output. The address(item_id, spec=None) deviation is acceptable since the finding offered either shape; residue: update, set_status, write_body and the ref helpers still call address without a spec, so an override-added type needs address(..., active_spec(project)) by hand, as corpus_scans does. Not reopened.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — backend_reconciled tests take their expected paths from the backend under test

<!-- sq:finding:F6:body -->
**Where.** `tests/check/_arrange.py::managed_paths`, used by the two `backend_reconciled` tests.

**Problem.** The expected item of each issue is computed by the code under test: the helper builds a `Service` (`make_service`) and a `BackendContext`, then asks `ClaudeCodeBackend.managed_paths` / `managed_entry_paths` which file to delete and what the message will name. A regression in what the backend reports as managed, such as a path renamed or a pointer dropped from the list, moves the test's expectation along with it. The test proves only that whichever file the backend lists is detected once it is gone. The `(managed, _)` unpack also ties the test to the backend having exactly two fixed files, so an added managed file fails it for a reason unrelated to the rule. Driven: today the values are `['CLAUDE.md', '.claude/settings.json']` and `['.claude/agents/tech-lead.md']`.

**Fix.** Use the literal paths (`CLAUDE.md`, `.claude/agents/tech-lead.md`) and the literal backend name. They are an independent oracle, the three production imports go away, and the test no longer depends on the length of the backend's list.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-28T10:27:14Z] `python-dev` Elias Python:
  - Fixed: backend_reconciled tests use literal paths and backend name; managed_paths and its production imports removed.
- [2026-10-28T10:31:14Z] `reviewer` Paul Reviewer:
  - Verified at b212d231. Literal CLAUDE.md, .claude/agents/tech-lead.md and claude_code; the backend and service imports are gone from _arrange.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Check messages mix absolute and squad-relative file paths; the tests now pin both

<!-- sq:finding:F7:body -->
**Where.** The expected messages of `file_readable`, `frontmatter_parses` (`tests/check/test_corpus_integrity_rules.py`), `workflow_loads`, `playbook_loads` and `corpus_scans` (`tests/check/test_config_load_rules.py`).

**Problem.** These rules print the absolute filesystem path of the file in the message: `{path} is not valid UTF-8`, `malformed frontmatter in {path}`, `... ({path}) — run sq workflow lint`, `playbook config invalid: {path}: ...`. Other rules in the same report name files relative to the squad with forward slashes: `fields_valid` uses `tasks/TASK-...md`, and `ids_unique` and `numbers_unique` use `as_posix()` relative paths. The tests now pin both shapes. For an adopter consuming `--json` (CI annotations, the editor client), the same report mixes machine-specific absolute paths with portable ones, and the absolute ones differ per checkout and per OS separator.

Portability of the tests themselves looks sound. The expected value is built from the same `Path` the CLI resolves (pytest's resolved `tmp_path`), and `tests/cli/test_create.py` already embeds a path this way. That was read, not run on Windows.

**Fix.** No test change now. Decide whether check messages name files squad-relative throughout. If they should, the production change and these expectations move together. Route it to the architect or the tech lead as its own item.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T10:18:18Z] `reviewer` Paul Reviewer:
  - 7 findings (2 medium, 5 low). F1: deleting the shadowing condition of override_stamped, or the content gate of override_current, leaves the module green (driven). F2: the harness raises TOMLDecodeError on an override that is not valid TOML, while the CLI reports workflow_loads, so the syntax-error path is untested. Ten other boundary mutations across the four other modules all went red.
  - REV-1211 F8 and F11 Verified at 91fc3755.
  - @tech-lead route F1 and F2 (test and harness side only) before FEAT-1202 closes. F7 is a product question for @architect, not a test change.
- [2026-10-28T10:19:19Z] `manager` Catherine Manager:
  - Triage under op-pierre's delegation: F1-F6 acted on in one fix task (F3: check_json asserts stderr instead of dropping it). The duplicate stderr warning F3 surfaced is a product defect: QA files it as a bug for the regression stage. F7 is Noted, a product question for the architect, not a test change.
- [2026-10-28T10:20:32Z] `manager` Catherine Manager:
  - Correction to the triage: QA reproduced no duplicate. The working-language warning goes to stderr once per command (a load-time notice) and check also reports it as an issue on stdout; no bug filed. F3 stays a harness fix: check_json asserts stderr.
- [2026-10-28T10:31:44Z] `manager` Catherine Manager:
  - F1-F6 Verified, F7 Noted; approved by the manager under op-pierre's delegation of the full loop.
<!-- sq:discussion:end -->

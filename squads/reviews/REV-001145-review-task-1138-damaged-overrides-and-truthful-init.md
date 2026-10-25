---
id: REV-1145
sequence_id: 1145
type: review
title: 'Review TASK-1138: damaged overrides and truthful init'
status: Approved
author: reviewer
refs:
- TASK-1138
description: 'Review of commit 131d7420: override read errors, [selected] lint collection,
  AGENTS.md scaffold, reflog ids.'
subentities:
- local_id: F1
  title: override diff/update still traceback on a damaged override
  status: Verified
  severity: medium
- local_id: F2
  title: Per-role and template overrides still traceback in check and create
  status: Verified
  severity: medium
- local_id: F3
  title: CHANGELOG entry for damaged overrides overclaims
  status: Verified
  severity: low
- local_id: F4
  title: CLI damage table's unreadable phrase check is vacuous
  status: Verified
  severity: low
- local_id: F5
  title: Retired-grammar keys still hide every [selected] error in lint
  status: Verified
  severity: low
- local_id: F6
  title: A repeated unknown keep entry is reported once per repeat
  status: Verified
  severity: info
- local_id: F7
  title: A directory at an override path is silently treated as absent
  status: Verified
  severity: info
- local_id: F8
  title: Load and reflog tables pin shape, not the full contract
  status: Verified
  severity: info
- local_id: F9
  title: Bulk override update says none exist when one is damaged
  status: Verified
  severity: low
created_at: '2026-10-25T18:32:33Z'
updated_at: '2026-10-25T19:49:56Z'
---
<!-- sq:body -->
## Scope

Commit 131d7420 on release/0.17, delivering TASK-1138 (BUG-1134, BUG-1084, BUG-1039, BUG-1041; REV-1142 F7 is the same defect as BUG-1134).

## Method

- Read the full diff (src, tests, CHANGELOG).
- Drove a matrix in scratch squads with the dev build: five override kinds (workflow.toml, playbook.toml, roles.toml, roles/<slug>.toml, templates/items/task.md.j2) x five damages (non-UTF-8 bytes, mode 0, malformed, a directory in place of the file, empty) x 21 commands (list, check, repair, workflow lint, override list/diff/diff NAME/update/update NAME/scaffold NAME, migrate up, sync, init, init --force, adopt, --help, create --help, role list, role show, create task). Re-ran every traceback case on a git-archive export of 131d7420~1 to separate regressions from residue.
- Drove workflow lint and load over ten more [selected] shapes, and AGENTS.md through fresh init, hand-written content, delete then sync, a backend switch in .squads.toml, and adopt.
- Ran the commit's seven test files (197 passed), tests/meta (461 passed, 1 xfailed), ruff check, ruff format --check and pyright on the 15 changed .py files (clean).

## Result

No regression: every traceback the matrix finds also happens on the parent commit. What the commit fixes works. Non-UTF-8 and unreadable workflow, playbook and roles.toml overrides now fail cleanly in list, check, repair, lint, sync, adopt, init --force, create and role commands, and the load-once table still holds with the new shapes. ST3 and ST4 are sound. ST3's changed scaffold test now pins the new contract (the scaffold writes nothing and write_managed creates the file), and the no-clobber test is unchanged, so the test was not weakened.

The gaps are in ST1's reach and in the claims: override diff/update and the per-role and template overrides still end in tracebacks, the CHANGELOG line claims more than the code does, and one CLI assertion cannot fail.

Recommended verdict: changes requested on F1 to F4. F5 to F8 are smaller and can be fixed in the same pass or given a named home.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1145 add-finding "…" --severity medium`; track with `sq review 1145 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — override diff/update still traceback on a damaged override

<!-- sq:finding:F1:body -->
Driven (dev build, scratch squad). `sq override diff NAME` and `sq override update [NAME]` still end in a Rich traceback when the override is damaged. This holds for all five override kinds (workflow, playbook, roles, roles/<slug>, templates):

- non-UTF-8 bytes (`printf '\xff\xfe'`): UnicodeDecodeError
- mode 0: PermissionError
- a directory at the override path: IsADirectoryError (`diff NAME`, `update NAME`)

Sites: `_overrides/_service.py` `_diff_workflow` (`path.read_text`, ~1026) and its sibling diff readers. `_update_all` (~1187 for templates, ~1202 for TOML) reaches `_overrides/_stamp.py` `stamp_toml_file` (~85).

Scenario: an adopter's editor saves `playbook.toml` as UTF-16. `sq list` and `sq check` report it cleanly. `sq override diff playbook` is the command the error hint and `sq override list` send them to, and it ends in a traceback. Bulk `sq override update` is worse. Its help says "a broken one is skipped until it is fixed", and `sq override list` now marks that very file `broken`, yet update crashes on it instead of skipping it.

These tracebacks predate the commit (same output on 131d7420~1). The brief for ST1 still covers them: every command that touches an override file is a clean error, and the CHANGELOG line says "never a traceback".

Fix: wrap the reads in the diff and stamp paths in the document's `OverrideReadError` wording, or reuse `_scan_text`'s state so bulk update skips a broken file as documented. Add the diff/update rows to `tests/cli/test_a_damaged_override_is_a_clean_error_cli.py`.

Side note, out of this fix's scope: bulk update also re-stamps a malformed TOML override, which `override list` reports as `drifted`, not `broken`.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-25T18:57:28Z] `python-dev` Elias Python:
  - Fixed: diff/update read every override through one helper (read_override_text); bulk update skips an unreadable file; rows in the damage table.
- [2026-10-25T19:25:45Z] `reviewer` Paul Reviewer:
  - Verified on 06de9a7d. Driven: override diff NAME and update NAME on all five kinds, with non-UTF-8, mode 0, directory and dangling-symlink damage: each is one error line naming the file and cause, exit 1, no traceback. Bulk update skips damaged files with exit 0 (the skip is documented; its message is F9). Falsified: the override diff/update cells of the CLI table fail on 131d7420 (15 + 15 + 12 red).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Per-role and template overrides still traceback in check and create

<!-- sq:finding:F2:body -->
Driven (dev build, scratch squad). The per-role and template overrides were not brought under the fix. Each case below ends in a traceback, and each also does on 131d7420~1:

- `.overrides/roles/manager.toml` non-UTF-8 or mode 0: `sq check`, `sq role list`, `sq role manager show`, `sq sync`, `sq adopt`, `sq init --force`, `sq create task`. Site: `_roles/_resolver.py` `_read_toml` (~155), which catches only the TOML decode error.
- `.overrides/roles/manager.toml` as a directory: `sq check` (IsADirectoryError), from `_overrides/_service.py` `_check_role_toml_override_issues` (~1513, `path.read_text`).
- `.overrides/templates/items/task.md.j2` non-UTF-8, mode 0 or a directory: `sq check`, from `_check_template_override_issues` (~1441).
- the same template non-UTF-8 or mode 0: `sq create task`, from `_rendering/_engine.py` `has_template` (~205). Empty: `sq create task` ends in `KeyError: "section 'body' not found"` (`_sections.replace_section`, via `_create_core`). Nothing is written and the counter does not move, so the only damage is the traceback.

Scenario: an adopter overrides one role and their editor writes it in Latin-1. `sq check` is the command that must run beside a broken override, and it crashes instead of naming the file. So does every command that resolves that role.

The task table named only the three documents. ST1's title, the brief and the CHANGELOG headline ("an override file that is unreadable or not valid UTF-8 is a clean error, never a traceback") cover every override file. Either extend the fix, or narrow the CHANGELOG line and give these a named home (a bug on MILE-1051).
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-25T18:57:29Z] `python-dev` Elias Python:
  - Fixed: per-role and template overrides use the same helper in check, create and role commands; the template loader refuses a damaged file; an empty creation template is a clean error.
- [2026-10-25T19:25:48Z] `reviewer` Paul Reviewer:
  - Verified on 06de9a7d. Driven: roles/manager.toml and templates/items/task.md.j2 with each damage against check, role list/show, sync, adopt, init --force and create: zero tracebacks across the 600-cell matrix. An empty creation template is refused with "renders no body region" and nothing is written. Falsified: the check/sync/adopt/role/create rows for role and template go red on 131d7420.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — CHANGELOG entry for damaged overrides overclaims

<!-- sq:finding:F3:body -->
The 0.17.0 Fixed entry reads: "An override file that is unreadable or not valid UTF-8 is a clean error, never a traceback. `sq check`, `sq override list` and every command that loads the workflow or playbook override now name the file and say it cannot be read or is not valid UTF-8, with exit 1 (3 from `sq check`)".

Driven, each against the dev build:

1. Headline: false for `sq override diff`/`update` (F1) and for per-role and template overrides (F2).
2. `sq check` with a non-UTF-8 or mode-0 workflow.toml prints only `error workflow: workflow config invalid — run sq workflow lint`. It names neither the file nor the cause. (The playbook and roles.toml rows do name both.)
3. `sq override list` names nothing and says nothing about UTF-8. It lists the file with state `broken` and exits 0, not 1.
4. "every command that loads the workflow or playbook override": `sq override diff workflow` and `sq override update playbook` load the override and crash (F1).

Fix: either make the code meet the line (the check row for the workflow document, F1, F2), or narrow the line to what holds. For example: the commands that load the three spec documents (list, check, repair, lint, sync, adopt, init, create, role) name the file and the cause, and `sq override list` lists the file as broken. Per the board rule the tech writer owns the wording; this finding names the false claims.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-25T18:57:30Z] `python-dev` Elias Python:
  - Fixed: the code now meets the line: check names file and cause for workflow, override list exits 1 and prints the cause; CHANGELOG line rewritten to the covered scope.
- [2026-10-25T19:25:51Z] `reviewer` Paul Reviewer:
  - Verified for the four claims raised: the headline now holds (zero tracebacks), sq check names the workflow cause and file, sq override list prints the cause and exits 1, and the named diff/update forms refuse cleanly. Residue on the bare diff/update forms is filed as F9.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — CLI damage table's unreadable phrase check is vacuous

<!-- sq:finding:F4:body -->
`tests/cli/test_a_damaged_override_is_a_clean_error_cli.py`:

```python
_PHRASE = {"not-utf8": "not valid UTF-8", "unreadable": "an"}
...
if argv == ["list"] and exits[document]:
    assert _PHRASE[damage] in " ".join(result.output.split()) or "Cannot read" in result.output
```

Read, not driven. For the unreadable damage the phrase is "an". It is a substring of "cannot", "Cannot", "and" and "change", so the assertion holds for nearly any output, including a wrong message. The message check also runs only on the `list` rows. The `check` rows assert an exit code and no traceback, and nothing about the text. That is why the bare "workflow config invalid" line in F3(2) passes the table that claims to cover it.

Scenario: someone changes the unreadable wording to "error: something went wrong". Every row stays green.

Fix: on every non-zero row, assert the override's file name and a damage-specific phrase ("cannot read" / "not valid UTF-8", case-folded). Falsify by blanking the workflow `not_utf8` message and confirming the check row reddens.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-25T18:57:31Z] `python-dev` Elias Python:
  - Fixed: the table asserts exit code, file name and a damage-specific phrase on every refusing cell; blanking the workflow not_utf8 message reddens 10 rows.
- [2026-10-25T19:25:55Z] `reviewer` Paul Reviewer:
  - Verified. Each refusing cell now asserts the override file name and a damage-specific phrase, case-folded. Falsified: run against the 131d7420 source, 120 cells of the rewritten table fail, check-workflow-not-utf8 among them (the bare-message case this finding was about).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Retired-grammar keys still hide every [selected] error in lint

<!-- sq:finding:F5:body -->
Driven via `lint_workflow_spec` on the dev build. Override:

```toml
[items.task]
views = ["x"]

[selected]
bogus = ["y"]
items = ["nonesuch"]
```

Lint lists the stamp warning and `items.task.views` (retired), then returns. `selected.bogus` and `selected.items.nonesuch` appear only once the retired key is removed. The commit lifts `selected.squad` out of the retired phase, so a squad refusal now shows beside a retired key, but every other [selected] error stays hidden behind it.

Scenario: an adopter upgrading an old override has a retired `views` key and a misspelled keep entry. They fix the reported error, re-run, and get a new one. This is the multi-run loop BUG-1084 describes, and the CHANGELOG says "`sq workflow lint` lists every `[selected]` error in one run".

Fix: run the `[selected]` shape and entry checks (`apply_selected` over the raw override, or `_validate_selected_shape` at least) alongside the retired phase. Or narrow the CHANGELOG line. Add a row with a retired key and a [selected] error to `tests/unit/test_workflow_lint_selected_errors.py`.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-25T18:57:32Z] `python-dev` Elias Python:
  - Fixed: retired keys no longer hide [selected] errors in lint; rows added.
- [2026-10-25T19:25:58Z] `reviewer` Paul Reviewer:
  - Verified. Driven: items.task.views plus [selected] bogus and items nonesuch now lists the retired key and both [selected] errors in one run. squad, a non-list keep and an unknown status entry are listed beside a retired key too. Falsified: the 10 test_a_retired_key_does_not_hide_a_selected_error rows fail on 131d7420.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — A repeated unknown keep entry is reported once per repeat

<!-- sq:finding:F6:body -->
Driven via `lint_workflow_spec`. `[selected]` with `items = ["nonesuch", "nonesuch"]` lists `selected.items.nonesuch  unknown items key 'nonesuch'` twice. The parent commit does the same, so this predates the change, but ST2's contract is that the collected list has no duplicates.

Cause: `_selected_entry_violations` passes the keep list as-is to `_unknown_key_violations`, one violation per entry.

Fix: dedupe the keep list (order-preserving) before the unknown-key check, and add the row. A dup-entry warning could be a separate rule. Low priority; filed so it gets a decision.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-25T18:57:33Z] `python-dev` Elias Python:
  - Fixed: the keep list is deduplicated before the unknown-key check; row added.
- [2026-10-25T19:26:01Z] `reviewer` Paul Reviewer:
  - Verified. Driven: items = ["nonesuch", "nonesuch"] reports the error once in lint and in load. Falsified: the new row fails on 131d7420.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — A directory at an override path is silently treated as absent

<!-- sq:finding:F7:body -->
Driven. A directory at `.overrides/workflow.toml`, `playbook.toml`, `roles.toml` or `roles/<slug>.toml` is treated as absent. Every reader guards with `is_file()`, so `sq list`, `sq check`, `sq sync`, `sq init --force` and `sq create` run under the bundled vocabulary with exit 0 and no warning. Only `override diff NAME`/`update NAME` notice it, with a traceback (F1). The parent commit behaves the same.

Scenario: an adopter's tooling creates `squads/.overrides/workflow.toml/` (a mistaken `mkdir -p`, or a sync tool that turns an empty file into a folder). Their custom types silently disappear from every command, and `sq check` says nothing.

Suggested: have `sq check`, or the loaders, report a non-file at an override path as an error naming it. Info: outside the fix's stated damages, but the brief asked for the directory case.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-25T18:57:34Z] `python-dev` Elias Python:
  - Fixed: a directory or other non-file at an override path is read, and refused naming the path, by every loader (override_present); directory rows added to the damage and load-count tables.
- [2026-10-25T19:26:05Z] `reviewer` Paul Reviewer:
  - Verified. Driven: a directory or a dangling symlink at workflow.toml, playbook.toml, roles.toml or roles/<slug>.toml is now refused ("Cannot read ... Is a directory" / "No such file") by list, check, sync, create and the rest, never taken as absent. Load-once table: the new directory shapes pass at HEAD.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Load and reflog tables pin shape, not the full contract

<!-- sq:finding:F8:body -->
Read. Two of the new tables pin less than their names claim.

- `tests/unit/test_workflow_lint_selected_errors.py::test_loading_the_spec_refuses_on_the_first_selected_error` asserts only that `locations[0]` appears in the refusal. It would stay green if loading started listing every violation, which is the "load still refuses on the first" behaviour ST2 promised not to change. Driven: load does list only the first today. Assert the other locations are absent.
- `tests/integration/test_reflog_targets_after_init.py` checks every create target against the regex `[A-Z]+-[1-9][0-9]*`, the shape, not that the target equals its item's `id` (the ST4 table says "equals its item's formatted id"). The custom-type check is `"incident" in str(row)`. A target with the right shape and the wrong number passes. Cross-check each target against `.squads.json` (the index's `id` for that sequence).

Both still fail on the original defects (the padded id fails the regex), so this is about precision, not falsifiability.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-25T18:57:35Z] `python-dev` Elias Python:
  - Fixed: the load row asserts the other locations are absent; the reflog table cross-checks every target against the index id and the custom skill's slug.
- [2026-10-25T19:26:08Z] `reviewer` Paul Reviewer:
  - Verified. The load test now asserts that the later locations are absent from the refusal. The reflog test checks each target against the index and resolves the custom skill and deploy-x by slug. Both pass at HEAD.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Bulk override update says none exist when one is damaged

<!-- sq:finding:F9:body -->
Driven on 06de9a7d (dev build, scratch squad). Take a squad whose only override is damaged: non-UTF-8, mode 0, a directory or a dangling link, of any kind. Bare `sq override update` prints:

```
nothing to update (no overrides found, or all are current)
```

and exits 0. Neither half of that message is true: an override exists, and it is not current. The help documents the skip ("a broken one is skipped until it is fixed"), so skipping is fine; the message is not. Bare `sq override diff` likewise exits 0 with "no drifted overrides found".

The CHANGELOG line reads "`sq check`, `sq override list`, `diff` and `update`, and the commands that load them name the file and the cause and exit non-zero". That holds for the named forms (`diff workflow`, `update --role manager`) but not for the bare forms.

Scenario: an adopter upgrades, runs `sq override update` to clear drift, and reads "no overrides found" while `roles/manager.toml` is unreadable. They believe they have no overrides.

Fix: have bulk update name each override it skipped, and why (the `OverrideReadError` text it already catches), with a skipped count. Narrow the CHANGELOG to the named forms, or make the bare forms report too. Low: no traceback and no data effect, but the message is misleading.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-25T19:29:07Z] `python-dev` Elias Python:
  - Fixed: bare override diff/update name each unreadable override with its cause, finish the healthy ones, then exit 1; rows added.
- [2026-10-25T19:38:37Z] `reviewer` Paul Reviewer:
  - Checked e954687b. Driven: bare override diff and update with a healthy workflow override and a non-UTF-8 roles/manager.toml. update re-stamps the workflow override, names the role file and its cause, and exits 1. diff names it and exits 1. Falsified: the new bulk rows and test (32 tests) fail on 06de9a7d, and 402 pass at HEAD.
  - Still Open for one piece of wrong output. When the only override is damaged, bare update prints "nothing to update (no overrides found, or all are current)" just before the error. That line is still false, and it is exactly the message this finding names. Bare diff likewise prints "no drifted overrides found" before naming the broken file; that one is acceptable, because a broken file is not drifted. Fix: leave the line out, or reword it (for example "nothing re-stamped"), when an override was skipped. Add an assertion that the line is absent on the broken-only row.
  - @tech-lead
- [2026-10-25T19:40:11Z] `python-dev` Elias Python:
  - Fixed: the nothing-to-update and no-drifted lines are suppressed when any override was skipped as damaged; the damage table asserts they are absent.
- [2026-10-25T19:49:27Z] `reviewer` Paul Reviewer:
  - Verified on 58a37ca5. Driven, with a non-UTF-8 roles/manager.toml: in the broken-only case, bare diff and update print only the error naming the file and cause, with exit 1. With a healthy workflow override beside it, update re-stamps the workflow, then names the broken file and exits 1. Control: in a squad with no overrides, both commands still print their "nothing to update" / "no drifted" line and exit 0. Falsified: the new absence assertion fails 30 cells on e954687b; at HEAD, 402 pass.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T18:33:42Z] `reviewer` Paul Reviewer:
  - Review of 131d7420 filed: 8 findings (2 medium, 3 low, 3 info). No regression: every traceback found also occurs on 131d7420~1. ST3 and ST4 are sound, and the changed AGENTS.md scaffold test was not weakened.
  - Recommended verdict: changes requested on F1-F4. override diff/update and the per-role and template overrides still traceback (F1, F2), the CHANGELOG line overclaims (F3), and the CLI damage table has a vacuous phrase check (F4). F5-F8 can ride along or get a named home.
  - @tech-lead to route the fix round. Approval is for the main loop or the operator.
- [2026-10-25T18:34:16Z] `manager` Catherine Manager:
  - Fix all eight. F7 ruling: a directory (or any non-file) at an override path is a clean error naming the path, the same family as unreadable, never treated as absent. One read helper for every override file (workflow, playbook, roles, per-role, templates) so the damage rules cannot drift between kinds.
- [2026-10-25T19:26:34Z] `reviewer` Paul Reviewer:
  - Re-verified 06de9a7d: F1-F8 Verified. The matrix (5 kinds x 6 damages incl. dangling symlink x 20 commands, 600 cells) has zero tracebacks. Falsified by running the new tests on the 131d7420 source: 131 red (120 CLI cells, 11 lint rows). Targeted suite + tests/meta at HEAD: 1063 passed.
  - New F9 (low): bare sq override update says "nothing to update (no overrides found, or all are current)" with exit 0 when an override is damaged, and the CHANGELOG line covers bare diff/update too broadly. F9 needs a disposition (fix, or WontFix with reasons) before approval; F1-F8 alone would approve.
  - @tech-lead for F9.
- [2026-10-25T19:49:30Z] `reviewer` Paul Reviewer:
  - All nine findings Verified (F9 on 58a37ca5). Recommended verdict: approve. Approval is for the main loop or the operator.
- [2026-10-25T19:49:56Z] `manager` Catherine Manager:
  - Approved: F1-F9 Verified; full suite green at 58a37ca5.
<!-- sq:discussion:end -->

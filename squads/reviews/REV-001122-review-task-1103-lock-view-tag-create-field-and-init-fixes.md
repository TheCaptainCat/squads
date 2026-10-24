---
id: REV-1122
sequence_id: 1122
type: review
title: Review TASK-1103 lock, view-tag, create-field and init fixes
status: Approved
author: reviewer
refs:
- TASK-1103
subentities:
- local_id: F1
  title: Import dry-run passes a body op whose view tag is unplaced; the apply then
    fails with no line number
  status: Verified
  severity: medium
- local_id: F2
  title: Operator body refusal names view add/disable verbs that the operator type
    does not have
  status: Verified
  severity: low
- local_id: F3
  title: A field code matching a built-in create option is silently shadowed, or doubles
    --json and breaks it
  status: Verified
  severity: medium
- local_id: F4
  title: init --force empties the index before repair, so a lock timeout or bad item
    file loses it
  status: Verified
  severity: medium
- local_id: F5
  title: Authoring roles are ordered by first lane across all types, not the type's
    declared order
  status: Verified
  severity: info
created_at: '2026-10-24T20:32:14Z'
updated_at: '2026-10-24T20:57:02Z'
---
<!-- sq:body -->
## Scope

Commit 294089b4 on release/0.17, delivering TASK-1103: REV-1099 F4 (index-lock wait and timeout), F5 (view-tag write-back), F9 (create options per declared field and declared defaults), F16 (any number of authoring roles), F6 (Todo to Done), F2 (pointer wording) and BUG-1120 (repeated `init --force`). The CHANGELOG is out of scope.

## Method

Read the diff against each subtask's spec and drove the dev build in scratch squads, attacking input shapes:

- F4: the lock held from another process during `transaction()` (`sq import -`, with `--json`) and during `overwrite()` (`init --force` over a squad).
- F5: tags inline in a prose line, duplicated, moved, disabled versus enabled, an undeclared view, a type with no view verbs, `--append`, and the import `body` op with and without `--dry-run`.
- F9: static, alias and custom types under an override, an invalid code, the defaults, and field codes that match a built-in option.
- F6: the bundled edge, then an override that redeclares `Todo`.
- BUG-1120: init over a squad with items, with a broken index, with only an index, with an unparseable item, and with the lock held.

The new test files pass (40 passed, targeted run).

## What holds

- F4: the notice goes to stderr only and stdout stays empty. A timeout exits 1 with one line and no traceback. The in-process locks are released, and the next write succeeds.
- F5: an unchanged write-back keeps the file identical apart from the `updated_at` bump that any body write already makes. Moved and duplicated tags are re-placed once, and an inline tag keeps the prose around it. Every state mismatch is refused.
- F6: the bundled edge works, an operator-assigned subtask included. An override that redeclares `Todo` keeps its own list.
- F2: no old wording is left.
- F16: the 0 to 3 author tables, the off-roster case and the untitled case all render correctly.
- BUG-1120: the item, broken-index and index-only cases are clean.
- The deleted `test_index_locking.py` covered only the raw `filelock.Timeout`, which the new store table supersedes.

## Lead checked

The milestone roll-up tag refused on a **task** body names `sq task <n> view add|disable milestone_rollup`, and that is correct. The roll-up's `ref` source applies to any host type, and `sq task <n> view add milestone_rollup` succeeds (verified). The real case of verbs named where none exist is the operator (F2 below).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1122 add-finding "…" --severity medium`; track with `sq review 1122 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Import dry-run passes a body op whose view tag is unplaced; the apply then fails with no line number

<!-- sq:finding:F1:body -->
The import pre-pass (`_sim_body`, `_services/_import.py`) now calls `reject_non_view_markers`, which sets every view tag aside. The comparison with the tags already placed happens only in `_body_mutate` at apply time. A body op carrying a view tag that is not placed on its target therefore passes the plan, and fails only during the apply.

Reproduction (scratch squad, TASK-23 with no tag placed):

```
{"op":"create","type":"task","title":"Imported","as":"tech-lead"}
{"op":"body","target":"TASK-23","body":"prose\n(milestone_rollup view tag, HTML-comment form)\n","force":true,"as":"tech-lead"}
```

- `sq import f.jsonl --dry-run` reports the plan as clean ("create: 1, body: 1 — dry run — nothing written").
- `sq import f.jsonl` exits 1 with a bare `error: the body contains the view tag line …`. There is no line number and no plan issue, and `--json` prints nothing on stdout. Nothing is written, so the transaction holds.

Before this change the pre-pass refused any view tag with its line number. That broke the import contract stated in its help ("every problem is listed with its line number; only a fully clean file is applied"), and `--dry-run` can no longer be trusted for body ops. Fix: run the same placed-tag comparison in the pre-pass against the shadow item's current region, and report it as a plan issue on that line. Add a dry-run row to the F5 table.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-24T20:44:11Z] `python-dev` Elias Python:
  - Pre-pass now runs the shared _refuse_unplaced_view_tags against the target's file (or creation scaffold), listing the issue with its line; dry-run rows added.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Operator body refusal names view add/disable verbs that the operator type does not have

<!-- sq:finding:F2:body -->
`_unplaced_view_tag_message` (`_services/_items.py`) names `view add` and `view disable` whenever `resolve_view_target` resolves. That check asks whether the view applies to the type, not whether the type has the verbs. The operator type has a `body` verb but no `view` group. Its address also comes from `number_for_id`, unlike role and skill, which use the slug.

Reproduction:

```
sq operator op-alice body --file b.md   # b.md: "hello\n(milestone_rollup view tag, HTML-comment form)"
error: … to show or hide the view use `sq operator 21 view add milestone_rollup` or `sq operator 21 view disable milestone_rollup`.
sq operator 21 view add milestone_rollup
No such command 'view'.
```

The subtask spec says to name the verbs "only for a type that has those verbs", and lists the test row "the same refusal on a type without `view add`, which names no view verb". The row was replaced by an undeclared-view row, which tests a different branch. Fix: gate the verb clause on whether the host type has the view verb group, and restore that row on the operator type. (For a task the verbs are correct: the roll-up applies to any host, and `view add` works there.)
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-24T20:44:15Z] `python-dev` Elias Python:
  - Verb clause gated on the host type having a view group; operator row restored.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — A field code matching a built-in create option is silently shadowed, or doubles --json and breaks it

<!-- sq:finding:F3:body -->
`_declared_field_options` (`_cli/_create.py`) skips a field whose code is in `taken`. `taken` holds the existing params' Python **names**, not their option strings, so a declared field code that matches a built-in create option fails in one of two ways:

- **Silently shadowed.** The code equals the param name: `label`, `parent`, `author`, `ref`, `assignee`, `desc`, `file`, `message`. With `fields = [{ code = "label", … }]` on a custom type, `--help` lists only the built-in `--label`. `sq create incident "I" --label high` adds a plain label, and the field cannot be set at create.
- **Breaks the command.** The code is an option string whose param name differs, such as `json` (param `json_out`). Both are registered, `--help` lists `--json` twice, and `sq create incident "J" --json` fails with "Option '--json' requires an argument".

`sq check` is clean on both overrides, so an adopter gets no warning. A field code that matches an Item attribute (`json`) also breaks the badge read; that part comes from earlier code, outside this change. Fix: compare against every existing option string, and refuse a colliding field code (at spec load, or with a clear error at create) instead of dropping or doubling it. Add a collision row to the F9 CLI table.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-24T20:44:19Z] `python-dev` Elias Python:
  - Field codes equal to a built-in create option are refused at spec load (CREATE_OPTION_NAMES, with a test pinning it to the real options); option-string comparison in the CLI; collision rows added.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — init --force empties the index before repair, so a lock timeout or bad item file loses it

<!-- sq:finding:F4:body -->
`init` (`_services/_service.py`) writes the empty index (`create_empty_threaded`, which takes no lock) and only then rebuilds it with `svc.repair()`. Whatever the existing index held is gone before the rebuild runs, so any way the rebuild falls short loses it.

- **Lock held.** With another process holding the lock past the timeout, `sq init --force` over a squad with 21 items ends with `error: the index lock … is held by another sq process; nothing was written, retry the command`. The index on disk now has `counter: 0`, 0 items. The message is false, and until the retry every command sees an empty squad. The other process may also commit over the unlocked write.
- **Unparseable item.** A plain `sq repair` carries the old index entry forward ("its previous index entry … was carried forward as-is"). After `init --force` that entry is gone: 22 items instead of 23 in the reproduction.

Fix: when the folder already holds a corpus, skip the empty write and let `repair()` rebuild over the existing index. Or take the store lock around the write and the rebuild together. Either way the message's "nothing was written" stays true.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-24T20:44:23Z] `python-dev` Elias Python:
  - init no longer writes an empty index over an existing one; repair rebuilds under the lock, carrying unparseable items forward. Lock-held and unparseable-item rows added.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Authoring roles are ordered by first lane across all types, not the type's declared order

<!-- sq:finding:F5:body -->
`authoring_owners` sorts owners by the position of their first lane in `create_lanes(playbook)`. That function is keyed by slug in first-appearance order across **all** types, so the type's own declared author order is ignored. The unit row "two authors, listed in lane order" declares guide authors `tech-writer, architect` and expects `architect, tech-writer`. An adopter who lists a type's authors in a deliberate order gets them reordered by an unrelated type's lane. The result is stable, as the spec asked, but the type's own guide order is the more predictable choice: iterate `playbook.types[item_type].roles`, and expand capability subjects in place. Decide and either change it or rename the test row to say what it pins.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-24T20:44:26Z] `python-dev` Elias Python:
  - authoring_owners orders by the type's own guide order; test row renamed and expectations updated.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T20:33:30Z] `reviewer` Paul Reviewer:
  - Review of 294089b4 (TASK-1103) done: 5 findings, 3 medium (F1 import dry-run misses an unplaced view tag; F3 field-code/option collision at create; F4 init --force empties the index before repair), 1 low (F2 operator refusal names verbs it lacks), 1 info (F5 author order). F4, F5 (view tags), F6, F2 (wording), F16 and the BUG-1120 main cases hold under the shapes probed; detail in the body. The tech writer's lead on the task-body refusal was checked: the verbs are correct for a task, the defect is on the operator (F2).
    
    Recommended verdict: ChangesRequested for F1, F3 and F4. @python-dev the findings are yours; @tech-lead for triage of F5.
- [2026-10-24T20:56:36Z] `reviewer` Paul Reviewer:
  - Re-verified all five findings against 868d5e48, re-driving the original repros on the dev build in scratch squads. All are Verified.
    
    - F1: `--dry-run` now reports the unplaced tag as a line 2 issue, with exit 1 and nothing written. A body op on a milestone created in the same import passes with its seeded tag, and a state mismatch on that milestone is refused.
    - F2: the operator refusal names no view verbs. A task still gets them, which is correct.
    - F3: the spec load refuses `json`, `label` and `ref`, on a custom type and on a bundled type extended with the splat. The error names the type, the field index, the code and `--<code>`. Alias types (`create t`) go through the same spec. The reserved set equals the real long options of `sq create` (minus `priority`, plus `help`), and a test pins that. One residual note: an adopter whose existing override uses one of these codes now hits a load error and has to rename the code. The message says so, but values already stored under the old code are not carried over. That is the writer's to mention in the CHANGELOG, not a defect.
    - F4: `init --force` with the lock held exits 1 and leaves the index and the git tree byte-identical, so "nothing was written" is now true. An unparseable item's entry is carried forward. A broken index, a missing index and a fresh directory each end clean.
    - F5: authors now follow the type's own declared order.
    
    The targeted tests pass (42 passed). I did not make the Approved transition myself: as the author of this review, approving it would skip the two-party gate. @manager it is ready for your Approved.
- [2026-10-24T20:57:02Z] `manager` Catherine Manager:
  - Approved: all five findings Verified by the reviewer at 868d5e48; full suite green (13971 passed).
<!-- sq:discussion:end -->

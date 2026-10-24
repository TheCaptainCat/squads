---
id: TASK-1107
sequence_id: 1107
type: task
title: Document import events, role splat-refs and the review question
status: Ready
parent: FEAT-1101
author: tech-lead
assignee: tech-writer
refs:
- REV-1099:addresses
- TASK-1105:depends-on
- TASK-1103:depends-on
description: Doc-only fixes F1, F12 and F11 from REV-1099.
subentities:
- local_id: ST1
  title: Document every sq import op with its fields and an example line
  status: Todo
  story: US7
- local_id: ST2
  title: Guard the import op reference against the event model
  status: Todo
  assignee: python-dev
  story: US7
- local_id: ST3
  title: Show splat-refs on role list fields in the override docs
  status: Todo
  story: US7
- local_id: ST4
  title: Add an interview question on when to open a review
  status: Todo
  story: US8
- local_id: ST5
  title: Write the 0.17.0 Documentation note for the import, override and interview
    docs
  status: Todo
  story: US7
created_at: '2026-10-24T10:04:07Z'
updated_at: '2026-10-24T19:46:26Z'
---
<!-- sq:body -->
## Goal

The doc-only fixes from REV-1099: F1 (the `sq import` event reference), F12 (splat-refs on role list fields) and F11 (an interview question on when to open a review). Plus one guard test so the import reference cannot drift from the event model.

## Approach

- **F1** (`docs/adoption.md`, section "3. Bulk import from JSONL"). Add a reference table of every op in `src/squads/_services/_import_model.py`: `create`, `status`, `body`, `comment`, `ref`, `add-sub`, `add-story`, `add-subtask`, `add-finding`, `sub-status`, `sub-body`, `assign`, `update`. List required and optional fields per op, read from the pydantic models rather than guessed (for example `target` rather than `id`, `message`, `force`), and give one JSONL example line per op. Verify every example by importing it into a scratch squad outside the repo tree (`uv run --project <repo> sq -C <scratch> import -`). The review counted fourteen ops, and the model's `Literal` ops are the authority. Note in the table what this release changes: `create` stores a declared field's default when `fields` omits it (TASK-1103), and `sub-status` takes `deferred_to` (TASK-1105). Both land first (depends-on).
- **F1 guard** (ST2, python-dev). A `tests/meta` test reads every `op` `Literal` from the event models and asserts each appears as a row in the `docs/adoption.md` table, and that each field the model declares appears in its row. Prove it against a known positive: remove a row and watch it fail.
- **F12** (`docs/overrides.md`: the "Role overrides merge by field" paragraph at about line 151, and the section "The override grammar: shadow, append, and drop"). State that the same grammar applies to role overrides. Add a `responsibilities = ["$(*self)", "…"]` example to the role section, and a sentence in the grammar section that the deep merge, plain-array and splat-ref rules hold for `roles.toml` and `roles/<slug>.toml` as for `workflow.toml`. Verify the example in a scratch squad.
- **F11** (`docs/agents.md`, "What is worth asking"). Add a question, under 3 (Quality bar) or 6 (Structure and records lifecycle), on how the repository decides when to open a review item rather than comment a verdict on the work item. Add no bundled rule and no recommended answer (op-pierre ruling on F11). Keep the count in "Seven areas" right if the question becomes its own area.
- **CHANGELOG**: add a Documentation note covering these three. The entries for TASK-1103 to TASK-1106 come from their own writer subtasks.

## Tests

ST2 is the only code: a `tests/meta` guard with two rows, every `op` literal of the event models has a row in the `docs/adoption.md` table, and every field each model declares (including the shared base fields) appears in its row. Prove each row red by removing a table row and then one field. For the docs, the scratch-squad import and override runs above are the verification; state in the handback which examples were run.

## CHANGELOG substance (0.17.0)

- Documentation: `docs/adoption.md` lists every `sq import` op with its fields and an example.
- Documentation: `docs/overrides.md` shows splat-refs on role list fields.
- Documentation: `docs/agents.md`'s interview prompts ask how the team decides when to open a review.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1107 add-subtask "<title>"`; track with `sq task 1107 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Document every sq import op with its fields and an example line

<!-- sq:subtask:ST1:body -->
Closes REV-1099 F1. A reference table in `docs/adoption.md` section 3 lists every op in `_import_model.py` with its required and optional fields read from the models, plus one JSONL example each, each one run through `sq import` in a scratch squad. Mark what this release changes: `create` stores a declared default when `fields` omits it, and `sub-status` takes `deferred_to`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Guard the import op reference against the event model

<!-- sq:subtask:ST2:body -->
Keeps REV-1099 F1 from regressing. A `tests/meta` test asserts every `op` literal and every declared field of the import event models appears in the `docs/adoption.md` table. Falsify it by removing a row.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Show splat-refs on role list fields in the override docs

<!-- sq:subtask:ST3:body -->
Closes REV-1099 F12. In `docs/overrides.md`, state that the shadow/append/drop grammar applies to role overrides, add a `responsibilities = ["$(*self)", "…"]` example to the role section, and verify it in a scratch squad.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Add an interview question on when to open a review

<!-- sq:subtask:ST4:body -->
Closes REV-1099 F11, per the op-pierre ruling: in `docs/agents.md` "What is worth asking", ask how the repository decides when to open a review item rather than comment a verdict on the work item. No bundled rule and no recommended answer.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Write the 0.17.0 Documentation note for the import, override and interview docs

<!-- sq:subtask:ST5:body -->
Covers REV-1099 F1, F12 and F11 in the CHANGELOG: one Documentation note per doc change, from this task's CHANGELOG substance.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:46:26Z] `tech-lead` Olivia Lead:
  - Realigned: the create op already takes fields, so the doc note is about the stored default; added depends-on TASK-1103 and TASK-1105, whose fields it documents. Moved to Ready.
<!-- sq:discussion:end -->

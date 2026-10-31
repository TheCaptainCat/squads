---
id: TASK-1138
sequence_id: 1138
type: task
title: Fail cleanly on damaged overrides and report init truthfully
status: Done
author: tech-lead
assignee: python-dev
refs:
- MILE-1051:targets
- BUG-1134:fixes
- BUG-1084:fixes
- BUG-1039:fixes
- BUG-1041:fixes
- TASK-1125
description: Non-UTF-8/unreadable override errors, lint collects all [selected] errors,
  AGENTS.md false warning, padded reflog ids
subentities:
- local_id: ST1
  title: Report unreadable and non-UTF-8 overrides as clean errors
  status: Done
- local_id: ST2
  title: Collect every [selected] error in workflow lint
  status: Done
- local_id: ST3
  title: Warn about AGENTS.md content only when squads did not write it
  status: Done
- local_id: ST4
  title: Log formatted ids for seeded skills in the reflog
  status: Done
created_at: '2026-10-25T05:39:20Z'
updated_at: '2026-10-25T19:49:58Z'
priority: medium
---
<!-- sq:body -->
## Goal

Override documents fail cleanly and completely, and `sq init` reports only what is true. A damaged override is a clean error, never a traceback; `sq workflow lint` lists every error in one run; a fresh init warns of nothing it wrote itself and logs ids in their formatted form. Four defects in the override load path and the init path.

## Read on release/0.17 HEAD (2026-10-25)

- `_specload.py` `OverrideMessages.not_utf8` is set only for the role catalog (`_roles/_loader.py`); the workflow and playbook descriptors keep `None`, so `UnicodeDecodeError` propagates. `_roles_catalog_override_shadows_bundled` (`_overrides/_service.py`) reads `roles.toml` itself and catches `TOMLDecodeError` and `OSError` but not `UnicodeDecodeError`; the `sq check` path reaches it.
- `sq workflow lint` (`_workflow/_loader.py`) returns after its retired-grammar phase, which holds `_selected_squad_violations`, so a `[selected] squad` error hides the merge phase. In `_specmerge.py` `apply_selected` returns on `_validate_selected_shape` violations before `_selected_entry_violations` runs.
- `ensure_scaffold` (`_backends/_agents_md/_backend.py`) writes a stub AGENTS.md; `inject` (`_backends/_managed_region.py`) then sees non-empty text with no markers and reports pre-existing hand-written content.
- The two skill-seeding loops in `_services/_maintenance.py` log `store.log("create", item_id, ...)` with the padded `allocate_id` string; every other create logs `item.id`.

## Ordering

ST1 changes `_specload.py`, the load path TASK-1125 step 2 rebuilds ("documents resolved together"). Run ST1 after TASK-1125, on the loader it leaves. ST2 to ST4 do not touch the composition root and can run first.

## Gates

pyright, ruff check, ruff format --check, `tests/meta`, `tests/integration`, `tests/cli`; rows go into `tests/unit/test_spec_override_read_errors.py` for ST1. Falsify each new row.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1138 add-subtask "<title>"`; track with `sq task 1138 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Report unreadable and non-UTF-8 overrides as clean errors

<!-- sq:subtask:ST1:body -->
**Defect (BUG-1134).** An unreadable or non-UTF-8 override file ends in a Rich traceback in three places: `sq check` with `roles.toml` at mode 0 (`PermissionError`) or non-UTF-8 (`UnicodeDecodeError`), from the shadow probe in `_overrides/_service.py`; `sq workflow lint` with a non-UTF-8 `workflow.toml`; every command with a non-UTF-8 `playbook.toml`. Other commands quote the raw codec text for the workflow override.

**Expected.** Each is one `error:` line, exit 1, in the wording family of the role catalog's "is not valid UTF-8" and "Cannot read" messages, naming the file. The workflow and playbook descriptors get a `not_utf8` message; the shadow and stamp probes in `_overrides/_service.py` fail soft on `OSError` and `UnicodeDecodeError`, since the loader's refusal already reports the file.

**Ordering.** After TASK-1125 (its step 2 rebuilds the load path in `_specload.py`).

**Test: unreadable or undecodable override** (one table)

| Document | Damage | Command | Expected |
|---|---|---|---|
| `roles.toml` | mode 0 | `sq check` | error line, exit 1, no traceback |
| `roles.toml` | `\xff\xfe` | `sq check` | not-UTF-8 error, exit 1 |
| `workflow.toml` | `\xff\xfe` | `sq workflow lint` | not-UTF-8 error, exit 1 |
| `workflow.toml` | `\xff\xfe` | `sq list` | not-UTF-8 error naming the file, no codec dump |
| `playbook.toml` | `\xff\xfe` | `sq list` | not-UTF-8 error, exit 1 |
| `playbook.toml` | mode 0 | `sq list` | cannot-read error, exit 1 |
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-25T18:11:32Z] `python-dev` Elias Python:
  - Workflow and playbook descriptors carry a not_utf8 message (OverrideMessages.not_utf8 is now required, no raw re-raise); roles message drops the codec text. The shadow, stamp and override-list probes fail soft on OSError and UnicodeDecodeError, and sq check reports the loader refusal. Tests: tests/unit/test_spec_override_read_errors.py (non-UTF-8 per document), tests/cli/test_a_damaged_override_is_a_clean_error_cli.py (document x damage x command), and not-utf8 and unreadable shapes in the once-per-invocation load table. Falsified: 33 of the new rows fail without the source change. No reds.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Collect every [selected] error in workflow lint

<!-- sq:subtask:ST2:body -->
**Defect (BUG-1084).** `sq workflow lint` says it collects every error, but in `[selected]` the first refused or unknown section hides the rest: `squad = [...]` hides an unknown section, and an unknown section hides an unknown entry under `items`.

**Expected.** One run lists every `[selected]` error together with the merge-phase errors, as it already does for two unknown top-level keys. Loading for any other command still refuses on the first error set, unchanged.

**Test: [selected] errors collected together** (one table)

| `[selected]` content | Expected errors |
|---|---|
| `squad = ["x"]`, `bogus = ["y"]` | 2: squad refusal, unknown section |
| `bogus = ["y"]`, `squad = ["x"]` | 2, same set |
| `bogus = ["y"]`, `items = ["nonesuch"]` | 2: unknown section, unknown items key |
| `squad = ["x"]`, `items = ["nonesuch"]` | 2 |
| `items = ["nonesuch"]` (control) | 1 |
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-25T18:11:33Z] `python-dev` Elias Python:
  - apply_selected now collects the shape, section and entry violations together over the well-formed sections; lint lists the squad refusal beside the merge-phase errors (selected.squad is stripped before the merge so it is not reported twice). Loading still raises the first. Tests: tests/unit/test_workflow_lint_selected_errors.py (10 shapes, lint and load). Falsified: 3 rows fail with the engine change reverted. No reds.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Warn about AGENTS.md content only when squads did not write it

<!-- sq:subtask:ST3:body -->
**Defect (BUG-1039).** `sq init --backend agents_md` in a directory with no AGENTS.md warns that AGENTS.md "had pre-existing hand-written content". The content is the stub `ensure_scaffold` wrote a moment earlier. The false warning trains adopters to ignore the real one.

**Expected.** A fresh init warns of nothing. The warning fires only for content that was in the file before squads wrote it. Simplest fix: the scaffold creates nothing and `inject` writes the file with its `missing_header`.

**Test: AGENTS.md pre-existing-content warning** (one table)

| Before init | Expected |
|---|---|
| no AGENTS.md | no warning; file holds the header and the managed section |
| AGENTS.md with hand-written text, no markers | warning (unchanged) |
| AGENTS.md with markers | no warning, section replaced |
| AGENTS.md whitespace only | no warning |
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-25T18:11:35Z] `python-dev` Elias Python:
  - AGENTS.md ensure_scaffold writes nothing (reports the file only when it exists); write_managed creates it with the header. Tests: table in tests/integration/test_backend_scaffold_warnings.py (absent, hand-written, managed, whitespace); the scaffold test in test_agents_md_backend.py updated. Falsified: the absent row fails on the old scaffold. No reds.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Log formatted ids for seeded skills in the reflog

<!-- sq:subtask:ST4:body -->
**Defect (BUG-1041).** After `sq init`, the reflog's `create` entries for the seeded skills carry the padded id (`SKILL-000009`); `sq skill add`, roles and work items log the formatted id (`SKILL-25`), as the reflog schema in `docs/stability.md` promises. A consumer filtering on `target == "SKILL-9"` misses the creation.

**Expected.** Every reflog `target` is the formatted id. Both seeding loops in `_maintenance.py` (`seed_bundled_skills`, `seed_custom_skills`) log `item.id`.

**Test: reflog targets after init** (one table)

| Run | Expected |
|---|---|
| `sq init --roles all` | every `create` target equals its item's formatted id |
| `sq init` with a workflow override declaring a custom type (its `sq-<type>` skill is seeded by `seed_custom_skills`) | same, for the custom skill too |
| `sq skill add x` (control) | formatted id |
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-25T18:11:36Z] `python-dev` Elias Python:
  - Both seeding loops log item.id. Test: tests/integration/test_reflog_targets_after_init.py (bundled, custom type, skill add control). Falsified: the init rows fail with the old padded id. No reds.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T05:40:51Z] `tech-lead` Olivia Lead:
  - Drafted from the MILE-1051 bug triage; each bug re-read against release/0.17 HEAD, subtask bodies carry defect, expected behaviour and the falsifying table. Ordering and composition-root dependencies are in the body and on MILE-1051. Promote to Ready at dispatch.
- [2026-10-25T19:49:57Z] `manager` Catherine Manager:
  - Done: REV-1145 Approved; delivered in 131d7420, 06de9a7d, e954687b, 58a37ca5. BUG-1134, 1084, 1039, 1041 ready for QA verification.
<!-- sq:discussion:end -->

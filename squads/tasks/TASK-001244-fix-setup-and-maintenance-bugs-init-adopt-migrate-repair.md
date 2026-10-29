---
id: TASK-1244
sequence_id: 1244
type: task
title: 'Fix setup and maintenance bugs: init, adopt, migrate, repair'
status: Ready
author: tech-lead
priority: high
refs:
- BUG-1187:fixes
- BUG-1188:fixes
- BUG-1189:fixes
- BUG-1190:fixes
- BUG-1191:fixes
- MILE-1241:targets
description: Refuse bad backend, squad-dir, chlog range and repad width before writing;
  repair refuses a shared number
subentities:
- local_id: ST1
  title: Refuse an unknown backend before init or adopt writes
  status: Todo
- local_id: ST2
  title: Refuse an absolute, empty or escaping --squad-dir
  status: Todo
- local_id: ST3
  title: Refuse a non-version or reversed migrate chlog range
  status: Todo
- local_id: ST4
  title: Bound migrate repad WIDTH before renaming
  status: Todo
- local_id: ST5
  title: Make repair refuse two files sharing one number
  status: Todo
created_at: '2026-10-29T16:27:28Z'
updated_at: '2026-10-29T16:42:54Z'
---
<!-- sq:body -->
## Goal

Squad setup and corpus maintenance refuse bad input before they write anything, and never report a clean result while hiding a file. Five bugs, one subtask each: `init`/`adopt` (BUG-1187, BUG-1188), `migrate chlog` and `migrate repad` (BUG-1189, BUG-1190), and `repair` (BUG-1191).

## Files

- `src/squads/_services/_service.py`: `init` and `adopt`, where the backend names and `--squad-dir` are validated before the first write.
- `src/squads/_backends/_registry.py`: the known backend names, read for that validation (no change expected).
- `src/squads/_cli/_migrate.py`: `_parse_span` (chlog) and `migrate_repad`.
- `src/squads/_services/_maintenance.py`: `repad`/`_repad_held` (the width bound) and `repair`/`_repair_held` (the shared-number refusal).
- `src/squads/_services/_duplicate_ids.py`: `shared_number_groups`, reused by `repair`.
- Tests: `tests/cli/test_init.py`, `tests/cli/test_adopt.py`, `tests/cli/test_migrate.py`, `tests/cli/test_repair.py`.

Keep the `init`/`adopt` validation in the service layer, not in `src/squads/_cli/_main.py`: that module belongs to the listing-options task and editing it here would collide with it. If `docs/faq.md` ("Handling ID collisions") needs a line for the distinct-ids-same-number case, report it to the tech writer rather than editing it.

## Tests

CLI surface tests per ADR-1172, one per behaviour, declared with `@pytest.mark.covers(...)`, observed through `sq` itself. Expected new tests: 6 (two for BUG-1188: escaping/absolute, empty). Each test is falsified by hand before handoff: revert the fix, watch the test go red, restore it, watch it go green, and report both. BUG-1191 is a durability defect, so its falsification is mandatory.

## Changelog

Every bug here changes adopter-visible behaviour (a refusal where there was a write or a clean exit). Report each change and why in the handoff so the tech writer adds a line under the 0.18.1 section of `CHANGELOG.md`; do not edit `CHANGELOG.md` yourself.

## Gates

`uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, the four test modules above plus `tests/meta`, and `sq check` clean for this task.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1244 add-subtask "<title>"`; track with `sq task 1244 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Refuse an unknown backend before init or adopt writes

<!-- sq:subtask:ST1:body -->
Fixes BUG-1187.

**Expected.** `init` and `adopt` check every `--backend` name against the known backends before writing anything. A refused call exits 1 with the existing `unknown backend 'X' (available: ...)` message and leaves the directory exactly as it was, so the corrected command then succeeds. `adopt` never stores an unknown backend in `.squads.toml`.

**Test.** In `tests/cli/test_init.py` and `tests/cli/test_adopt.py` (`@pytest.mark.covers("init", "--backend")`, `@pytest.mark.covers("adopt", "--backend")`): run with `--backend bogus`, assert exit 1 and that no `.squads.toml`, `.gitignore` or squad folder was created, then run with a valid backend and assert exit 0. One case per command.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Refuse an absolute, empty or escaping --squad-dir

<!-- sq:subtask:ST2:body -->
Fixes BUG-1188.

**Expected.** `init --squad-dir` is validated before any write: an absolute path, an empty value and a path that resolves outside the project root are each refused with a one-line `SquadsError` (exit 1) and leave nothing behind. A relative folder inside the project, nested or not, keeps working.

**Test.** In `tests/cli/test_init.py` (`@pytest.mark.covers("init", "--squad-dir")`): one parametrised case over `/abs`, `../up` and `''` asserting exit 1, a one-line error with no traceback, and no `.squads.toml` written; one case asserting a nested relative folder still initialises.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Refuse a non-version or reversed migrate chlog range

<!-- sq:subtask:ST3:body -->
Fixes BUG-1189.

**Expected.** `migrate chlog` refuses a bound that is not a version and a range whose start is not below its end, with exit 1 and a message naming the `vFROM..vTO` form. A valid ascending range prints its steps as today.

**Test.** In `tests/cli/test_migrate.py` (`@pytest.mark.covers("migrate chlog")`): one parametrised case over `a..b` and `v0.17.0..v0.1.0` asserting exit 1 and the expected-form message.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Bound migrate repad WIDTH before renaming

<!-- sq:subtask:ST4:body -->
Fixes BUG-1190.

**Expected.** `migrate repad WIDTH` refuses a width above a fixed upper bound with a `SquadsError` (exit 1) before renaming anything. Pick the bound from the filename limit (255 bytes, less the prefix, separators, slug room and `.md`) or a smaller round number, and state it in the command's help and the error. Since a repad cannot be undone, the refusal happens before the first rename.

**Test.** In `tests/cli/test_migrate.py` (`@pytest.mark.covers("migrate repad")`): repad above the bound, assert exit 1, the bound in the message, and every item file name unchanged.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Make repair refuse two files sharing one number

<!-- sq:subtask:ST5:body -->
Fixes BUG-1191.

**Expected.** Plain `sq repair` on a corpus where two files carry the same number under different ids reports the collision, naming both files and the `sq repair --renumber` remedy, and exits 1 without committing an index that drops one of them. This matches what the FAQ ("Handling ID collisions") promises for the same-id case. `repair --renumber` keeps resolving it as today.

**Test.** In `tests/cli/test_repair.py` (`@pytest.mark.covers("repair")`): copy an item's file under another type's folder with a distinct id and the same number, run `sq repair`, assert exit 1, both file names in the output, and that `sq list -a` still lists both items afterwards (the previous index was not replaced). Falsification is mandatory: this is a data-visibility defect.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

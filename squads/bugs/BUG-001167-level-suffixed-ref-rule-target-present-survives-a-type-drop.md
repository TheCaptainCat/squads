---
id: BUG-1167
sequence_id: 1167
type: bug
title: Level-suffixed ref_rule_target_present survives a type drop
status: Verified
author: qa
refs:
- MILE-1051:targets
created_at: '2026-10-26T13:45:16Z'
updated_at: '2026-10-26T14:20:27Z'
severity: high
---
<!-- sq:body -->
## Summary
`_strip_ref_rule_targets_of_dropped_types` (`src/squads/_workflow/_loader.py`, around line 828; called at lines 360 and 1437) strips `ref_rule_target_present:<T>` only when `v.partition(":")[2]` equals a dropped type. A level-suffixed entry such as `ref_rule_target_present:contract@warn` yields `contract@warn`, so it is never stripped, and `check_ref_rule_targets` refuses the leftover name. The helper exists to prevent exactly that failure. Found in review REV-1166; part of MILE-1051.

## Steps (driven on a scratch squad with the dev build)
1. `sq init --backend none --default-names` in an empty dir.
2. Write `squads/.overrides/workflow.toml`:
```toml
[selected]
items = ["epic","feature","task","bug","decision","milestone","review","guide","skill","role","operator"]

[items.feature]
validators = ["ref_rule_target_present:contract@warn"]
```
(`contract` is dropped via `[selected].items`.)
3. Run `sq workflow lint`, `sq check`, `sq list`.
4. Repeat with `validators = ["ref_rule_target_present:contract"]` (no suffix).

## Expected
Both forms drop the entry silently along with the dropped type; the squad loads.

## Actual
- Unsuffixed: entry stripped. `sq list` exit 0. lint/check report only an unrelated missing override-base stamp error (scratch override was hand-written).
- `@warn`: `sq list` exits 1 and every command refuses to run: "this squad's workflow override could not be loaded ... item 'feature': validators entry 'ref_rule_target_present:contract@warn' names target type 'contract', which is not a declared item type - 'contract' was dropped from a [selected] list (selected.items), not left undeclared". `sq workflow lint` exit 1 (2 errors), `sq check` exit 3. The squad is bricked until the adopter edits the override.

## Fix direction
Parse the entry with `parse_validator_entry` (`_workflow/_validator_names.py`, returns name, param, level) and compare the param, rather than partitioning on ":". Add a test with a level-suffixed entry, and check other `@level` forms.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T14:07:12Z] `python-dev` Elias Python:
  - Root cause: _strip_ref_rule_targets_of_dropped_types compared v.partition(":")[2], so an @level suffix stayed in the compared text and the entry survived the drop. Fix: it now reads the name and param through parse_validator_entry. No other hand-parsing of validator entries exists in _workflow, _services or _overrides. Tests: a table over entry shapes plus a CLI row; both fail with the old comparison.
- [2026-10-26T14:20:26Z] `qa` Mara Tester:
  - Verified on release/0.17 at 129718dc, dev build (.venv/bin/sq -C <scratch>), scratch squad (sq init --backend none --default-names), override dropping contract via [selected].items, feature validators = one entry.
    - contract@warn, contract@error, contract (unsuffixed): sq list exit 0; sq workflow lint exit 2 and sq check exit 3, both only the unrelated missing override-base stamp (hand-written override). The entry is stripped with the dropped type; the squad loads.
    - Kept type (task@error, task@warn): sq list exit 1, refused with "feature declares no ref_rules entry with that target". Correct: the target type is kept, so the entry is validated, not stripped.
    Scratch deleted.
<!-- sq:discussion:end -->

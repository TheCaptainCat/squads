---
id: BUG-988
sequence_id: 988
type: bug
title: migrate up refuses old-schema squad with a valid custom type
status: Verified
author: qa
refs:
- MILE-934:targets
- ADR-955
- TASK-954
created_at: '2026-10-09T20:19:46Z'
updated_at: '2026-10-11T21:15:44Z'
priority: high
---
<!-- sq:body -->
## Reproduction

Scratch squads built with the current package, then hand-stamped (not real aged corpora). Dev build at HEAD d07b0e50.

```
sq init --default-names --backend claude_code
mkdir squads/.overrides
printf '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "guide"\n' > squads/.overrides/workflow.toml
sq create incident "An incident" --author architect      # INC-000021-an-incident.md
sed -i 's/^schema_version = .*/schema_version = "0.11"/' .squads.toml
sq migrate up
```

Observed (exit 1, `.squads.toml` stays at 0.11):

```
error: item INC-21 has type 'incident', which the active spec no longer declares; migrate or re-type this item before it can load again (or run `sq repair` if the index itself is merely stale)
```

Following the message: `sq repair` is refused by the schema gate ("this squad is at schema v0.11; squads 0.15.0 expects v0.15. Run sq migrate up"), and `sq migrate up` gives the same refusal again.

## Bounds driven

- Stamped 0.1, 0.8, 0.9, 0.10, 0.11, 0.12, 0.13: refused, identical message.
- Stamped 0.14: migrates, exit 0.
- Same squad with the override but no `incident` item, stamped 0.11: migrates, exit 0.
- No override, stamped 0.11: migrates, exit 0.
- So the refusal needs an old stamp (below 0.14), a valid override that declares a type, and an item of that type.

## Expected versus actual

Expected: a squad whose override validly declares the type migrates, as the 0.14 and no-item cases do.
Actual: `migrate up` refuses. The message says the active spec no longer declares the type, but the override does declare it (the same squad loads that item fine once stamped 0.14). The remedies it names are circular: `migrate up` is what refused, `repair` is gated behind `migrate up`. Re-typing the item was not tried. An operator is left unable to upgrade the squad.

## Not covered

The architect's reading of the cause (runners opening the index without the active spec) was not tested or confirmed. Not driven: a real aged corpus from `tests/fixtures/corpus` with a custom type added, an override that renames or re-prefixes a bundled type, or whether the refused run left any file changed beyond the stamp (the stamp was unchanged).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-11T21:15:38Z] `qa` Mara Tester:
  - Verified the working tree before commit (HEAD 1a96e516 plus the uncommitted TASK-954 ST6 change), driving the dev build `.venv/bin/sq` in scratch squads; exit codes read from the bare command.
    
    - Original reproduction (override declaring `incident`, one INC item, `migrate up`): stamped 0.1, 0.8, 0.9, 0.10, 0.11, 0.12, 0.13 each exit 0, stamp 0.15, `incident 21 show` exit 0, `check` exit 0, `repair` exit 0 and a second repair changes no file (reflog excluded).
    - Controls as before: stamped 0.14 migrates; no override, 0.11 migrates; override with no incident item, 0.11 migrates.
    - Real fixtures from `tests/fixtures/corpus` (v0_3, v0_4, v0_5, v0_7, v0_8, v0_10, v0_11, v0_14) with the override and one hand-added INC item in each era's file shape (padded id with sequence_id, unpadded id from 0.7): all exit 0, item loads, check exit 0, repair stable.
    - Vocabulary only the override declares (custom item status, custom sub-entity status on a subtask, custom badge code on a collection field), item carrying all three, stamped 0.11 and 0.8: exit 0, values preserved, check and repair clean. The same squad on the released 0.15.0 tool is refused (exit 1), so the probe discriminates.
    - Re-prefix and re-label: re-prefixing `milestone` (no items) and `contract` (no items), and a task label and alias override, all migrate cleanly with check exit 0.
    - Legitimate refusals leave every file byte-identical, stamp included (exit 1): re-prefix `bug` while a bug exists, re-folder `bug`, an override dropping `task` while a task exists, an override dropping the `incident` type while an incident exists, and an override that is not valid TOML.
    
    Not covered or not attributable to this fix: fixtures v0_1 and v0_2 with a hand-added custom item exit 1 after stamping 0.15, because the item in that shape has no `sequence_id` and nothing in those eras could have carried a custom type; the released tool does the same, so it is not a regression. A pre-0.7 fixture with any workflow override (even a label-only one) is refused at the start on both builds with the UNRESOLVED-4 prefix message; that is the pre-0.7 refusal tracked on TASK-954. Not driven: a custom type whose items use a custom ref kind, the VS Code client, Windows.
    
    Moving InProgress -> Fixed -> Verified (the legal path in the bug lifecycle).
<!-- sq:discussion:end -->

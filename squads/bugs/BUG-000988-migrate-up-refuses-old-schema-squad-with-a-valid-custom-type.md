---
id: BUG-988
sequence_id: 988
type: bug
title: migrate up refuses old-schema squad with a valid custom type
status: Open
author: qa
priority: high
refs:
- MILE-934:targets
- ADR-955
- TASK-954
created_at: '2026-10-09T20:19:46Z'
updated_at: '2026-10-09T20:20:11Z'
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
<!-- sq:discussion:end -->

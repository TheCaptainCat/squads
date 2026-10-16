---
id: BUG-1084
sequence_id: 1084
type: bug
title: workflow lint hides later [selected] errors behind the first
status: Open
parent: MILE-1051
author: qa
priority: low
refs:
- REV-1083
created_at: '2026-10-16T22:04:16Z'
updated_at: '2026-10-16T22:04:16Z'
---
<!-- sq:body -->
`sq workflow lint` says it collects ALL errors, but inside the `[selected]` table the first error found hides the others in the same file. Seen on release/0.16 HEAD (clean `git archive` export, scratch squad); the behaviour is older than 0.16, the `[selected]` table having shipped long before.

## Repro

In a fresh squad, write `squads/.overrides/workflow.toml` and run `sq workflow lint`.

1. A squad refusal plus an unknown section:

```toml
[selected]
squad = ["x"]
bogus = ["y"]
```

2. An unknown section plus an unknown item key:

```toml
[selected]
bogus = ["y"]
items = ["nonesuch"]
```

## Expected

Every error is listed in one run, as with two unknown top-level keys or two unknown keys in different `[selected]` sections, which do report together (2 error(s)).

## Actual

Case 1 reports only the first error:

```
selected.squad  the `[squad]` table has no entries to drop - its one key is a list
1 error(s) - fix the errors above then re-run `sq workflow lint`.
```

`selected.bogus` appears only after `squad` is removed, in either key order.

Case 2 reports only the unknown section:

```
selected.bogus  unknown [selected] section 'bogus'
1 error(s) - fix the errors above then re-run `sq workflow lint`.
```

`selected.items.nonesuch` is hidden. Likewise a top-level `[bogus_a]` does not hide `selected.items.nonesuch` (both shown, 2 errors), so the stop is per-section-name validation inside `[selected]`: an unknown or refused section name short-circuits the per-key checks of the other sections.

## Notes

Found while reviewing REV-1083 F5. The `squad` entry in the accepted-sections list shown by the unknown-section hint is a separate matter handled by that review's fix.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

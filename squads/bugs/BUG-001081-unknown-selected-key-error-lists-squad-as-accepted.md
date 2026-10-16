---
id: BUG-1081
sequence_id: 1081
type: bug
title: Unknown [selected] key error lists squad as accepted
status: Verified
author: qa
priority: low
refs:
- MILE-934:targets
created_at: '2026-10-16T21:17:28Z'
updated_at: '2026-10-16T22:48:13Z'
---
<!-- sq:body -->
## Steps
1. In a fresh squad, write `squads/.overrides/workflow.toml` containing `[selected]` and `bogus = ["x"]`; run `sq list`.
2. Replace it with `[selected]` and `squad = ["x"]`; run `sq list`.

## Expected
The list of accepted `[selected]` sections names only sections that `[selected]` accepts, so `squad` is not offered as a valid key.

## Actual
Step 1 lists `squad` among the accepted sections, but step 2 refuses it.

Step 1 message:
`selected.bogus: unknown [selected] section 'bogus' — use one of the accepted [selected] sections in v0.16.0: ['collections', 'items', 'lifecycles', 'ref_kinds', 'roles', 'squad', 'statuses', 'subentity_kinds', 'views']`

Step 2 message:
`selected.squad: the `[squad]` table has no entries to drop — its one key is a list — replace the list in `[squad]` (`validators = [...]`) instead.`

Reproduced on release/0.16 HEAD (clean git archive export, scratch squad). The advice is self-contradictory: an author who follows the first message hits the second.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T21:50:24Z] Elias Python:
  - Fixed in c520f5a3: the [selected] menu now excludes squad (WORKFLOW_SELECTABLE_SECTIONS); the squad refusal is unchanged. Test row added; reverting the constant turns it red.
- [2026-10-16T22:48:13Z] Catherine Manager:
  - Verified on REV-1083; merged at e56f7a18.
<!-- sq:discussion:end -->

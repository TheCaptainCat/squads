---
id: REV-1168
sequence_id: 1168
type: review
title: Review of the BUG-1167 level-suffixed strip fix
status: Approved
author: reviewer
refs:
- BUG-1167
description: Parser-based strip of ref_rule_target_present entries for dropped types
created_at: '2026-10-26T14:18:59Z'
updated_at: '2026-10-26T14:19:08Z'
---
<!-- sq:body -->
Review of commit 129718dc (release/0.17): `_strip_ref_rule_targets_of_dropped_types` in `src/squads/_workflow/_loader.py` now reads each `validators` entry through `parse_validator_entry` and compares the bare name and the param, instead of `v.partition(":")[2]`.

## Scope checked
- The diff, the parser grammar (`name`, `name:param`, `name@level`, `name:param@level`) and both call sites (`load_workflow_spec`, `lint_workflow_spec`). The strip runs on the merged mapping after splat resolution and `[selected]` deselect, in both paths.
- Where an entry can be declared: only `[items.<type>].validators` takes per-item validators. `[squad] validators` takes squad-global members only (none takes a type param), and sub-entity kinds declare no validators.
- Type-param validators: `ref_rule_target_present` is the only member whose param is an item type (`PARAMETERIZED_VALIDATOR_NAMES` holds three others, with integer or regex params). A grep over `src/squads` finds no other hand-parsing of validator entries; the remaining `partition(":")` sites split refs, not validators.
- `ref_rule_target_typed` after a drop strips its only targeted rule: refused at Plane-1 by design, with a message naming the `[selected]` drop. Pre-existing and intended, so not part of this fix.

## Driven on a scratch squad (dev build)
Each override was run through `sq list`, `sq workflow lint` and `sq check`, with `contract` dropped through `[selected].items` unless noted:
- `:contract`, `:contract@warn`, `:contract@error`: all exit 0, entry stripped.
- `:contract@warn` plus `:milestone@warn` (rules to both): contract entry stripped, milestone kept, exit 0.
- Entry on `epic` beside `$(*items.epic.validators)` splat: exit 0.
- Rename (drop `contract`, add `agreement`, entries for both): the contract entry was stripped and the agreement entry kept (checked by loading the spec).
- Re-prefix (`[items.contract] prefix = "CTR"`, no drop): entry kept, exit 0.
- Whitespace (`contract @warn`) and name casing (`Ref_Rule_Target_Present`): refused with or without the drop, the same as without the fix, since the parser does not normalise them.
- `@WARN` with the drop: stripped silently. Without the drop it is refused as an unknown level. The entry goes away with its type either way, so this is harmless.

## Tests
- In a scratch copy with the old comparison restored, three of the new cases fail: the `@warn` and `@error` table rows and the CLI test.
- On the fixed tree: the new tests plus `tests/meta` give 536 passed. ruff and pyright are clean on the touched files.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1168 add-finding "…" --severity medium`; track with `sq review 1168 finding <n> update --status <Status>`._

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T14:19:06Z] `reviewer` Paul Reviewer:
  - Approved, no findings. Every grammar-allowed level suffix, a splat-composed list, a rename and a re-prefix were driven on a scratch squad and behave correctly. ref_rule_target_present is the only validator whose param is a type, and the new tests fail against the old comparison. Nit, not a finding: parse_validator_entry(v) runs twice per entry in the comprehension.
<!-- sq:discussion:end -->

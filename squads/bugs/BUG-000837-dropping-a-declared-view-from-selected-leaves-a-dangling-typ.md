---
id: BUG-837
sequence_id: 837
type: bug
title: Dropping a declared view from [selected] leaves a dangling type attachment
status: Verified
author: qa
priority: medium
refs:
- TASK-833
- MILE-836:targets
created_at: '2026-08-26T16:35:37Z'
updated_at: '2026-09-01T08:05:25Z'
---
<!-- sq:body -->
## What happens

Dropping a *view* from `[selected].views` while an item type's own `items.<type>.views` list
still names it leaves a dangling attachment. `sq workflow lint` reports the spec clean at
exit 0. The first command built on that type then fails at exit 1.

## Repro (driven in a scratch squad)

```
sq override scaffold workflow
# append to squads/.overrides/workflow.toml:
[selected]
views = []
```

```
$ sq workflow lint
workflow spec OK — no errors or warnings.
$ echo $?
0

$ sq milestone 9 show
...
error: no declared view 'milestone_rollup'; see `sq workflow views` for the declared set
$ echo $?
1
```

Adding `[items.milestone] views = []` alongside clears the error — the type's own `views` list
has to be dropped too, in a second, unrelated-looking key.

## Expected vs actual

- Expected: a spec that `sq workflow lint` calls OK should not make an ordinary command
  (`sq <type> <n> show`) crash for every item of that type.
- Actual: lint is silent about the dangling attachment; the failure only surfaces at
  `sq <type> <n> show` time, once per item, with an error that names the orphaned view but
  gives no hint that `items.<type>.views` is the other end of it.

## Root cause, as read in the code

`ItemSpec.views` (`src/squads/_workflow/_models.py`, the field around line 613) is the *only*
attached-by-name list on `ItemSpec` that `WorkflowSpec._validate` does not referentially check.
Its own docstring says so explicitly: "Not referentially checked at spec-build time on
purpose... a name that doesn't resolve is instead refused where it's actually used" (
`ViewsMixin.resolve_view`, `src/squads/_services/_views.py`).

Every other attached-by-name list on the same model IS checked at spec-build time, on the
merged mapping, so `sq workflow lint` catches a dangling reference before any command runs:
- `ItemSpec.parents` and `ItemSpec.lifecycle` — `_check_item_refs`
- `ItemSpec.validators` — `_check_validators_assignment`
- `RefRule.target`/`kind` — `_check_ref_rule_targets` / the ref_rules parse step
- field `collection` — `_check_field_collections`
- `SubentityKindSpec.lifecycle` — `_check_subentity_kinds`

`_check_views` (same file) does check the *forward* direction — a view's own `source.name`
resolving against `[ref_kinds]`/`[subentity_kinds]`/`[items]` — but nothing checks the reverse:
that a name an `items.<type>.views` list attaches actually exists as a declared `[views.<name>]`
entry.

The asymmetry looked for elsewhere (across `parents`, `lifecycle`, `validators`, `ref_rules`,
field `collection`, and sub-entity-kind `lifecycle`) was not found — each of those is checked
reciprocally. `items.<type>.views` appears to be the only unchecked attachment.

## Which surface should have caught it

Spec-level: `sq workflow lint` is the tool that exists to validate spec coherence before any
command runs against it, and this is exactly the shape of error it otherwise catches (a name
attached from one section that doesn't resolve in the section it names). It did not catch this
one.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T16:36:12Z] Mara Tester:
  - Driven in a scratch squad (fresh init + override scaffold), not this tree: lint OK at exit 0, sq milestone show exit 1 with 'no declared view'. Root cause in body: items.<type>.views is the only attached-by-name list on ItemSpec that WorkflowSpec._validate does not check reciprocally — parents/lifecycle/validators/ref_rules/field-collection/subentity-kind-lifecycle all are.
  - @tech-lead for triage.
- [2026-08-26T17:08:16Z] Olivia Lead:
  - Triaged: TASK-842 ST1 carries this as one of four axes of the same unvalidated ItemSpec.views attachment (dangling attachment, typo name, incompatible source, missing template). Fixing them one at a time leaves the other three.
- [2026-08-26T17:44:59Z] Elias Python:
  - Fixed via TASK-842 ST1: WorkflowSpec._validate now checks items.<type>.views reciprocally, so a dangling attachment (dropped view name, typo, or subentity-kind mismatch) is refused at load with [selected] provenance where applicable, not on first sq <type> <n> show.
- [2026-09-01T07:27:52Z] Mara Tester:
  - Verified in a scratch squad. Drove the exact original repro: override scaffold + append [selected] views = [] (dropping milestone_rollup while items.milestone.views still names it). sq workflow lint now refuses at exit 1 (was exit 0), naming the dangling attachment with [selected] provenance ('was dropped from a [selected] list (selected.views), not left undeclared'); sq milestone show now fails at the same load boundary with a consistent error (not the old lint-OK-then-show-crashes split). Confirmed the positive path is untouched: also dropping items.milestone.views = [] alongside restores a clean lint (exit 0) and a working sq milestone show (exit 0) — the reciprocal-key fix didn't just add a blanket refusal.
<!-- sq:discussion:end -->

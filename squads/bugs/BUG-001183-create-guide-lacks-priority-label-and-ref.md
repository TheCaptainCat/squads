---
id: BUG-1183
sequence_id: 1183
type: bug
title: create guide lacks --priority, --label and --ref
status: Open
author: qa
priority: low
severity: low
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:30Z'
updated_at: '2026-10-29T16:31:23Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree in a scratch squad.

## Command
`sq create guide "g" --author architect --priority high`

## Observed
```
Usage: sq create guide [OPTIONS] TITLE
╭─ Error ─╮
│ No such option: --priority │
```
Exit code 2. `--label` and `--ref` fail the same way (`No such option: --label`). The `sq create guide --help` option list carries only --tech, --tag, --parent, --desc, --assignee, -m, --file, --json.

## Expected
The guide type declares `fields = [{ code = "priority", ... }]` (src/squads/_specs/workflow.toml, `[items.guide]`), so `create guide` should accept `--priority` like every other type that declares the field; `--label` and `--ref` are offered by `create task` and `create bug`. Today the priority can only be set after creation with `sq guide N update --priority high` (works, exit 0).

## Severity
low
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

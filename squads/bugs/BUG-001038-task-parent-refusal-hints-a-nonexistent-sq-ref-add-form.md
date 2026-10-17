---
id: BUG-1038
sequence_id: 1038
type: bug
title: Task-parent refusal hints a nonexistent 'sq ref add' form
status: Open
author: qa
priority: low
refs:
- REV-1032
- MILE-1051:targets
created_at: '2026-10-16T09:01:09Z'
updated_at: '2026-10-16T12:24:17Z'
---
<!-- sq:body -->
## Repro

```
$ sq create task --author tech-lead --parent TASK-22 "T child"
error: a task's parent must be of type feature; link a bug or review with `sq ref add <task> <id> --kind fixes|addresses` (got task)
(exit 1)
$ sq ref --help
No such command 'ref'.
```

## Expected

The hint names a command that exists: `sq task <n> ref add <id> --kind fixes|addresses` (`sq task N ref add TARGET --kind ...` per `sq task 22 ref add --help`).

## Cause

The text is a ref-kind hint in `src/squads/_specs/workflow.toml` lines 434-435 (kinds `fixes` and `addresses`), shipped as bundled vocabulary, so every adopter sees it. Note the sibling text in `_specs/roles.toml:92` already uses the right form.

Found in the docs audit (REV-1032 asides).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

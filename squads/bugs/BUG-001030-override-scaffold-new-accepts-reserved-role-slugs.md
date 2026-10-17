---
id: BUG-1030
sequence_id: 1030
type: bug
title: override scaffold --new accepts reserved role slugs
status: Open
author: qa
priority: low
refs:
- FEAT-980
created_at: '2026-10-16T08:24:07Z'
updated_at: '2026-10-16T08:24:07Z'
---
<!-- sq:body -->
## Observed

With the dev build, `sq override scaffold --new <slug>` accepts reserved role slugs and writes a role override that `sq role activate` then refuses. The `op-` prefix behaves the same way.

## Reproduction (dev build, scratch squad)

```
cd /home/pchat/projects/squads
S=<scratchpad>/qa-scaffold
uv run --all-extras sq -C $S init --default-names --backend none
uv run --all-extras sq -C $S override scaffold --new squads
uv run --all-extras sq -C $S role activate squads
```

Outputs:

```
scaffolded new role override: .../squads/.overrides/roles/squads.toml   (rc=0)
error: slug 'squads' is reserved for system entries; a role needs another slug   (rc=1)

scaffolded new role override: .../squads/.overrides/roles/operator.toml   (rc=0)
error: slug 'operator' is reserved for the anonymous author; a role needs another slug   (rc=1)

scaffolded new role override: .../squads/.overrides/roles/op-foo.toml   (rc=0)
error: slug 'op-foo' is reserved for operators (the 'op-' prefix); a role needs another slug   (rc=1)
```

The three dead override files stay on disk after the failed activation.

## Expected

The scaffold refuses a reserved slug up front (exit 1, same message as activate) and writes nothing.

## Suggested fix

Run the same reserved-slug check that `sq role activate` uses (squads, operator, `op-` prefix) at the start of the `--new` branch of `override scaffold`, before any file is written. Share the validator rather than copying the rules. Add a CLI test per slug: exit 1, no file under `.overrides/roles/`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

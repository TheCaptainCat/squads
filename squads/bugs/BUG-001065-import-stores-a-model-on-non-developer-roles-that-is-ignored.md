---
id: BUG-1065
sequence_id: 1065
type: bug
title: Import stores a model on non-developer roles that is ignored
status: Open
author: qa
priority: low
refs:
- REV-1064
- MILE-1051:targets
created_at: '2026-10-16T17:50:50Z'
updated_at: '2026-10-16T17:50:50Z'
---
<!-- sq:body -->
## Summary

`model` set through `sq import` on a bundled or project-defined role (not a developer) is accepted and stored, but has no effect: the role definition comes from the overrides, so `sq role show`, the `.claude/agents` pointer and `sq check` all ignore it. Found in REV-1064 F4.

## Repro (dev build 0.16.0, scratch squad, `sq init --default-names --roles all`)

1. `sq list -t role` shows ROLE-4 is the bundled reviewer.
2. Import file with one line: `{"op":"update","target":"ROLE-4","fields":{"model":"haiku"}}`
3. `sq import m.jsonl --as qa` prints `update: 1` / `imported 1 event(s)`, exit 0.
4. `squads/agents/roles/ROLE-000004-reviewer.md` frontmatter now holds `model: haiku`.
5. `sq role reviewer show` still prints `model: opus`; `.claude/agents/reviewer.md` still has `model: opus`; `sq check` prints `no issues`.

The same import on a developer role (python-dev) takes effect, per REV-1064 F4.

## Expected

The import refuses `model` on a non-developer role instead of storing a value that nothing reads.

## Suggested fix

Refuse `model` in the import on any non-developer role (bundled or project-defined), with a message pointing to `.overrides/roles/<slug>.toml` or `roles.toml`. A developer keeps accepting it. Add a service-level test and an import CLI test for both cases.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

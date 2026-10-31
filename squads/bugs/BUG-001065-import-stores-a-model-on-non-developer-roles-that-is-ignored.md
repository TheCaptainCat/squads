---
id: BUG-1065
sequence_id: 1065
type: bug
title: Import stores a model on non-developer roles that is ignored
status: Verified
author: qa
refs:
- REV-1064
- MILE-1051:targets
created_at: '2026-10-16T17:50:50Z'
updated_at: '2026-10-26T06:46:33Z'
priority: low
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
- [2026-10-16T18:06:39Z] `op-pierre` Pierre Chat:
  - 2026-10-16: every role needs its model, not only developers. The fix is not to refuse a model on a non-developer role: a model set on any role must take effect.
- [2026-10-26T06:45:44Z] `qa` Mara Tester:
  - Verified on the dev build, judged against op-pierre's ruling (a model set on any role must take effect) and TASK-1153 ST2.
    - Import `{"op":"update","target":"ROLE-3","fields":{"model":"haiku"}}` on bundled reviewer: `update: 1`, `role reviewer show --json` model haiku; after `sq sync` .claude/agents/reviewer.md has `model: haiku`. Project role (lead) via import sonnet: show --json sonnet, pointer `model: sonnet`.
    - `role qa update --model sonnet` -> pointer sonnet at once; per-slug file model=opus plus stored haiku -> haiku wins; `role reviewer update --model ""` clears back to catalog opus; developer (`dev add --tech python`, update --model haiku) -> haiku.
    - Invalid: import `opuss` and `Sonnet` -> `model 'opuss' is not one of ['haiku', 'inherit', 'opus', 'sonnet']`, `nothing written`, rc 1; `update --model opuss` -> same message, rc 1; role file has no opuss.
    - Observation, not a failure: after an import the pointer is stale until `sq sync`; `sq check` now warns `managed pointer is out of date ... run sq sync`, so it is no longer silent (the original report said check printed no issues).
    Moving to Verified.
<!-- sq:discussion:end -->

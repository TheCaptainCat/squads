---
id: TASK-1126
sequence_id: 1126
type: task
title: Name every sq check finding by a registered rule
status: Ready
parent: FEAT-1092
author: tech-lead
priority: medium
refs:
- REV-956:addresses
- TASK-1125:depends-on
- TASK-1124:depends-on
- TASK-1077:depends-on
- TASK-1104:depends-on
description: 'REV-956 F11: additive rule key in sq check --json, a rule registry,
  a guard, and adopter docs on binding rules.'
subentities:
- local_id: ST1
  title: Add the rule field, registry and guard; emit rule in --json
  status: Todo
  story: US4
- local_id: ST2
  title: Document the binding check rules for adopters
  status: Todo
  assignee: tech-writer
  story: US4
created_at: '2026-10-24T21:53:55Z'
updated_at: '2026-10-24T21:55:44Z'
---
<!-- sq:body -->
## Goal

Every `sq check` finding names the rule that produced it, and adopters can see which findings are binding. Finding F11. This is the one adopter-visible change in FEAT-1092: an additive `rule` key on each finding in `sq check --json`, which stays within the additive-only promise for `--json` shapes in `docs/stability.md`. Human output is unchanged.

## Re-measured on 2026-10-24 (working tree, read)

- `CheckIssue` is still `level`, `item`, `message` (`src/squads/_services/_results.py:145`).
- 72 `CheckIssue(` constructions: 54 in `_services/_validators.py`, 14 in `_services/_maintenance.py`, 3 in `_cli/_main.py` and 1 in `_workflow/_models.py`. The check mixin split in the structural task moves the `_maintenance.py` ones.
- `check` still matches a finding by message text: `message.startswith("on disk but not in index")` (`_services/_maintenance.py:3207`).
- The eight sources REV-956 F11 lists stand: the raw-text scan, the per-file load boundary, override checks, orphaned skills, duplicate ids, the per-item catalog, the squad-global catalog, and confirmed cross-source candidates, plus the three config-load findings `_cli/_main.py` adds.

## Approach

1. Add a `rule: str` field to `CheckIssue`. Add a registry module beside the check mixin, for example `src/squads/_services/_check_rules.py`, that names every non-catalog rule with its source and whether it is binding (always on) or selectable. A catalog finding's rule is the validator's own declared name, so the spec stays its single source and the registry holds no copy.
2. Every construction passes a rule. `check` matches on the rule, never on message text.
3. `sq check --json` emits `rule` on every finding.
4. Rewrite the two docstrings that describe the two kinds of finding in the plain terms TASK-1077 sets ("file checks", "the validator catalog"). Drop "pre-parse" and state the rule the file checks actually satisfy: per file, not selectable, and still reported when the frontmatter cannot be read.
5. Adopter docs (ST2, tech writer): a paragraph listing the binding rules and saying that they cannot be deselected and why, beside where `docs/overrides.md` documents the selectable validators. Note the new key in `docs/stability.md`'s `--json` section if it enumerates keys.

## Tests

- **`tests/meta` guard:** every `CheckIssue(` construction under `src/` passes a `rule` that is registered or is a declared validator name (AST scan), with a liveness row that plants an unregistered rule and sees it fail. This is the one place the rule is encoded. No per-finding test asserts its own rule name.
- **One table, "rule reaches `--json`"**, with one row per source (eight sources plus the config-load path), because each source is its own code path. Each row checks that a planted defect's finding carries the expected rule in `sq check --json`. No level-by-type cross product.
- **Goldens:** the `sq check --json` goldens gain the key. Regenerate them and review the diff to confirm it adds only `rule`.
- Falsify: drop `rule` from one source and see its row and the guard go red.

## Generated output

No generated agent file changes. The `sq check --json` shape gains one key.

## CHANGELOG substance (the writer authors the entry)

Added: every finding in `sq check --json` carries a `rule` naming the check that produced it. The docs now list the findings that are always on and cannot be deselected, and why. Tools reading `--json` can match findings by rule instead of by message text.

## Order

After the composition-root task (both edit the `sq check` fallbacks in `_cli/_main.py`), the structural task (the check mixin split), TASK-1077 (the validator wording) and TASK-1104 (new check warnings that this names). Before the test-rebuild inventory (TASK-1111), so the rebuilt check tables can assert rule names rather than message text.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1126 add-subtask "<title>"`; track with `sq task 1126 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add the rule field, registry and guard; emit rule in --json

<!-- sq:subtask:ST1:body -->
Add `rule` to `CheckIssue` and a rule registry beside the check mixin, with catalog findings named by their declared validator. Name all 72 constructions, match on the rule instead of message text in `check`, and emit `rule` in `sq check --json`. Rewrite the two finding-kind docstrings in TASK-1077's plain terms, without "pre-parse". Add the meta guard, the per-source table, and the regenerated goldens.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Document the binding check rules for adopters

<!-- sq:subtask:ST2:body -->
Document for adopters which `sq check` findings are always on and cannot be deselected, and why, beside the selectable validators in `docs/overrides.md`. Note the additive `rule` key where `docs/stability.md` describes `--json` shapes. Write the CHANGELOG entry from the developer's handoff.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

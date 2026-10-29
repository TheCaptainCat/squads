---
id: BUG-1239
sequence_id: 1239
type: bug
title: display.assignee ignores [display] pronouns in --json
status: InProgress
author: qa
priority: medium
severity: medium
refs:
- FEAT-1226
created_at: '2026-10-29T12:25:02Z'
updated_at: '2026-10-29T12:26:01Z'
---
<!-- sq:body -->
## Steps

On release/0.18 (72a5e491), scratch squad: `sq init --default-names --roles all`; `sq role qa update --pronouns she/her`; `sq create task "Pronoun probe" --author tech-lead --assignee qa`. Then for `[display] pronouns = true` and for `pronouns = false` in `.squads.toml`, run `sq task 21 show --json`, `sq list --json` and `sq tree --json`, and read `display.assignee` of TASK-21.

## Actual

`display.assignee` is `"Mara Tester"` on all three surfaces with the setting true and with it false. It never carries `(she/her)`. The setting does work elsewhere: `sq role qa show` prints `Mara Tester (she/her) (qa)` with true and `Mara Tester (qa)` with false.

## Expected

ADR-1224 (Names): role and operator names are display values with pronouns applied or left out according to `[display] pronouns`, on every surface, `--json` and HTTP included. With true, `display.assignee` is `Mara Tester (she/her)`; with false, `Mara Tester`.

## Regression?

No. 0.17.0 has no `display` object in `show --json`, and its text `show` and `list` print the assignee slug (`qa`) in both versions, so the text output is identical. This is a gap in the new 0.18 `display.assignee` value, not a change from 0.17.

## Affected

`display.assignee` in `show`, `list` and `tree` `--json` (and the API). Text `list`/`show`/`tree` show the slug, unchanged from 0.17.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

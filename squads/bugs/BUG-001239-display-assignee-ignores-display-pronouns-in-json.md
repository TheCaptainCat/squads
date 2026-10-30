---
id: BUG-1239
sequence_id: 1239
type: bug
title: display.assignee ignores [display] pronouns in --json
status: Verified
author: qa
refs:
- FEAT-1226
created_at: '2026-10-29T12:25:02Z'
updated_at: '2026-10-29T12:37:53Z'
priority: medium
severity: medium
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
- [2026-10-29T12:32:34Z, edited 2026-10-29T12:32:52Z] `python-dev` Elias Python:
  - Fixed in e7f6f893 on worktree-agent-a6c1528fd4b8d474e (from release/0.18 663203c8), not pushed. Every role and operator display name in the item projections now goes through `ItemOpsMixin.display_names()`: `participant_names` takes the pronouns that `shown_pronouns()` resolves, the same source and the same `Name (pronouns)` form `role show` uses. When `[display] pronouns = false`, that map is empty and the bare name shows. This covers `display.assignee` on show (item and sub-entities), list, mine, tree, graph, search, sub-entity listings and show, the item write responses, and the view sources.
  - Test: one surface case in tests/cli/test_list.py (`covers("list", "--json")`). It gives `manager` pronouns, asserts the whole `list --json --type bug --all` document with `Catherine Manager (she/her)`, then sets `[display] pronouns = false` in `.squads.toml` and asserts it again with `Catherine Manager`. Falsified twice, each red: pronouns never applied, and the config switch ignored. No existing expectation changed.
  - Text output: identical to released 0.17.0 on twin scratch squads (13 commands incl. show, show --full, sq show, list, tree, mine, search, sub-entity list and show, graph, each with the setting on and off: 26 identical). Gates: pyright 0, ruff check and format clean, pytest -n 2 tests/meta tests/cli 1545 passed. @qa to verify.
- [2026-10-29T12:37:39Z] `qa` Mara Tester:
  - Verified on release/0.18 bd7aab88, dev tree, scratch squad with qa pronouns she/her. display.assignee in --json: with [display] pronouns=true it is "Mara Tester (she/her)", with false "Mara Tester", on task show, sq show, list, mine, tree, graph, search, subtasks, subtask show and the item update write response (all exit 0). comment and add-subtask write responses carry no display assignee. Text output of show, show --full --comments, sq show, list, list --all, mine, tree, graph, search, subtasks, subtask show and role show is identical to released 0.17.0 on twin squads, setting on and off; the only difference is one extra comment the dev squad got from my own repeated probe.
<!-- sq:discussion:end -->

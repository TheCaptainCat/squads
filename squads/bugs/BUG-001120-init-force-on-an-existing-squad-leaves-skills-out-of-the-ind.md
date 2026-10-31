---
id: BUG-1120
sequence_id: 1120
type: bug
title: init --force on an existing squad leaves skills out of the index
status: Verified
author: qa
created_at: '2026-10-24T18:52:57Z'
updated_at: '2026-10-24T20:59:27Z'
priority: medium
---
<!-- sq:body -->
## Steps

Scratch dir, never the repo itself:

```
mkdir X && git init X
sq -C X init --force     # first init: sq check exits 0
sq -C X init --force     # second init over the existing squad
sq -C X check; echo $?   # exits 3
```

Note: a single `init --force` on an empty dir is clean (`sq check` exit 0, "no issues"). The failure needs `--force` to run over an existing squad (second run).

## Expected

`sq init --force` re-run leaves a consistent squad: `sq check` exits 0.

## Actual

`sq check` exits 3 with 12 errors, all skills:

```
error SKILL-9: on disk but not in index (run `sq repair`)
... (SKILL-10 through SKILL-19)
error SKILL-20: on disk but not in index (run `sq repair`)
```

Flagged: SKILL-9 to SKILL-20, i.e. every bundled skill (greeting, sq-bug, sq-contract, sq-decision, sq-epic, sq-feature, sq-guide, sq-memory, sq-milestone, sq-review, sq-task, squads). The skill files `agents/skills/SKILL-0000NN-<slug>.md` are on disk, but `.squads.json` holds only the 8 role items (counter=8). Index counter was not advanced for the skills the re-init wrote.

## Versions

- Released `sq` 0.16.0 (`~/.local/bin/sq`): reproduces.
- Dev build (`uv run --all-extras sq`, release/0.17 working tree): reproduces, identical output.

## Workaround

`sq repair` clears it (rebuilt index: 20 items, counter=20; `sq check` then exits 0). `sq sync` does NOT clear it (check still exits 3 after sync).

## Likely area

`sq init --force` path (`_services/_service.py` init) writing skill files outside an index transaction, or not reusing the existing index. Not diagnosed.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T20:57:57Z] `manager` Catherine Manager:
  - Fixed by TASK-1103 ST8 (294089b4, hardened in 868d5e48 per REV-1122 F4). @qa please verify.
- [2026-10-24T20:59:25Z] `qa` Mara Tester:
  - Verified on dev build in scratch squads: fresh squad and one holding a task, init --force run 3 times each; sq check exit 0 after every run (bare exit codes). Skills 12 on disk, index 20 items; next created item got TASK-21 (fresh) and TASK-22 (after existing TASK-21), counter continues past highest.
<!-- sq:discussion:end -->

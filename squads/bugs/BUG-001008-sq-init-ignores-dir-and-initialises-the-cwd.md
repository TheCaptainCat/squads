---
id: BUG-1008
sequence_id: 1008
type: bug
title: sq init ignores --dir and initialises the cwd
status: Fixed
author: qa
refs:
- REV-995
created_at: '2026-10-15T19:08:38Z'
updated_at: '2026-10-15T20:44:30Z'
---
<!-- sq:body -->
`sq init --dir X` ignores `--dir` and initialises the current working directory.

**Reproduction** (driven, in an empty scratch folder, with the released tool and the dev tree):

```
mkdir rel && cd rel && pwd
sq init --dir sub
find . -maxdepth 2
```

Run once with `~/.local/bin/sq` and once with `uv run --project <repo> sq`. Both reported "squads initialized" with the squad at `<cwd>/squads` and wrote `.squads.toml`, `CLAUDE.md`, `.gitignore`, `.claude/` and `squads/` into the working directory. No `sub/` directory was created.

**Expected.** `--dir X` names the squad folder, as it does for every other command (`--dir` > `.squads.toml` walk-up > default); `init` creates the squad at X.

**Actual.** `init` never reads `--dir`; it initialises `Path.cwd()` (`_cli/_main.py`, `_services/_service.py`). Run with `--dir` pointing inside another squad, it still writes a new squad into the cwd and leaves the named folder untouched.

**Versions affected.** Reproduced on `sq` 0.15.0 (released tool) and the dev tree on release/0.16 (reports 0.15.0). Found by the reviewer in REV-995 pass 7 (F27); it predates that work.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T20:44:09Z] `python-dev` Elias Python:
  - Fixed in the working tree (uncommitted): sq -C X init creates X/.squads.toml and X/squads. Tests: tests/cli/test_c_init_and_adopt_create_at_the_directory.py (test_c_creates_exactly_what_running_from_the_directory_creates, test_c_init_into_a_new_subfolder_leaves_the_working_directory_with_only_that_folder, test_c_naming_a_missing_directory_exits_2_and_creates_nothing). @qa to verify once committed.
<!-- sq:discussion:end -->

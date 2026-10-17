---
id: BUG-1060
sequence_id: 1060
type: bug
title: Schema gate refuses sq override update and diff on a behind squad
status: Verified
author: qa
priority: low
refs:
- MILE-934:targets
description: Override stamp/diff verbs unreachable exactly when an upgrade makes overrides
  drift
created_at: '2026-10-16T13:33:13Z'
updated_at: '2026-10-16T19:08:39Z'
---
<!-- sq:body -->
On a squad behind the package's schema, the schema gate refuses `sq override update` and `sq override diff`. These are the documented way to re-stamp an override's base version (`squads:override-base:<version>`) and to see what an upgrade changed under it. An upgrade is exactly when overrides drift, and a behind-schema squad is exactly when the gate refuses them, so the documented workflow is unavailable when it is needed. (Hand-editing the stamp is legitimate, since override files are user-owned. The defect is only that the convenient, checked command is blocked.)

## Reproduction

Scratch squad in /tmp/claude-1000/-home-pchat-projects-squads/afc5b560-8dbe-465b-84f6-883ab1b53ed1/scratchpad/qa-stamp/ (git-inited).

1. Released tool 0.15.0: `cd <scratch> && ~/.local/bin/sq init` (schema v0.15).
2. `~/.local/bin/sq override scaffold workflow`, then `override list` shows `workflow  0.15.0  current`. To stand in for a bundled spec changing under the override, the stamp line was set to `0.14.0` by hand; `~/.local/bin/sq --dir <scratch>/squads override list` then shows `drifted`.
3. Dev build (0.16.0 at HEAD 4b79c836, run from a clean `git archive` copy because the working tree does not import):
   `uv run --all-extras sq -C <scratch> override list|diff workflow|update workflow`

Output, all three, exit 1:

    error: this squad is at schema v0.15; squads 0.16.0 expects v0.16. Run sq migrate up to upgrade it (see `sq migrate help`).

`sq list` gives the same refusal. `override update --help` works (the gate skips `--help`), so the verb is advertised but unusable.

## Cause

`src/squads/_cli/__init__.py` calls `common.require_current_schema(ctx.invoked_subcommand)` in the root callback. `require_current_schema` (`src/squads/_cli/_common.py`) returns only for subcommand `None` or `migrate`; everything else goes to `apply_gate(None)`, which exits 1 on any schema mismatch unless `--help` was requested. Commands opt in with `@common.past_the_gate(Ground, behind=, ahead=)`; but that grant is read only inside the `migrate` group callback (`migrate_grants()` in `_cli/_migrate.py`). Only three migrate commands carry grants today (MIGRATION, and two NO_SQUAD_STATE). No `override` command is granted, and the root gate never consults grants for other groups.

## Expected

`sq override update` and `sq override diff` (and likely `override list`) run on a behind-schema squad: they read and rewrite only `.overrides/*` files and the bundled specs, not the corpus.

## Suggested fix

Let the override stamp and diff commands through the gate. They depend on override files and the bundled spec, not on the corpus schema. Concretely, decorate `update`, `diff` and `list` with `@common.past_the_gate(Ground.NO_SQUAD_STATE, behind=True)` and have the root gate consult grants for non-migrate groups too (or add an `override` group callback like migrate's). Check first that these commands do not load the corpus: `override diff` and `list` resolve the active spec, which loads the override, so confirm an override that no longer validates against the new spec still reports drift rather than crashing. Keep `scaffold` gated (it writes new bodies). Keep ahead-of-package squads refused (`ahead=False`): a newer squad's override layout is unknown. If instead they must stay gated, the refusal message should say that the stamp can be edited by hand.

Side observation: the dev tree (working tree and HEAD) fails to import with `ModuleNotFoundError: No module named 'squads._models._extras'` from the migration runners. I restored that file from 4b79c836^ in the scratch copy only to run the repro. Not filed separately here.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T13:35:11Z] `op-pierre` Pierre Chat:
  - 2026-10-16: targets 0.16.
- [2026-10-16T18:14:31Z] `python-dev` Elias Python:
  - Fixed in the commit "Let override list, diff and update past the schema gate on a behind squad": the override group now gates each command by its declared grant (list, diff, update behind-only; scaffold and ahead stay refused) and the three read the squad paths without opening the corpus. Table over 6 verbs x 4 override states (none, valid, conflicting, does-not-load) plus ahead and scaffold controls; falsification 24 of 32 fail on the old gate (8 are the refusal controls). docs/migration.md updated.
- [2026-10-16T18:23:30Z] `python-dev` Elias Python:
  - Commit fa227fdf on branch worktree-agent-a2f892de06784925e.
- [2026-10-16T19:08:39Z] `manager` Catherine Manager:
  - Verified: fix approved on REV-1067 and merged into release/0.16 at 977730ec; full suite 11471 passed, 0 failed.
<!-- sq:discussion:end -->

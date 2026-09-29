---
id: REV-972
sequence_id: 972
type: review
title: Skew canary sq resolution and type-catalog keys
status: Approved
author: reviewer
refs:
- TASK-968
- MILE-934:targets
subentities:
- local_id: F1
  title: Pinned uv run sq tests one binary, reports another's version
  status: Verified
  severity: medium
- local_id: F2
  title: A dead or unrunnable SQ_CANARY_CMD pin falls through or skips green
  status: Verified
  severity: medium
- local_id: F3
  title: SQ_CANARY_CMD split on whitespace breaks spaced Windows paths
  status: Verified
  severity: low
- local_id: F4
  title: poetry --directory runs the canary's sq in the live repo squad
  status: Verified
  severity: high
- local_id: F5
  title: A relative pin is checked from one cwd and spawned from another
  status: Verified
  severity: low
- local_id: F6
  title: Pinned branch re-implements discovery's config-command check
  status: Verified
  severity: low
- local_id: F7
  title: A pin's own cwd-moving flag still runs sq in the live repo
  status: Verified
  severity: medium
created_at: '2026-09-29T13:43:29Z'
updated_at: '2026-09-29T14:12:37Z'
---
<!-- sq:body -->
Review of the canary hardening in `clients/vscode/test/canary/`: `resolveSq.ts`, `resolveSq.test.ts`, and the `skewCanary.test.ts` diff.

## What holds

- **Reuse.** `resolveCanarySq` delegates to `resolveSqInvocation` from `src/discovery.ts` and to the real `createNodeDiscoveryEnvironment`; the only canary-specific logic is the `--project`/`--directory` rewrite for the discovered uv/poetry cases, which is needed because `runSq` runs from a scratch dir. No ordering logic is copied. (read)
- **Default resolution.** Unpinned, the canary resolves to the repo `.venv/bin/sq` and all 45 tests pass; the stderr line names the binary and version. (driven)
- **Exact key set.** `TYPE_ENTRY_KEYS` matches `TYPE_CATALOG_FIELDS` in `src/squads/_cli/_workflow_cmd.py` key for key, and `assertExactKeys` compares sorted arrays, so missing, extra and renamed keys all fail; every live entry is checked, not only `bug`. (read; lane green, driven)
- `REPO_ROOT` comes from `__dirname`, so the canary's workspace root does not depend on the cwd vitest is launched from. (read)
- No bare `execFileSync('sq'` remains under `test/`. (driven, rg)
- Comment length and content follow the house rule; no ticket IDs or versions. (read)

## What does not

Two gaps, both in the `SQ_CANARY_CMD` pin path; see the findings. The default path is sound.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 972 add-finding "…" --severity medium`; track with `sq review 972 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Pinned uv run sq tests one binary, reports another's version

<!-- sq:finding:F1:body -->
**Driven.** The file header gives `SQ_CANARY_CMD="uv run sq"` as an example pin. A pin resolves as `config-command` and keeps its args verbatim (`['run', 'sq']`). The `--project <repo>` rewrite in `resolveSq.ts` applies only when `source === 'uv'`/`'poetry'`, not to a pinned uv/poetry command. So the two call sites run different binaries:

- `runSq` uses `cwd: scratchDir`. That directory has no `pyproject.toml` above it, so `uv run sq` falls back to `VIRTUAL_ENV` or to whatever `sq` is on PATH.
- `sqVersion` runs with no `cwd`, so it inherits the process cwd (`clients/vscode`, inside the repo). There `uv run sq` finds the repo project and reports the repo's version.

Measured on this machine with `VIRTUAL_ENV` unset and `~/.local/bin` on PATH: from the scratchpad, `uv run which sq` gives `/home/pchat/.local/bin/sq` (a global uv-tool install); from `clients/vscode` it gives `/home/pchat/projects/squads/.venv/bin/sq`. A pinned canary run printed `skew canary sq: uv run sq [config-command] -> squads 0.15.0`, but that version came from the repo `.venv`, while the live tests would talk to the global tool. The versions match here only by chance. This is the stale-global substitution the task set out to remove, and the version line now vouches for the wrong binary.

**Fix direction:** run `sqVersion` with the same `cwd` as `runSq` (or run both from the repo), and either apply the project-pointing rewrite to pinned uv/poetry commands or drop `uv run sq` from the header example. Add a table row for a pinned `uv run sq`.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-09-29T13:52:06Z] Ada Typescript:
  - Version probe and live tests share execSq from a non-repo dir; pinned uv/poetry commands get the same project rewrite.
- [2026-09-29T13:57:15Z] Paul Reviewer:
  - Verified (driven): version probe and live tests share execSq; pinned uv run sq is rewritten to --project and printed version is the tested binary. Canary 50/50 from a cwd outside the repo.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — A dead or unrunnable SQ_CANARY_CMD pin falls through or skips green

<!-- sq:finding:F2:body -->
**Read, and the table codifies it.** `resolveCanarySq` passes the pin in as discovery's `config-command` step, so a pin that does not resolve silently falls through to `.venv`, uv, poetry and then PATH. The row "a pinned command that does not exist falls through to the .venv" asserts exactly that. A pin that resolves but cannot run (`--version` fails) sets `SQ_AVAILABLE` to false, and the whole live block is skipped with exit 0.

For the extension, falling through is the right call: config is a preference. For the canary, `SQ_CANARY_CMD` is set to test *that* binary on purpose, for example a release build in CI. A typo in the path gives a green run against a different `sq`, or skips the run entirely. The only signal is `[venv]` or `not runnable` on stderr, which a green CI log does not surface.

**Fix direction:** when `SQ_CANARY_CMD` is set and does not resolve, or does not answer `--version`, fail the suite loudly instead of falling through or skipping. Flip the dead-pin row to expect that failure.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-09-29T13:52:15Z] Ada Typescript:
  - A pin that does not resolve or answer --version fails the suite (beforeAll throws); no fall-through, no skip.
- [2026-09-29T13:57:20Z] Paul Reviewer:
  - Verified (driven): a dead pin, a non-executable pinned file, and malformed or non-string JSON pins all fail the suite loudly (beforeAll throws, exit 1); none falls through or skips green.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — SQ_CANARY_CMD split on whitespace breaks spaced Windows paths

<!-- sq:finding:F3:body -->
**Read.** `resolveSq.ts` builds the pin with `pinned.trim().split(/\s+/)`, so a pin whose path contains a space breaks at the space. `C:\Program Files\squads\sq.exe` becomes `C:\Program`, which fails `fileExists`, and then the pin falls through to the next strategy (see the dead-pin finding). Windows paths with spaces are common, and the Windows `.venv/Scripts/sq.exe` layout is in scope for this task.

**Fix direction:** treat a pin that names an existing file as a single path before splitting on whitespace, or accept a JSON array (the shape `squads.command` already uses). Add a table row for a spaced Windows path.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-09-29T13:52:21Z] Ada Typescript:
  - A pin naming an existing file is one path; a JSON argv array is also accepted; else whitespace split.
- [2026-09-29T13:57:26Z] Paul Reviewer:
  - Verified (driven): a pinned path with a space and its JSON-array form both resolve to one path; malformed JSON falls to whitespace split and fails as unresolved.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — poetry --directory runs the canary's sq in the live repo squad

<!-- sq:finding:F4:body -->
**Driven.** `pointAtProject` rewrites any poetry invocation to `poetry --directory <repo> ...`. That applies to a pinned `poetry run sq` and to the discovered poetry step alike. In Poetry 2 (2.3.0 here), `--directory`/`-C` *changes the working directory* to the project before running the command. So every `execSq(..., scratchDir)` call runs `sq` in the repo root, not in the scratch squad.

Measured from the scratchpad: `poetry --directory /home/pchat/projects/squads run pwd` prints `/home/pchat/projects/squads`, while `poetry --project /home/pchat/projects/squads run pwd` prints the scratchpad. A live canary run with `SQ_CANARY_CMD="poetry run sq"` failed in `beforeAll` with `sq init ... error: /home/pchat/projects/squads/.squads.toml already exists`: the canary's `sq init` targeted this repo's own squad. It stopped only because init refuses to overwrite. On a checkout without a `.squads.toml` at the root, init would succeed, and the canary's `sq create`/`update` calls would then write test items into the live corpus. I checked that no file under `squads/` changed during that run.

The table row "a pinned poetry run sq is pointed at the repo" (and "only poetry and a project") asserts `--directory`, so the tests codify the bug.

**Fix direction:** use `poetry --project <repo> run sq`, which selects the project and keeps the cwd. Add a live or driven check that `sq` runs in the scratch dir (e.g. the resolved squad dir), not only that the argv matches.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-09-29T14:01:18Z] Ada Typescript:
  - Poetry now gets --project (keeps cwd); a guard test runs every resolution shape and fails on any cwd-moving flag. Driven with a fake poetry: sq ran in the scratch dir.
- [2026-09-29T14:04:52Z] Paul Reviewer:
  - Verified (driven): pinned and discovered poetry now get --project. A live canary run through a fake poetry in the scratchpad (refusing --directory/-C and any repo cwd) passed 61/61; all 18 calls ran in the scratchpad or scratch squad, none in the repo. Real poetry --project keeps the cwd (driven, pwd). A pin carrying its own cwd flag is F7.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — A relative pin is checked from one cwd and spawned from another

<!-- sq:finding:F5:body -->
**Driven.** `parsePin` and the resolution check test a relative pin with `fileExists`, relative to the *process* cwd. `execSq` then runs it with `cwd` set to the tmpdir or scratch dir, where the same relative path points elsewhere. `SQ_CANARY_CMD=../../.venv/bin/sq` from `clients/vscode` resolved as `[pinned]` and then failed with `does not answer --version`. The binary exists and works; the path just changed meaning between the check and the spawn. The run failed loudly, so this is not a silent green, but the message sends the reader to the wrong cause.

**Fix direction:** `path.resolve` a pin's first element when it contains a separator, before the check and the spawn.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-09-29T14:01:23Z] Ada Typescript:
  - Relative pin paths are resolved against the process cwd before the check and the spawn.
- [2026-09-29T14:05:00Z] Paul Reviewer:
  - Verified (driven): relative pins, plain and as JSON, resolve to the absolute repo .venv/bin/sq before the check and the spawn.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Pinned branch re-implements discovery's config-command check

<!-- sq:finding:F6:body -->
**Read.** The pinned branch of `resolveCanarySq` no longer goes through `discovery.ts`. It re-implements `tryConfigCommand`: the `/[\\/]/` path-versus-bare-name test duplicates `looksLikeFilesystemPath`, followed by the same `fileExists`/`isOnPath` choice. The task asked for the resolution order to be reused, not copied, and the two can now drift (e.g. if discovery learns `PATHEXT` handling for pinned names).

**Fix direction:** call `resolveSqInvocation(repoRoot, { command: argv }, env)` and treat any result whose `source` is not `config-command` as the unresolved-pin failure. That keeps the no-fall-through rule without a second copy of the check.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-09-29T14:01:26Z] Ada Typescript:
  - The pinned check now goes through resolveSqInvocation and rejects any result not sourced from config-command.
- [2026-09-29T14:05:06Z] Paul Reviewer:
  - Verified (read + driven): the pinned branch calls resolveSqInvocation and requires source config-command; dead, malformed and non-string pins stay unresolved. absolutize runs twice on the first element (parsePin, then resolveCanarySq): redundant, harmless.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — A pin's own cwd-moving flag still runs sq in the live repo

<!-- sq:finding:F7:body -->
**Driven.** The cwd guard added for F4 (`CWD_MOVING_FLAGS` in `resolveSq.test.ts`) is a unit test over the table's own rows. Nothing at runtime rejects a cwd-moving flag that the pin itself carries, and `pointAtProject` passes such flags through:

- `SQ_CANARY_CMD="uv --directory <repo> run sq"` resolves to `uv --directory <repo> run sq`.
- `"poetry -C <repo> run sq"` resolves to `poetry --project <repo> -C <repo> run sq`.
- `"uv run --directory=<repo> sq"` resolves unchanged apart from the added `--project`.

All three came from `resolveCanarySq` with the real Node environment. `uv --directory X run pwd` prints `X` (driven, with X a scratch dir), so each of these pins runs the canary's `sq init`/`create`/`update` in the repo root: the same live-squad write as F4. `uv --directory <repo> run sq` is a natural way to write "the repo's sq from anywhere". The guard also matches exact tokens only, so the `--directory=<path>` and `-C<path>` forms would slip past it even as a test.

**Fix direction:** reject a resolved invocation carrying a cwd-moving flag (either form) at runtime, as a pin failure. Alternatively, have the canary assert before its first write that `sq` resolves the scratch squad, not the repo's. Keep the unit guard, but match prefixes.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-09-29T14:10:04Z] Ada Typescript:
  - beforeAll now proves the invocation sees no squad from the scratch dir before any write; cwd-moving flags (split, = and attached forms) are also rejected at resolution.
- [2026-09-29T14:12:28Z] Paul Reviewer:
  - Verified (driven, decoy squad in the scratchpad, never the repo): uv/poetry -C, --directory and =-form pins are rejected at resolution; a --dir pin at a squad and a TMPDIR symlinked into a squad both hit the beforeAll guard (refusing to write). A wrapper that changes directory only on write commands passes the guard by construction, but its init was refused by the target squad existing .squads.toml, so nothing was written (decoy sha1 unchanged). A pinned wrapper is trusted code, so that is residual, not a defect.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T13:47:06Z] Paul Reviewer:
  - ChangesRequested. Default resolution (.venv first, via discovery.ts) and the 9-key exact set are sound; canary green 45/45 unpinned (driven). Both medium findings sit in the SQ_CANARY_CMD pin path: F1 a pinned uv run sq runs against the scratch dir while --version runs from the repo cwd (driven), F2 a dead pin falls through or skips green. F3 low: pin split on whitespace. @typescript-dev please address F1-F3 on TASK-968.
- [2026-09-29T13:58:09Z] Paul Reviewer:
  - Re-review: F1-F3 Verified (driven). Still ChangesRequested for new F4 (high): poetry --directory chdirs into the repo, so a poetry-resolved canary runs sq init/create against the live squad; driven, init refused only because .squads.toml exists, nothing written. F5/F6 low. @typescript-dev please take F4-F6 on TASK-968.
- [2026-09-29T14:05:35Z] Paul Reviewer:
  - Re-review 2: F4-F6 Verified (driven; poetry probed only through a scratchpad fake). Still ChangesRequested for new F7 (medium): the cwd guard is test-only, so a pin such as uv --directory <repo> run sq still runs the canary sq in the repo root. @typescript-dev please take F7 on TASK-968.
- [2026-09-29T14:12:37Z] Paul Reviewer:
  - Re-review 3: F1-F7 all Verified; Approved at the coordinator request. sq honours no env var for the squad dir (only SQUADS_SESSION_ID/SQUADS_PARENT_SESSION_ID), so there is no env redirect to guard. Canary lane 68 tests; guard and resolution paths driven against a scratch decoy only.
<!-- sq:discussion:end -->

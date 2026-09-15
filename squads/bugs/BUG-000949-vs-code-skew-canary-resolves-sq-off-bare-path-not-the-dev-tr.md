---
id: BUG-949
sequence_id: 949
type: bug
title: VS Code skew canary resolves sq off bare PATH, not the dev tree
status: Open
author: qa
severity: medium
refs:
- BUG-896
- MILE-934:targets
- BUG-935
created_at: '2026-09-15T08:00:34Z'
updated_at: '2026-09-15T08:12:59Z'
---
<!-- sq:body -->
## Problem

The VS Code client's skew canary (`clients/vscode/test/canary/skewCanary.test.ts`) resolves
`sq` by shelling out to a bare command name, which Node/the OS resolve off `PATH` only:

```ts
function isSqOnPath(): boolean {
  try {
    execFileSync('sq', ['--version'], { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}
...
function runSq(args: readonly string[]): string {
  return execFileSync('sq', args, { cwd: scratchDir, encoding: 'utf8' });
}
```

Every invocation in the file (`isSqOnPath`, `runSq`, used by all 8+ live-`sq` test blocks) goes
through this same bare-name call. There is no fallback to a project-local interpreter.

**Read.** The suite's own file-header docstring already names the consequence in writing:

> It shells out to whatever `sq` PATH resolves first, and cannot tell a stale one from the one
> you are developing against. An older `sq` earlier on PATH than the project's own environment
> reports drift that does not exist — missing sub-commands, absent keys — so check `sq --version`
> against the core before believing a red run here.

## Why this is not just a documented limitation

**Read**, `clients/vscode/src/discovery.ts` — the extension's own runtime `sq`-resolution logic,
which this canary exists to keep honest:

```
Order (first that works wins), auto-detecting the workspace toolchain — never PATH-only:
  1. squads.sqPath / squads.sqCommand (explicit config)
  2. workspace virtualenv — `.venv/bin/sq` (`.venv/Scripts/sq.exe` on Windows)
  3. `uv` on PATH + a project at the workspace root -> `uv run sq`
  4. `poetry` on PATH + a project at the workspace root -> `poetry run sq`
  5. bare `sq` on PATH (fallback)
```

Bare-PATH is explicitly the *last-resort fallback* in the extension's real resolution order,
specifically because it is unreliable. The canary exists to catch drift between the CLI and the
client, but it uses the one resolution strategy the client itself treats as least trustworthy,
and skips none of the other four. So the suite meant to validate the client's view of `sq` does
not use the client's own method of finding `sq`.

## Driven

In this repo, `.venv/bin/sq` and whatever `sq` resolves to on `PATH` currently happen to be the
same binary (both report `squads 0.15.0`) — so the canary is not visibly wrong today. But that is
incidental to this environment, not a property the canary establishes or checks:

```
$ which sq
/home/pchat/projects/squads/.venv/bin/sq
$ sq --version
squads 0.15.0
$ .venv/bin/sq --version
squads 0.15.0
```

Confirmed by reading `runSq`/`isSqOnPath`: neither consults `discovery.ts`, an env var, or the
workspace `.venv` — both call `execFileSync('sq', ...)` verbatim. Any machine with an older `sq`
installed globally and earlier on `PATH` than the project's own `.venv` reproduces the header's
documented failure mode without changing a single line of this file. This session, a
typescript-dev skipped this test lane for exactly this reason rather than trust its output.

## Expected vs actual

- **Expected:** the canary resolves `sq` the same way the extension it is guarding does (or at
  minimum prefers the workspace `.venv/bin/sq` over a bare `PATH` lookup), so a stale global `sq`
  cannot masquerade as "the one you are developing against."
- **Actual:** it resolves `sq` by bare `PATH` lookup only, and its own header text is the only
  thing standing between a contributor and a misleading red (or falsely green) run.

## Not claimed

- Not claiming a live false result exists in this repo today — driven: PATH and `.venv` agree
  here. This is a latent reliability gap in the test's own setup, exposed by environment, not a
  currently-failing assertion.

## Relationship to BUG-896

Checked BUG-896 first, as asked. It is not a duplicate: BUG-896 is about the shape of the
*assertion* once a resolved `sq` is running (`arrayContaining` vs. an exact key set — blind to an
added/removed key on two of three JSON surfaces). This defect is upstream of that — about *which
binary gets resolved and invoked* in the first place. Fixing BUG-896's assertion shape does
nothing for a run where the wrong `sq` answered every `runSq` call to begin with.

## Severity

Judged **medium**. Not lower: this is the suite whose whole purpose is catching CLI/client drift,
and its own setup can silently substitute the wrong binary in either direction (false drift on a
correct client, or a masked real regression) — and it already cost a real testing lane this
session. Not higher: it is test-infrastructure only, never reaches production behavior or user
data, degrades to a documented, self-aware skip rather than a silent wrong pass in the common
case, and the remedy is a well-understood fix (reuse a `.venv`-first resolution order, matching
`discovery.ts`).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T08:12:59Z] Pierre Chat:
  - Targeted at 0.16 alongside BUG-935 -- both are the VS Code skew canary, different mechanisms
    (which binary resolves, versus what the assertion asserts). Take them as one job rather than
    fixing one half and leaving its twin.
<!-- sq:discussion:end -->

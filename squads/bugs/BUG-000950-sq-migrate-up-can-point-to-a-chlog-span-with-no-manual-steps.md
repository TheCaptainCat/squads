---
id: BUG-950
sequence_id: 950
type: bug
title: sq migrate up can point to a chlog span with no manual steps in it
status: Open
author: qa
severity: medium
refs:
- BUG-937
- MILE-867:targets
created_at: '2026-09-15T08:00:35Z'
updated_at: '2026-09-15T08:03:37Z'
---
<!-- sq:body -->
## Problem

`sq migrate up` can print a "manual steps remain" line whose own suggested `sq migrate chlog`
command then reports none — a false instruction to the operator at the end of an irreversible
corpus migration.

## Driven — reproduced in a scratch squad, not the live corpus

```
$ cat .squads.toml
schema_version = "0.14"
squad_dir = "squads"
active_backends = []
squads_version = "0.15.0"

$ sq migrate up
  0.15.0 (schema v0.14→v0.15): The milestone roll-up moves off its type attachment onto a
  sq:view:milestone_rollup body tag: seed the tag on every existing milestone lacking one, …
migrated to schema v0.15; index rebuilt — run `sq sync` to refresh managed files
manual steps remain — read them with `sq migrate chlog v0.15.0..v0.15.0`

$ sq migrate chlog v0.15.0..v0.15.0
no manual steps for v0.15.0..v0.15.0
```

Exit code is 0 both times — nothing about the run signals that the pointer it just printed is
wrong.

This is exactly what happened on this repo's own 0.14→0.15 migration this session; the git
history of `.squads.toml` shows precisely this pre-migration state:

```
$ git show 07901f83 -- .squads.toml
-schema_version = "0.14"
+schema_version = "0.15"
 squad_dir = "squads"
 active_backends = ["claude_code"]
 squads_version = "0.15.0"
```

`squads_version` was already `"0.15.0"` while `schema_version` was still `"0.14"` — the exact
condition the reproduction above recreates from a fresh squad.

## Root cause — read, then confirmed by the reproduction

`_cli/_migrate.py`'s `migrate_up` builds the `chlog` span from the config's `squads_version`
field, taken *after* `run_pending_migrations()` has returned:

```python
if any(m.manual for m in applied):
    span = f"v{svc.paths.config.squads_version}..v{__version__}"
    console.print(f"[yellow]manual steps remain[/yellow] — read them with `sq migrate chlog {span}`", ...)
```

`squads_version` is documented (`_models/_config.py`) as "squads version that last generated the
managed (tool-owned) files" — it is bumped independently, by `sync()` (`_stamp_version`), and is
**decoupled from `schema_version`**. `migrate up` itself never touches `squads_version` (only
`_stamp_schema` is called from `run_pending_migrations`), so nothing in this command keeps the
two in step. Whenever `squads_version` has already reached the running package's `__version__`
before `migrate up` runs — which requires no prerelease/rc string, no clock skew, nothing exotic,
just a squad where the version stamp happened to catch up before the schema did — the span
degenerates to `vX..vX`.

That degenerate span is *structurally* empty regardless of comparator correctness:
`migrate_chlog`'s filter is `lo < m.version <= hi` (open at `lo`, `_cli/_migrate.py:135`), so
`lo == hi` can never select anything, by construction — not by an off-by-one in this case.

`applied` — the list `run_pending_migrations` reports back — is correct: it does contain the
migration, and that migration's `manual` field genuinely carries real runbook text
(`_migrations/_v0_14_to_v0_15.py::MANUAL`, driven: 15+ lines describing the milestone roll-up
tag backfill). So `any(m.manual for m in applied)` correctly fires the "manual steps remain"
line — the runner's message is not lying about the *existence* of manual steps. The lookup line
is the one that is wrong: it is pointed at a span the tool itself can prove will never contain
anything, using a value (`squads_version`) that answers a different question ("when did this
squad last sync?") than the one this line needs ("what release was this squad's schema actually
migrated from?").

## Not the same defect as BUG-937

Checked BUG-937 (`sq migrate chlog silently drops manual steps on a prerelease bound`) before
filing, since it reports the identical *symptom* (`migrate up` names a chlog span, that exact
command reports none). Its root cause is different and does not cover this case: BUG-937 is a
comparator bug — `version_tuple` mis-orders a prerelease suffix (`"0.14.0rc1"` sorts *above*
`"0.14.0"`), so a real, non-degenerate span (`lo != hi`) silently excludes an entry that should
be inside it. This defect's reproduction above uses two identical, suffix-free strings
(`"0.15.0"` twice) — `version_tuple`/`schema_tuple` ordering is not exercised at all, because
there is nothing to mis-order: the span is empty by construction before any comparison runs.
Fixing BUG-937's comparator (splitting a segment's suffix instead of concatenating its digits)
changes nothing about this case — `v0.15.0..v0.15.0` stays empty under a correct comparator too.
The two bugs share a symptom and a caller, not a mechanism; both trace to the same `migrate_up`
print site but fail via unrelated code paths (which value feeds `lo`, vs. how `lo`/`hi` compare).

## Expected vs actual

- **Expected:** every span `sq migrate up` tells the operator to read contains the manual steps
  it just said remain.
- **Actual:** whenever `squads_version` has already caught up to `__version__` before the
  migration's own schema catches up (a state this project's own release history produced,
  cleanly, with no prerelease strings involved), the printed span is guaranteed empty and the
  named migration's real manual content is unreachable through the command the tool itself gave.

## Severity

Judged **medium**. Not lower: it is a false instruction printed at the exact moment an operator
is relying on the tool to tell them the truth about an irreversible corpus rewrite, and it
reproduces from ordinary, non-exotic state (this repo's own 0.14→0.15 cut hit it, not a
constructed edge case). Not higher: the exit code stays 0, nothing is corrupted or lost, the real
manual text is not deleted — it is still readable by opening the migration's own module or by
guessing a wider span (as BUG-937's control command shows) — and the fix is local to how the span
is computed, not to the migration mechanism itself.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T08:03:37Z] Pierre Chat:
  - Targeted at 0.15. Queue it after the view features -- it is not blocking them, and the fix does
    not depend on them; it just goes out later in the release.
<!-- sq:discussion:end -->

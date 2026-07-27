---
id: TASK-665
sequence_id: 665
type: task
title: 'sq check: confirm cross-source claims before reporting them'
status: Draft
author: tech-lead
refs:
- ADR-663:implements
- BUG-655:fixes
- TASK-664:depends-on
description: Partition check's issues into single-source and cross-source; cross-source
  claims become candidates confirmed by one cheap re-read before they are reported.
subentities:
- local_id: ST1
  title: Partition check's issues into single-source and cross-source
  status: Todo
- local_id: ST2
  title: One confirm round over the candidate set
  status: Todo
- local_id: ST3
  title: Name the skew direction on a confirmed drift
  status: Todo
- local_id: ST4
  title: Claim boundary in the docstring, exit-code tests, changelog
  status: Todo
created_at: '2026-07-27T14:22:53Z'
updated_at: '2026-07-27T14:46:38Z'
---
<!-- sq:body -->
Implements ADR-663 §3. `sq check` stays lock-free; a cross-source claim becomes a *candidate*
that must survive one confirmation round before it is reported.

## Problem

`Service.check()` loads the index, then walks every item file (0.5–2s on a few hundred items),
then compares one against the other — so the comparison spans two different points in time.
This is not a corner case produced by unusual timing: because the safe write order puts the
markdown first, an in-flight create is *guaranteed* to present a file the older index snapshot
does not know, and an in-flight remove the reverse. `_index_reconciled` reports both directions
at **error** level, so a concurrent mutation makes `sq check` exit 3 — the same race that
produces a cosmetic status-drift warning also produces a false hard gate failure. That matters
because every agent runs this gate before handoff.

BUG-655 filed this as low/cosmetic. The ADR corrects that: the error-level reconciliation half
comes from the same stale-snapshot pair, so the fix has to cover both.

## Decided: no reader lock

A shared reader lock (or a brief exclusive one) is rejected. It would hold up every writer for
the length of the board's most frequent read; mutations acquire with a 10s timeout, so a real
`filelock.Timeout` would replace a false warning, and a `check` run during a bulk import (one
transaction spanning hundreds of items) would block for the whole import or time out. Do not
convert Layer 3 to a read/write lock.

## Design

Partition the issues `check` produces by their inputs.

**Single-source** — derived from one file's own text: marker damage, missing `id`, unwritten
sub-entity body, over-long titles, status-banner prose, and the override checks. Reported
as-is; they are exactly as true as the one read that produced them.

**Cross-source** — any claim comparing the on-disk scan against the index snapshot. Today that
is `_drift_issues`' status drift and parent drift (`_services/_maintenance.py`), plus both
directions of `_index_reconciled` (`_services/_validators.py`): "on disk but not in index" and
"in index but no markdown file". These become candidates, not findings. After the scan, and
only when the candidate set is non-empty, re-load the index (one small read) and re-read only
the candidate items' `.md`, then re-evaluate the same predicates against that fresh pair. Only
claims that still hold are reported.

Exactly **one** confirm round. A retry loop would not terminate under continuous mutation, and
the residual false positive needs an unlucky mutation in both the scan window *and* the confirm
window for the same item.

A clean board pays nothing: no candidates, no second pass.

## Consequences to encode

- Every cross-source claim must be evaluable for a **single item id** — that is what makes it
  confirmable. This is a standing requirement on future validators, not just a property of
  today's three: a cross-source predicate that cannot be evaluated per item cannot be confirmed
  and does not belong in `check`. `index_reconciled` is a squad-global validator whose issues
  are already per-item/per-file; keep that shape and make the requirement explicit.
- Where the two `updated_at` values order the pair, a confirmed drift names the direction:
  markdown-ahead is the expected repairable skew, index-ahead means the ordering rule was
  violated (or the failure was out of model). Both stay at `warn`, because forged clocks
  (`sq --at`) make direction an informative detail, not a gate signal.
- State in `check()`'s own docstring what it may claim: it reports the board as of a point in
  time, takes no lock, never blocks a mutation, is never blocked by one, and never writes. A
  reported drift or reconciliation error means a **real, durable** inconsistency that `sq
  repair` heals. It may **not** claim quiescence — "clean" means "no confirmed inconsistency
  was observed", not "the board is consistent now".

## Sequencing

This lands after the atomic-write work, and the reason is substantive, not scheduling: the confirm
pass only filters **cross-source** claims. While squad-data writes still truncate in place, a
concurrent reader can hit a half-written file and get a *single-source* error that no confirm round
can filter — a cut inside the frontmatter block yields `file has no 'id' in frontmatter`, and a cut
inside the body yields a half-written sq marker reported as unclosed. Both are error-level, both
come from one file's own text, and both are therefore reported as-is. So the promise this task
makes — "a reported error means a real, durable inconsistency" — is only true once writes are
atomic.

A bare `yaml.YAMLError` escaping the frontmatter split is **not** part of that rationale and is not
a failure mode to design around: it is structurally unreachable from a single truncated write,
because the frontmatter dict is fully serialized in memory before any byte is written, so a cut can
only land before the closing `---` exists or at/after it with the whole dict already on disk.

## Constraints

- No new stored field. A generation/version counter in `.squads.json` is rejected: it cannot be
  reconstructed from the markdown, so it cannot live in the index. The index file's mtime is
  legal but redundant once the confirm pass only runs when candidates exist.
- No CLI surface, flag, or output-format change. No schema bump, no migration.
- `check` still never writes anything.
- Keep the confirm pass off the hot path for a clean board — do not re-load the index
  unconditionally.
- Do not duplicate a comparison predicate between the scan pass and the confirm pass; the two
  copies would drift apart. One function per predicate, callable against either pair.
- Full gate before handoff: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .`, and the suite.

## Acceptance

- A mutation committing between the scan and the confirm pass produces no reported issue — for
  a drift candidate and for both reconciliation directions.
- A real, durable drift left on disk is reported on every run, and names its direction.
- A concurrent mutation no longer makes `sq check` exit 3.
- A clean board runs no second pass (no extra index load, no extra file read).
- `uv run sq check` clean; the suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 665 add-subtask "<title>"`; track with `sq task 665 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Partition check's issues into single-source and cross-source |  |
| ST2 | Todo |  | One confirm round over the candidate set |  |
| ST3 | Todo |  | Name the skew direction on a confirmed drift |  |
| ST4 | Todo |  | Claim boundary in the docstring, exit-code tests, changelog |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Partition check's issues into single-source and cross-source

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Split what `check()` produces today into the two classes the ADR defines, and make each
cross-source claim carry the item sequence number it was derived from, so the confirm pass can
re-read exactly those items and re-run exactly those predicates.

Cross-source, and only these three today:
- status drift and parent drift (`_drift_issues`, `_services/_maintenance.py`);
- `_index_reconciled`'s "on disk but not in index" direction;
- `_index_reconciled`'s "in index but no markdown file" direction.

Everything else — marker damage, missing `id`, unwritten sub-entity body, over-long titles,
status-banner prose, the two override checks, and the rest of the per-item catalog — is
single-source and reported as-is.

Keep each cross-source predicate a single function that can be re-run against a fresh
`(index entry, frontmatter)` pair. Do not duplicate the comparison logic between the scan pass
and the confirm pass; two copies will drift apart.

Note the asymmetry: "in index but no markdown file" has no on-disk frontmatter to re-read, so
its confirm input is the item id plus a fresh existence check against a freshly loaded index.

Also write down the standing requirement this shape imposes: a cross-source predicate must be
evaluable for a single item id, or it cannot be confirmed and does not belong in `check`. Put it
where the next person adding a validator will read it.

Acceptance:
- The candidate-vs-finding split is explicit in the code, not implied by call order.
- A test asserts a single-source issue (e.g. marker damage) is reported with no second read.
- The requirement on future cross-source validators is stated at the validator seam.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — One confirm round over the candidate set

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
After the scan, when the candidate set is non-empty, re-load the index (one small read) and
re-read only the candidate items' `.md` files, then re-evaluate their own predicates against
that fresh pair. Report only the claims that still hold.

Exactly one round: no loop, no retry, no backoff. Under continuous mutation a retry loop would
not terminate, and one round already reduces the residual false positive to a mutation landing
in both the scan window *and* the confirm window for the same item.

An empty candidate set means no second pass at all — no index re-load, no file re-read. That is
the common case and it must stay free.

Keep the re-read scoped to the candidates. A full rescan would reintroduce exactly the cost the
lock-free design exists to avoid, and would widen the window it is meant to close.

Because a mutation commits both sides while holding the lock, a candidate produced by an
in-flight transaction resolves on the recheck, while a durable inconsistency reproduces on every
recheck.

Acceptance:
- A mutation applied between the two passes drops the phantom issue — tested for a drift
  candidate and for both reconciliation directions.
- A durable inconsistency left on disk survives the confirm pass and is reported.
- On a clean board the index is loaded exactly once and no file is read twice.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Name the skew direction on a confirmed drift

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
When the two `updated_at` values order the pair, a confirmed drift says which side is ahead.
Markdown-ahead is the expected repairable skew; index-ahead means the ordering rule was violated,
or the failure was out of the stated model (host crash, power loss).

The level stays `warn` for both directions. Forged clocks (`sq --at`) make the direction an
informative detail for whoever reads the report, not a gate signal — do not promote index-ahead
to `error`.

Keep the existing "run `sq repair`" guidance in the message; the direction is added context, not
a replacement. When the timestamps do not order the pair (equal, or one missing), say nothing
about direction rather than guessing.

Acceptance:
- One test per direction asserting the message names it.
- A test asserting both directions are still `warn`, so a drift never changes the exit code.
- A test asserting no direction is claimed when the timestamps do not order the pair.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Claim boundary in the docstring, exit-code tests, changelog

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
State in `check()`'s own docstring what it may and may not claim: it reports the board as of a
point in time; it takes no lock, never blocks a mutation, is never blocked by one, and never
writes. A reported drift or reconciliation error means a real, durable inconsistency that
`sq repair` heals. It may **not** claim quiescence — "clean" means "no confirmed inconsistency
was observed", not "the board is consistent now".

Tests to add beyond the per-subtask ones:
- A concurrent-mutation run exits 0 rather than 3. Assert the exit code of a bare invocation
  (`cmd >/dev/null 2>&1; echo $?`) — a pipeline masks it.
- The whole flow end to end through the CLI, not only the service, since this is a gate agents
  invoke as `sq check`.

Name tests by the behaviour they pin, never by a ticket id — repo rule, and `tests/meta`
enforces it.

Add the adopter-facing CHANGELOG line under the unreleased section: `sq check` no longer reports
phantom drift or reconciliation errors — and no longer fails — while another process is mutating
the board. Adopter-facing wording only: no ticket ids, no repo-process detail.

Acceptance:
- The docstring carries the claim boundary.
- Exit-code test passes and asserts a bare invocation's status.
- Full suite green under `uv run --all-extras`; run it once, redirect to a file, and read the
  file rather than re-running to reslice output.
- CHANGELOG updated in the unreleased section.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T14:46:38Z] Olivia Lead:
  - Dependency rationale on TASK-664 corrected in the body — the `yaml.YAMLError` half was a phantom (BUG-668 shows the frontmatter dict is fully serialized before any byte is written, so a cut can only precede the closing `---` or follow a complete dict). The edge stands on the real half: a truncated read yields single-source errors (missing `id`, half-written marker) that no confirm round can filter, so this task's promise only holds once writes are atomic.
<!-- sq:discussion:end -->

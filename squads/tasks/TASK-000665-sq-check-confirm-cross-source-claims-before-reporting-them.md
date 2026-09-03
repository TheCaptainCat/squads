---
id: TASK-665
sequence_id: 665
type: task
title: 'sq check: confirm cross-source claims before reporting them'
status: Done
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
  status: Done
  assignee: python-dev
- local_id: ST2
  title: One confirm round over the candidate set
  status: Done
  assignee: python-dev
- local_id: ST3
  title: Name the skew direction on a confirmed drift
  status: Done
  assignee: python-dev
- local_id: ST4
  title: Claim boundary in the docstring, exit-code tests, changelog
  status: Done
  assignee: python-dev
created_at: '2026-07-27T14:22:53Z'
updated_at: '2026-07-28T07:24:43Z'
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

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Partition check's issues into single-source and cross-source

<!-- sq:subtask:ST1:body -->
Cross-source claims (status/parent drift; both index/disk reconciliation directions) split from single-source scan issues in _services/_maintenance.py and _services/_validators.py. Drift is decomposed into _status_drift/_parent_drift/_drift_issues (single-item, reused unchanged by scan and confirm); index_reconciled's two directions factored into _on_disk_not_indexed(seq, fid, *, indexed: bool)/_not_on_disk(item, *, on_disk: bool) — bool-flag signatures, evaluable per item id. The per-item-id requirement is stated on SquadGlobalValidator's docstring, the seam where the next validator gets added. A dedicated test proves a single-source issue (marker damage) triggers no second index load.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — One confirm round over the candidate set

<!-- sq:subtask:ST2:body -->
Service.check() now runs a scan pass, then _confirm_cross_source(index, on_disk): if the drift/orphan/missing candidate sets are all empty it returns immediately (no reload, no reread). Otherwise it reloads the index once and, per candidate, re-observes at the path the fresh index gives that item (drift: reread the file there; missing: existence check there) — the orphan direction has no fresh index-given path, so it re-checks the original scanned path plus fresh index membership, matching the ADR's asymmetry note. Same predicate functions run in both passes (no duplicated comparison). Verified with genuine two-coroutine interleaving (anyio task group + a real transaction landing inside a paused _scan_for_check) for all three candidate kinds, plus a CLI-level version using a real background thread through the full sq check stack. Sabotage-checked: reverting the confirm round to unconfirmed reporting makes exactly these tests fail (both service- and CLI-level), while the durable/true-positive tests keep passing.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Name the skew direction on a confirmed drift

<!-- sq:subtask:ST3:body -->
_drift_direction(item, fdata) compares item.updated_at (index) against the frontmatter's own updated_at (parsed via clock.parse_iso); returns markdown/index/None. _drift_message appends '— markdown is ahead' or '— index is ahead of markdown, which should not happen' only when determinable; level stays warn either way. Tests pin both directions, the warn level in both, and that no direction is claimed when the pair doesn't order (equal timestamps).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Claim boundary in the docstring, exit-code tests, changelog

<!-- sq:subtask:ST4:body -->
check()'s docstring now states the claim boundary: no lock, never blocks/blocked, never writes; a reported issue means a real durable inconsistency; a clean result means no confirmed inconsistency was observed, not that the board is consistent now. Exit-code coverage: a service-level test asserts the index is loaded exactly once on a clean board and exactly twice when a candidate exists; CLI-level tests (through invoke/CliRunner, one via a real background thread racing the CLI's own check() through a class-level _scan_for_check pause) assert exit 0 under a race and exit 3 for a durable orphan, plus one literal subprocess invocation (no shell pipe) for the plain clean-board case. CHANGELOG [0.12.2]/Changed gained the adopter-facing line; no ticket ids.
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
- [2026-07-27T20:29:56Z] Elias Python:
  - All 4 subtasks Done. ADR-663 §3 implemented as written, with one point of interpretation: for the on-disk-but-not-indexed direction the ADR's 'path the freshly loaded index gives for that item' has no referent (nothing indexes it), so the confirm re-observation there is the original scanned path + fresh index membership — matches ST1's own asymmetry note, which only spells this out for the other direction.
  - check() partitions issues into single-source (reported as-is) and cross-source candidates (drift, both reconciliation directions); a non-empty candidate set triggers exactly one index reload + per-candidate reread, never a full rescan. Confirmed drift names markdown-ahead/index-ahead when the updated_at pair orders it, warn either way, silent when it doesn't.
  - sq check exit codes: clean board or a resolved-by-confirm candidate -> 0 (no cross-source issue reported); a real durable drift or reconciliation break -> 3 exactly as before, now naming direction for drift. A mutation racing the scan never produces a phantom warn or error.
  - Tests: tests/service/test_check_confirms_cross_source_claims.py (12) - genuine two-coroutine interleaving via anyio task group + a paused _scan_for_check for all 3 candidate kinds, the clean-board-pays-nothing / single-source-no-second-read checks, 3 durable-inconsistency-still-reported tests, 3 direction tests. tests/cli/test_check_confirms_cross_source_claims_cli.py (4) - same race through the full CLI via a real background thread + class-level monkeypatch, a durable-orphan exit-3 test, a clean-board exit-0 test, and one literal subprocess invocation (no shell pipe).
  - Verified the headline tests aren't stubs: temporarily reverted _confirm_cross_source to report straight from the scan pair (pre-fix behavior) - the 3 concurrency tests + the reload-count test failed as expected (both service and CLI level), the durable/true-positive tests kept passing. No case found where the confirm round swallows a real inconsistency.
  - Gates green: pyright/ruff check/ruff format --check on all touched files; tests/meta clean (ticket-ID hygiene scan required 2 rounds of cleanup - first pass left an ADR reference in a validators.py comment). CHANGELOG [0.12.2]/Changed line added (no version bump - left for the release cut). Did not touch _index/_store.py, store._log, or the mixins; did not run sq check or the full suite (both yours per brief); no commits.
- [2026-07-27T20:34:07Z] Elias Python:
  - Amendment per the re-amended ADR-663 §1/§3: _drift_message now tells the reader to repair before mutating that item again, not merely to repair. New composition: '{field} drift between frontmatter and index{direction suffix}; run `sq repair` before this item is mutated again, or the fix is lost silently.' Direction suffix unchanged and still composes cleanly (em-dash clause, then the semicolon-separated action clause).
  - No existing test asserted the old exact string ('(run `sq repair`)' as a drift-message suffix) - only my own new test file did, and only via substrings that survive unchanged ('status drift', 'markdown is ahead', 'index is ahead of markdown', absence of 'ahead' when undetermined). Updated nothing else; reconciliation messages (on disk but not in index / in index but no markdown file) are untouched - out of scope, and not what §1's healing-window argument is about (there's no frontmatter value to silently lose there).
  - Gates green (pyright/ruff check/ruff format --check on _maintenance.py), tests/meta clean, both test files still 16/16 green. Did not reopen any other file.
<!-- sq:discussion:end -->

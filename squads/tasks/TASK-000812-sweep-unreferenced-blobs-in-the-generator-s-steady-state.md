---
id: TASK-812
sequence_id: 812
type: task
title: Sweep unreferenced blobs in the generator's steady state
status: Done
parent: FEAT-791
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-777:implements
- REV-808:addresses
- TASK-799
description: Give the manifest generator a reachability sweep so an unreferenced blob
  cannot survive a regeneration, and restate never-prune as no revision an index entry
  names is ever removed
subentities:
- local_id: ST1
  title: Reachability sweep in the generator's write mode
  status: Done
  story: US1
- local_id: ST2
  title: Orphan guard as a maintained invariant
  status: Done
  story: US1
created_at: '2026-08-25T18:11:01Z'
updated_at: '2026-08-25T23:40:08Z'
---
<!-- sq:body -->
## Scope

ADR-777 amendment C1, on FEAT-791 US1. The content store's two coverage assertions are
reconciled: an unreferenced blob is not retained history. The generator's steady-state contract
gains one clause — **drop a blob no index entry references** — and the orphan guard is promoted
from an assertion that something went wrong into an invariant the generator maintains.

## The case is the ordinary development loop, not an edge case

The index's per-version entry is a **wholesale replacement** keyed on `[project].version`
(`scripts/gen_template_manifest.py:151-169`), while the store is **insert-if-absent, never
deletes** (`:162-167`, and the contract stated at `:19-20`). So every intermediate revision of an
artifact within one release is orphaned by the next regeneration. No deletion is involved
anywhere.

Driven by the architect in a copied tree against the shipped documents: edit one bundled template
and regenerate, one orphan; edit and regenerate again, two; restoring the template to its shipped
content clears neither. Changing and then deleting an artifact in one release — the shape this
surfaced as — is one instance of the general case.

**Verified against the shipped documents in this tree**, which shows exactly how reachable it is:
84 blobs, 84 referenced, 0 orphans today; and six artifact keys already carry content named
**only** by the `0.14.0` entry — `agents/item_skill.md.j2`, `agents/role.md.j2`,
`agents/squads_skill.md.j2`, `claude/claude_section.md.j2`, `workflow.md.j2` and
`_specs/workflow.toml`. Any further edit to one of those six orphans its current blob on the next
regeneration and reds the suite. By contrast `workflow_static.md.j2` and `_specs/playbook.toml`
carry blobs also named by `0.13.0`/`0.13.1`, so a first edit to either does not orphan.

## What changes, and what does not

- **The orphan assertion does not yield.**
  `tests/meta/test_override_manifest_and_stamp_freshness.py:150-158` was written to catch "the
  orphan a bug or a hand-edit would otherwise accumulate silently"; that premise does not reach a
  routine regeneration. A guard with no discharging action available for a sanctioned operation
  does not report a problem, it becomes one. It stays, and becomes an invariant the generator
  maintains. Its docstring, which says "with nothing pruning", stops being true and moves with it.
- **The generator's steady-state contract gains one clause.** Its statement at `:22-24` — "hash
  the current tree, replace this version's index entry, insert what is absent from the store" —
  gains the sweep, and the never-deletes sentence at `:19-20` is narrowed with it.
- **`sq override diff`'s promise is untouched by construction.** Every revision that promise
  covers is named by an index entry, so a reachability sweep cannot remove one. The architect
  drove the sweep against the shipped store: 2 blobs removed, all 84 index-named hashes still
  resolving, `--check` clean.

## Never-prune, stated precisely

**No revision an index entry names is ever removed.** That is the sentence to carry forward, and
it is a narrowing of "never deletes" to what its own reason supports rather than an overruling of
it.

The hazard the original clause names is a mis-ordered regeneration destroying retained history
under the index's replace semantics. A run rewrites exactly one entry — the current version's —
so the only blobs it can orphan are revisions that entry alone named; historic entries are never
rewritten, so no revision they name can become unreferenced, and the sweep provably cannot reach
one. That argument is the reason the sweep is safe, and it belongs in the code that performs it,
not only in the decision record.

## The rejected alternative, so it is not re-proposed

Requiring a deletion to ride a release in which the artifact is otherwise unchanged. It is
unenforceable, silent when violated, answers only the deletion instance while leaving the
double-edit case to accumulate, and makes a sanctioned operation conditional on an unrelated axis
that whoever performs it has to remember. Deleting bundled artifacts outright is already
sanctioned, so that rule would be a trap laid for a decision already made.

## Traps

- **Sweep on reachability across the whole index, never on "not in the current tree".** A blob
  reachable from any version's entry stays. The predicate is `set(store) - {every hash every
  entry names}` — the same set the guard computes.
- **`--check` writes nothing and must stay that way** (`:105-148`). It may report an orphan; it
  may not remove one.
- **The seeding script is not in scope.** The store's history below this release was populated
  once as a data step against release tags, not as a capability of the generator.
- **The compressed ceiling is unaffected and slightly better served** — a swept blob is bytes
  nothing can diff against, so the ceiling keeps measuring retention rather than churn. The
  ceiling assertion stays as it is.
- **Both retention guards must keep passing after a sweep**: every index-named hash resolves
  (`:135-147`), and the store's version coverage still reaches the index's own floor.

## Acceptance

- A write-mode run removes every blob no index entry references, and removes nothing else.
- Editing a bundled artifact and regenerating twice leaves the store with no orphan, and every
  index-named hash across every version still resolving.
- Deleting a bundled artifact and regenerating leaves the store with no orphan, historic entries
  and their blobs intact, and the key gone only from the current version's entry.
- A blob named by any historic entry is never removed, proven by a case where the current
  version's entry stops naming it while an older entry still does.
- `--check` reports but never removes, and still writes nothing.
- The orphan guard passes as an invariant rather than by luck, and its docstring states what the
  generator now maintains instead of "with nothing pruning".
- The generator's steady-state contract and its never-deletes statement read as the narrowed rule:
  no revision an index entry names is ever removed.
- `python scripts/gen_template_manifest.py --check` is clean, and the store stays under its
  compressed ceiling.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 812 add-subtask "<title>"`; track with `sq task 812 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Reachability sweep in the generator's write mode

<!-- sq:subtask:ST1:body -->
Add the reachability sweep to the generator's write mode
(`scripts/gen_template_manifest.py:151-169`): after the index entry for `[project].version` is
replaced and the current tree's blobs are inserted, remove every blob no index entry references.

The predicate is reachability across the **whole** index, not membership of the current tree:
`set(store) - {every hash every version's entry names}` — the same set the orphan guard computes.
A blob reachable from any version's entry stays.

Why this is safe, and the argument belongs in the code rather than only in the decision record: a
run rewrites exactly one entry, the current version's, so the only blobs it can orphan are
revisions that entry alone named. Historic entries are never rewritten, so no revision they name
can become unreferenced, and the sweep provably cannot reach one.

Restate the two contract sentences the sweep changes:

- the never-deletes statement (`:19-20`) becomes the narrowed rule — **no revision an index entry
  names is ever removed** — with the reason above, not a bare assertion;
- the steady-state contract (`:22-24`), today "hash the current tree, replace this version's index
  entry, insert what is absent from the store", gains the sweep clause.

`--check` (`:105-148`) writes nothing and must stay that way. It may report an orphan; it may not
remove one.

Out of scope: `scripts/seed_content_store.py`. The store's history below this release was
populated once as a data step against release tags, not as a capability of this generator.

Report what was swept in the run's output the way insertions are reported, so a regeneration that
removes bytes says so.

Done when a write-mode run leaves no unreferenced blob, removes nothing an entry names, `--check`
still writes nothing, and both contract sentences read as the narrowed rule.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Orphan guard as a maintained invariant

<!-- sq:subtask:ST2:body -->
Promote `tests/meta/test_override_manifest_and_stamp_freshness.py:150-158` from an assertion that
something went wrong into the invariant the generator maintains, and cover the sweep.

The guard stays. Its docstring does not: it currently reads "With nothing pruning, an orphaned
blob is the only sign of a hand-edit or generator bug — this is the guard that would catch it",
and pruning is exactly what changes. State instead what the generator maintains, so the next
reader is not told the store is append-only.

Cover the sweep itself, in a copied tree so the repo's own documents are untouched:

- edit a bundled artifact and regenerate **twice**: no orphan afterwards, and every index-named
  hash across every version still resolves;
- delete a bundled artifact and regenerate: no orphan, historic entries and their blobs intact,
  and the key gone only from the current version's entry;
- a blob the current version's entry stops naming while an **older** entry still names it: not
  removed — this is the leg that proves never-prune, and it is the one a sweep written against the
  current tree instead of the whole index would fail;
- `--check` on a store carrying an orphan: reports, writes nothing, leaves the orphan in place.

The two retention guards must keep passing alongside it: every index-named hash resolves
(`:135-147`), and the store's version coverage still reaches the index's own floor. The
compressed-ceiling assertion is unaffected and stays as it is.

Assert the sweep on the store's contents, not only on the guard passing — a test that just re-runs
the guard cannot tell a sweep from a store that happened to have no orphans.

Done when all four cases pass, the guard's docstring describes the maintained invariant, and the
retention guards are green beside it.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T18:14:06Z] Olivia Lead:
  - Authored from ADR-777 C1. Verified the mechanism: the index entry is a wholesale replacement keyed on the project version (gen_template_manifest.py:151-169) while the store is insert-if-absent (:162-167, contract at :19-20), and the orphan guard sits at tests/meta/test_override_manifest_and_stamp_freshness.py:150-158 with a docstring that says "with nothing pruning" - which is what stops being true.
  - Measured how reachable this is against the shipped documents rather than restating the drive: 84 blobs, 84 referenced, 0 orphans today, and SIX artifact keys already carry content named only by the 0.14.0 entry - agents/item_skill, agents/role, agents/squads_skill, claude/claude_section, workflow.md.j2 and _specs/workflow.toml. Any further edit to one of those six orphans its blob on the next regeneration and reds the suite. workflow_static.md.j2 and _specs/playbook.toml carry blobs also named by 0.13.x, so a first edit to either does not.
  - Priority is high rather than the finding low severity, on that measurement: it is not a latent tidiness issue, it blocks the next task in this release that edits _specs/workflow.toml. TASK-813 carries the depends-on. TASK-798 is NOT blocked - I checked its two artifacts and both are shared with 0.13.x.
  - ST2 keeps the leg that proves never-prune: a blob the current entry stops naming while an older entry still does must survive. That is the leg a sweep written against the current tree instead of the whole index would fail, and it is the one the guard alone cannot distinguish. @python-dev
- [2026-08-25T22:12:40Z] Elias Python:
  - ST1: sweep added to _write_mode() (scripts/gen_template_manifest.py) — after the index entry replace + insert-if-absent, compute referenced = union of hashes across ALL manifest entries and delete any store key not in it. Reported alongside inserted count.
  - Repro against the shipped documents (copied tree, real script): edit role.md.j2 + regen -> 1 inserted, 1 swept, store stays at 84/0 orphans (unswept baseline would have grown to 85/1). Edit again + regen -> same: 84/0. Restore original content + regen -> converges back to byte-identical shipped store. Delete role.md.j2 + regen -> 83 blobs, 0 orphans, key gone only from 0.14.0's entry, historic entries (0.4.0-0.13.1) untouched.
  - --check now also reports an orphan (new check against the whole index, same predicate the guard uses) but still writes nothing — covered by a dedicated test.
  - git diff on the real repo: templates_manifest.json and content_store.json show NO diff at all (already clean, 0 orphans before I started) — confirms the sweep is a true no-op here and nothing but 0.14.0 could have moved.
  - ST2: guard docstring at tests/meta/test_override_manifest_and_stamp_freshness.py now states the invariant the generator maintains instead of 'with nothing pruning'. Added 5 tests driving scripts/gen_template_manifest.py directly (same sys.path pattern as the bump_version script test) against a copied tree: double-edit no-orphan, delete-keeps-history (3 distinct historic hashes for role.md.j2 across releases all survive), the never-prune leg (a blob only a historic entry names survives a no-op run — proves the sweep reads the whole index, not the current tree), and --check reports+never-removes an orphan. tests/meta: 231 passed.
  - Gates clean repo-wide: pyright/ruff check/ruff format --all-extras all pass. No sq IDs or § markers in the diff.
- [2026-08-25T23:40:07Z] Catherine Manager:
  - Delivered as specified and reviewed, then superseded within the round: the sweep it built was withdrawn after review found it destroys shipped store history once the running version has been released. The rebuilt-store design that replaces it is TASK-822. Closing Done against what was delivered, not against what survives.
<!-- sq:discussion:end -->

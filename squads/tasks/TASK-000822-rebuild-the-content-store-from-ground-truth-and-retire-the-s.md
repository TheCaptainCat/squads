---
id: TASK-822
sequence_id: 822
type: task
title: Rebuild the content store from ground truth and retire the sweep
status: Done
parent: FEAT-791
author: tech-lead
assignee: python-dev
priority: urgent
refs:
- REV-817:addresses
- ADR-777:implements
- TASK-812
- TASK-799
- TASK-816
- MILE-836:targets
description: Withdraw the generator's reachability sweep, make removal a capability
  of an all-or-nothing rebuild against the release tags, and widen the freshness check
  to the whole index
subentities:
- local_id: ST1
  title: Withdraw the sweep from the generator's write mode
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST2
  title: Rebuild the store from the tags, all-or-nothing
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST3
  title: Widen --check to the whole index and state what it checked
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST4
  title: Move the orphan assertion to the release gate
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST5
  title: Parametrise the retention fixture off the running version
  status: Done
  assignee: python-dev
  story: US1
created_at: '2026-08-25T23:08:49Z'
updated_at: '2026-08-26T16:01:06Z'
---
<!-- sq:body -->
## Scope

FEAT-791 US1 — the content store's removal semantics, the freshness check's reach, and the coverage
that would have caught both. ADR-777 amendments D1 through D7.

This is a **release blocker, not a background cleanup.** The generator's write mode currently sweeps
every blob no index entry references, immediately after replacing the running version's entry
wholesale. That is safe only while `[project].version` names a version that has never shipped. It
names `0.14.0`, which is not tagged — so the destructive window opens the moment `v0.14.0` is cut,
and stays open until someone bumps.

## Repository state today: exposed, not damaged

Verified against the tree: the index covers 16 versions, the store holds 85 blobs, 85 are
referenced, 0 index-named hashes are unresolvable, 0 orphans, and neither document differs from
git. Every indexed version except `0.14.0` has a local tag. Nothing is broken and nothing needs
recovering — the work here is closing the hole and making the loss reportable, not repairing a
corpus.

The corpus is also recoverable, which sizes the fix. The architect damaged a clone — a regeneration
at a shipped version destroyed three blobs and rewrote 11 of that entry's 29 hashes — and
`scripts/seed_content_store.py` alone reproduced both documents byte-identically against the branch
head, printing every correction. So this is not data-loss recovery. What carries the severity is
that nothing reports the loss, nothing documents the recovery, and the corpus reads clean while
broken.

## Why the sweep cannot be repaired in place

D1's finding, and the reason two obvious patches are both wrong:

- **Scoping the sweep to blobs the run itself orphaned removes nothing.** In the released-version
  case those blobs *are* the shipped revisions. The patch makes the sweep provably equal to its
  stated premise while leaving the premise false.
- **Refusing to rewrite an existing entry whose hashes differ from the tree** refuses the ordinary
  development loop — the second and every later regeneration of the working version, which is the
  case the sweep exists to serve.

From inside the working tree the two are indistinguishable: *an entry for V names hashes this run no
longer names* describes a discarded scratch revision of an unreleased V and a shipped revision of a
released V equally well. Only publication separates them, and publication is not in the tree. Do not
attempt a third variant of the same repair — the premise cannot be made true where the sweep runs.

Publication is knowable only from the release tags, and the generator never reads git by design
(a rule answering off the local tag list gives different answers per clone, and fails unsafe when it
cannot see a tag). So the discriminator moves to the actor that already holds it.

## Verified against the tree

- `scripts/gen_template_manifest.py:186-193` — the sweep, with C1's safety argument restated in the
  comment above it. `:19-24` states the same argument in the module docstring, and `:27-29` states
  the steady-state contract that has to lose its last clause.
- `scripts/gen_template_manifest.py:127-145` — `_check_mode` binds `recorded = manifest[version]`
  and verifies coverage for that one entry. `:147-152` is the orphan scan, which detects an extra
  blob where the failure of interest is a missing one. `:161` prints `store coverage ok` off that
  single entry.
- `scripts/seed_content_store.py:145-149` — the seeder **skips** an untagged version and continues.
  That is correct today for the running version, which the generator owns, and it is exactly the
  skip D3 forbids for any other version. The rebuild has to tell those two cases apart.
- `scripts/seed_content_store.py` is insert-only end to end; it has no removal path. The rebuild is
  a new capability on it, not a re-run of what is there.
- `tests/meta/test_override_manifest_and_stamp_freshness.py:328-330` — the `sweep_tree` fixture
  copies the repository's `pyproject.toml` verbatim; `:352-355` — `_run_write_mode` calls
  `gen._current_version()`. So every retention and sweep test runs at the repository's own version,
  including `test_a_blob_only_a_historic_entry_names_survives_the_sweep` (`:409`), the leg written
  to prove never-prune. It exercises only the half of the argument that was true.

## What the store becomes

Its authoritative definition is not "what the generator has accumulated" but **every hash the index
names, resolved to its content** — a total function of the index, the release tags and the working
tree. A derived artifact is rebuilt, not pruned incrementally.

## Acceptance

1. The generator's write mode never deletes. Its steady-state contract is hash the current tree,
   replace this version's index entry, insert what is absent from the store — and the docstring and
   inline comment say exactly that, with no residue of the withdrawn safety argument.
2. A rebuild recomputes the store as the closure of every index-named hash, sourced from each
   version's tag and — for the running version — from the working tree, and drops whatever is not in
   that closure.
3. The rebuild is **all-or-nothing**. A version whose ground truth it cannot reach is a refusal that
   names the version and deletes nothing. Never a skip: skipping is what turns an incomplete tag
   list into silent loss, the same failure mode in a new place. The refusal names `git fetch --tags`
   first, because a stale local tag list is the likeliest cause.
4. The rebuild reports an index entry that disagrees with its own tag, and corrects it to the tag.
   That is the mis-ordered regeneration, visible only to something holding both.
5. `--check` verifies coverage across the whole index — every version, every key — failing when any
   index-named hash does not resolve, naming the version and the artifact rather than a count.
6. The success line states what was checked and over which versions. A message asserting more than
   its check performed is the defect, not a wording preference.
7. An orphan is reported and does not fail an ordinary check; it fails the release gate, where the
   rebuild that discharges it runs. The store-size ceiling is measured on the rebuilt store.
8. `--check` still writes nothing, ever.
9. The recovery is documented where someone hitting the loss will find it — the two scripts'
   docstrings and the release runbook — including that restoring the index entry from the tag alone
   is insufficient and the rebuild is what completes it.
10. Coverage per D6, below, all four legs.
11. `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` clean; the full suite
    green; both documents byte-identical to git after a no-op run.

## Coverage owed (D6), written so it cannot pass vacuously

- **The fixture takes its version as a parameter and asserts that version differs from the
  repository's.** This clause is what makes the other three non-vacuous: a fallback to the running
  version has to fail loudly rather than pass quietly.
- One case **at a version the copied index already carries, with hashes differing from the copied
  tree**, asserting every hash that entry named still resolves afterwards. Owed whatever mechanism
  ships.
- One case that **damages the corpus, applies the documented recovery, and asserts the whole index
  resolves.** Its absence is what let a broken corpus report clean.
- One case where **`--check` fails for a hash missing from a historic entry**, not the running
  version's.

## Out of scope

- Anything the review's other findings cover. This task is F1 alone.
- Changing what the index records, its key namespace, or the per-version wholesale-replace
  semantics. Only removal, the check's reach, and the coverage move.
- Running `scripts/bump_version.py`. `pyproject.toml` is at `0.14.0`, unshipped, and the release's
  regenerations are keyed to it.

## Ordering

`TASK-816` is a manifest-regenerating edit in flight. It is safe while `0.14.0` is untagged and
becomes the exact destructive case if the tag lands first. Either it regenerates before the tag, or
after this task removes the sweep. Recorded on both; not a blocking dependency, because nothing in
either task's own work waits on the other.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 822 add-subtask "<title>"`; track with `sq task 822 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Withdraw the sweep from the generator's write mode | US1 |
| ST2 | Done | python-dev | Rebuild the store from the tags, all-or-nothing | US1 |
| ST3 | Done | python-dev | Widen --check to the whole index and state what it checked | US1 |
| ST4 | Done | python-dev | Move the orphan assertion to the release gate | US1 |
| ST5 | Done | python-dev | Parametrise the retention fixture off the running version | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Withdraw the sweep from the generator's write mode

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US1 — Widen the manifest to every overridable bundled artifact
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Delete the reachability sweep at `scripts/gen_template_manifest.py:186-193` and the `swept` counter
it feeds into the write-mode report. Write mode returns to three steps: hash the current tree,
replace this version's index entry, insert what is absent from the store.

Three pieces of prose carry the withdrawn argument and all three have to go, not be softened:

- the module docstring's store paragraph at `:19-24`, which restates the safety argument verbatim;
- the steady-state contract sentence at `:27-29`, whose last clause is "drop every blob no index
  entry references";
- the inline comment above the sweep itself.

Replace them with what ships: the generator never deletes, and removal is the rebuild's. Point at
the rebuild by name so a reader who wants a blob gone knows where to go — a rule with no
discharging action is what produced the sweep in the first place.

Do not leave a flag, an opt-in, or a commented-out sweep. The premise is false in a state this
repository enters on tag day; a dormant copy is a future re-enablement.

The write-mode report line loses its swept count. Check whether any test asserts that wording before
changing it.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Rebuild the store from the tags, all-or-nothing

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US1 — Widen the manifest to every overridable bundled artifact
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Give `scripts/seed_content_store.py` a rebuild capability: recompute the store as the closure of
every index-named hash, sourced from each version's release tag and — for the running version only —
from the working tree, then drop whatever is not in that closure.

No premise about sequencing is involved. The closure is computed from ground truth rather than
inferred from what changed, which is the whole reason removal belongs here and not in the generator.

**All-or-nothing, and this is the part to get right.** The script today does
`skipped_untagged.append(version); continue` at `:145-149`. That is correct for the running version,
whose entry the generator owns from the tree, and it is exactly the skip D3 forbids for anything
else. So the rebuild needs the discriminator stated explicitly: the running version is sourced from
the tree; every other indexed version must resolve from its tag or the rebuild refuses, names the
version, and deletes nothing. Verified against the tree today, all 15 non-running indexed versions
are tagged locally and `0.14.0` is not — so the happy path is reachable and the refusal is not
theoretical, it is what protects a fresh or shallow clone.

The refusal message names `git fetch --tags` as the first remedy. A stale local tag list is the
likeliest cause and it is the one the operator can fix in a second.

Same pass: an index entry disagreeing with its own tag is the mis-ordered regeneration, visible only
to something holding both. The seeder already detects and prints exactly that (`corrections`, and
the NOTE block at `:154-162`) — make sure the rebuild path reports it the same way and corrects to
the tag rather than to the store.

Prove it end to end: damage a clone the way the ruling describes — set `[project].version` to a
shipped release, regenerate, watch blobs go — then run the rebuild alone and assert both documents
come back byte-identical to the branch head with `git diff` empty. Report the damage and the
recovery, not just the recovery.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Widen --check to the whole index and state what it checked

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US1 — Widen the manifest to every overridable bundled artifact
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
`_check_mode` binds `recorded = manifest[version]` at `:127` and verifies coverage for that one
entry, then prints `store coverage ok` at `:161`. A store missing a shipped revision reports clean,
and write mode re-inserts only from the current tree, so nothing re-heals it either. That is how a
broken corpus reads clean.

Widen it: every version, every key. The retention promise is stated over every release the index
covers, so the gate that discharges it has to be stated over the same set. A failure names the
version and the artifact — `0.9.0:_rendering/templates/workflow.md.j2` — not a count. A count tells
the operator something is wrong and nothing about what.

Then fix the success line, which is the defect and not a wording nit: it says what was actually
checked and over which versions. Something an operator can read and tell whether the whole index or
one entry was verified.

The running version's own freshness checks — missing, phantom, stale — stay scoped to the running
version. Only the store-coverage half widens.

`--check` still writes nothing. Assert that: run it against a damaged store and confirm both
documents are byte-identical afterwards.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Move the orphan assertion to the release gate

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US1 — Widen the manifest to every overridable bundled artifact
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
An orphan-free store is a property of the release artifact, not of the working tree. Between
releases, discarded revisions of the working version are ordinary development residue and assert
nothing about retention; the rebuild at the cut clears them.

So: `--check`'s orphan scan (`:147-152`) keeps reporting orphans and stops failing an ordinary
check. The failure moves to the release gate, where the rebuild that discharges it runs — an orphan
there means the rebuild has not been run, which is actionable, whereas an orphan in a dev tree means
someone edited a template twice.

The store-size ceiling moves with it: measured on the rebuilt store, so it keeps measuring retention
rather than churn. Find the existing ceiling assertion before changing it and confirm what it
currently measures rather than assuming.

Wire the rebuild into the release runbook as a step before the tag, and say in the runbook what its
refusal means and how to clear it. A gate whose discharging command is not written down is the
shape of problem this whole change exists to remove.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Parametrise the retention fixture off the running version

<!-- sq:subtask:ST5:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US1 — Widen the manifest to every overridable bundled artifact
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
The `sweep_tree` fixture copies the repository's `pyproject.toml` verbatim
(`tests/meta/test_override_manifest_and_stamp_freshness.py:328-330`) and `_run_write_mode` reads the
version back through `gen._current_version()` (`:352-355`). Every retention and sweep test therefore
runs at the repository's own version — including `test_a_blob_only_a_historic_entry_names_survives
_the_sweep` (`:409`), the leg written to prove never-prune, which exercises only the half of the
argument that was true. A leg that cannot fail is not coverage.

**Take the version as a fixture parameter and assert it differs from the repository's.** That
assertion is the load-bearing one — without it a future refactor silently falls back to the running
version and every leg below passes quietly. Make its failure message say so.

Then the three legs:

- One at a version the copied index already carries, with hashes differing from the copied tree,
  asserting every hash that entry named still resolves afterwards. This is owed whatever mechanism
  ships, so write it against the behaviour rather than against the implementation.
- One that damages the corpus, applies the documented recovery, and asserts the whole index
  resolves. Its absence is what let a broken corpus report clean, so this leg is the regression test
  for the finding itself.
- One where `--check` fails for a hash missing from a **historic** entry, not the running version's.

Falsify each before handing back: break the behaviour, watch the leg go red, restore it, watch it go
green, and report both.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T23:35:10Z] Elias Python:
  - Sweep withdrawn from gen_template_manifest.py write mode (code + all 3 prose sites: docstring store paragraph, steady-state contract, inline comment). Write mode is back to hash/replace/insert only.
  - seed_content_store.py gained --rebuild: recomputes each version's entry from git ls-tree at its own tag (not trusted from the possibly-corrupted key set on file) — running version from the working tree — union of hashes becomes the store, drops the rest. All-or-nothing: an untagged non-running version refuses (names it, points at git fetch --tags) and writes nothing at all.
  - --check widened to whole-index store coverage (version:artifact naming), success line states what it checked; orphan always reported, only fails under new --release-gate.
  - Release runbook (SKILL-508) and both scripts' docstrings document the recovery and the new step order: rebuild before the release-gate check, before the tag.
  - Driven end to end on a real clone: damage (pin to 0.9.0, regenerate) then --rebuild recovers byte-identical to git; untagged-version refusal verified with a synthetic missing tag and writes nothing; real repo's own manifest/store are byte-identical after a --rebuild no-op.
  - tests/meta/test_override_manifest_and_stamp_freshness.py: rebuild_tree fixture takes version as a parameter, asserts it differs from __version__ (falsified: removing that assert makes the guard-proving test fail with DID NOT RAISE, confirming it's load-bearing) — 4 new/rewritten legs per D6 plus the sweep-era tests updated for no-deletion. tests/meta: 237 passed. Targeted file: 23 passed.
  - pyright/ruff check/ruff format clean (--all-extras). sq check clean. Both templates_manifest.json and content_store.json unchanged in git status throughout.
  - Not done: full pytest suite (left for the gate per instructions); no CHANGELOG entry (scripts/ is a repo dev tool, not adopter-facing).
- [2026-08-25T23:53:25Z] Paul Reviewer:
  - Reviewed at 2a81c06 — REV-823, 8 findings (1 critical, 1 high, 3 medium, 3 low). Acceptance 1, 5, 7, 8 and the D6 coverage all verified by driving the CLI. Acceptance 2/3 do not hold: the rebuild sources the running version from the working tree even when its tag exists, so it destroys a shipped release's blobs in the between-releases window (REV-823 F1), and an unreadable or artifact-less tag empties an entry instead of refusing (F2). Acceptance 9 (the documented recovery) is wrong as written for the very case it names. Leaving the status alone — @manager @tech-lead.
- [2026-08-26T00:07:05Z] Elias Python:
  - Addressed REV-823 F1-F5 (F6-F8 left, tracked separately).
  - F1 (critical): discriminator fixed. _resolve_version() now sources a version from its own tag whenever the tag exists, including when that version is also the running one -- only a truly untagged version falls back to the tree. Driven: v0.14.0 tagged + still running + a post-tag edit + --rebuild now corrects the entry to the tag and keeps the shipped blob, where before it deleted it.
  - F2 (high): the rebuild now has a floor. _git_ls_tree distinguishes a git failure (None) from a legitimate empty listing ([]); a tag whose listing comes back empty while the index previously recorded templates for it is also a refusal. Driven both shapes from the review (a git-ls-tree shim exiting 128; v0.4.0's tag moved onto the root commit) -- both refuse, exit 1, nothing written.
  - F3 (medium): --check now tracks freshness problems (running version, generator fixes) separately from store problems (whole-index coverage + release-gate orphan, only the rebuild fixes) and names the remedy that actually applies, both if both fired.
  - F4 (medium): SKILL-508 rewritten to one ordered sequence -- bump, then fetch tags + rebuild + release-gate, then commit both documents -- with the reason the bump has to come first stated explicitly, and each of the gate's two failure shapes given its own remedy.
  - F5 (medium): both scripts reject an unrecognized flag with exit 2 and a usage line; seed_content_store.py also refuses --check + --rebuild together rather than letting --rebuild's write win silently.
  - Coverage added: a fixture leg pins the version to an already-tagged release and rebuilds without ever moving off it (the exact F1 state), asserting the tag wins and the shipped blob survives; a second leg fakes one tag's listing empty via monkeypatch (real tags for every other version) and asserts the run aborts with both documents untouched.
  - Gates: pyright/ruff/ruff format clean (--all-extras). tests/meta 238 passed. Targeted file 24 passed. sq check clean. Both templates_manifest.json and content_store.json byte-identical to git before, during, and after (verified with --check, --release-gate, and a --rebuild no-op against the real repo).
<!-- sq:discussion:end -->

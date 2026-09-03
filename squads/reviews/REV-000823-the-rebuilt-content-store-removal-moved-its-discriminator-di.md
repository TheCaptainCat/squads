---
id: REV-823
sequence_id: 823
type: review
title: 'The rebuilt content store: removal moved, its discriminator did not'
status: Approved
author: reviewer
refs:
- REV-817
- FEAT-791:addresses
- TASK-822:addresses
description: 'Driven review of 2a81c06 (TASK-822): the rebuild reproduces the withdrawn
  sweep''s loss when the running version is already tagged'
subentities:
- local_id: F1
  title: Rebuild destroys a shipped release's blobs once its tag exists
  status: Fixed
  severity: critical
- local_id: F2
  title: 'Rebuild has no floor: an unreadable or artifact-less tag empties an entry'
  status: Fixed
  severity: high
- local_id: F3
  title: Store-coverage failure names a remedy that cannot fix it
  status: Fixed
  severity: medium
- local_id: F4
  title: Runbook's rebuild and release-gate steps contradict each other on order
  status: Fixed
  severity: medium
- local_id: F5
  title: A mistyped flag silently runs write mode; --check --rebuild writes
  status: Fixed
  severity: medium
- local_id: F6
  title: Rebuild reports a net size delta as a drop count; restorations invisible
  status: Fixed
  severity: low
- local_id: F7
  title: Rebuild's two writes are neither atomic nor rolled back
  status: Fixed
  severity: low
- local_id: F8
  title: Release-gate success line is identical to --check's
  status: Fixed
  severity: low
created_at: '2026-08-25T23:50:01Z'
updated_at: '2026-08-26T09:21:56Z'
---
<!-- sq:body -->
## Scope

Commit `2a81c06` on `release/0.14`, TASK-822 alone — the fix for REV-817's F1: the generator's
reachability sweep withdrawn, removal moved to an all-or-nothing rebuild in
`scripts/seed_content_store.py --rebuild`, `--check` widened to the whole index, `--release-gate`
added, the retention fixture parametrised, and the release runbook (SKILL-000508) extended.

Anything outside that commit's TASK-822 surface, and REV-817's other findings, are out of scope.

## Method

Driven, not read. A clone of the repository at `2a81c06` (tags included) in a scratch directory;
every probe run against that clone with the repository's own tree untouched. Both scripts were
exercised through their command lines, not through their functions, except where a claim is
labelled **read** or **inferred**. Every claim below carries its label. One targeted test run
(`tests/meta/test_override_manifest_and_stamp_freshness.py`, 23 passed). No full suite, nothing
committed, nothing fixed.

## What is sound

- **The generator has no removal path left.** Read: `_write_json` is called from `_write_mode`
  alone, `_check_mode` never writes, and no `del`/`pop`/reassignment of `store` exists anywhere
  in the file. Driven: a shipped blob survived a write-mode regeneration at a released version,
  and both `--check` and `--release-gate` left both documents byte-identical.
- **The whole-index widening works.** Driven: deleting a blob that only historic entries name now
  fails `--check` at exit 1, naming every `version:artifact` that stopped resolving. Before the
  widening this reported clean.
- **The orphan split works.** Driven: an extra blob is a stderr note at exit 0 under `--check`,
  and a failure at exit 1 under `--release-gate`.
- **The untagged-version refusal works.** Driven: an indexed version with no local tag refuses,
  names the version, points at `git fetch --tags`, exits 1, and leaves both documents
  byte-for-byte unchanged.
- **The happy path is a true no-op.** Driven: `--rebuild` against the clean clone reproduced both
  documents byte-identically, 16 versions, 85 blobs, 0 dropped, `git diff` empty.
- **The non-vacuity guard holds.** Read: the fixture's assertion is pinned by its own test, and
  the two legs that carry real weight assert against a literal `0.9.0` entry, so a silent fallback
  to the running version would fail them loudly rather than pass them quietly. The two `9.9.9`
  legs would pass vacuously under such a fallback, but they assert non-removal, which is now
  unconditional — nothing is hidden behind them.

## What is not

The removal capability moved from the generator to the rebuild, but the discriminator did not.
ADR-777 D2 moved removal into the tag-reading script precisely so publication could decide it;
the rebuild instead decides on *is this the running version*. Those two differ exactly when
`[project].version` names an already-tagged release — the steady state D1 identified — and in that
window the rebuild performs the same destruction the sweep did, from the same false premise, while
the release gate reports clean. The runbook's stated ordering walks the operator into it, and the
two script docstrings name the rebuild as the recovery for the one case where it is the damage.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 823 add-finding "…" --severity medium`; track with `sq review 823 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Rebuild destroys a shipped release's blobs once its tag exists

<!-- sq:finding:F1:body -->
**Severity: critical. Driven.**

`scripts/seed_content_store.py:243` chooses each version's ground truth with
`if version == running_version:` — the working tree — and the tag otherwise. ADR-777 D2 moved
removal into this script because *publication* is the discriminator and only the tag list holds
it. The code does not use publication. It uses "is this the running version", and those two part
company in exactly the state D1 named: `[project].version` keeps naming a release from the moment
it is tagged until someone bumps.

In that window the rebuild sources an **already-shipped, already-tagged** version from the working
tree, rewrites its index entry to whatever the tree now holds, and — because the rebuild *is*
allowed to delete — drops the shipped revision it just stopped referencing. That is the withdrawn
sweep's loss, performed by its replacement, from the same false premise.

**Driven**, in a clone at `2a81c06`:

```
# runbook order: rebuild, gate, tag
$ python3 scripts/seed_content_store.py --rebuild && \
  python3 scripts/gen_template_manifest.py --release-gate && git tag v0.14.0 HEAD
# steady state: post-release, pre-bump. A dev edits a bundled template.
$ printf '\n{# post-release edit #}\n' >> src/squads/_rendering/templates/workflow.md.j2
$ python3 scripts/gen_template_manifest.py
wrote manifest for v0.14.0: 29 artifact hashes (1 new blob(s) inserted)
# the generator is blameless — the shipped blob is still there, reported as an orphan:
$ python3 scripts/gen_template_manifest.py --check
note: orphaned blob in content store: 8ef14278...
manifest v0.14.0 is current (...); 1 orphan(s) reported          # exit 0
# now the rebuild, with v0.14.0 tagged and [project].version still 0.14.0:
$ python3 scripts/seed_content_store.py --rebuild
rebuilt from ground truth: 16 version(s), 85 blob(s) (1 dropped ...)   # exit 0
```

After that run: the shipped `v0.14.0` revision of `_rendering/templates/workflow.md.j2` is gone
from the store; the `0.14.0` index entry names `eaf22c06...` while the artifact actually at tag
`v0.14.0` hashes to `8ef14278...`; no correction is printed, because the tree *is* what the
rebuild consulted; and `--release-gate` afterwards prints "store coverage verified across all 16
indexed version(s)" and exits 0. The corpus reads clean while broken — the precise defect ADR-777
D7 says the store is protected against.

**The documentation makes it worse, not better.** `scripts/seed_content_store.py:47-52` and
`scripts/gen_template_manifest.py:37-45` both name `--rebuild` as the recovery from a mis-ordered
regeneration. But the mis-ordered regeneration is *by definition* a run at a version that is both
shipped and the running version — so an operator who follows the documented recovery literally
re-enshrines the corruption in the index and destroys the shipped blobs the generator had
carefully preserved. Neither docstring states the precondition. The test suite knows it does not
hold: `tests/meta/test_override_manifest_and_stamp_freshness.py`'s recovery test carries it in a
docstring ("moving the version off it first is what makes 0.9.0 a historic entry again") and its
body performs the move before recovering. That precondition never reached the shipped prose.

**Reachability, ranked.** The runbook (see the runbook finding) tells the operator to run the
rebuild before the §1 gates, which is before the version bump — the unsafe state, every cut.
Independently (**inferred**), `--check` now emits an orphan note on any dev tree where a template
was edited twice, which invites a between-releases `--rebuild` to tidy up; that is the same state.

**Bound.** The loss is recoverable: **driven**, bumping the version off the shipped release and
re-running `--rebuild` restored the destroyed blob and corrected the entry back to its tag,
printing the correction. So this is silence, not irrecoverability — which is exactly the ground
D7 says the rule stands on.

**What I would want.** The discriminator the ADR asked for: source a version from the tree only
when it is *not* published — `version == running_version and not _tag_exists(f"v{version}")` —
and from its tag whenever the tag exists, including for the running version. That also makes the
documented recovery true as written. Whatever ships, the coverage owed is a leg where the running
version is tagged and the tree disagrees with it, which no current test reaches. ADR-777 D3's own
wording ("sourced from each version's tag and — for the running version — from the working tree")
needs the same correction; the implementation follows the ADR faithfully, and the ADR is what is
wrong.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-08-26T00:06:25Z] Elias Python:
  - Fixed: discriminator is now publication (tag exists), not running-version equality. _resolve_version() sources any tagged version from its own tag, always; the working tree is only used for a version with no tag. Driven: v0.14.0 tagged + still running, a post-tag edit written by the generator, then --rebuild — the entry corrected back to the tag-derived hash, the shipped blob survives (git show v0.14.0:... matches). Coverage: test_seed_content_store_rebuild_prefers_the_tag_even_when_it_is_also_the_running_version.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Rebuild has no floor: an unreadable or artifact-less tag empties an entry

<!-- sq:finding:F2:body -->
**Severity: high. Driven.**

The all-or-nothing promise has no floor. `scripts/seed_content_store.py:40-43` states it as: a
version whose ground truth it cannot reach — "no local tag, **or a tag that does not reproduce
every hash the index names for it**" — is a refusal that writes nothing at all, for any version.
The code implements only the first clause.

`_collect_tree_at_tag` (`scripts/seed_content_store.py:180-199`) refuses (`return None`) in two
cases: the tag does not exist, or `git show` fails for a path `git ls-tree` already listed. It
never checks that what it derived covers what the index recorded. And `_git_ls_tree`
(`:165-177`) maps **any** non-zero git exit to `return []` — an empty tree, not an error. A
version whose tag resolves but whose listing comes back empty therefore produces an empty entry,
which is a legal result, and every blob only that entry named is dropped.

**Driven, the realistic shape** — one `git ls-tree` failure (a partial or blobless clone, a
missing object, any git error), with `git rev-parse` still succeeding so the tags all "exist":

```
$ PATH=<shim making only `git ls-tree` exit 128>:$PATH \
  python3 scripts/seed_content_store.py --rebuild
rebuilt from ground truth: 16 version(s), 30 blob(s) (55 dropped ...)     # exit 0
# every historic entry is now {}, 55 of 85 blobs destroyed
$ python3 scripts/gen_template_manifest.py --release-gate
manifest v0.14.0 is current (29 artifacts); store coverage verified across all
16 indexed version(s) (35 hash(es))                                       # exit 0
```

A total, silent wipe of the retained corpus, reported as a successful rebuild, certified clean by
the release gate on the next line. The `(35 hash(es))` is the only trace, and it is a number an
operator has no baseline for.

**Driven, the second shape** — a tag that exists but whose tree carries no artifacts (a tag
pointed at the wrong commit, a fetch of a fork's tags, a repository whose layout moved). Moving
`v0.4.0` onto the root commit and rebuilding: `0.4.0`'s entry became `{}`, its 2 uniquely-named
blobs were destroyed, exit 0, and `--release-gate` reported clean afterwards. The correction log
printed 26 lines of `recorded <hash> -> ground-truth <absent>` — which is the tool announcing it
is about to delete a release's whole history and calling it a correction.

Both shapes fail in the unsafe direction, which is the direction ADR-777 D2 singles out: "a rule
that silently permits a deletion when it cannot see the tag fails in the unsafe direction."

**What I would want.** `_git_ls_tree` must distinguish "no such path at this tag" (git exits 0
with empty output) from "git failed" (non-zero), and the latter is a refusal. And the second
clause of the docstring's own promise needs to exist in code: a derivation that resolves fewer
keys than the index records for that version is a refusal naming the version and the missing
keys, not a correction — a shipped entry losing keys wholesale is never an ordinary correction.
If the intended behaviour really is to let a tag's tree narrow an entry, the docstring at `:40-43`
is the thing to fix, since it promises a refusal the tool does not perform.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-26T00:06:27Z] Elias Python:
  - Fixed: _git_ls_tree now returns None (not []) on a non-zero git exit, propagated as a refusal; _collect_tree_at_tag also refuses when a tag's listing comes back empty while the old entry recorded templates. Driven both shapes: a git-ls-tree shim forcing exit 128, and v0.4.0's tag moved onto the root commit — both now refuse, exit 1, nothing written. Coverage: test_seed_content_store_rebuild_refuses_when_a_tag_resolves_but_lacks_an_artifact.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Store-coverage failure names a remedy that cannot fix it

<!-- sq:finding:F3:body -->
**Severity: medium. Driven.**

The widened check now detects the failure REV-817 F1 was about — and then prints the wrong way out
of it. `scripts/gen_template_manifest.py:203-208` selects the remediation line on the orphan
branch alone: `run: python scripts/seed_content_store.py --rebuild` if the failure included an
orphan under `--release-gate`, otherwise `run: python scripts/gen_template_manifest.py`. An
unresolved store hash — the failure the widening exists to surface — takes the else branch.

The generator cannot fix it, by design: write mode is insert-if-absent from the current tree only,
so a hash a historic entry names and the tree no longer produces is never re-inserted.

**Driven** (blob only historic entries name deleted from the store):

```
$ python3 scripts/gen_template_manifest.py --check
error: manifest v0.14.0 is not current (10 problem(s)):
  hash not in content store: 0.10.0:_rendering/templates/agents/greeting_skill.md.j2
  ... (10 versions)
run: python scripts/gen_template_manifest.py                    # exit 1
$ python3 scripts/gen_template_manifest.py                       # the printed remedy
manifest already up to date for v0.14.0 (29 artifacts)           # exit 0
$ python3 scripts/gen_template_manifest.py --check ; echo $?
1                                                                # unchanged
$ python3 scripts/seed_content_store.py --rebuild                # the actual remedy
rebuilt from ground truth: 16 version(s), 85 blob(s) (-1 dropped ...)
$ python3 scripts/gen_template_manifest.py --check ; echo $?
0
```

The remedy the tool names exits 0 and heals nothing, and its success wording ("already up to
date") reads as confirmation that the problem is gone. This is the same class of defect REV-817
F1 turned on — a message asserting more than the run performed — displaced from the success line
into the remediation line, at the release gate.

The runbook repeats the misdiagnosis: SKILL-000508 §1 says a `--release-gate` failure "means the
rebuild below either was not run, or was not run last". That is true of an orphan and false of an
unresolved hash, which means genuine data loss rather than a stale ordering.

**What I would want.** Branch the remediation on what actually failed: any unresolved hash, and
any orphan under the release gate, points at `seed_content_store.py --rebuild`; only the running
version's own missing/phantom/stale hashes point at the generator. When both classes are present,
name both. And SKILL-000508 §1 should distinguish the two failures rather than diagnosing one.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-26T00:06:29Z] Elias Python:
  - Fixed: _check_mode splits freshness_problems (running version only) from store_problems (whole-index unresolved + orphan-under-gate) and prints the remedy for whichever fired, both if both fired. Driven: a hash missing from a historic entry now prints 'run: seed_content_store.py --rebuild', which actually clears it (verified the old remedy exited 0 and healed nothing, the new one clears the check).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Runbook's rebuild and release-gate steps contradict each other on order

<!-- sq:finding:F4:body -->
**Severity: medium. Read, against a driven consequence.**

`SKILL-000508` gained two steps that contradict each other on ordering, and the reading an
operator will actually follow is the unsafe one.

- §1 ("Gates — all green before anything else") lists
  `gen_template_manifest.py --release-gate`, and on failure says to run "the rebuild below".
- §2 ("Prep") carries the rebuild bullet, positioned **after** the version bump, and ends: "Run
  this before the gates in §1, so `--release-gate` there checks the rebuilt store".

Those two placements are mutually exclusive. Taken as the rebuild bullet instructs — before §1 —
the bump has not happened yet, so `[project].version` still names the **previously shipped,
tagged** release, which is precisely the state that makes the rebuild destroy that release's
blobs (see the critical finding, driven). Taken as its position in §2 implies — after the bump —
the rebuild is safe, but then the §1 gate ran against a store that was not rebuilt, which is the
premise the §1 bullet was added to establish. There is no reading that satisfies both bullets.

Two smaller gaps in the same edit:

- **No step re-runs the gate after the rebuild.** The re-check appears only inside §1's failure
  branch, so an operator whose gate passed first time never verifies the rebuilt store.
- **No step commits the rebuilt documents.** `--rebuild` writes two tracked files under
  `src/squads/_rendering/`. §2 never says to commit them; the generator's own docstring checklist
  does ("Commit them together with any template/spec-document changes"), the runbook does not.

**What I would want.** One ordered sequence in §2, and §1's content-store bullet reduced to a
pointer at it: bump the version, regenerate, `git fetch --tags`, `--rebuild`, `--release-gate`,
commit both documents, then tag. The bump must precede the rebuild explicitly, and the runbook
should say why — that the rebuild trusts the working tree for whatever `[project].version` names.
Also state what a failure means for each of the gate's two failure classes, per the remediation
finding.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-08-26T00:06:31Z] Elias Python:
  - Fixed: SKILL-508 rewritten to one ordered sequence in Prep -- fetch tags, changelog, bump, THEN fetch tags again + rebuild + release-gate (with the 'why the bump comes first' stated explicitly), then commit both documents. Gates section now only points at that sequence instead of carrying its own contradictory standalone bullet. Both failure classes (unresolved hash vs orphan) are named with their distinct remedies.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — A mistyped flag silently runs write mode; --check --rebuild writes

<!-- sq:finding:F5:body -->
**Severity: medium. Driven.**

Both scripts select their mode by membership tests over `sys.argv[1:]`
(`scripts/gen_template_manifest.py:254-262`, `scripts/seed_content_store.py:304-309`) and never
reject an unrecognised argument. On release tooling that an operator types by hand from a runbook,
a mistyped flag silently selects a **write** mode and exits 0.

**Driven**, against the clean clone:

```
$ python3 scripts/gen_template_manifest.py --relase-gate
manifest already up to date for v0.14.0 (29 artifacts)      # exit 0 — write mode
$ python3 scripts/seed_content_store.py --rebiuld
seeded 15 tagged version(s); store now holds 85 blob(s) ... # exit 0 — the one-time seed pass
$ python3 scripts/seed_content_store.py --check --rebuild
rebuilt from ground truth: 16 version(s), 85 blob(s) (0 dropped ...)  # wrote, despite --check
```

Each was a no-op here because the tree was clean, which is the reason it will not be noticed until
the tree is not. A mistyped `--release-gate` at the cut is exactly the mis-ordered regeneration the
rest of this work exists to make survivable; a mistyped `--rebuild` runs a one-time historical
rekey pass that was never meant to be re-run casually; and `--check --rebuild` writes both
documents while the operator believes they asked for a dry run — `--check` is the one word in
this tool that is supposed to mean "writes nothing, ever".

**What I would want.** Reject unknown arguments with a usage line and exit 2 in both scripts, and
make `--check --rebuild` either a dry-run rebuild or a refusal — never a write. `argparse` costs
four lines and removes the whole class.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-08-26T00:06:32Z] Elias Python:
  - Fixed: both scripts reject any argv entry outside their small allow-list with exit 2 and a usage line. seed_content_store.py also refuses --check + --rebuild together (exit 2, writes nothing) rather than letting --rebuild's write win silently. Driven: --relase-gate and --rebiuld (typos) both now exit 2 instead of running write mode.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Rebuild reports a net size delta as a drop count; restorations invisible

<!-- sq:finding:F6:body -->
**Severity: low. Driven.**

`scripts/seed_content_store.py:294` computes `dropped = store_before_size - len(new_store)` — a
net size delta reported as a count of deletions. A rebuild that inserts (which is what recovery
*is*) reports a negative drop, and a rebuild that both restores and drops reports neither.

**Driven**, both shapes:

```
# recovery of one deleted blob:
rebuilt from ground truth: 16 version(s), 85 blob(s) (-1 dropped — not in the closure ...)
# one shipped blob restored + one dev-tree blob dropped, in the same run:
rebuilt from ground truth: 16 version(s), 85 blob(s) (0 dropped — not in the closure ...)
```

The second is the one that matters: the run had just corrected a shipped release's entry back to
its tag and restored the blob behind it — the tool's headline capability — and its report line says
nothing happened. The correction log carried it, but the summary an operator reads at a release cut
did not.

**What I would want.** Count the two sets, not the delta: blobs in the closure that were absent
from the old store (restored/inserted) and blobs in the old store outside the closure (dropped),
each reported on its own.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-08-26T00:13:12Z] Olivia Lead:
  - Tracked on TASK-824 (Ready, low, python-dev, FEAT-791 US1) — "Rebuild reporting and durability: honest counts, atomic writes", subtask ST1. Re-verified against the tree after 3fb7c38, not against the reviewed 2a81c06.
- [2026-08-26T00:13:16Z] Olivia Lead:
  - Confirmed at seed_content_store.py:360 (dropped = store_before_size - len(new_store)) reported at :363-366. Acceptance asks for two set computations plus an explicit no-negative-count assertion, since a negative count is the deltas signature.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Rebuild's two writes are neither atomic nor rolled back

<!-- sq:finding:F7:body -->
**Severity: low. Read, with one inconclusive probe.**

`scripts/seed_content_store.py:295-296` writes the two documents with two successive
`Path.write_text` calls (`_write_json`, `:113`). Neither is atomic, and there is no rollback
between them, so "writes nothing at all, for any version" (`:42-43`) describes the refusal path
only — not an interrupted run. An interruption can leave the manifest rewritten with the store
un-rebuilt, or a truncated `content_store.json` (364 KB on this branch).

**Why I am rating it low rather than higher.** The ordering happens to be the safe one: the
manifest is written first, so a failed store write means the drops never happened — the store is a
superset of the closure, not a subset, and no blob is lost. Every resulting state is loud: an
index naming hashes the store lacks fails `--check` at exit 1, and a truncated store raises a JSON
decode error on the next load. Both documents are tracked in git, so `git checkout` is a complete
recovery. So the practical invariant survives; it is the stated one that does not.

I attempted to drive a harmful partial state by making the store read-only mid-run; the probe
produced a `PermissionError` traceback but no observable partial state, because the run I
constructed had nothing to write to the store. **Inconclusive** — I am reporting the code shape,
not a driven loss.

**What I would want.** The repository already has the pattern: `src/squads/_index/_store.py` writes
via a temporary file plus `os.replace`. Applying it to `_write_json` in both scripts costs three
lines and makes the docstring's promise literally true. Writing both documents to temporaries and
replacing them one after the other still is not a single transaction, but it removes truncation
entirely and narrows the window to two adjacent renames.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-08-26T00:13:14Z] Olivia Lead:
  - Tracked on TASK-824 (Ready, low, python-dev, FEAT-791 US1) — "Rebuild reporting and durability: honest counts, atomic writes", subtask ST2. Re-verified against the tree after 3fb7c38, not against the reviewed 2a81c06.
- [2026-08-26T00:13:29Z] Olivia Lead:
  - Keeping your low, correcting the reason rather than inheriting it. Two mitigants hold: both documents are git-tracked so checkout is a complete recovery, and the manifest-written/store-not state IS diagnosable — it is an index naming hashes the store lacks, exactly what the whole-index --check widening catches at exit 1 pointing at --rebuild.
  - One does not hold. "The store is a superset of the closure, not a subset, and no blob is lost" is true of the drop half only. The rebuild also restores: a corrected entry names hashes present in new_store and absent from the old one. Interrupt between :361 and :362 on a recovery run and the index is rewritten to the corrected hashes while the store still lacks the blobs behind them — nothing lost from git, but the tree is left in the state the operator ran the rebuild to leave.
  - So the genuinely undiagnosed state is narrower than a half-written pair: a truncated JSON document. write_text truncates before writing and _load_json parses with no error handling, so a partial content_store.json surfaces as an unhandled JSONDecodeError traceback rather than a diagnosis. That is the piece I added scope for beyond the atomic write.
  - Low stands on the mitigants, and the label should not gate the fix — the os.replace pattern is already in _index/_store.py, it is a few lines, and it removes truncation entirely. Recorded on the task that the residual is a two-rename window, not a transaction, and that the docstring should claim exactly that.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Release-gate success line is identical to --check's

<!-- sq:finding:F8:body -->
**Severity: low. Driven.**

Acceptance turned on the success line stating what was checked, and it now does for the whole-index
widening. Two things it still does not state.

**The release gate is indistinguishable from an ordinary check.** With no orphans present, both
modes print the identical line (`scripts/gen_template_manifest.py:211-218` — `release_gate` reaches
the success line nowhere):

```
$ python3 scripts/gen_template_manifest.py --check
manifest v0.14.0 is current (29 artifacts); store coverage verified across all 16 indexed version(s) (416 hash(es))
$ python3 scripts/gen_template_manifest.py --release-gate
manifest v0.14.0 is current (29 artifacts); store coverage verified across all 16 indexed version(s) (416 hash(es))
```

Orphan-freeness is the one property the release gate adds, and a clean gate run never says it
verified it. Pasted into a release thread the two lines are the same evidence, which is the shape
of problem the finding this task fixed was about.

**`416 hash(es)` is not 416 hashes.** It is `sum(len(entry) for entry in manifest.values())` —
index references. The store holds 85 blobs. An operator comparing the two numbers has no way to
reconcile them from the wording.

**What I would want.** Under `--release-gate`, add the clause it earned — orphan-free, over N
blobs — and word the count as references, e.g. "416 index reference(s) over 85 stored blob(s)".
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-08-26T00:13:16Z] Olivia Lead:
  - Tracked on TASK-824 (Ready, low, python-dev, FEAT-791 US1) — "Rebuild reporting and durability: honest counts, atomic writes", subtask ST3. Re-verified against the tree after 3fb7c38, not against the reviewed 2a81c06.
- [2026-08-26T00:13:19Z] Olivia Lead:
  - Confirmed by driving both modes on the current tree — the two success lines are byte-identical, release_gate reaches :206-207 and never the success path at :222-228, and 416 vs 85 checks out (416 index references, 85 stored blobs). Added one thing the finding did not name: SKILL-000508 section 2 tells the operator what each gate failure means and never what a clean gate line looks like, so the runbook half is in scope too.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T23:53:13Z] Paul Reviewer:
  - Review of 2a81c06 (TASK-822) complete: 8 findings — 1 critical, 1 high, 3 medium, 3 low. Verdict ChangesRequested; the Approved transition is the approver's, not mine.
  - The one that matters (F1, critical, driven): removal moved from the generator to the rebuild, but the discriminator did not. seed_content_store.py:243 branches on "is this the running version", not on "is this published" — the discriminator ADR-777 D2 moved into this script precisely because it holds the tags. The two differ exactly when [project].version names an already-tagged release, and in that window --rebuild sources a shipped version from the working tree, rewrites its index entry, and deletes the shipped blob. Same loss as the withdrawn sweep, same false premise, and --release-gate reports clean afterwards. Both script docstrings name --rebuild as the recovery for the mis-ordered regeneration, which is by definition that exact state; the recovery as documented is the damage. The test suite knows the precondition and states it in a docstring — it never reached the shipped prose.
  - Clean, driven, and worth saying plainly: the generator has no removal path left (only _write_mode writes; --check and --release-gate leave both documents byte-identical); the whole-index coverage widening works and names version:artifact; the orphan split works (note at exit 0 under --check, failure at exit 1 under --release-gate); the untagged-version refusal works and writes nothing; and a no-op --rebuild reproduces both documents byte-identically. The fixture's non-vacuity assertion is load-bearing where it needs to be.
  - @tech-lead @architect F1 is a design correction (and ADR-777 D3's own wording needs it too), F2 is a missing floor in the rebuild, F4 is the runbook order. @manager my read on the release: not safe to cut until F1 and F4 are settled — following the runbook as written puts the operator in F1's state at every cut.
- [2026-08-26T00:06:47Z] Elias Python:
  - F1-F5 fixed and driven; F1 (critical) verified two ways: v0.14.0 tagged+running with a post-tag edit recovers the shipped blob and corrects the entry, and a new fixture leg asserts it directly without ever moving the version off the tagged release. F2's two shapes (git-ls-tree failure, tag moved to an artifact-less commit) both refuse with nothing written.
  - F6-F8 left untouched, tracked separately per your note.
  - Gates clean: pyright/ruff/ruff format (--all-extras), tests/meta 238 passed, targeted file 24 passed (23 + the new tag-resolves-but-empty leg). Both manifest documents byte-identical to git throughout.
  - @tech-lead @architect for awareness -- TASK-822 back to InReview.
- [2026-08-26T00:09:16Z] Catherine Manager:
  - F1 through F5 fixed and committed; the rebuild now takes publication as its discriminator, so a tagged version is sourced from its tag even while it is also the running version. F6 to F8 stay open and are tracked for follow-up.
- [2026-08-26T00:13:40Z] Olivia Lead:
  - F6, F7 and F8 now have a home: TASK-824 (Ready, low, python-dev, FEAT-791 US1) — "Rebuild reporting and durability: honest counts, atomic writes", one subtask each. They were left untracked when F1-F5 were fixed; that is closed now.
  - Grouped as one task rather than three lines. They are one surface — what the rebuild writes and what it tells the operator it did. F6 and F7 are adjacent lines in the same function (:360-362) and F8 is the success line in the sibling script the same operator reads in the same release step. Splitting F7 out would put a second dev inside seed_content_store.py:355-366 while F6s is already there.
  - F7 severity: keeping low, but the stated reason needed correcting — the superset argument holds for drops and not for restores, so an interrupted recovery run leaves the tree in the broken state the operator ran the rebuild to leave. Detail on the finding. The one state nothing diagnoses is a truncated document, which is in scope now.
  - The task body notes that F1-F5 landed in 3fb7c38 and every citation was re-verified against the current tree, since the review was driven against 2a81c06 and both scripts moved.
  - @reviewer nothing here needs re-driving. @manager three low findings against a landed surface; the atomicity fix is worth landing before the v0.14.0 tag since the runbook has the operator commit both documents together at that step.
<!-- sq:discussion:end -->

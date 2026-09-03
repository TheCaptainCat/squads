---
id: REV-808
sequence_id: 808
type: review
title: Ref-kind vocabulary and provenance manifest landing
status: Approved
author: reviewer
refs:
- FEAT-790
- FEAT-791
description: 'Review of 958974c: TASK-796, TASK-806 (FEAT-790) and TASK-799 (FEAT-791)'
subentities:
- local_id: F1
  title: The 0.5-to-0.7 runner's on-disk output also changed retroactively
  status: Fixed
  severity: high
- local_id: F2
  title: Manifest-freshness guard lost its stale-hash assertion
  status: Fixed
  severity: medium
- local_id: F3
  title: Pre-0.14 spelled-default refs become a false skew refusal on upgrade
  status: Fixed
  severity: medium
- local_id: F4
  title: README carries a third, untracked closed-nine-kinds claim
  status: Fixed
  severity: medium
- local_id: F5
  title: Width-tolerant ref severing lost its bare-ref coverage
  status: Fixed
  severity: low
- local_id: F6
  title: sq workflow lint passes a spec every mutation then refuses
  status: Fixed
  severity: low
- local_id: F7
  title: Never-prune plus no-orphans deadlocks a same-release delete
  status: Fixed
  severity: low
- local_id: F8
  title: The VS Code client binds edge labels to a literal kind name
  status: Fixed
  severity: low
created_at: '2026-08-25T17:43:57Z'
updated_at: '2026-08-25T23:39:03Z'
---
<!-- sq:body -->
## Scope

Commit `958974c` on `release/0.14` — the landed portion of FEAT-790 (TASK-796, TASK-806) and
FEAT-791 (TASK-799). TASK-797, TASK-798, TASK-800, TASK-801, TASK-805 and TASK-807 are not in
this commit and their scope is not reviewed as defect here.

Driven on real squads: three scratch squads built with `sq init` and mutated through the CLI, a
git worktree at `958974c^` for cross-version comparison, a copied source tree for generator write
modes, and in-process probes against the shipped manifest, content store and guard module. Every
claim below is labelled **driven** (I ran it), **read** (I traced the code), or **inferred**.

## Verdict

Three defects worth acting on, four smaller ones. The encoding invariant itself holds on every
live write path — the remaining hole is in a migration runner, not in the service layer.

## Category results

**1. The encoding invariant — clean on every live write path.** Enumerated every site that can
put a `refs` value on disk or in the index and drove each on a real squad: `create --ref
ID:related`, `create --ref ID:blocks`, `ref add --kind related`, `ref add ID:related` (kind
embedded in the target), `skill <n> ref add --kind related`, the bulk importer (create-event refs
and a `ref` event), sub-entity add/update, `status`, `update`, `retype`, `repair`, `sync`, and a
whole-corpus sweep grepping disk and index for a spelled default. No spelled default was emitted
anywhere; the non-default controls stayed spelled; `sq check` exit 0 throughout (**driven**).

`_services/_retype.py:311-314::_remap_ref` was checked rather than accepted: it takes the kind
from `split_ref` of an already-stored ref and hands it straight back to `make_ref`, so it can
carry a pre-existing bad encoding forward but has no path to mint one. The "carries forward but
cannot mint" assessment is correct (**read**), and `resync_edges` (`_retype.py:295-308`) is its
only caller. `renumber`/`repair --renumber` rewrite ids textually (`_apply_remap`, then a
disk rescan), so they preserve whatever encoding the file already holds — also not a mint
(**read**). `adopt` ingests through `svc.repair()`, so it inherits the fold (**read**). The
VS Code client never writes refs (**read**).

The renamed-default case was driven too: an `.overrides/workflow.toml` renaming the default kind
to `linked` keeps every bare ref working, writes `--kind linked` bare, refuses the retired
`related` by name, and leaves `sq check` clean — A1's safety claim holds under drive.

**2. The frozen 0.1→0.2 runner — byte-identical, proven.** Ran `_v0_1_to_v0_2._fold_ref_kinds`
over six fixtures (bare / bare+map-naming-default / spelled-default / spelled-non-default+map /
bare+map-naming-non-default / empty `:` suffix) under `958974c` and under `958974c^` in a git
worktree, same interpreter, and diffed the JSON: **identical on every row** (**driven**). The
runner's private `_fold_legacy_kinds` reproduces the retired `DEFAULT_KIND` collapse exactly.

The *other* runner did not survive the same test — see finding F1.

**3. The eight corrected historic manifest hashes — clean, independently verified.** Recomputed
the SHA-256 of the CRLF-normalised bytes of every artifact named by every index entry, straight
from its own release tag (`git show v<X>:src/squads/<key>`), after `git fetch --tags`:
**387 recorded hashes across 15 tagged releases, zero mismatches, zero keys absent at their tag**
(**driven**). Running the identical check against the pre-commit manifest returns exactly the
eight rows the commit corrected — one in v0.4.0, seven in v0.6.0 — and no others, so no other
release's recorded hash moved in the rekey (**driven**). The corrections are right, and the
rewrite of shipped provenance is justified.

**4. The content store — clean.** Shipped index and store checked directly: 416 index entries
resolving to 84 distinct hashes, 84 blobs, **zero index-named hashes missing from the store, zero
orphaned blobs**, and every blob hashes to its own key (**driven**). The store deflates to
79.7 KB against the 256 KB ceiling. Insert-if-absent/never-deletes driven in a copied tree:
re-running the generator at an unchanged version is a no-op; deleting a bundled template drops it
from the current version's entry while every historic entry and blob survives; bumping the version
appends an entry and preserves the previous one (**driven**).

`sq override diff` driven for all five base shapes on a real squad: carried base (real Δ-upgrade),
below-artifact-floor, below-index-floor, a version squads never released, and a downgrade — all
exit 0, the partial Δ-upgrade is labelled with where it starts and what is not represented, the
downgrade refuses by name, the drift classifier stays silent, and `sq check` exits 0 in every case
(**driven**). The retired "refer to the changelog" message is gone. This category is honoured.

**5. Tests touched — mostly sound, two exceptions.** The skew-guard test is genuinely restored and
stronger than before (parametrized over default and non-default, and now asserting exact ref
equality rather than a `startswith` prefix). The eight `WorkflowSpec.model_validate` fixtures that
gained `ref_kinds` are hand-built specs that enumerate every section; adding the new one keeps them
realistic, not passing. `test_declared_ref_rules_are_not_inert.py` was generalised correctly and
gained a real new case. The literal-9 cheatsheet pin is disclosed and owned by TASK-798.
The two exceptions are F2 and F5 below.

## Tracked-elsewhere confirmations

- **TASK-805** (forked stamp finding) — confirmed the only instance. The playbook obligation was
  content-gated in place at `_interactions/_loader.py:483`, and the role kind now measures against
  `ROLES_KEY`; only the workflow kind carries a second, forked implementation
  (`_overrides/_service.py:1157`) beside the loader's ungated one (**read**).
- **TASK-807** (`sq graph` dropping undeclared-kind edges) — confirmed the only instance: two
  sites, one mechanism (`if kind not in ctx.kinds: continue` in `_out_neighbours` and
  `_in_neighbours`, `_services/_refs.py:74-76` and `:105-107`). Every other ref surface either
  lists the edge or warns on it (**read**).
- **TASK-798** (cheatsheet kinds table) — **not** the only instance of the retired policy. See F4.

## What I could not test

Nothing in categories 1–5 was left untested. Two limits worth naming: the v0.14.0 manifest entry
cannot be verified against a tag because that release is not cut, and the guard-module probes for
F2 were run in-process against the installed package rather than by editing a bundled template,
because this review does not modify the tree.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 808 add-finding "…" --severity medium`; track with `sq review 808 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | The 0.5-to-0.7 runner's on-disk output also changed retroactively |
| F2 | 🟡 medium | Fixed |  | Manifest-freshness guard lost its stale-hash assertion |
| F3 | 🟡 medium | Fixed |  | Pre-0.14 spelled-default refs become a false skew refusal on upgrade |
| F4 | 🟡 medium | Fixed |  | README carries a third, untracked closed-nine-kinds claim |
| F5 | 🟢 low | Fixed |  | Width-tolerant ref severing lost its bare-ref coverage |
| F6 | 🟢 low | Fixed |  | sq workflow lint passes a spec every mutation then refuses |
| F7 | 🟢 low | Fixed |  | Never-prune plus no-orphans deadlocks a same-release delete |
| F8 | 🟢 low | Fixed |  | The VS Code client binds edge labels to a literal kind name |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — The 0.5-to-0.7 runner's on-disk output also changed retroactively

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**Driven.** `_migrations/_v0_5_to_v0_7.py` was not touched by this commit and still imports the
live `split_ref`/`make_ref` from `_models._item` (`src/squads/_migrations/_v0_5_to_v0_7.py:48-53`),
using them in `_unpad_ref` (`:117-128`). Both primitives changed meaning in this commit — the old
`split_ref` returned `"related"` for a bare ref and the old `make_ref` collapsed `"related"` back
to bare; the new ones are structural. So this frozen runner's on-disk output moved, which is
exactly the invariant TASK-806 ST3 established and declared closed.

Reproduction (both trees, one interpreter, `git worktree add <dir> 958974c^`):

    PYTHONPATH=<tree>/src .venv/bin/python3 -c "
    from squads._migrations import _v0_5_to_v0_7 as m
    print(m._unpad_ref('TASK-000007:related'))"

- at `958974c^`: `TASK-7`
- at `958974c`:  `TASK-7:related`

Every other input I tried (`TASK-000007`, `TASK-000007:blocks`, `TASK-000007:`, `TASK-7`,
`not-an-id`, `TASK-000007:scopes`) is unchanged; the spelled-default row is the only one that
moved. Two adopters running the same 0.5-to-0.7 schema transform at different squads versions get
different bytes, and the newer one writes a spelled default kind onto disk — the encoding A1
forbids outright — which then lands the squad in the state finding F3 describes.

Two things make this survivable-but-unowned rather than caught:

1. **The new meta guard cannot see it, by design.**
   `tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py:29` scans for exactly
   one name (`fold_legacy_kinds`), and `test_the_scan_does_not_flag_the_purely_mechanical_ref_primitives`
   pins `split_ref`/`make_ref` as permanently allowed on the ground that they are "structural — no
   vocabulary of their own". That ground is what failed: their being structural *today* is
   precisely the change that moved this runner's output. The guard's rationale is falsified by the
   defect it was written to prevent recurring.
2. **No test covers the case.** `tests/integration/test_unpadded_id_migration.py` exercises
   `refs` only with bare ids (`_devolve_to_padded` pads `bug.id`), so no fixture in the suite ever
   feeds this runner a spelled `:related` ref (**read**).

Fix shape (matching ST3's own ruling, not restating it): the runner carries its own frozen
`_unpad_ref` ref handling, byte-asserted for a fixed input against what it produced before
`make_ref` became structural; and the meta guard's exemption for `split_ref`/`make_ref` in
`_migrations/` is reconsidered rather than reasserted, since a purely mechanical primitive that
can change its collapse behaviour is not frozen.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Manifest-freshness guard lost its stale-hash assertion

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**Driven.** The widening deleted the one assertion that made the guard a freshness guard.
`tests/meta/test_override_manifest_and_stamp_freshness.py`, before:

    mismatched = {name for name, actual in installed.items() if manifest_entry.get(name) != actual}
    assert not mismatched, f"manifest hashes are stale for: {sorted(mismatched)}"

After (`:62-83`), only `missing` and `extra` survive — presence, never content. The module
docstring still promises the opposite: "an artifact edit without re-running the generator script
fails loudly, not silently".

Reproduction — a faithful simulation of the real "edited a template, forgot to regenerate" state
(index still names the previous release's hash for that key; the store, never written, holds no
blob for the new content):

    real = M._load_manifest(); victim = "_rendering/templates/agents/role.md.j2"
    idx = deepcopy(real); idx[__version__][victim] = real["0.13.1"][victim]
    store = deepcopy(M._load_store()); store.pop(real[__version__][victim])
    # patch _load_manifest/_load_store/invalidate_cache, then call every test_* in the module

Result: **all twelve tests in the module pass.** Control: the same probe with the entry deleted
outright is still caught ("manifest is missing hashes for: ..."), so the probe is sound.

What still holds, and why this is medium rather than high: `scripts/gen_template_manifest.py
--check` retains its own `stale` list (`:130-132`) and does catch it — driven in-process against a
doctored manifest copy, exit 1 with "stale hash: _rendering/templates/agents/role.md.j2". CI runs
that in `.github/workflows/test.yml:36-37`, so a stale manifest cannot reach a release.

What is lost is the local net. A dev or agent whose gate is `uv run --all-extras pytest` gets no
signal, and the guard now asserts less than its name and docstring claim — the same shape as the
narrowed regression test this whole review exists because of. Note also that the tests/meta store
guards cover every version the index names, while `--check` only verifies the running version's
own entry, so the two are not interchangeable.

No other test in the tree asserts manifest staleness — `templates_manifest.json`,
`current_template_hash` and `artifact_hash_at_version` appear only in this module and the three
scripts (**read**). The two surviving content checks reach exactly four of the 29 artifacts:
`items/task.md.j2` via `template_changed_since`, and the three spec TOMLs via
`artifact_changed_since`.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Pre-0.14 spelled-default refs become a false skew refusal on upgrade

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**Driven, across versions.** ADR-775 A3 rules out a corrective sweep on the premise that "a corpus
migrated to schema 0.2 before the structural change holds the canonical form on disk, so nothing
needs rewriting there", and that the only thing a squad can hold wrongly is its *index*, and only
if it ran `sq repair` at an interim build carrying the structural primitives. That premise is too
narrow: disk can hold a spelled default too, and at the previous version that was a legal,
self-consistent, `sq check`-clean state.

Reproduction (git worktree at `958974c^` for the "before" side, same squad folder throughout):

1. `sq init`, create two tasks, then write `refs:\n- TASK-3:related` into one item's frontmatter
   (a hand edit, a merge resolution, a third-party generator, or an import — pre-0.14
   `Item.from_frontmatter` folded only when an `extra.ref_kinds` map was present, so a spelled
   default passed through verbatim).
2. At `958974c^`: `sq repair` stores `TASK-3:related` in the index; `sq check` is **clean**;
   `sq task 2 status InProgress` succeeds and rewrites the spelled form back to disk. Nothing
   about this state is wrong at that version.
3. At `958974c`: `sq check` reports `warn TASK-2: refs drift between frontmatter and index`, and a
   legal transition is **refused** with `TASK-8: on-disk frontmatter has diverged from the index
   (refs) — run sq repair before mutating TASK-8 again` (that exact refusal driven separately on a
   third squad with the same encoding planted consistently on both sides).

Both sides hold byte-identical text. Nothing diverged; only the load-time fold changed. The
message names a cause that is not the cause, and `sq check`'s wording ("drift between frontmatter
and index") says the same.

The advertised remedy does work, and I drove the whole recovery: `sq repair` at 0.14 re-derives the
index bare, the next ordinary mutation rewrites the file bare, and `sq check` is clean and stays
clean. So no new verb is owed — A3 is right about that. What is missing is that nothing tells the
adopter this will happen: no migration `manual` step, no CHANGELOG line, and a refusal message that
sends them to `sq repair` while describing a divergence that does not exist.

This is not hypothetical for a 0.5-era squad either: finding F1's runner now *produces* exactly
this encoding during `sq migrate up`.

Two things would close it without reopening the design: state the cause accurately in
`skew_message`/the check finding when both sides carry the same bytes and only the resolved kind
differs, and record the upgrade behaviour where an adopter will meet it.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-25T18:00:19Z] Robert Architect:
  - Ruled on ADR-775 A3 and amended in place. The no-sweep premise is withdrawn: you are right that disk is not already canonical everywhere, since the create door wrote a spelled default until this commit and from_frontmatter folded only when a legacy ref_kinds map was present. Reproduced your state and the whole recovery.
  - The 0.14 migration owes no ref-canonicalisation step, on a mechanism rather than an assumption. run_pending_migrations ends every non-empty batch with repair() before it stamps, and the root callback refuses every command on a squad whose schema is behind. Drove it: a squad holding the spelled default consistently on both sides, stepped through sq migrate up, comes out with a bare index, a mutation that succeeds, and sq check clean. The migration IS the sweep. That also caps F1 - the runner mints the encoding and the same run repairs it away.
  - A step of its own is refused on its own terms too. A frozen runner cannot resolve which kind carries default without reading the live spec, which A3 last clause forbids; and this state is not keyed to a schema version - a hand edit, a merge resolution, an import or a third-party writer reach it at any version, including after migrating. A one-shot step cannot cover an arrival path that stays open, so sq repair is the standing remedy rather than a fallback.
  - The refusal message is wrong and is the one thing owed - new A4. The refusal stands (the index really does hold a non-canonical encoding, and rewriting the file from it would commit the spelled form) but the diagnosis does not: frontmatter_skew compares disk-after-fold against index-as-stored, so what it sees is the fold, not a divergence. Rule: a refusal may not assert a cause the reader can disprove. The two cases separate at the site from data already in hand - a diverging key whose RAW disk value already equals the index is a normalisation difference by construction, while the legacy ref_kinds map differs raw and stays reported as needing repair.
  - No manual runbook clause and no release note: both would describe a state the upgrade path does not let an adopter reach. The message is the notification, which is why it has to be true. @tech-lead A4 wants a task under FEAT-790 - skew_message plus the matching sq check finding wording, one state and one explanation on both surfaces. Leaving this finding Open until that lands.
- [2026-08-25T18:14:29Z] Olivia Lead:
  - Tracked as TASK-811 under FEAT-790 (medium, python-dev, US1): "Report a stale index encoding as one, never as a divergence" - skew_message plus the sq check finding, one state and one explanation on both surfaces, no manual clause and no release note. One correction to A4 stated test, driven: the legacy extra.ref_kinds case does NOT differ raw, because the round trip pops ref_kinds out of extra so only refs reaches the diverging list and its raw value equals the index. Raw-equality alone would classify it as normalisation; the task makes that row load-bearing. A4 mechanism half is also recorded on TASK-813, the 0.14 runner the no-sweep conclusion rests on.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — README carries a third, untracked closed-nine-kinds claim

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
**Driven + read.** ADR-775 section 6 names exactly two carriers of the retired closed-vocabulary
policy — `docs/stability.md:322-328` and `_rendering/templates/workflow_static.md.j2:88` (which is
also the generated `squads` skill text) — and TASK-798 inherits those two. Grepping the tree for
the claim finds a fourth line nobody owns:

`README.md:320`

    - sq <type> <n> ref add TARGET [--kind related|blocks|depends-on|implements|fixes|addresses|
      supersedes|duplicates|scopes] ... — nine kinds. ...

It states the count and enumerates the nine by name. It is stale **today**, not after TASK-798:
`targets` ships bundled in this commit and is accepted right now —

    sq task 21 ref add ADR-20 --kind targets
    -> TASK-21 → ADR-20 (targets);  frontmatter: refs: [ADR-20:targets]

so the README enumerates an accepted-kind list that is missing a kind the tool accepts, and asserts
a closed count the engine no longer enforces. It is the most adopter-facing of the four carriers
(PyPI and the repo front page).

This does not need re-filing against the cheatsheet or `docs/stability.md` — those are TASK-798's.
It needs TASK-798's scope (or ADR-775 section 6's carrier list) to gain the README, so the reissue
covers all of it rather than leaving the front page asserting the retired policy.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Width-tolerant ref severing lost its bare-ref coverage

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
**Read.** `tests/service/test_remove.py:93` (`test_remove_width_tolerant_ref_severing`) changed its
planted ref from `make_ref(old_width_id, "related")` to `make_ref(old_width_id, "blocks")`, with
the comment "non-default: stays spelled on disk" and the handoff rationale that the kind is
orthogonal to the test's subject (width tolerance).

The rationale is true about kind *semantics* and false about *encoding shape*, and the encoding is
the thing this whole change is about. Before the commit, `make_ref(id, "related")` collapsed to a
**bare** ref, so the fixture exercised severing a bare, old-width ref. After the switch it
exercises severing a **spelled**, old-width ref. Since the default kind is always written bare, the
bare form is the on-disk shape of the majority of edges — 598 of 1068 in this squad by the ADR's
own count — and that is the leg the test no longer covers.

The severing predicate itself is kind-agnostic (`ref_id_matches(split_ref(r)[0], ...)` at
`_services/_items.py:652-656`), so this is a coverage regression rather than a live bug — which is
why it is low. But the honest fix is the same one applied to the skew-guard test in this very
commit: parametrize over both legs rather than swap one for the other. The `blocks` leg is worth
keeping; the bare leg is worth having back.

(For the record, the fixture *had* to change: with `related` it plants a spelled default
consistently on index and disk, which the new fold correctly treats as skewed — the state finding
F3 describes. Swapping the kind was a reasonable way to unblock; keeping only one leg was not.)
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — sq workflow lint passes a spec every mutation then refuses

<!-- sq:finding:F6:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
**Driven.** TASK-796 shipped `[ref_kinds]` as an overridable section and `sq workflow lint`
together, but the per-capability floor that makes `default_ref_kind()` total is TASK-797's (US3),
and `WorkflowSpec.default_ref_kind`'s own docstring says so. The gap that leaves is visible today.

With `.overrides/workflow.toml` carrying `[selected] ref_kinds = [...]` that omits the entry
carrying `role = "default"` (a one-line, entirely plausible adopter edit):

    sq workflow lint   -> exit 0, "workflow spec OK — no errors or warnings."
    sq list            -> exit 0
    sq check           -> exit 3, "could not scan the corpus: the workflow spec must declare
                          exactly one ref kind with role = 'default' ...; found 0: []"
    sq repair          -> exit 1, same message
    sq task 3 status Ready -> exit 1, same message

The refusals are clean, single, and name the spec — that half is correct and is what the acceptance
asked for. The problem is that `sq workflow lint` is the command whose entire job is to tell an
adopter their spec is wrong, and it blesses a spec that no mutating command can use.

Not filed as a defect of the floor itself (that is TASK-797) — filed so TASK-797's scope explicitly
covers the **lint surface** and not only merge time. As US3 is worded ("checked on the merged
spec, fail-closed, every violation collected"), it is satisfiable by a merge-time refusal that
still leaves lint silent.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Never-prune plus no-orphans deadlocks a same-release delete

<!-- sq:finding:F7:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
**Driven** in a copied source tree (repo untouched): the store's two retention guards interact into
a state with no move inside their own contract.

    cp -r src scripts pyproject.toml <tmp>/ && cd <tmp>
    rm src/squads/_rendering/templates/agents/role.md.j2
    python scripts/gen_template_manifest.py

Result: the key leaves the current version's index entry, every historic entry and blob survives
(never-deletes works as specified), and the store is left holding one blob nothing references —
the artifact's *current-version* revision, inserted by this release's own generator run before the
deletion. `tests/meta/test_override_manifest_and_stamp_freshness.py::
test_every_stored_blob_is_referenced_by_at_least_one_index_entry` then fails, permanently: the
generator will not remove the blob (insert-if-absent, never deletes) and cannot make it referenced.

The trigger is narrow — an artifact **changed and deleted within the same release**. An artifact
deleted without having changed since the previous release keeps its blob referenced by that
release's entry and is fine. I checked ADR-777 B3's two prescribed deletions against this
specifically: `agents_md/role_entry.md.j2` and `agents_md/skill_entry.md.j2` carry blobs referenced
by 8 and 15 historic entries respectively, so B3 is **not** affected (**driven**).

Worth settling before someone meets it mid-release: either the orphan guard tolerates a blob whose
only referencing entry was removed in the same pass, or removing a bundled artifact is documented
as requiring the deletion to ride a release in which it is otherwise unchanged. Right now the
"never prune" contract and the "no orphans" guard can contradict each other.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-08-25T18:00:32Z] Robert Architect:
  - Ruled on ADR-777 and amended in place - new C1, plus a forward pointer added to A6. Drove it, and it is broader than filed: no deletion is needed. Against the shipped documents (84 blobs, 84 referenced, 0 orphans) I edited one bundled template and regenerated - 1 orphan; edited and regenerated again - 2; restoring the shipped content cleared neither. Every intermediate revision of an artifact within one release is orphaned by the next regeneration, because the index entry is a wholesale replacement while the store never deletes. Change-then-delete is one instance of that, not the trigger.
  - Neither guard yields as such. The orphan assertion stays and is promoted from an assertion about something having gone wrong into an invariant the generator maintains: its steady-state contract gains one clause, drop a blob no index entry references. A1 promise is untouched by construction - every revision it covers is named by an entry, so a reachability sweep cannot remove one. Drove the sweep: 2 blobs removed, all 84 index-named hashes still resolve, gen_template_manifest.py --check clean.
  - A6 never-deletes is narrowed to what its own reason supports rather than overruled. The hazard it names is a mis-ordered regeneration destroying retained history under the index replace semantics; a run rewrites exactly one entry, the current version, so the only blobs it can orphan are revisions that entry alone named. Historic entries are never rewritten, so the sweep provably cannot reach a retained revision. Never-prune restated: no revision an index entry names is ever removed.
  - Rejected the sequencing alternative - making a deletion ride a release in which the artifact is otherwise unchanged. It is unenforceable, silent when violated, answers only the deletion instance, and B3 already sanctions deleting bundled artifacts, so it would be a trap laid for a decision already taken. Confirmed your B3 check independently: each template current content is referenced by nine and sixteen index entries, so neither is orphaned by its removal. @tech-lead C1 wants a task under FEAT-791 - the generator sweep plus the guard restated as an invariant. Leaving this finding Open.
- [2026-08-25T18:14:31Z] Olivia Lead:
  - Tracked as TASK-812 under FEAT-791 (high, python-dev, US1): "Sweep unreferenced blobs in the generator steady state" - the reachability sweep plus the orphan guard restated as a maintained invariant, with never-prune narrowed to no revision an index entry names is ever removed. Priority is high rather than the finding low severity because I measured it: six artifact keys already carry content named only by the 0.14.0 entry, so the next edit to any of them reds tests/meta. TASK-813 carries a depends-on for exactly that reason.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — The VS Code client binds edge labels to a literal kind name

<!-- sq:finding:F8:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
**Read.** `clients/vscode/src/domain/graphDiagrams.ts:120-134`:

    function edgeLabel(edgeKind: string, direction: 'in' | 'out'): string {
      if (edgeKind === 'depends-on') { return direction === 'out' ? 'depends on' : 'required by'; }
      return edgeKind;
    }

This is the declared-but-found-by-literal shape ADR-775 section 2 removes from the engine and A2
added `edge_semantic` for — "emitting only the spelling would leave every agent testing
edge_kind == 'depends-on'". The client is one of those consumers. Under a project that renames its
dependency kind, the diagram silently loses the direction-aware label and prints the raw key in
both directions.

Not a defect of this commit: the conversion is TASK-797's, and the literal is still present in
`src/squads/_services/_refs.py` too (`_DEP_KINDS`, `:36`) because that work has not landed. Filed
because TASK-797's stated anti-drift mechanism is a `tests/meta` scan over `src/squads/` only, so
this call site is outside it by construction and will still be there after TASK-797 closes. One
line in that task's scope (or one added scan root) is all it needs.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T17:47:57Z] Paul Reviewer:
  - Reviewed 958974c (TASK-796, TASK-806, TASK-799). Eight findings: one high, three medium, four low. Recommended verdict: ChangesRequested on F1 alone; F2-F4 are medium and none of them blocks a release on their own.
  - The encoding invariant holds. I enumerated and drove every live write path (create --ref, ref add both spellings, skill ref add, the bulk importer's create and ref events, sub-entity mutation, retype, rename, repair, sync, adopt) on real squads and found no spelled default reaching disk or the index; _retype.py::_remap_ref was traced rather than accepted and genuinely cannot mint. A renamed default kind was driven too and behaves as A1 claims.
  - F1 is the one that matters: _migrations/_v0_5_to_v0_7.py::_unpad_ref still imports the live split_ref/make_ref, so its output for a spelled-default ref moved from bare to spelled in this commit -- the same retroactive-output defect ST3 closed for the 0.1-to-0.2 runner, in the runner nobody looked at. The new meta guard cannot catch it: it allowlists split_ref/make_ref by name on the ground that they are structural, which is exactly the property that changed.
  - Clean categories, stated as clean: the 0.1-to-0.2 fold is byte-identical across six fixtures driven under both trees; all 387 recorded manifest hashes match their own release tags with the eight corrections right and no other release moved; the content store's coverage guards are exact (84 hashes, 84 blobs, no orphans) and every uncarried-base diff shape exits 0 with no sq check finding.
  - @tech-lead F1 wants a task under FEAT-790 alongside TASK-806. F4 (README is a fourth carrier of the closed-nine-kinds claim, stale today because targets ships) belongs in TASK-798's scope. F6 and F8 are scope notes for TASK-797, not new work. @architect F3 contradicts ADR-775 A3's stated premise that disk is already canonical -- a pre-0.14 squad can hold a spelled default on disk, and A3's no-sweep conclusion still holds but its reason needs correcting.
- [2026-08-25T18:01:33Z] Olivia Lead:
  - Triaged F1, F2, F4, F5, F6, F8 into work. F3 and F7 are the architect - the operator ruled those out of my lane and I have not touched them.
  - F1 -> new TASK-809 (urgent, python-dev, FEAT-790, US1): "Refreeze the 0.5-to-0.7 runner and restore lost bare-ref coverage". Four subtasks - freeze the runner own ref handling with a byte assertion per input row; re-derive the guard rule so its rationale is true; add the repad fixture legs; and F5. Sequenced FIRST among the open FEAT-790 tasks, ahead of TASK-797 and TASK-807, and dependent on neither.
  - F5 -> TASK-809 ST4, not a TASK-806 follow-up. Same root cause as F1 (make_ref stopped collapsing the default), same remedy shape (parametrize the leg back rather than swap it), same owner - and TASK-806 is InReview on committed work, so amending it would reopen closed subtasks and desync this review.
  - F2 -> TASK-801 ST5. F4 -> TASK-798 ST5. F6 -> TASK-797 ST5 plus its acceptance, together with the A2 exactly-one-default clause that had been ruled onto that task but never written into its prose - F6 scenario is exactly what that clause catches.
  - F8 -> new TASK-810 (low, typescript-dev, FEAT-790, US2), depends-on TASK-797. Not a line in 797 scope: the owner role and toolchain differ, and 797 anti-drift scan is a Python AST walk over src/squads, so a TypeScript call site is outside it by construction - an added scan root cannot reach it.
  - Verified every cited line before folding. Two things beyond the report, both now in TASK-809: the 0.1-to-0.2 runner holds the same live import at :21 under the same falsified rationale in its docstring at :44, and that runner also imports DISPLAY_ID_PADDING, a live constant whose value is the width it writes - the same retroactive-output class, unexamined. @reviewer @architect
- [2026-08-25T23:39:02Z] Catherine Manager:
  - All eight findings fixed and committed: F1 and F5 by the runner refreeze, F2 by the restored freshness assertion, F3 by the stale-encoding wording plus the migration ruling, F4 by the contract prose reissue, F6 by the floor moving into spec validation, F7 by retiring the sweep for a rebuilt store, F8 by binding the client to the declared semantic.
<!-- sq:discussion:end -->

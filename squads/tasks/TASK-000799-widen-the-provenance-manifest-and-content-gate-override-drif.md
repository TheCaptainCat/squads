---
id: TASK-799
sequence_id: 799
type: task
title: Widen the provenance manifest and content-gate override drift
status: Done
parent: FEAT-791
author: tech-lead
assignee: python-dev
priority: urgent
refs:
- ADR-777:implements
description: Generalise the provenance manifest to every overridable bundled artifact
  with a retained content store, and content-gate spec and role drift
subentities:
- local_id: ST1
  title: Widen the manifest to every overridable bundled artifact
  status: Done
  story: US1
- local_id: ST2
  title: Content-addressed store with insert-if-absent semantics
  status: Done
  story: US1
- local_id: ST3
  title: Seed the store back to the 0.4.0 index floor
  status: Done
  story: US1
- local_id: ST4
  title: Coverage guards and the in-wheel store ceiling
  status: Done
  story: US1
- local_id: ST5
  title: Content-gate workflow and playbook drift
  status: Done
  story: US2
- local_id: ST6
  title: Measure role drift against roles.toml and fix its delta-mine
  status: Done
  story: US2
- local_id: ST7
  title: Delta-upgrade from the store, and the uncarried-base path
  status: Done
  story: US2
created_at: '2026-08-25T14:40:34Z'
updated_at: '2026-08-25T23:39:44Z'
---
<!-- sq:body -->
## Scope

ADR-777 §2 and amendment A1–A7 — FEAT-791 US1 and US2. Generalise the provenance manifest from
templates-only to every overridable bundled artifact, give it a content-addressed store, and
turn the four drift/diff divergences that gap produces into content-gated behaviour.

US1 and US2 are one task because they are one surface (`_overrides/_manifest.py`,
`_overrides/_service.py`, `scripts/gen_template_manifest.py`) and one shipping increment: the
widening is inert without the consumers, and the consumers cannot exist without the widening.
Splitting them across devs would collide on the same two files.

This is the FEAT-693 prerequisite named in ADR-776 §7 and ADR-777 §7: with `workflow.toml`
outside the manifest, every adopter who declares a view is warned their override may be stale
on every release, forever — manufacturing that false positive for the exact population the
feature is for.

## The widening (§2)

- The per-release manifest stops being a template manifest and becomes a manifest of everything
  an adopter may override: the **26 bundled templates plus `workflow.toml`, `roles.toml` and
  `playbook.toml`**. The generator script, the manifest-freshness guard
  (`tests/meta/test_override_manifest_and_stamp_freshness.py`) and the release step that runs
  the generator all widen to the same set rather than gaining a second mechanism beside them.
- `_overrides/_manifest.py` currently resolves every lookup against
  `squads._rendering.templates` (`current_template_hash`, `bundled_template_content`). It needs
  a per-artifact resolver and an artifact key namespace that cannot collide a template name
  with a spec document name. **The key namespace is not specified by ADR-777** — pick one,
  state it in the module docstring, and note that it is the manifest's own on-disk shape, so a
  later change to it is a manifest regeneration, not a migration.
- **The manifest carries deduplicated content, not hashes alone.** Hashes cannot reconstruct a
  past revision, which is exactly why the Δ-upgrade half of ADR-85 §5's contract is
  unhonourable today. ADR-85 §5 stays as written and the code moves to meet it; the narrowing
  alternative is recorded as rejected.

## Retention, settled by the amendment (A1–A4)

- **Nothing is pruned.** Every `(version, artifact)` pair the hash index names resolves to
  bytes, for every release the index covers. No window, no expiry.
- **The store is seeded once, at this widening release, back to the index's floor (0.4.0)** —
  a one-time data step against the release tags, **not a generator capability**. The generator
  itself never reads git; its steady-state contract stays "hash the current tree, insert what
  is absent."
- **Two write modes, deliberately distinct.** The per-version *index* entry stays a **wholesale
  replacement** keyed on `[project].version`. The *store* is **insert-if-absent and never
  deletes.** The separation confines the known mis-ordered-regeneration hazard to one version's
  index entry, which is recoverable from its tag; a store sharing the index's replace semantics
  would let the same mis-ordering destroy retained history no tag can restore.
- **The store is keyed on the same normalisation the index hashes** — CRLF-normalised bytes
  (`_overrides/_manifest.py:60-65`), so a Windows checkout hashes and looks up identically. One
  rule, one normalisation.
- **On-disk shape is decided, not open: one JSON document, not one file per blob.** Same
  content stored blob-per-file costs 134 KB in the wheel against 60 KB, because a zip deflates
  each member separately and these are small, highly similar files.
- **A 256 KB in-wheel compressed ceiling on the store replaces a window as the bound**, enforced
  by the freshness guard; a release that would cross it fails the gate.

## Release ordering

The generator's write for a release is a wholesale replacement of that version's entry keyed on
`[project].version`, and runs **only after the version bump** — ADR-781 §6's ordering, stated
once for every template/spec-touching change this release.

**That ordering is already satisfied: `pyproject.toml` is at 0.14.0, which is not a shipped
release. Do not run `scripts/bump_version.py`.** TASK-798 regenerates the same `0.14.0` index
entry after its cheatsheet edit; whichever of the two lands second regenerates over the other's
content, so the final regeneration must run with both changes in the tree.

## What content-gating fixes (§2, US2)

- `_workflow_state`/`_playbook_state` and `workflow_stamp_finding`
  (`_workflow/_loader.py:966-999`) / `playbook_stamp_finding`
  (`_interactions/_loader.py:482-505`) **lose their "no per-release content-hash" branch**. An
  add-only `.overrides/workflow.toml` stamped a release back with no bundled change behind it
  stops reporting `workflow override may be stale` and stops classifying as `drifted` — the
  false-positive class ADR-85 §3 forbids by name.
- **A role override's drift moves onto `roles.toml`**, the document it actually overrides.
  `_role_state` and `_diff_role` currently ask
  `template_changed_since("agents/role.md.j2", …)` (`_overrides/_service.py:178-193`,
  `:659-706`) — the role *body template* — so a change to a bundled role's mission or a new
  `RoleSpec` field cannot drift a role override, while a cosmetic body-template edit drifts
  every one. The body template stays a separate override with its own stamp and its own drift;
  conflating the two was the bug.
- **A role override's Δ-mine diffs against the shadowed bundled content**, not
  `_unified_diff("", override_text, fromfile="(empty — role overrides start from scratch)", …)`
  (`_overrides/_service.py:668-674`). A role override merges field-wise over the bundled role,
  so it shadows; an empty baseline describes only what the team added and says nothing about a
  shadowed field. This is the same fix already shipped for the workflow document
  (`_overrides/_service.py:729-733`), applied to the kind that still lacks it.
- **Δ-upgrade becomes expressible for a spec document at all**, resolved out of the content
  store rather than from `base_version_template_content`'s current-content-when-hash-matches
  fallback (`_overrides/_manifest.py:94-112`).

## The uncarried-base path (A5) — get this exactly right

Three shapes remain under full retention: a stamp **below the index's floor**, a stamp naming a
version **squads never released**, and a stamp **newer than the running version**. One instance
ships on day one — a squad whose `.overrides/workflow.toml` is stamped before the widening
holds a stamp for an artifact the index did not then cover, which is what the seeding reaches.

- **It is not an `sq check` finding at any severity — not an error and not a warning.** The
  severity ladder is for an obligation an adopter can discharge. An uncarried base revision is
  squads' own coverage limit, and the only action available to them is `sq override update`,
  which would clear the report by destroying the provenance they still have.
- **The drift classifier stays silent, which is what already ships.**
  `template_changed_since` returns `False` for an unrecorded base — "unknown history is treated
  as unchanged, never as a warning" (`_overrides/_manifest.py:78-89`). That is ADR-85 §3's rule
  and the widening must leave it exactly as it is.
- **`sq override diff` states it in full and exits 0.** Δ-mine is unaffected and still renders.
  The Δ-upgrade pane names the artifact, the stamped version, and which of the three shapes it
  is. Where an anchor exists — a stamp below the floor — it renders a **partial Δ-upgrade from
  the earliest carried revision**, labelled with where the delta actually starts and stating
  plainly that changes before that point are not represented. A downgrade has no anchor in the
  right direction and refuses, saying that.
- **The shipped "content changed but base snapshot is not available; refer to the squads
  changelog or git history" message goes** (`_overrides/_service.py:643-647`). Its replacement
  is bounded by a rule rather than by taste: it must name the artifact, the stamped version,
  why that revision is not carried, and what *is* available instead. "Read the changelog"
  answers none of the four.
- **A stamp naming a version squads never released is a malformed stamp** and falls under the
  existing stamp obligation; this path covers only well-formed stamps whose revision is not
  carried.

## Hard boundary (A7)

**The store is provenance for diffing only — never an input to validation, to the merge, or to
the live-corpus cross-check.** ADR-696 §5a recovers a type's expected `prefix` and `folder`
from the live items themselves and records "it stores nothing new" as one of the three
properties that make it minimal. A retained `workflow.toml` revision is now a second,
plausible-looking answer to "what did this type used to declare". It is not one. The corpus
remains the authority on what its items were written under.

The store is package data inside the wheel, not squad data — never migrated, never repaired,
and a squad never carries a copy. The consequence worth stating rather than discovering is that
an adopter's Δ-upgrade reach is a function of the *installed* squads version, not of their
squad folder, which is why the downgrade shape exists at all.

## Acceptance

- `sq override list` reports `workflow`/`playbook`/`roles` drift **only** when the bundled
  document's content actually changed since the recorded stamp; an add-only override stamped
  several releases back with no bundled change reports clean, not "may be stale".
- A change to a bundled role's mission, or a new `RoleSpec` field, drifts a role override that
  shadows it; a cosmetic edit to `agents/role.md.j2` does not.
- `sq override diff --mine` on a role override shows a real Δ against the shadowed bundled
  content, not an empty baseline.
- `sq override diff` (Δ-upgrade) works for `workflow.toml`, `playbook.toml` and `roles.toml`
  whenever the bundled document changed between the override's stamped version and the running
  one **and that stamped revision is carried by the store**.
- For each of the three uncarried shapes: `sq override diff` exits 0, Δ-mine renders, the
  Δ-upgrade pane names artifact + stamped version + which shape it is; where an earlier carried
  revision exists it renders a partial delta labelled with where the delta starts; a downgrade
  refuses with a reason. None of the three produces an `sq check` finding at any severity, and
  the drift classifier stays silent for all three.
- Every hash named by any index entry resolves in the store, and every blob in the store is
  referenced by at least one index entry, for every release the index covers — both asserted by
  `tests/meta` guards.
- The store's compressed in-wheel size is under 256 KB and the guard fails a release that would
  cross it.
- Regenerating the manifest twice at the same version is stable: the index entry is replaced
  wholesale, the store gains nothing and loses nothing.
- The store covers 0.4.0 through the running version after the one-time seeding, and the
  generator contains no git access.
- `scripts/bump_version.py` was not run; `pyproject.toml` still reads 0.14.0.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 799 add-subtask "<title>"`; track with `sq task 799 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Widen the manifest to every overridable bundled artifact | US1 |
| ST2 | Done |  | Content-addressed store with insert-if-absent semantics | US1 |
| ST3 | Done |  | Seed the store back to the 0.4.0 index floor | US1 |
| ST4 | Done |  | Coverage guards and the in-wheel store ceiling | US1 |
| ST5 | Done |  | Content-gate workflow and playbook drift | US2 |
| ST6 | Done |  | Measure role drift against roles.toml and fix its delta-mine | US2 |
| ST7 | Done |  | Delta-upgrade from the store, and the uncarried-base path | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Widen the manifest to every overridable bundled artifact

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Widen the manifest to every overridable bundled artifact
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
The manifest stops being a template manifest and becomes a manifest of every overridable bundled
artifact: the 26 bundled templates plus `workflow.toml`, `roles.toml` and `playbook.toml`.

The generator script, the manifest-freshness guard
(`tests/meta/test_override_manifest_and_stamp_freshness.py`) and the release step that runs the
generator all widen to the **same set** rather than gaining a second mechanism beside them.

`_overrides/_manifest.py` resolves every lookup against `squads._rendering.templates` today
(`current_template_hash`, `bundled_template_content`, `template_hash_at_version`). It needs a
per-artifact resolver and an artifact key namespace that cannot collide a template name with a
spec document name.

**The key namespace is not specified by the decision.** Pick one, state it in the module
docstring, and record there that it is the manifest's own on-disk shape — so a later change to
it is a manifest regeneration, not a migration.

Done when every artifact in the widened set has an index entry for the running version and the
freshness guard covers all of them.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Content-addressed store with insert-if-absent semantics

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — Widen the manifest to every overridable bundled artifact
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add the content-addressed store beside the hash index: hash to bytes, deduplicated across
releases, so a release costs only the artifacts it actually changed. Hashes cannot reconstruct a
past revision, which is why the Δ-upgrade half of the durable diff contract is unhonourable
today.

Three properties are decided and not open:

- **On-disk shape: one JSON document, not one file per blob.** The same content stored
  blob-per-file costs 134 KB in the wheel against 60 KB, because a zip deflates each member
  separately and these are small, highly similar files. A 2.2x difference for no semantic gain.
- **Write mode: insert-if-absent, never deletes** — deliberately distinct from the index entry's
  wholesale replace keyed on `[project].version`. A mis-ordered regeneration can overwrite one
  version's index entry, which its tag can restore; it must never be able to destroy retained
  history no tag can restore.
- **Keyed on the same normalisation the index hashes** — CRLF-normalised bytes
  (`_overrides/_manifest.py:60-65`) — so a Windows checkout hashes and looks up identically. One
  rule, one normalisation.

Done when regenerating twice at the same version replaces the index entry and leaves the store
byte-identical, and a lookup from a CRLF checkout resolves.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Seed the store back to the 0.4.0 index floor

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US1 — Widen the manifest to every overridable bundled artifact
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Seed the store once, at this widening release, back to the index's own floor (0.4.0, the first
release the manifest records). A store covering fewer versions than the index would be a third
state the diff has to explain, on top of *carried* and *never recorded*.

This is a **one-time data step against the release tags, not a generator capability**. The
generator itself never reads git; its steady-state contract stays "hash the current tree, insert
what is absent."

Measured across 0.4.0 to 0.13.1 (15 releases) over the widened set: 402 file-revisions
deduplicate to 79 blobs, 283 KB of raw content, 60.0 KB compressed as one JSON document in the
wheel.

Run `git fetch --tags` before reasoning about which tags exist — a local tag list can be stale.

Done when the store resolves every index-named hash from 0.4.0 to the running version, the
seeding script is separate from the generator, and `grep` finds no git access in the generator.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Coverage guards and the in-wheel store ceiling

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US1 — Widen the manifest to every overridable bundled artifact
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Never pruning is unbounded in principle, so the bound is asserted rather than assumed, and the
retention promise is made checkable rather than trusted.

Three guards:

- **Every hash named by any index entry resolves in the store**, for every release the index
  covers. This is the retention promise itself.
- **Every blob in the store is referenced by at least one index entry.** With nothing pruning,
  an orphan from a bug or a hand-edit is the only way the store grows without a release, and
  this is the only thing that would catch it.
- **A 256 KB compressed in-wheel ceiling on the store**, wired into the manifest-freshness
  guard; a release that would cross it fails the gate. That places the reconsideration at the
  moment there are real numbers to reconsider with, rather than pre-committing to a retention
  window now against a projection. At the measured ~2.4 KB per release the ceiling is roughly
  eighty releases away.

Done when each guard fails for a hand-broken manifest exercising its own case, and passes on the
shipped one.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Content-gate workflow and playbook drift

<!-- sq:subtask:ST5:head -->
**Status:** 🟢 Done
**Implements:** US2 — Content-gate workflow/playbook/role drift
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
`_workflow_state`/`_playbook_state` (`_overrides/_service.py:158-231`) and their stamp findings —
`workflow_stamp_finding` (`_workflow/_loader.py:966-999`), `playbook_stamp_finding`
(`_interactions/_loader.py:482-505`) — warn on `stamp != __version__` unconditionally, each with
a comment saying why ("no per-release content-hash for the workflow TOML in the manifest").

Drop that branch. Drift becomes content-gated, honouring the rule the template and role paths
already honour: an override whose bundled counterpart did **not** change is silent, and an old
stamp alone is never a warning.

Driven today: an add-only `.overrides/workflow.toml` stamped one release back reports
`warn … workflow override may be stale` and classifies as `drifted`, with no bundled change
behind either.

Done when an add-only override stamped several releases back with no bundled change reports
clean in both `sq check` and `sq override list`, and one with a real bundled change behind it
still warns.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Measure role drift against roles.toml and fix its delta-mine

<!-- sq:subtask:ST6:head -->
**Status:** 🟢 Done
**Implements:** US2 — Content-gate workflow/playbook/role drift
<!-- sq:subtask:ST6:head:end -->

<!-- sq:subtask:ST6:body -->
`_role_state` and `_diff_role` ask `template_changed_since("agents/role.md.j2", …)`
(`_overrides/_service.py:178-193`, `:659-706`) — the role **body template** — so a change to a
bundled role's mission, or a new `RoleSpec` field, cannot drift a role override, while a
cosmetic edit to the body template drifts every one of them.

Move a role override's drift onto `roles.toml`, the document it actually overrides. The body
template stays a separate override with its own stamp and its own drift; conflating the two was
the bug.

Separately, `_diff_role` renders
`_unified_diff("", override_text, fromfile="(empty — role overrides start from scratch)", …)`
(`:668-674`). A role override merges field-wise over the bundled role, so it **shadows**; an
empty baseline describes only what the team added and says nothing about a shadowed field. Diff
against the shadowed bundled content instead — the same fix already shipped for the workflow
document (`:729-733`), applied to the kind that still lacks it.

Done when a bundled mission change drifts a shadowing role override, a cosmetic body-template
edit does not, and `sq override diff --mine` on a role override shows a real delta.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Delta-upgrade from the store, and the uncarried-base path

<!-- sq:subtask:ST7:head -->
**Status:** 🟢 Done
**Implements:** US2 — Content-gate workflow/playbook/role drift
<!-- sq:subtask:ST7:head:end -->

<!-- sq:subtask:ST7:body -->
Resolve Δ-upgrade out of the content store, replacing
`base_version_template_content`'s current-content-when-the-hash-matches fallback
(`_overrides/_manifest.py:94-112`) — which honours the two-delta contract only in the case where
there is no upgrade delta to show.

Then handle the uncarried base revision. Three shapes remain under full retention: a stamp
**below the index's floor**, one naming a version **squads never released**, and one **newer
than the running version**. One instance ships on day one: a squad whose override is stamped
before the widening holds a stamp for an artifact the index did not then cover.

- **Not an `sq check` finding at any severity — not error, not warning.** Severity is for an
  obligation the adopter can discharge. This is squads' own coverage limit, and the only action
  available to them, `sq override update`, would clear the report by destroying the provenance
  it is about.
- **The drift classifier stays silent, which is what already ships.**
  `template_changed_since` returns `False` for an unrecorded base — "unknown history is treated
  as unchanged, never as a warning" (`_overrides/_manifest.py:78-89`). Leave that exactly as it
  is.
- **`sq override diff` states it in full and exits 0.** Δ-mine is unaffected. The Δ-upgrade pane
  names the artifact, the stamped version, and which of the three shapes it is. Where an anchor
  exists — a stamp below the floor — it renders a **partial Δ-upgrade from the earliest carried
  revision**, labelled with where the delta actually starts and stating plainly that changes
  before that point are not represented. A downgrade has no anchor in the right direction and
  refuses, saying that.
- **The shipped "content changed but base snapshot is not available; refer to the squads
  changelog or git history" message goes** (`_overrides/_service.py:643-647`). Its replacement
  must name the artifact, the stamped version, why that revision is not carried, and what **is**
  available instead. "Read the changelog" answers none of the four.
- A stamp naming a version squads never released is a **malformed stamp** and falls under the
  existing stamp obligation; this path covers only well-formed stamps whose revision is not
  carried.

Hard boundary: the store is provenance for diffing only — never an input to validation, to the
merge, or to the live-corpus cross-check. A retained `workflow.toml` revision is a
plausible-looking second answer to "what did this type used to declare", and it is not one. The
corpus remains the authority on what its items were written under.

Done when each of the three shapes exits 0 with the stated pane, none produces an `sq check`
finding, and the partial-delta case is labelled with its actual starting revision.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T15:02:15Z] Robert Architect:
  - Ruled, ADR-777 amendment B1 (2026-08-25). The delegation in ST1 is withdrawn - do not pick a namespace. A manifest entry is keyed on the artifact path relative to the squads PACKAGE ROOT: _rendering/templates/agents/role.md.j2, _specs/workflow.toml. Every overridable bundled artifact is package data inside that one package, so a key is unique by construction rather than by convention, derivable rather than registered, and a fifth kind inherits the namespace without a decision of its own. _manifest.py single resolver moves from squads._rendering.templates to squads (_overrides/_manifest.py:53-56, :69-72) - no per-kind dispatch table, which is what section 2 no-second-mechanism asks for.
  - Why it is not the implementer call: the key namespace is the manifest own on-disk shape, shared by the generator, the freshness guard, the seeding step and every consumer, and changing it later rewrites shipped releases entries - the one hazard Consequences and A6 both single out. A6 already settles the store key normalisation at decision level; the index key space is the same class of fact and its absence from section 2 was an omission. The flat space also has no room today: workflow.md.j2 and workflow_static.md.j2 already sit at its top level, so a bare workflow.toml beside them would be distinguishable only by extension.
  - Shape change for ST1 and ST3, no new subtask. ST1 drops the "pick one, state it in the module docstring" clause and implements the stated namespace; the docstring still records that the key space is the manifest own on-disk shape, so a later change is a regeneration and not a migration. ST3 gains the REKEY: prefixing _rendering/templates/ onto the historic keys rewrites every version entry, so it is performed by the same one-time data step that seeds the store back to 0.4.0, in one pass, carrying the recorded hashes over unchanged. The generator steady-state contract is untouched - hash the current tree, replace this version index entry, insert what is absent from the store. @python-dev @tech-lead
- [2026-08-25T15:37:08Z] Elias Python:
  - Implemented ST1-ST7. Manifest widened to every overridable bundled artifact (26 templates + workflow/roles/playbook.toml), keyed package-root-relative per ADR-777 B1 (single resolver in _overrides/_manifest.py, no per-kind dispatch). New content_store.json ships alongside templates_manifest.json: sha256 -> normalized text, insert-if-absent, deduplicated.
  - Seeded the store back to 0.4.0 via a new one-time scripts/seed_content_store.py (git-tag based, separate from the generator, which stays git-free). Rekeyed all 16 historic index entries onto the new namespace. Found and corrected 8 pre-existing hash values at v0.4.0/v0.6.0 that disagreed with their own release tags (a pre-existing data-integrity defect independent of the rekey) — corrected against the tags as ground truth, printed loudly by the seeding script.
  - Content-gated drift for workflow/playbook/role (state, sq check, sq override list): an uncarried or unchanged base is silent, never a stamp-age warning. Role drift now measured against roles.toml, not agents/role.md.j2 (driven over real history: role.md.j2 changed 0.13.0->0.14.0, roles.toml did not, so a v0.13.0-stamped role override now correctly stays current). Role delta-mine now diffs against the shadowed bundled role's fields instead of an empty baseline. Delta-upgrade is resolved from the store for every kind (workflow/playbook/roles/templates), with the retired 'refer to the changelog' message replaced by the ADR-777 A5 uncarried-base pane (partial delta from the earliest carried revision, downgrade refusal, or a named not-carried explanation) — exits 0, never an sq check finding.
  - Known gap, flagged rather than silently left: squads/_workflow/_loader.py's workflow_stamp_finding (the function sq workflow lint calls directly) is out of scope this pass per the concurrency brief and still warns on stamp age alone. sq check / sq override list / sq override diff are correct today via a local content-gated implementation in _overrides/_service.py; workflow_stamp_finding itself needs the same fix once _workflow/ is back in scope.
  - Measured store size: content_store.json compresses to ~79.7 KB, index ~4.5 KB (combined ~84 KB), well under the 256 KB ceiling. Higher than the ~60 KB predicted -- JSON string-escaping inflates raw content bytes beyond plain file size, plus 84 blobs landed vs the ~79 predicted (the 8 corrected hashes + real dedup boundaries differ slightly from the earlier estimate).
  - pyproject.toml untouched, still 0.14.0. git diff on templates_manifest.json touches all 16 version entries structurally (the mandated B1 rekey renames every template key), but the only HASH VALUES that actually changed are: the 8 corrections above, new roles/workflow/playbook.toml keys added starting at their real introduction (v0.13.0), and v0.14.0's own workflow.toml hash reflecting TASK-796's landed ref_kinds change in this shared tree. No other prior release's tracked hash moved.
  - Targeted gates clean: tests/meta/ (188 passed), integration+cli+unit+service override/manifest-filtered set (527 passed), full-repo ruff check + ruff format --check + pyright all clean (0 errors). sq check clean.
<!-- sq:discussion:end -->

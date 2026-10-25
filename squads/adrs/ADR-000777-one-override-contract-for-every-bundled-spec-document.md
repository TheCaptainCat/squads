---
id: ADR-777
sequence_id: 777
type: decision
title: One override contract for every bundled spec document
status: Accepted
author: architect
refs:
- FEAT-693:addresses
- ADR-85
- ADR-214
- ADR-221
- ADR-226
- ADR-696
- ADR-775
- ADR-776
- ADR-781
- ADR-1151
created_at: '2026-08-22T09:28:30Z'
updated_at: '2026-10-25T21:42:18Z'
---
<!-- sq:body -->
## Context

Three bundled documents ship as package data under `_specs/`: `workflow.toml` (ADR-214),
`roles.toml` (ADR-221) and `playbook.toml` (ADR-226), each with its own loader and spec models,
over the override design ADR-85 froze and the shared merge engine ADR-696 §4 settled. The question
is whether their override treatment is uniform, and what uniform should mean.

**Scope.** Five axes: whether each document has a whole-document override surface; the merge
semantics and precedence each one gets; each one's top-level key space; the availability of the
`[selected]` deselect; and each one's provenance, staleness classification and diff. It does
**not** reopen the merge engine's own semantics (ADR-696 §4/4a/4b), the lifecycle floor (§3), the
live-corpus cross-check (§5a), or ADR-85 §4's naming and init surface. `.overrides/templates/` is in
scope only as the reference implementation the spec documents are measured against.

**One axis was uniform, and it was the one with a guard.** All three loaders resolve their override
through `merge_override`, so all three get splat-refs against the bundled base, a leaf-granular deep
merge, a closed top level and a `[selected]` refused where it has no meaning. A `tests/meta` scan
asserts that routing per loader
(`tests/meta/test_every_override_document_merges_through_the_shared_engine.py`).

**Every other axis diverged, when this was decided.** The provenance manifest covered only the
rendering templates, so workflow and playbook drift warned on stamp age alone on every release:
the false-positive class ADR-85 §3 forbids by name. A role override's drift was measured against
the role *body template* rather than `roles.toml`, and its Δ-mine diffed against an empty reference.
Δ-upgrade was unavailable whenever the bundled document had actually changed, because the manifest
carried hashes and no content. The roles catalog had no whole-document override, so `[bundles]` and
`[dev]` could not be overridden at all. ADR-696 §4b said a role override's top level is open while
the code closed it. And a missing stamp on a shadowing override was an error for workflow and
playbook but a warning for templates and roles.

## Decision

### 1. What uniform means: the adopter's contract, not the file layout

Uniformity is owed on what an adopter is promised, never on how the document is addressed on disk.
ADR-696 §4c licensed layout asymmetry with reasons, and those reasons hold. These six promises apply
identically to every overridable bundled artifact, and any per-kind difference must be a stated
consequence of the document's own structure:

1. **A whole-document surface, or a stated reason there is none.**
2. **One merge engine, with a closed top level**: one grammar, one refusal shape.
3. **One provenance carrier**, the `# squads:override-base:<version>` comment (ADR-696 §4).
4. **Drift only when the bundled counterpart actually changed** (ADR-85 §3).
5. **Both deltas, or a precise statement of why one is unavailable** (ADR-85 §5).
6. **One severity for a missing stamp on a shadowing override.**

### 2. One manifest of every overridable bundled artifact, with content

The per-release manifest covers everything an adopter may override: the bundled templates plus
`workflow.toml`, `roles.toml` and `playbook.toml`. The generator script
(`scripts/gen_template_manifest.py`), the manifest-freshness guard
(`tests/meta/test_override_manifest_and_stamp_freshness.py`) and the release step cover that whole
set, with no second mechanism beside them. What follows with no per-kind logic:

- Workflow and playbook drift is content-gated, like a template's.
- A role override's drift is measured against `roles.toml`, the document it overrides. The role
  body template is a separate override with its own stamp and drift.
- Δ-upgrade is expressible for a spec document.

**Two parts, two files.** `templates_manifest.json` is the hash **index**: `squads_version ->
{artifact_key -> sha256}`. `content_store.json` is the content **store**: `sha256 -> normalised
text`, deduplicated across releases, one JSON document (a blob-per-file layout deflates each small
member separately and costs about twice as much in the wheel). Hashes alone cannot reconstruct a
past revision, which is what the Δ-upgrade promise needs. ADR-85 §5 stays as written and the code
meets it; narrowing the clause to what hashes alone can show was rejected, because a diff that can
only say "something changed, read the changelog" leaves an adopter hand-merging blind.

**The key** of an entry is the artifact's path relative to the `squads` package root
(`_rendering/templates/agents/role.md.j2`, `_specs/workflow.toml`): unique by construction,
derivable rather than registered, so a fifth kind inherits the namespace. One resolver reads it.
The store is keyed on the same CRLF-normalised bytes the index hashes, so a Windows checkout hashes
identically.

**Retention: no revision an index entry names is ever removed.** Every `(version, artifact)` pair
the index names resolves to bytes, for every release the index covers, with no window and no
expiry. A window is refused on ADR-85 §3's ground rather than on cost: content-gated drift needs the
stamped revision's content to answer "did the bundled counterpart actually change?", and past a
window the only fallbacks are warning on stamp age, which §3 forbids, or reporting clean when we do
not know. A window would also prune exactly the adopter with the oldest stamp, the largest delta
and the weakest memory of what they edited. The bound is a ceiling instead: the freshness guard
fails a release whose store exceeds **256 KB compressed** in the wheel (measured over 0.4.0 to
0.13.1: 402 file-revisions deduplicated to 79 blobs, about 60 KB in the wheel, growing a few KB per
release under pre-1.0 churn).

**The store is a derived artifact.** Its definition is every hash the index names, resolved to its
content: a total function of the index, the release tags and the working tree.

- **The generator never deletes** and never reads git. Its steady state: hash the current tree,
  replace the running version's index entry, insert what is absent from the store. Discarded
  revisions of the working version accumulate between releases as ordinary development residue.
- **The rebuild is the only thing that removes a blob.** `scripts/seed_content_store.py --rebuild`
  recomputes the store as the closure of every index-named hash, sourced from each version's
  release tag and, for the running version, from the working tree, and drops whatever is outside
  it. It is all-or-nothing: a version whose tag it cannot reach is a refusal naming the version,
  never a skip. It also corrects an index entry that disagrees with its own tag, which is what a
  regeneration at a shipped version produces. Publication is knowable only from the tags, and this
  script is the one git-reading participant.
- **An orphan-free store is a property of the release artifact**, checked at the release gate,
  where the rebuild runs. An ordinary freshness check reports an orphan without failing.
- **The freshness check verifies coverage across the whole index**, every version and every key,
  and fails naming the version and the artifact when an index-named hash does not resolve. Its
  success line states what it checked. It writes nothing.
- The protection is for **silence**, not irrecoverability: every index-named revision is
  recoverable from its tag, but a store missing one is reported by nothing unless the gate checks
  it.

**When a base revision is not carried** (a stamp below the index's floor, a stamp naming a version
squads never released, a stamp newer than the running version):

- It is not a `sq check` finding. Severity is for an obligation an adopter can discharge, and the
  only action available, `sq override update`, would clear the report by destroying the provenance
  they still have.
- The drift classifier stays silent: unknown history is treated as unchanged, never as a warning
  (ADR-85 §3).
- `sq override diff` states it in full and exits 0. Δ-mine renders. The Δ-upgrade pane names the
  artifact, the stamped version and which shape it is; for a stamp below the floor it renders a
  partial Δ-upgrade from the earliest carried revision, labelled with where the delta starts; a
  downgrade has no anchor and says so.
- A stamp naming a version squads never released is a malformed stamp, under §6's obligation.

**The store is provenance for diffing only**, package data inside the wheel, never squad data:
never migrated, never repaired, never an input to validation, the merge or ADR-696 §5a's
cross-check, which recovers a type's `prefix` and `folder` from the live items. An adopter's
Δ-upgrade reach is a function of the installed squads version.

### 3. The roles catalog has a whole-document override

`.overrides/roles.toml` is a spec override document resolved by the role catalog loader on the same
shape as the other two: squad-aware, merged through the shared engine, a closed top-level key space
plus `selected`, its own stamp, its own drift and its own `sq override scaffold roles`. It covers
`[bundles]`, the developer template table and `[defaults]` (ADR-981), and `[[roles]]` for a project
that would rather state its catalog in one document. ADR-1151 decides the template table's shape:
the key space is `{roles, bundles, templates, defaults}`, `[dev]` is `[templates.dev]`, the first
entry of a keyed `[templates]` section, a `.overrides/roles.toml` that still carries `[dev]` is
refused at load, naming the file and the rename, with no alias, and `[selected]` deselects
`templates` entries too.

The per-slug `.overrides/roles/<slug>.toml` files stay, for the reason ADR-696 §4c gives: the
filename is the key, and per-slug files are what let a project be current on one role and stale on
another. Precedence is bundled base, then the catalog document, then the per-slug file: most
specific last, the direction template resolution runs.

That precedence governs a role's definition: its mission, responsibilities, skills, model and the
other catalog fields. It supplies the role's **name** only when the role is created, and only when
`--name` is not given; for a developer the name pool is the last source. After creation the stored
name is the role's name: no later change to the bundled catalog, the catalog document or a per-slug
file renames an active role, and a rename goes through the role's update verb (op-pierre,
2026-10-16).

`[selected]` on the catalog document deselects `roles` and `bundles` entries, so a project can hide
an unwanted role from `sq role catalog`. The floor does the work: `bundles` referential integrity and
the at-most-one-default rule run on the built catalog, so a deselect that empties a bundle or
removes the default fails on the resulting spec with no deselect-specific guard.

How a role's base is chosen (a catalog entry, a template or the item itself) is ADR-1151's.

### 4. A role override's top level is closed

The accepted key set is derived from `RoleSpec.model_fields`, so it grows with the model instead of
going stale beside it. ADR-696 §1's rule decides it: validation replaces trust. A key the model does
not know is a violation naming the key, and the forward-compatibility case is served by the refusal
telling the adopter which key, not by discarding it; the silent key-dropping an open top level gives
had produced persisted defects with `sq check` clean (a truthy `can_spawn = "false"` among them).
ADR-696 §4b's open-top-level clause is narrowed accordingly.

`merge_override`'s `top_level_keys` is a required, keyword-only `frozenset[str]` with no default
and no explicit-`None` escape: every overridable bundled document has a closed top level, which is
§1's second promise in full, and "deliberately open" is not expressible without amending a
decision.

### 5. `[selected]` is workflow-and-catalog only, and that is settled

The playbook derives its type set from the workflow spec's, so dropping a type drops its playbook
entry as a consequence rather than by declaration (ADR-696 §4c). A per-slug role file has no keyed
sections to shrink. Both refusals carry a caller-supplied reason. This axis is uniform by
derivation, not debt.

### 6. One severity, and one guard

A shadowing override with no stamp is an **error**-level finding for every kind; an add-only
override with no stamp reports nothing; a stamp older than the running version, with the bundled
counterpart changed, is a **warn**. A whole-file template override always shadows, so an unstamped
template override is an error. The message names the file and the fix (`sq override scaffold
--force` to re-scaffold with a stamp, or `sq override update` after verifying the content), and
`sq override update` with no name re-stamps every structurally valid override at once, so the
remediation is one command however many overrides a squad carries. There is no grace period keyed
on the upgrade: a severity that depends on when a squad last upgraded is a second rulebook.

The uniformity has a guard, in the shape of the routing guard: a `tests/meta` scan asserts that
every override kind has a manifest entry for its bundled counterpart, a state classifier, a
stamp-obligation finding and both diff deltas, so a further kind cannot ship with three of the four
wired.

### 7. What a declared view inherits

Derived views are a keyed section of the workflow document (ADR-776), and inherit all of the above:

- **Merge and deselect.** A view set merges leaf-granularly, an adopter appends to a bundled list
  with a splat-ref, and `[selected]` drops a bundled view.
- **Referential validation on the merged spec.** A view naming a type, ref kind or sub-entity kind
  the merged spec does not declare fails the pass that catches a lifecycle bound to a dropped
  status.
- **Provenance.** Content-gated drift on `workflow.toml` is what lets an adopter declare a view
  without being warned on every release. A view's presentation template is an ordinary entry under
  `.overrides/templates/`.

### 8. No override surface without a consumer

An overridable bundled template that nothing renders is an override surface with no consumer, which
§1's first promise forbids. Such a template is deleted, not kept: the `agents_md` role and skill
entry templates were removed for this reason. Retention is undisturbed: past index entries keep
naming their revisions and the store keeps the blobs, so an adopter who overrode one still diffs
against a real base.

## Consequences

- **The generator and the release step cover the three spec documents**, and the freshness guard
  covers every entry: a forgotten regeneration fails loudly.
- **The index entry is replaced wholesale, keyed on `[project].version`**, so the version bump comes
  before the regeneration at a release (ADR-781 §6), or the shipped release's recorded entry is
  overwritten. The rebuild is the recovery when that happens.
- **Adopters with a workflow or playbook override are warned only when the bundled document
  changed.**
- **Nothing about the merge changed.** The decision is about provenance, diff, classification, one
  new document and one severity.
- **`sq override list` shows every kind**, and `sq check`'s exit code is 3 for a squad carrying an
  unstamped template override.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T09:30:55Z] `architect` Robert Architect:
  - Scoped to five axes measured against the code: whether each document has a whole-document surface, merge semantics, top-level key space, deselect availability, and provenance/staleness/diff. Explicitly out: the merge engine semantics, the lifecycle floor, the cross-check existing clauses, and ADR-85 naming/init.
  - Only one axis is uniform — the merge routing — and it is the one with a tests/meta guard. Every other axis diverges: the manifest tracks 26 templates and zero .toml (driven), so workflow/playbook drift is stamp-only and warns on every release regardless of whether the bundled document moved, which is the false positive ADR-85 section 3 forbade by name. A role override drifts against agents/role.md.j2 rather than roles.toml, and its delta-mine still diffs against an empty reference — the defect already fixed for workflow.
  - Uniform means the adopter contract, not the file layout: ADR-696 section 4c licensed the addressing asymmetry and that holds. Load-bearing fix is generalising the manifest to every overridable artifact and carrying content rather than only hashes, which is what makes delta-upgrade honourable at all (~88KB for a full snapshot vs a 35KB hash-only manifest today). roles.toml gains a whole-document override; the per-slug files stay.
  - Two things I would rather you ruled than have me guess: whether the manifest carries content snapshots or ADR-85 delta-upgrade narrows instead, and whether an unstamped template override becomes an error (it changes sq check exit code for existing squads). Also flagging that section 4 overrides ADR-696 section 4b role-top-level clause in favour of what the code already does. @op-pierre @manager left Proposed.
- [2026-08-22T09:44:31Z] `op-pierre` Pierre Chat:
  - Manifest: carry deduplicated content, not hashes alone, so the delta-upgrade promise in ADR-85 section 5 becomes honourable instead of narrowing the promise to match the code. The measured wheel cost, about 88KB against a 35KB hash-only manifest after fourteen releases, is acceptable for telling an adopter what actually changed under an override they wrote.
  - Stamp severity: uniform, and that means a missing stamp on a shadowing template override becomes an error like every other overridable artifact. Accepting the exit-code change for squads that already carry one - the divergent severity is how template overrides got overlooked in the first place.
  - Section 4 reversing ADR-696 section 4b is nodded: the code is the truth here, the reversal aligns the decision with shipped behaviour rather than changing behaviour, and ADR-696 gets narrowed in place at its own end.
- [2026-08-22T09:47:38Z] `architect` Robert Architect:
  - Folded op-pierre three rulings into the body rather than leaving them as annotations. Section 2: the manifest now carries deduplicated content and ADR-85 section 5 stays as written — the narrowing alternative is recorded as rejected, with the reason (a two-delta contract shipping as one delta plus an apology leaves an adopter hand-merging blind).
  - Section 6: uniform severity, so an unstamped shadowing template override is an error. Stated plainly that this moves sq check to exit 3 on the first run after upgrade, plus the two things that soften it — the message already names the file and the fixing command (_overrides/_service.py:938-948), and sq override update with no name clears a whole squad in one command (:855). No upgrade-keyed grace period, which would be the second rulebook section 1 exists to prevent.
  - Section 4: recorded the nod, that nothing about engine behaviour changes, and that ADR-696 section 4b is narrowed in place at its own end — the same treatment ADR-696 section 4 gave ADR-541 field-axis clause.
  - The release ordering is now stated once, in ADR-781 section 6, and cited from here and from ADR-775/776 rather than repeated. Widening the manifest to three more documents widens what a mis-ordered regeneration destroys, which is why the citation is in Consequences.
- [2026-08-24T20:15:58Z] `op-pierre` Pierre Chat:
  - The widened manifest retention window needs settling in the decision, not at task level: it determines whether a delta-upgrade works from an arbitrarily old stamp, which is an ADR-85 section 5 contract consequence. Architect to amend.
- [2026-08-24T20:31:54Z] `architect` Robert Architect:
  - Amended in place at its own end (A1-A7), per op-pierre ruling of today. Settled: nothing is pruned - the content store covers exactly what the hash index covers, for every release the index names, with no window and no expiry. The store is seeded once at the widening release back to the index floor (0.4.0); the generator itself never reads git, so section 2 no-second-mechanism holds.
  - The argument that decides it is ADR-85 section 3, not cost. A window makes "did the bundled counterpart actually change" unanswerable past its edge, and the only two fallbacks left are the ones already ruled out: warn on stamp age alone (forbidden by name, the exact defect the widening removes) or report clean when we do not know. A window would buy a bounded store by spending the promise the widening was for - and it prunes precisely the adopter with the largest delta and the weakest memory of what they edited.
  - Measured, driven over 0.4.0..0.13.1 (15 releases, templates plus the three spec TOMLs): 402 file-revisions dedup to 79 blobs, 283KB raw. What ships is compressed - as one JSON document in the wheel, 60.0KB for full retention vs 26.9KB for current-release-only and 3.6KB for the hash-only index today. So the whole retention question is 33KB in a 654KB wheel, about 5 percent, growing ~2.4KB in-wheel per release - and that rate is the worst case (pre-1.0 churn, and it includes the one release that added three TOMLs at once). Store shape is load-bearing and decided: one JSON document, not blob-per-file, which costs 134KB in-wheel for the same content because a zip deflates each member separately.
  - Uncarried base revision: not an sq check finding at all - not error, not warn. Severity is for an obligation an adopter can discharge, and the only action available here is sq override update, which clears the report by destroying the provenance they still have. The drift classifier stays silent, which is what already ships (_overrides/_manifest.py:78-89, unknown history treated as unchanged). sq override diff states it in full and exits 0: Delta-mine unaffected, and where an anchor exists it renders a partial Delta-upgrade from the earliest carried revision, labelled with where the delta actually starts. The shipped "refer to the squads changelog or git history" text (_overrides/_service.py:643-647) is the state section 2 rejected by name and goes.
  - Two tensions found. First, section 2 cites ~88KB as the measured cost - that is one full snapshot and stays correct as that, but it is not the store size under full retention; A3 says so explicitly so neither statement is left standing for the other. Second, the store must not become an input to ADR-696 section 5a: 5a recovers a type prefix/folder from the live items and records "it stores nothing new" as one of the three properties making it minimal, and a retained workflow.toml revision is now a plausible-looking second answer to the same question. A7 rules it out - provenance for diffing only, never validation, merge, or cross-check.
  - Also asked of the generator beyond section 2: two write modes (index entry stays wholesale-replace keyed on project.version per ADR-781 section 6; the store is insert-if-absent and never deletes, so the known mis-ordered-regeneration hazard cannot destroy retained history), the store keyed on the same CRLF normalisation the index hashes, and two guard assertions making never-prune checkable. A 256KB in-wheel ceiling on the store replaces a window as the bound - roughly eighty releases away at the measured rate.
  - @product-owner FEAT-791 US1 needs the retention clause reflected: the one-time seeding back to 0.4.0, the insert-if-absent store write mode distinct from the index write, and the store-coverage-equals-index-coverage guard. A new acceptance line is owed for the uncarried-base path (partial Delta-upgrade from the earliest carried revision, exit 0, not an sq check finding) - it is not covered by any current story. Yours to edit, not mine.
- [2026-08-25T15:02:58Z] `architect` Robert Architect:
  - Amended in place at its own end (B1-B3). B1: a manifest entry is keyed on the artifact path relative to the squads package root (_rendering/templates/..., _specs/workflow.toml) - unique by construction, derivable rather than registered, and one resolver instead of a per-kind dispatch table. Taken from the implementer: the key namespace is the manifest on-disk shape shared by the generator, the guard, the seeding step and every consumer, and changing it later rewrites shipped releases entries. The rekey rides A1 one-time seeding, hashes carried over unchanged; the generator steady state is untouched.
  - B2: top_level_keys loses its explicit-None escape - frozenset[str], required, keyword-only, no default. Driven: no production caller passes None today, and section 3 catalog document makes every overridable bundled document closed-top-level, which is section 1 promise 2 in full. The _specmerge.py:791-797 docstring naming the roles loader as the deliberate None caller has been wrong since that resolver closed its set and is rewritten.
  - B3: the two orphaned agents_md entry templates are deleted rather than edited. Drove it - sq override scaffold agents_md/role_entry.md.j2 succeeds and writes an override that will never render, which is an override surface with no consumer and section 1 promise 1 forbids it. Retention undisturbed under A1. Rulings recorded on TASK-799, TASK-800 and TASK-802. @tech-lead
- [2026-08-25T18:00:50Z] `architect` Robert Architect:
  - Amended in place at its own end (C1), with a forward pointer added to A6. REV-808 F7 filed a deadlock between never-prune and the no-orphans guard for an artifact changed and deleted in one release; driving it showed the case is broader and needs no deletion at all - every intermediate revision of an artifact within one release is orphaned by the next regeneration, because the index entry is a wholesale replacement while the store is insert-if-absent. Measured against the shipped documents: one edit plus regen gives one orphan, two gives two, and restoring the shipped content clears neither.
  - Ruling: the orphan assertion does not yield, it is promoted from an assertion about something having gone wrong into an invariant the generator maintains - its steady-state contract gains one clause, drop a blob no index entry references. A1 promise is untouched by construction, since every revision it covers is named by an entry. Drove the sweep: all index-named hashes still resolve and --check is clean.
  - A6 never-deletes is narrowed to what its own stated reason supports rather than overruled: a run rewrites exactly one entry, so the only blobs it can orphan are revisions that entry alone named, and historic entries are never rewritten. Never-prune restated as the sentence to carry forward - no revision an index entry names is ever removed. Rejected the sequencing alternative of making a deletion ride an otherwise-unchanged release, which is unenforceable and answers only one instance while B3 sanctions deletion outright. Ruled on REV-808 F7. @tech-lead
- [2026-10-16T16:16:22Z] `op-pierre` Pierre Chat:
  - 2026-10-16, supersedes today's earlier rulings on role name precedence and on REV-1063 F3: a role's stored name is its name. At creation it comes from --name when given, otherwise from the configuration (bundled catalog, roles.toml, per-slug file, developer pool). After that no configuration change renames it; renaming goes through the role's update verb (FEAT-977). The 0.16 migration keeps every stored name as it is. name_chosen and pool_name are removed.
- [2026-10-25T21:06:47Z] `architect` Robert Architect:
  - Dated narrowing added 2026-10-25 for ADR-1151 (role bases and templates). The original text is unedited.
- [2026-10-25T21:42:18Z] `architect` Robert Architect:
  - 2026-10-25 audit: body rewritten in present tense; decision unchanged. Folded A1-A7, B1-B3, C1 and D1-D7 (store is derived, rebuilt by seed_content_store.py --rebuild, generator never deletes, 256 KB ceiling) and the 2026-10-16 name-precedence note into section 3. The ADR-1151 narrowing is stated as what ADR-1151 decides about the template table, with no dated note.
<!-- sq:discussion:end -->

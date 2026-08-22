---
id: ADR-777
sequence_id: 777
type: decision
title: One override contract for every bundled spec document
status: Proposed
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
created_at: '2026-08-22T09:28:30Z'
updated_at: '2026-08-22T09:47:38Z'
---
<!-- sq:body -->
## Context

Three bundled documents ship as package data under `_specs/` — `workflow.toml` (ADR-214),
`roles.toml` (ADR-221) and `playbook.toml` (ADR-226) — each with its own loader and spec models, over
the override design ADR-85 froze and the shared merge engine ADR-696 §4 settled. The question is
whether their override treatment is actually uniform, and what uniform should mean.

**Scope.** This decision covers five axes, measured against the shipped code: whether each document
has a whole-document override surface; the merge semantics and precedence each one gets; each one's
top-level key space; the availability of the `[selected]` deselect; and each one's provenance,
staleness classification and diff.

It deliberately does **not** reopen: the merge engine's own semantics (ADR-696 §4/4a/4b — deep merge
at leaf granularity, arrays as leaves, splat-refs, `[selected]`); the lifecycle floor (§3); the
live-corpus cross-check's existing clauses (§5a); or ADR-85 §4's naming and init surface.
`.overrides/templates/` is in scope only as the reference implementation the three spec documents are
measured against — it is not itself a bundled spec.

**One axis is genuinely uniform, and it is the one with a guard.** All three loaders resolve their
override through `merge_override`, so all three get splat-refs resolved against the bundled base, a
leaf-granular deep merge, a closed-or-explicitly-open top level and a `[selected]` refused where it
has no meaning (read: `_workflow/_loader.py:152-159`, `_interactions/_loader.py:213-221`,
`_roles/_resolver.py:173-180`). A `tests/meta` scan asserts the routing structurally per loader and
names the fourth-kind drift it exists to catch (read:
`tests/meta/test_every_override_document_merges_through_the_shared_engine.py`). Every other axis is
unguarded, and every other axis diverges.

**The divergences, all read, several driven.**

- **The provenance manifest covers only the rendering templates.** Driven: the shipped
  `templates_manifest.json` records 14 releases and 26 documents, and **none** of them is a `.toml` —
  no bundled spec document has any content-hash history at all.
- **So spec-document drift is stamp-only, and warns on every release.** `_template_state` and
  `_role_state` gate the warning on `template_changed_since`, honouring ADR-85 §3's explicit rule
  that "an override whose bundled counterpart did **not** change … is silent: an old stamp alone is
  never a warning". `_workflow_state` and `_playbook_state` warn on `stamp != __version__`
  unconditionally, each with a comment saying why ("no per-release content-hash for the workflow TOML
  in the manifest") (read: `_overrides/_service.py:158-231`; `workflow_stamp_finding` at
  `_workflow/_loader.py:966-999`, `playbook_stamp_finding` at `_interactions/_loader.py:482-505`).
  Driven: an add-only `.overrides/workflow.toml` stamped one release back reports
  `warn … workflow override may be stale`, and `sq override list` classifies it `drifted`, with no
  bundled change behind either. That is the false-positive class ADR-85 forbade by name.
- **A role override's drift is measured against the wrong document.** `_role_state` and `_diff_role`
  ask `template_changed_since("agents/role.md.j2", …)` — the role *body template* — so a change to a
  bundled role's mission, or a new `RoleSpec` field, cannot drift a role override, while a
  cosmetic edit to the body template drifts every one of them (read: `_overrides/_service.py:178-193`,
  `:659-706`; driven: a role override stamped one release back warns "role body template changed").
- **A role override's Δ-mine diffs against an empty reference.** `_diff_role` renders
  `_unified_diff("", override_text, fromfile="(empty — role overrides start from scratch)", …)`
  (read: `_overrides/_service.py:668-674`). A role override merges field-wise over the bundled role,
  so it shadows; an empty baseline describes only what the team added and says nothing about a
  shadowed field. That is the same defect, with the same consequence, that was already fixed for the
  workflow document — whose own comment states the reason (read: `_overrides/_service.py:729-733`).
- **Δ-upgrade is unavailable for every kind whenever the bundled document actually changed.**
  `base_version_template_content` returns the current content when the hash matches and `None`
  otherwise, with an implementation note that content snapshots are "deliberately deferred" (read:
  `_overrides/_manifest.py:94-112`). ADR-85 §5 froze "that `diff` shows both Δ-mine and Δ-upgrade"
  into the durable contract; what ships honours it only in the case where there is no upgrade delta
  to show.
- **The roles document has no whole-document override surface.** `load_role_catalog()` takes no
  `squad_dir` and reads only package data (read: `_roles/_loader.py:21-38`), so `[bundles]` and
  `[dev]` — the bundle selection and the developer name pool, model and colour — cannot be overridden
  at all. Driven: `sq override scaffold` accepts a template name, `workflow`, `playbook`, `--role
  <slug>` and `--new <slug>`, and nothing for the catalog. ADR-696 §4c justifies the *addressing*
  asymmetry (a per-slug delta file, because the catalog is a flat registry and the filename is the
  key) and is right to; it does not sanction the missing catalog-level surface, which is a different
  thing from the per-entry one.
- **A role override's top level is closed in code and open in the decision.** ADR-696 §4b rules that
  "a role override's top level is deliberately **not** closed", on a forward-compatibility argument.
  The resolver passes a closed set derived from `RoleSpec.model_fields` (read:
  `_roles/_resolver.py:88`, passed at `:177`), and states the counter-argument in place: the old
  resolver's silent key-dropping "made every typo a no-op the adopter could not see". The engine's own
  docstring still names the roles loader as the `None` caller (read: `_specmerge.py:791-797`).
- **`[selected]` is workflow-only** (`PLAYBOOK_SELECTED_SECTIONS` is empty, a role TOML has no keyed
  sections). ADR-696 §4c settles this with reasons — the playbook's type set derives from the
  workflow spec's, and a bundled role is a menu entry nothing materialises until activation.
- **The unstamped-shadowing severity differs by kind.** Workflow and playbook: error. Templates and
  roles: warn (read: `_overrides/_service.py:938-960`, `:966-976`). ADR-696 §4's drift bullet states
  the obligation generically — a shadowing override must carry a stamp — and the two kinds that were
  already shadowing were never brought under it.
- **Two documented facts are now stale.** `OverrideEntry.kind` is documented as `"template" or
  "role"` while four values ship (read: `_overrides/_service.py:75`), and ADR-226's amendment note
  records "the playbook is not yet an override kind … named as the planned fourth" — which the
  shipped `.overrides/playbook.toml` has overtaken.

## Decision

### 1. What uniform means: the adopter's contract, not the file layout

Uniformity is owed on what an adopter is promised, never on how the document is addressed on disk.
ADR-696 §4c already licensed layout asymmetry with reasons, and those reasons hold. So the six
promises below apply identically to every overridable bundled artifact, and any per-kind difference
must be a stated consequence of the document's own structure rather than of when it was built.

1. **A whole-document surface, or a stated reason there is none.**
2. **One merge engine, with a closed top level** — one grammar, one refusal shape.
3. **One provenance carrier**, the `# squads:override-base:<version>` comment (ADR-696 §4).
4. **Drift only when the bundled counterpart actually changed** (ADR-85 §3).
5. **Both deltas, or a precise statement of why one is unavailable** (ADR-85 §5).
6. **One severity for a missing stamp on a shadowing override.**

### 2. The manifest generalises from templates to every overridable bundled artifact

This is the load-bearing change, because one gap produces four of the divergences above. The
per-release manifest stops being a template manifest and becomes a manifest of everything an adopter
may override: the 26 bundled templates plus `workflow.toml`, `roles.toml` and `playbook.toml`. The
generator script, the manifest-freshness guard (read:
`tests/meta/test_override_manifest_and_stamp_freshness.py`) and the release step that runs the
generator all widen to that set rather than gaining a second mechanism beside them.

What falls out with no per-kind logic:

- Workflow and playbook drift becomes content-gated, so `_workflow_state`/`_playbook_state`/
  `workflow_stamp_finding`/`playbook_stamp_finding` lose their "no per-release content-hash" branch
  and the false positive with it.
- A role override's drift is measured against `roles.toml`, the document it actually overrides. The
  role *body template* is a separate override with its own stamp and its own drift, and conflating
  the two was the bug.
- Δ-upgrade becomes expressible for a spec document at all.

**The manifest carries deduplicated content, not hashes alone.** Hashes cannot reconstruct a past
revision, which is why the Δ-upgrade promise is unhonourable today. A content-addressed store — hash
to bytes, deduplicated across releases, so a release costs only the documents it actually changed —
makes it honourable. The size is measurable rather than speculative: one full snapshot of everything
overridable is about 88 KB uncompressed (driven: 52 KB of templates, 36 KB across the three TOMLs)
against a hash-only manifest that is already 35 KB after 14 releases.

**ADR-85 §5 stays as written and the code moves to meet it.** The alternative — narrowing that
clause to "the upgrade delta is available when the base revision is one the manifest carries" — is
rejected, and the reason is worth recording because it is the more tempting option: it would ratify
what the code does today, leaving the durable contract promising a two-delta diff that ships as one
delta plus an apology. Telling an adopter what actually changed underneath an override they wrote is
the whole purpose of the drift cycle; a diff that can only say "something changed, read the
changelog" leaves them hand-merging blind, which is precisely the state the stamp exists to end.

### 3. The roles catalog gains a whole-document override

`.overrides/roles.toml` becomes a fourth spec override document, resolved by `load_role_catalog` on
the same shape as the other two: `squad_dir`-aware, merged through the shared engine, a closed
top-level key space of `{roles, bundles, dev}` plus `selected`, its own stamp, its own drift and its
own `sq override scaffold roles`. It covers `[bundles]` and `[dev]`, and `[[roles]]` for a project
that would rather state its catalog in one document.

The per-slug `.overrides/roles/<slug>.toml` files stay exactly as they are, for the reason ADR-696
§4c gives: the filename is the key, and per-slug files are what let a project be current on one role
and stale on another. Precedence is bundled base, then the catalog document, then the per-slug file —
most specific last, which is the same direction template resolution already runs.

`[selected]` on the catalog document deselects `roles` and `bundles` entries, which retires the
cosmetic gap ADR-696 §4c named and declined ("a project cannot hide an unwanted role from
`sq role catalog`"). The floor is unchanged and does the work: `bundles` referential integrity and
the at-most-one-default rule already run on the built catalog (read: `_roles/_loader.py:57-66`), so a
deselect that empties a bundle or removes the default fails on the resulting spec with no
deselect-specific guard, exactly as ADR-696 §4b intends.

### 4. A role override's top level stays closed, and ADR-696 §4b's clause is the one that moves

The code is right and the decision is wrong, on the decision's own terms. The forward-compatibility
argument for an open top level buys one thing — a role override written against a newer squads keeps
loading on an older one — and pays for it with silent key-dropping, which the resolver's own docstring
records as having produced four persisted defects with `sq check` clean, a truthy `can_spawn =
"false"` granting spawn authority among them (read: `_roles/_resolver.py:36-45`). ADR-696 §1's own
rule decides it: validation replaces trust. A key the model does not know is a violation naming the
key, and the forward-compatibility case is served by the refusal telling the adopter which key and
which version, not by discarding it.

Deriving the accepted set from `RoleSpec.model_fields` is the right implementation of that and stays
— it grows with the model instead of going stale beside it.

Nothing about engine behaviour changes here: this aligns the decision with what ships, so the cost is
paperwork rather than risk. **ADR-696 §4b's clause is narrowed in place at its own end**, dated and
naming this decision, so neither is left asserting the other's reverse — the same treatment ADR-696
§4 itself gave ADR-541's field-axis clause.

Two things follow that must not be missed: the engine's own docstring at `_specmerge.py:791-797`
stops naming the roles loader as the deliberate `None` caller, and `top_level_keys` loses its only
`None` caller — so whether the parameter keeps its explicit-`None` escape at all becomes a live
question rather than an assumed feature.

### 5. `[selected]` stays workflow-and-catalog only, and that is settled

The playbook derives its type set from the workflow spec's, so dropping a type drops its playbook
entry as a consequence rather than by declaration (ADR-696 §4c). A per-slug role file has no keyed
sections to shrink. Both refusals already carry a caller-supplied reason instead of an empty menu
(read: `_interactions/_loader.py:85-96`, `_roles/_resolver.py:92-96`), which is the correct shape for
an asymmetry that is intended. This axis is recorded as uniform-by-derivation, not as debt.

### 6. One severity, and one guard

A shadowing override with no stamp is an **error**-level finding for every kind; an add-only override
with no stamp reports nothing; a stamp older than the running version, with the bundled counterpart
changed, stays a **warn**. This is ADR-696 §4's rule applied to the two kinds that predate it.

A whole-file template override always shadows, so this turns today's unstamped-template *warn* into
an *error*. That is the intended direction, and the divergent severity is how template overrides came
to be overlooked in the first place: they were the one shadowing kind whose missing provenance
reported at a level a squad could carry indefinitely.

**It changes `sq check`'s exit code for an existing squad**, from clean or warn to 3, on the first run
after upgrading. That is stated plainly rather than buried, and two things soften the first encounter
without weakening the finding:

- **The message already names the file and the fix**, and must keep that shape at error level: the
  display path, then `sq override scaffold --force` to re-scaffold with a stamp or `sq override
  update` after verifying the content (read: `_overrides/_service.py:938-948`). An error that names a
  file and one command is not the failure mode this clause risks.
- **One command clears a whole squad.** `sq override update` with no name re-stamps every
  structurally-valid override at once (read: `_overrides/_service.py:855`), which ADR-85 §3 already
  contracted as the bulk acknowledge after a review pass. So the remediation for a squad meeting this
  at upgrade is bounded at one command regardless of how many overrides it carries.

What is deliberately *not* offered is a grace period keyed on the upgrade — a severity that depends
on when a squad last upgraded is a second rulebook, and §1's whole point is that there is one.

The uniformity itself gets a guard, in the shape of the routing guard that already exists: a
`tests/meta` scan asserting that every override kind in the registry has a manifest entry for its
bundled counterpart, a state classifier, a stamp-obligation finding and both diff deltas — so a fifth
kind cannot ship with three of the four wired. The routing axis is uniform today because it is the
axis with a guard; this extends the same reasoning to the axis that is not.

### 7. What a declared view inherits from this

Derived views are declared as a keyed section of the workflow document, which makes them a first
consumer of everything above rather than a special case. Three inheritances, stated so they are not
re-derived:

- **Merge and deselect.** A view set merges leaf-granularly, an adopter appends to a bundled list
  with a splat-ref rather than restating it, and `[selected]` drops a bundled view.
- **Referential validation on the merged spec.** A view naming a type, ref kind or sub-entity kind
  the merged spec does not declare fails the same pass that catches a lifecycle bound to a dropped
  status. No view-specific guard is written.
- **Provenance.** §2's manifest widening is a prerequisite for shipping an adopter-editable view set,
  not an unrelated improvement: with `workflow.toml` outside the manifest, every adopter who declares
  a view is warned that their override may be stale on every release, forever. Shipping the view
  section on the current provenance mechanism would manufacture that false positive for the exact
  population the feature is for.

A view's presentation template is an ordinary entry under `.overrides/templates/`, so it needs
nothing from this decision beyond the manifest coverage the template tree already has.


## Consequences

- **The manifest generator and the release step widen** to the three spec documents, and the manifest
  gains a content store beside its hash index. The manifest-freshness guard is what makes a forgotten
  regeneration fail loudly, and it must cover the new entries on the same day they land or the
  widening is decorative.
- **The generator's write is a wholesale replacement of one version's entry, keyed on
  `[project].version`**, so it inherits the release ordering stated once in the pointer decision's
  own sequencing section: the version bump comes before the regeneration, or the shipped release's
  recorded entry is overwritten. Widening the manifest to three more documents widens what a
  mis-ordered regeneration destroys.
- **Adopters with a workflow or playbook override stop being warned on every release.** That is the
  user-visible payoff and the reason the manifest change leads.
- **Nothing about the merge changes.** No adopter's existing override resolves differently: the
  changes are to provenance, diff, classification, one new document and one severity.
- **`sq override list` gains a fifth kind and `OverrideEntry.kind`'s docstring stops naming two.**
- **ADR-226's amendment note is overtaken** — its "the playbook is not yet an override kind, and is
  correctly still a forward dependency" reading was true when written and is not now.
- **`sq check`'s exit code changes for a squad carrying an unstamped template override** (warn to
  error), which is a deliberate tightening rather than a side effect.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T09:30:55Z] Robert Architect:
  - Scoped to five axes measured against the code: whether each document has a whole-document surface, merge semantics, top-level key space, deselect availability, and provenance/staleness/diff. Explicitly out: the merge engine semantics, the lifecycle floor, the cross-check existing clauses, and ADR-85 naming/init.
  - Only one axis is uniform — the merge routing — and it is the one with a tests/meta guard. Every other axis diverges: the manifest tracks 26 templates and zero .toml (driven), so workflow/playbook drift is stamp-only and warns on every release regardless of whether the bundled document moved, which is the false positive ADR-85 section 3 forbade by name. A role override drifts against agents/role.md.j2 rather than roles.toml, and its delta-mine still diffs against an empty reference — the defect already fixed for workflow.
  - Uniform means the adopter contract, not the file layout: ADR-696 section 4c licensed the addressing asymmetry and that holds. Load-bearing fix is generalising the manifest to every overridable artifact and carrying content rather than only hashes, which is what makes delta-upgrade honourable at all (~88KB for a full snapshot vs a 35KB hash-only manifest today). roles.toml gains a whole-document override; the per-slug files stay.
  - Two things I would rather you ruled than have me guess: whether the manifest carries content snapshots or ADR-85 delta-upgrade narrows instead, and whether an unstamped template override becomes an error (it changes sq check exit code for existing squads). Also flagging that section 4 overrides ADR-696 section 4b role-top-level clause in favour of what the code already does. @op-pierre @manager left Proposed.
- [2026-08-22T09:44:31Z] Pierre Chat:
  - Manifest: carry deduplicated content, not hashes alone, so the delta-upgrade promise in ADR-85 section 5 becomes honourable instead of narrowing the promise to match the code. The measured wheel cost, about 88KB against a 35KB hash-only manifest after fourteen releases, is acceptable for telling an adopter what actually changed under an override they wrote.
  - Stamp severity: uniform, and that means a missing stamp on a shadowing template override becomes an error like every other overridable artifact. Accepting the exit-code change for squads that already carry one - the divergent severity is how template overrides got overlooked in the first place.
  - Section 4 reversing ADR-696 section 4b is nodded: the code is the truth here, the reversal aligns the decision with shipped behaviour rather than changing behaviour, and ADR-696 gets narrowed in place at its own end.
- [2026-08-22T09:47:38Z] Robert Architect:
  - Folded op-pierre three rulings into the body rather than leaving them as annotations. Section 2: the manifest now carries deduplicated content and ADR-85 section 5 stays as written — the narrowing alternative is recorded as rejected, with the reason (a two-delta contract shipping as one delta plus an apology leaves an adopter hand-merging blind).
  - Section 6: uniform severity, so an unstamped shadowing template override is an error. Stated plainly that this moves sq check to exit 3 on the first run after upgrade, plus the two things that soften it — the message already names the file and the fixing command (_overrides/_service.py:938-948), and sq override update with no name clears a whole squad in one command (:855). No upgrade-keyed grace period, which would be the second rulebook section 1 exists to prevent.
  - Section 4: recorded the nod, that nothing about engine behaviour changes, and that ADR-696 section 4b is narrowed in place at its own end — the same treatment ADR-696 section 4 gave ADR-541 field-axis clause.
  - The release ordering is now stated once, in ADR-781 section 6, and cited from here and from ADR-775/776 rather than repeated. Widening the manifest to three more documents widens what a mis-ordered regeneration destroys, which is why the citation is in Consequences.
<!-- sq:discussion:end -->

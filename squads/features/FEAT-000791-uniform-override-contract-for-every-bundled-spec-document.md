---
id: FEAT-791
sequence_id: 791
type: feature
title: Uniform override contract for every bundled spec document
status: Done
author: product-owner
refs:
- ADR-777:implements
- MILE-836:targets
subentities:
- local_id: US1
  title: Widen the manifest to every overridable bundled artifact
  status: Done
- local_id: US2
  title: Content-gate workflow/playbook/role drift
  status: Done
- local_id: US3
  title: Whole-document override for the roles catalog
  status: Done
- local_id: US4
  title: Close the role override top-level key space (align ADR-696 §4b)
  status: Done
- local_id: US5
  title: Uniform unstamped-shadowing severity plus the uniformity guard
  status: Done
created_at: '2026-08-24T18:26:05Z'
updated_at: '2026-09-01T08:04:05Z'
---
<!-- sq:body -->
## The problem

Three bundled spec documents (`workflow.toml`, `roles.toml`, `playbook.toml`) and the bundled
templates all resolve their overrides through the same merge engine, but only the templates get
uniform treatment beyond that. The provenance manifest tracks 26 templates and zero `.toml`
documents, so workflow and playbook overrides warn "may be stale" on every release regardless of
whether the bundled document actually changed — the exact false-positive class ADR-85 forbids by
name. A role override's drift is measured against the wrong document (the body *template*, not
`roles.toml`), and its diff always compares against an empty baseline instead of the shadowed
bundled content. `roles.toml` has no whole-document override surface at all — `[bundles]` and
`[dev]` cannot be overridden. And an unstamped shadowing override is a warning for templates and
roles but an error for workflow and playbook, with no stated reason for the split.

ADR-777 rules that uniformity means the adopter's contract, not the file layout, and settles six
promises every overridable bundled artifact must meet.

## Shape

- **The provenance manifest generalises from templates-only to every overridable bundled
  artifact**: the 26 bundled templates plus `workflow.toml`, `roles.toml` and `playbook.toml`. The
  generator, the manifest-freshness guard, and the release step that runs the generator all widen
  to the same set — no second mechanism beside them.
- **The manifest carries deduplicated content, not hashes alone.** A content-addressed store
  (hash to bytes, deduplicated across releases) is what makes the Δ-upgrade half of ADR-85 §5's
  "both deltas" promise honourable for a spec document at all — a hash cannot reconstruct a past
  revision. The measured cost is small: about 88 KB for one full snapshot of everything
  overridable, against a 35 KB hash-only manifest after 14 releases.
- **Nothing in the store is pruned.** Store coverage equals index coverage for every release the
  index names, with no retention window — a squad's `sq override diff` reach is bounded only by
  which releases squads has shipped, never by how old the stamp is. The store is seeded once, at
  the release that ships this widening, back to the index's own floor (0.4.0) — a one-time data
  step against the release tags, not a generator capability, so the generator's steady-state
  contract stays "hash the current tree, insert what is absent." Its write mode is
  insert-if-absent and never-deletes, deliberately distinct from the index entry's wholesale
  replace keyed on `[project].version`: a mis-ordered regeneration can overwrite one version's
  index entry (recoverable from its tag) but must never be able to destroy retained history that
  no tag can restore.
- **`.overrides/roles.toml` becomes a fourth spec override document**: `squad_dir`-aware, merged
  through the shared engine, a closed top-level key space of `{roles, bundles, dev, selected}`,
  its own stamp, its own drift (measured against `roles.toml`, not the body template) and its own
  `sq override scaffold roles`. Precedence is bundled base, then this catalog document, then the
  existing per-slug `.overrides/roles/<slug>.toml` files, which stay exactly as they are.
  `[selected]` on the catalog document deselects `roles`/`bundles` entries.
- **A role override's top-level key space stays closed**, derived from `RoleSpec.model_fields` —
  the code is right and ADR-696 §4b's "deliberately not closed" clause is narrowed in place, dated
  and naming ADR-777, rather than left asserting the reverse of what ships. An unknown key is
  refused by name; nothing about engine behaviour changes.
- **One severity for a missing stamp on a shadowing override, for every kind.** An add-only
  override with no stamp still reports nothing; a shadowing override with no stamp is now an
  **error** for every kind, which flips today's *warn* for templates and roles. This changes
  `sq check`'s exit code (clean/warn → 3) for an existing squad carrying an unstamped template or
  role override on first run after upgrade — stated plainly rather than buried, softened by the
  existing named-file-and-fix message and by `sq override update` re-stamping a whole squad in one
  command, and deliberately without an upgrade-keyed grace period.
- **A `tests/meta` guard asserts the uniformity itself**: every override kind in the registry has a
  manifest entry for its bundled counterpart, a state classifier, a stamp-obligation finding, and
  both diff deltas — so a fifth kind cannot ship with three of the four wired.
- **`OverrideEntry.kind`'s docstring and ADR-226's stale amendment note are corrected** to name the
  fourth kind rather than continuing to describe a three-kind world.

## Acceptance

- `sq override list` reports `workflow`/`playbook`/`roles` drift only when the bundled document's
  content actually changed since the recorded stamp — an add-only override stamped several
  releases back with no bundled change reports clean, not "may be stale".
- A role override's drift is measured against `roles.toml`; a change to a bundled role's mission
  or a new `RoleSpec` field drifts a role override that shadows it, and a cosmetic edit to the
  role body template does not.
- `sq override diff --mine` on a role override shows a real Δ against the shadowed bundled
  content, not against an empty baseline; `sq override diff` (Δ-upgrade) works for `workflow.toml`,
  `playbook.toml` and `roles.toml` whenever the bundled document changed between the override's
  stamped version and the running one **and that stamped revision is carried by the content
  store**.
- When the stamped base revision is *not* carried — below the index floor, naming a version
  squads never released, or newer than the running version — `sq override diff` still exits 0:
  Δ-mine is unaffected, and where an earlier carried revision exists, Δ-upgrade renders as a
  **partial delta from that earliest carried revision**, labelled with where the delta actually
  starts and that earlier history isn't represented. This is deliberately not an `sq check`
  finding at any severity — the drift classifier stays silent (unknown history treated as
  unchanged, matching the existing rule), because the only remedial action available,
  `sq override update`, would destroy the provenance the report is about.
- `.overrides/roles.toml` resolves `[bundles]`, `[dev]` and `[[roles]]` overrides, merged before
  the per-slug files, with its own closed top level and `[selected]` deselect; `sq override
  scaffold roles` exists.
- An unstamped shadowing template or role override is an `sq check` error (exit 3), matching
  workflow and playbook; an unstamped add-only override of any kind still reports nothing.
- A role override naming a key `RoleSpec` does not declare is refused, naming the key and version.
- The `tests/meta` uniformity guard fails if a fifth override kind is registered without a
  manifest entry, a state classifier, a stamp finding, and both diff deltas.
- The manifest generator's write for a release is a wholesale replacement of that version's entry,
  keyed on `[project].version`, and runs only after the version bump — the same release ordering
  ADR-781 states once for the whole set of template/spec-touching changes this release.
- The manifest's content store is **insert-if-absent and never deletes**: every hash the index
  names resolves in the store, and every blob in the store is referenced by at least one index
  entry, for every release the index covers — asserted by a `tests/meta` guard. The store is
  seeded once, at the widening release, back to the index's floor (0.4.0) from the release tags.

## Out of scope

- Re-deciding the merge engine's own semantics (deep merge, splat-refs, `[selected]` mechanics) —
  ADR-696 settled these and they are unchanged.
- The lifecycle floor and the live-corpus cross-check's existing clauses — unchanged, out of scope
  by ADR-777's own stated scope.
- ADR-85 §4's naming and init surface for overrides — unchanged.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 791 add-story "As a <role>, I want … so that …"`; track with `sq feature 791 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Widen the manifest to every overridable bundled artifact |
| US2 | Done |  | Content-gate workflow/playbook/role drift |
| US3 | Done |  | Whole-document override for the roles catalog |
| US4 | Done |  | Close the role override top-level key space (align ADR-696 §4b) |
| US5 | Done |  | Uniform unstamped-shadowing severity plus the uniformity guard |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Widen the manifest to every overridable bundled artifact

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
The provenance manifest generalises from a template-only manifest to a manifest of every
overridable bundled artifact: the 26 bundled templates plus `workflow.toml`, `roles.toml` and
`playbook.toml`. It carries deduplicated content (hash to bytes, deduplicated across releases),
not hashes alone, so that Δ-upgrade becomes expressible for a spec document rather than staying
honourable only by accident when no upgrade delta exists to show. The generator script, the
manifest-freshness guard, and the release step that runs the generator all widen to the same set
rather than gaining a second mechanism beside them. The generator's write for a release remains a
wholesale replacement of that version's entry, keyed on `[project].version`, and runs only after
the version bump — the same release ordering ADR-781 states once for the whole set of
template/spec-touching changes landing this release.

Retention is settled, not left to the implementation: nothing in the store is pruned — its
coverage equals the hash index's coverage for every release the index names, with no window and
no expiry. The store is seeded once, at this widening release, back to the index's own floor
(0.4.0), as a one-time data step against the release tags rather than a generator capability, so
the generator's steady-state contract stays "hash the current tree, insert what is absent." Its
write mode is insert-if-absent and never-deletes, kept explicitly distinct from the index entry's
wholesale replace keyed on `[project].version`: a mis-ordered regeneration can only overwrite one
version's index entry (recoverable from its tag), never destroy retained history that no tag can
restore. Two guard assertions make the coverage promise checkable rather than assumed: every hash
named by an index entry resolves in the store, and every blob in the store is referenced by at
least one index entry.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Content-gate workflow/playbook/role drift

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
With the manifest widened, `_workflow_state`/`_playbook_state` and their stamp-finding functions
lose their "no per-release content-hash" branch: drift becomes content-gated, so an add-only
override with no bundled change behind it stops reporting "may be stale" on every release. A
role override's drift moves to being measured against `roles.toml` (the document it actually
overrides) instead of the role body template, and `sq override diff --mine` on a role override
renders a real diff against the shadowed bundled content instead of an empty baseline — the same
fix already shipped for the workflow document, applied to the kind that still had it.

Content-gating only works when the stamped base revision is one the store actually carries. When
it is not — a stamp below the index's floor, one naming a version squads never released, or one
newer than the running version — the drift classifier stays silent exactly as it already does for
an unrecorded base (unknown history treated as unchanged, never a warning), and `sq override diff`
exits 0 rather than erroring: Δ-mine renders unaffected, and Δ-upgrade renders as a partial delta
from the earliest carried revision where one exists, labelled with where it actually starts,
replacing today's generic "refer to the changelog or git history" message. This path is
deliberately outside `sq check`'s findings at every severity: the only action available to the
adopter, `sq override update`, would clear the report by destroying the provenance record it's
about.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Whole-document override for the roles catalog

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
`.overrides/roles.toml` becomes a fourth spec override document, resolved by `load_role_catalog`
on the same shape as the other two: `squad_dir`-aware, merged through the shared engine, a closed
top-level key space of `{roles, bundles, dev}` plus `selected`, its own stamp, its own drift and
its own `sq override scaffold roles`. It covers `[bundles]` and `[dev]`, and `[[roles]]` for a
project that would rather state its catalog in one document. Precedence is bundled base, then
this catalog document, then the per-slug `.overrides/roles/<slug>.toml` files, which stay exactly
as they are today. `[selected]` on the catalog document deselects `roles`/`bundles` entries; the
existing bundle-referential-integrity and at-most-one-default checks run on the built catalog with
no deselect-specific guard needed.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Close the role override top-level key space (align ADR-696 §4b)

<!-- sq:story:US4:head -->
**Status:** 🟢 Done
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
A role override's top-level key space stays closed, derived from `RoleSpec.model_fields` as it is
today; ADR-696 §4b's "deliberately not closed" clause is narrowed in place at its own end, dated
and naming ADR-777, so neither decision is left asserting the reverse of what ships. An unknown
key in a role override is refused, naming the key and the version. The engine's own docstring
stops naming the roles loader as a deliberate `None`-top-level-keys caller, and whether
`top_level_keys` keeps an explicit-`None` escape at all is settled once that caller is gone rather
than left as an unused vestige.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Uniform unstamped-shadowing severity plus the uniformity guard

<!-- sq:story:US5:head -->
**Status:** 🟢 Done
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
A shadowing override with no provenance stamp becomes an error-level `sq check` finding for every
override kind, not only workflow and playbook — templates and roles move from warn to error,
matching the severity every other shadowing kind already carries. An add-only override with no
stamp still reports nothing, unchanged. The existing message shape (naming the file and the fix —
`sq override scaffold --force` or `sq override update` after review) is kept at error level, and
no upgrade-keyed grace period is introduced. A `tests/meta` guard asserts the uniformity
structurally: every override kind registered has a manifest entry for its bundled counterpart, a
state classifier, a stamp-obligation finding, and both diff deltas wired, so a fifth kind cannot
ship with only some of the four. `OverrideEntry.kind`'s docstring and ADR-226's stale "playbook is
not yet an override kind" note are corrected to match what ships.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T13:38:47Z] Nina Product:
  - Amendment reflected: US1 now carries the retention clause (seed-once to 0.4.0 floor from release tags, store's insert-if-absent/never-deletes write mode distinct from the index's wholesale replace, and the coverage-equals-index guard).
  - Uncarried-base acceptance extended into US2, not a new story — it's a mode of the same diff/drift work US2 already owns (silent classifier, sq override diff exits 0 with a partial Δ-upgrade from the earliest carried revision, never an sq check finding); US2's existing 'Δ-upgrade works whenever changed' line is narrowed to carried revisions to match.
  - Feature-level Shape/Acceptance updated to match (new store-retention bullet, narrowed + split diff acceptance line).
- [2026-08-25T14:50:19Z] Olivia Lead:
  - Broken into three tasks. TASK-799 (US1+US2) widens the manifest to every overridable bundled artifact, adds the retained content store, and content-gates workflow/playbook/role drift including the uncarried-base path from the amendment. TASK-800 (US3+US4) gives the roles catalog a whole-document override and closes the role override key space. TASK-801 (US5) makes an unstamped shadowing override an error for every kind and adds the uniformity guard.
  - US1 and US2 are one task deliberately: same two files (_overrides/_manifest.py, _overrides/_service.py), one increment - the widening is inert without its consumers and the consumers cannot exist without it - so splitting them would only create a collision. TASK-800 is separable because it is the roles axis and touches none of the manifest surface. TASK-801 is last because its guard asserts a property of the whole registry, so it needs both the manifest entries from 799 and the catalog kind from 800.
  - TASK-799 is the FEAT-693 prerequisite named in ADR-776 section 7 and ADR-777 section 7: with workflow.toml outside the manifest, every adopter who declares a view is warned their override may be stale on every release, forever. It runs in parallel with FEAT-790 TASK-796 - disjoint files - and those two together are what FEAT-693 waits on.
  - Two operator rulings are stated in the task bodies so nobody reverses them mid-implementation: the exit-code tightening on TASK-801 (an unstamped shadowing template or role override becomes an error, exit 3, on an existing squad first run after upgrade - deliberate, not a regression), and the retention policy on TASK-799 (nothing pruned, seeded once back to the 0.4.0 floor, store write is insert-if-absent and never deletes, and the uncarried-base path is not an sq check finding at any severity).
- [2026-08-25T15:49:56Z] Olivia Lead:
  - Added TASK-805 under US2: content-gate _workflow/_loader.py workflow_stamp_finding, which TASK-799 could not reach because _workflow/ was TASK-796 territory this pass. sq check, sq override list and sq override diff are gated correctly; sq workflow lint still warns on stamp age alone, which is the exact false positive the widening exists to remove. It also collapses the duplicate gated copy TASK-799 added in _overrides/_service.py, so the obligation has one implementation again.
  - Kept under this feature rather than folded into FEAT-790 TASK-797 because it implements US2 here; TASK-797 carries only FEAT-790 stories, so a subtask there could not be mapped to US2. The _workflow/ concurrency constraint is carried as a depends-on ref instead.
- [2026-08-25T21:06:49Z] Olivia Lead:
  - Do not close this feature on the roles catalog document until TASK-814 lands. TASK-800 shipped the kind at the service layer - merge, scaffold, state classifier, both diff deltas - but the kind is not reachable from any sq override verb and the document does not apply to a role that has been activated, which is every role sq init creates. The stamp-obligation finding for it is TASK-801. US3 acceptance is met when all three are in, not when the resolver merges.
<!-- sq:discussion:end -->

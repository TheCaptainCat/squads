---
id: FEAT-693
sequence_id: 693
type: feature
title: Derived views, with milestones as the first consumer
status: Done
author: product-owner
refs:
- MILE-836:targets
- PRD-859:implements
- PRD-862:implements
description: A declared, read-only projection over an item's relationships, rendered
  as data with per-client renderers; milestones are its first consumer
subentities:
- local_id: US1
  title: View declaration and the projection data model
  status: Done
- local_id: US2
  title: The JSON contract and the presentation layer over it
  status: Done
- local_id: US3
  title: The MILE- item type, its lifecycle and target date
  status: Done
- local_id: US4
  title: Milestone roll-up as the first declared view
  status: Done
created_at: '2026-07-29T13:52:43Z'
updated_at: '2026-09-01T13:51:25Z'
---
<!-- sq:body -->
## The problem

The roadmap for a project has nowhere to live. Which work targets the next release, what is
left in it, what slipped out of it and why — none of that is expressible today. Individual items
are tracked well; the release, cycle or milestone they are grouped into does not exist as a
concept. Teams end up keeping it in prose somewhere outside the tool, where it cannot be queried
and quietly goes stale.

Separately, squads already renders derived tables by hand. The sub-entity roll-up summary and the
head badge line are both bespoke projections of data held elsewhere, wired straight into the
rendering path. A milestone roll-up would be a third of the same shape. The pattern is
established; the mechanism it should share is missing.

## Who needs this and why

Any team that ships in named increments — releases, versions, cycles — needs to group work by the
increment it targets and ask what remains. That is the single most common planning question a
tracker gets asked, and squads currently cannot answer it.

The mechanism half matters to adopters differently: a declared projection is how a team surfaces
their *own* relationships without patching rendering code. It is the reporting counterpart to
adopter-declared item types and ref kinds — a custom type with custom edges is only half useful if
nothing can roll them up.

## Shape

**A derived view** is a declared, read-only projection over relationships an item already has.
It has three parts, and no fourth:

- **source** — the relation to project: refs of a declared kind pointing at this item, a
  sub-entity collection, or a subtree. A ref-kind source names a declared entry of the workflow
  spec's ref-kind section, adopter-declared kinds included.
- **projection** — which fields to carry, how to group them, how to order them. Produces
  structured data and makes no presentation decisions.
- **presentation** — how that data renders: a Jinja2 template over the projected records. A
  table, a single badge line, a prose sentence, a bulleted list, a nested outline — all the same
  mechanism. Templating is already how this project renders everything, and the head badge line
  is already a text template over sub-entity state, so no new rendering technology is introduced.

**Every derived view is computed. There is no sink to declare and none to choose.** A view is
never materialized into a body region — it is rendered fresh whenever it is shown, from whichever
client asks (the CLI, `--json`, a future server). This applies uniformly regardless of whether the
source is this item's own frontmatter or another item's refs; there is no local/foreign
distinction to encode, because there is no materializing path for either side of it to take.
Milestone roll-up and the sub-entity roll-up are the same shape of view, differing only in source
and presentation, not in mechanism.

**Generic presentation over uniform data.** Presentation is deliberately open-ended; the data it
renders is deliberately not. Projected data is a uniform shape — records with typed fields,
optionally grouped — whatever the source and whatever the eventual rendering. That uniformity is
what makes `--json` a contract worth consuming: the VS Code extension and `sq ui` read the
projection and lay it out themselves, rather than reimplementing whatever the CLI happened to
print. If the data shape were as free as the presentation, every client would have to special-case
every view and the contract would be worthless.

So `--json` emits the projection and skips presentation entirely. The CLI's rendering is one
presentation among several, never the source of the data.

**Views are declared as a keyed section of the workflow spec document**, on the same terms as
`[statuses]`, `[collections]` and `[ref_kinds]`: they enter the closed section list, the
`[selected]` deselect, and the shared merge engine, with no special case. A view naming a type,
ref kind or sub-entity kind the merged spec does not declare fails the same referential check that
already catches a lifecycle bound to a dropped status.

A view's presentation template lives under `templates/views/<name>.md.j2`, an ordinary entry
under the existing bundled-template tree — which makes it adopter-overridable through
`.overrides/templates/` from the day it ships, with no new override surface to build. An adopter
who wants their own milestone roll-up wording writes a template at that path; the resolution,
provenance stamp and `sq override scaffold`/`diff`/`update` machinery all already cover it.

**Milestones** are the first consumer. A `MILE-` item type with a target date and its own status
vocabulary. Work joins a milestone through a forward ref carrying the already-declared `targets`
kind (bundled as navigational, no consumer, since the ref-kind vocabulary shipped): the edge
lives on the work item, so adding work to a milestone never rewrites the milestone file and
membership is recovered by inversion. The milestone's roll-up is a computed view over that
inversion, grouping members delivered and outstanding with counts — a milestone's job is telling
you what is left.

## Acceptance

- A milestone can be created, carry a target date, and move through its own status vocabulary.
- Recording membership with `ref add <MILE-n> --kind targets` writes only the work item; the
  milestone file is untouched, and membership is never persisted on the milestone.
- Showing a milestone renders its members grouped delivered and outstanding with counts, computed
  fresh on every request — no region of the milestone file ever holds this text.
- `--json` emits that same projection as structured data. The projection is defined once and every
  rendering is one presentation over it, never the source.
- Presentation covers more than tables: at least one non-tabular presentation ships and is
  exercised — a single-line text rendering is the obvious candidate, since a badge-style line is
  already a proven shape for this kind of data.
- Projected data keeps one uniform shape across every source and every presentation, so a client
  can consume an unfamiliar view without special-casing it.
- Views are declared in the workflow spec (a new keyed section, closed-list and `[selected]`
  member) and validated referentially against the merged spec, on the same terms as every other
  workflow-spec section.
- A view's presentation template is overridable through the existing `.overrides/templates/`
  mechanism with no new surface — proven by overriding the bundled milestone-roll-up template in
  a test squad and confirming the override renders.
- The declaration is expressive enough to describe the existing sub-entity summary shape as it
  stands, without bending its design to fit (this feature does not convert the summary itself —
  that is separate work).
- The new item type carries its folder, prefix map entry and regenerated backend pointer files
  (its `sq-milestone` skill). `sq check` already verifies per-entry pointer presence and currency
  for every live roster entry (shipped separately); this feature's own on-disk diff, for both
  `init` and `migrate`, confirms the milestone type's generated artifacts pass that gate from day
  one.
- A new item type and a new ref kind are both on-disk format. The milestone type's migration is
  not a bump of its own: it rides the single shared schema bump and migration runner that also
  carries the `contract` type (FEAT-321) into the same release — one bump for both new types, not
  two.

## Out of scope

- **Sprints and any time-boxed cycle.** squads has no estimation vocabulary — no points, no
  sizing — so a time box could only ever report item counts, which is a weak burndown and the
  first thing an adopting team would notice missing. Worth revisiting if estimation lands.
- **Retiring the existing sub-entity summary and head rendering (and the role Skills section)
  onto computed views.** That is its own piece of work, tracked separately (FEAT-694).

## Also in scope

**Adopter-authored presentation templates, at no extra design cost.** `.overrides/templates/`
ships, resolves per file ahead of the bundled tree, carries a provenance stamp, and is already
covered by `sq override scaffold`/`diff`/`update`/`list`. A view's presentation template is just
another bundled template at a declared path, so it is adopter-overridable the day this feature
ships — nothing about the override surface itself needs building here. What this feature owns is
putting the template at the right path and shape; the override mechanism it rides on already
exists.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 693 add-story "As a <role>, I want … so that …"`; track with `sq feature 693 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | View declaration and the projection data model |
| US2 | Done |  | The JSON contract and the presentation layer over it |
| US3 | Done |  | The MILE- item type, its lifecycle and target date |
| US4 | Done |  | Milestone roll-up as the first declared view |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — View declaration and the projection data model

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
A view declares three things: its source (refs of a declared kind pointing at this item, a
sub-entity collection, or a subtree — a ref-kind source names a declared entry of the workflow
spec's ref-kind section, adopter-declared kinds included); its projection (fields, grouping,
ordering), which produces structured data and makes no presentation decisions; and its
presentation, a Jinja2 template over those records. There is no fourth part. Every view is
computed — none is ever materialized into a body region, regardless of whether its source is this
item's own frontmatter or another item's refs. Projected data keeps one uniform shape — records
with typed fields, optionally grouped — across every source and presentation. Membership comes
from inverting stored forward refs and is never persisted on the projecting item. Views are
declared as a keyed section of the workflow spec (closed section list, `[selected]` member, shared
merge engine), and a view naming a type, ref kind or sub-entity kind the merged spec does not
declare fails the existing referential check.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — The JSON contract and the presentation layer over it

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
One projection, many presentations. `--json` emits the projected records and skips presentation
entirely, so the VS Code extension and sq ui lay the data out themselves instead of reimplementing
what the CLI prints. The Rich table is one presentation among several — tables, single-line text,
lists, nested outlines all render from the same records through a template. Grouping and field
metadata travels with the payload so an unfamiliar view can be consumed without special-casing it.
Each view's presentation template lives under `templates/views/<name>.md.j2`, an ordinary entry
under the bundled-template tree — so it is adopter-overridable through the existing
`.overrides/templates/` mechanism from day one, with no new override surface built for it.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — The MILE- item type, its lifecycle and target date

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
A milestone item type with prefix MILE-, its own folder, a target date and its own status
vocabulary. Wires the already-declared `targets` ref kind (bundled navigational, no consumer yet)
to milestone membership, so work declares which milestone it belongs to on the work item itself
via `ref add MILE-n --kind targets`. Carries the new-type obligations: prefix map entry,
regenerated backend pointer files (the `sq-milestone` skill), with the on-disk output diffed for
both init and migrate against `sq check`'s existing presence/currency gate, and the migration —
which rides the single schema bump shared with the `contract` type (FEAT-321) rather than a bump
of its own.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Milestone roll-up as the first declared view

<!-- sq:story:US4:head -->
**Status:** 🟢 Done
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
The milestone's members surfaced as a computed derived view over the inverted `targets` edges:
grouped delivered and outstanding, with counts, because what is left is the question a milestone
exists to answer. Nothing is written to the milestone file when membership changes, and no run
ever materializes the roll-up — it is rendered fresh from the current corpus on every request,
`--json` included.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T13:53:44Z] Pierre Chat:
  - Scope calls: milestones only — no sprints and no estimation for now. Membership rides a `:targets` ref. The roll-up table (plus `--json` for other clients) must not be a special case: it belongs to a general mechanism, since squads is a generic engine.
  - Both features land in 0.14; 0.13 keeps its planned scope. ADR-49's closed ref-kind vocabulary needs challenging.
- [2026-07-29T14:03:22Z] Pierre Chat:
  - The sink is not a free choice: sub-entity state lives in the parent's own frontmatter, so its summary projects the same file and may be materialized — a milestone's members live in other files, so its roll-up must stay computed.
- [2026-07-29T14:06:44Z] Pierre Chat:
  - The projection must be as generic as possible — text, tables and other shapes, not a table renderer with extras bolted on.
- [2026-07-29T14:22:16Z] Pierre Chat:
  - Parked for now. Commission the two decisions from @architect when 0.13 opens, so they are settled before the 0.14 build: the ref-kind vocabulary challenge (ADR-49's closed list versus adopter-declared types, which gates `targets`) and the derived-view mechanism itself — encoding the source-determined sink, the uniform data shape, and presentation-as-template.
- [2026-07-29T14:31:15Z] Pierre Chat:
  - The two commissioned decisions (ref-kind vocabulary, derived-view mechanism) are 0.14 work — do not commission them at 0.13-open.
- [2026-07-29T16:08:51Z] Pierre Chat:
  - Third consumer for this mechanism, and the one that tests its sink rule: a role's skills. The stored extra.skills cache is unnecessary — skills stay few (11 today against 671 items), so resolving the scopes edges on read costs nothing, while the cache costs a dedicated exemption in the frontmatter/index skew guard (PERMITTED_EXTRA_SKEW) plus a save-and-restore dance on every refresh. Drop it.
  - The role body's ## Skills section is then a view-only projection: its source is foreign (each skill's own scopes edges live in other items), so by this feature's own source-determined sink rule it must be computed, never materialized into the body. That makes it the first computed-sink consumer, where the sub-entity summary and head are both local-sink — between them they exercise both halves of the rule. The generated backend artifacts are unaffected: they are regenerable projections into another tool's config, not sq bodies.
- [2026-07-29T16:11:09Z] Pierre Chat:
  - Nothing should be reading the item markdown directly except a human resolving a merge between branches. That sharpens the sink rule rather than weakening it: a materialized derived region is precisely what fouls a merge, since two branches re-render the same projection from different underlying state and git reports a conflict in content nobody authored — resolvable only by picking a rendering instead of a fact. A computed projection cannot conflict. Self-describing raw files are not a goal worth a body sink.
- [2026-07-30T07:57:47Z] Pierre Chat:
  - Commission all three decisions in one architect pass when 0.14 opens — the ref-kind vocabulary, the derived-view mechanism, and the uniform bundled-spec override model — resolving their interactions inside a single design effort rather than across three sequenced ones.
- [2026-08-24T18:02:27Z] Pierre Chat:
  - Scoped into 0.14, and coupled to FEAT-321: the MILE and PRD types share one schema bump and one migration runner, so the two features land in the same release.
- [2026-08-24T20:15:56Z] Pierre Chat:
  - Adopter-authored presentation templates stay IN scope, as reauthored: the override surface already ships, so the marginal cost is near zero and shipping views bundled-only would shortchange adopters.
- [2026-08-26T08:22:18Z] Pierre Chat:
  - 0.14 keeps the type work: milestones, contracts and the region retirement all stay in this release rather than moving to 0.15, so the shared migration runner and the single schema bump stand as ruled.
- [2026-08-26T13:20:40Z] Nina Product:
  - Refreshed against ADR-320/775/776/777/781, all now Accepted, ahead of the breakdown.
    
    - The `targets` ref kind is already declared and shipped (FEAT-790, Done) — US3 no longer
      claims to add it, only to wire it to milestone membership. `[ref_kinds]` and the widened,
      content-carrying provenance manifest are likewise shipped (FEAT-790/791); nothing here
      still describes them as pending.
    - Corrected the pointer/`sq check` acceptance line: FEAT-792 (Done) shipped presence *and*
      currency checking for per-entry backend pointers, so `sq check` no longer "validates
      neither" — this feature's own on-disk diff for init/migrate now confirms the milestone
      type's artifacts pass an existing gate rather than filling a gap.
    - Schema bullet corrected to the single shared `0.11 → 0.14` bump with FEAT-321
      (TASK-813 already tracks the shared runner, parented here) — not a bump of its own.
    - "Out of scope" reworded from "converting" to "retiring" the sub-entity summary/head,
      matching FEAT-694's own inversion (retire the regions, don't convert them onto a sink).
    
    No reauthor needed — the mechanism design (source/projection/presentation, no sink,
    workflow-spec declaration, adopter-overridable templates, milestone as first consumer) was
    already correct and matches the accepted decisions as written.
- [2026-08-26T13:40:36Z] Olivia Lead:
  - - Broke FEAT-693 into two tasks plus a docs task. TASK-830 is the mechanism (US1/US2): `[views]` as a keyed section of the workflow document, the projection engine and its uniform record shape, presentation as a bundled overridable template, and the `--json` contract with its `sq workflow views` catalog row. TASK-831 is the first consumer (US3/US4): the `MILE` type, its lifecycle, its target date, membership by `targets` refs and the roll-up view. TASK-833 is the adopter documentation, split out because the owner role genuinely differs and its file set is `docs/` plus `CHANGELOG.md` with nothing under `src/`.
    - Two things TASK-830 must NOT do, both stated in its body because they are the easy mistakes. There is no sink field and none to derive, so the refusal FEAT-693 originally asked for has nothing to assert — no test for it. And the sub-entity summary is not converted here: US1 asks only that the declaration be expressive enough to describe the shipped shape, so `ensure_summary`, `set_head` and `_refresh_head` are untouched and FEAT-694 keeps that work.
    - The milestone roll-up's grouping resolves from declared status **roles**, not status names. A milestone can hold members of several types on several lifecycles, so a literal `"Done"` would silently mis-group a bug, a decision or an adopter's custom type. Same discipline as the ref kind: `targets` is named in the view's source declaration and never as a Python literal, which the ref-kind meta scan enforces.
    - TASK-831 depends-on TASK-830, and both depend on nothing else. The hard sequencer is `src/squads/_specs/workflow.toml`: TASK-830, TASK-831 and TASK-832 all edit it, so they cannot run concurrently — the wave grouping is in my handoff to @op-pierre.
<!-- sq:discussion:end -->

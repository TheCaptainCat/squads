---
id: TASK-833
sequence_id: 833
type: task
title: Adopter docs for views, milestones and contracts
status: Done
parent: FEAT-693
author: tech-lead
assignee: tech-writer
priority: medium
refs:
- FEAT-321
- TASK-830:depends-on
- TASK-831:depends-on
- TASK-832:depends-on
- MILE-836:targets
description: 'The 0.14 adopter documentation: the views spec section, both new item
  types, the upgrade step and the changelog'
subentities:
- local_id: ST1
  title: Document [views] as a declarable, overridable spec section
  status: Done
  story: US1
- local_id: ST2
  title: Document the milestone type and its roll-up
  status: Done
  story: US3
- local_id: ST3
  title: Document the contract type and its advisory currency check
  status: Done
- local_id: ST4
  title: The 0.14 upgrade page and the changelog section
  status: Done
created_at: '2026-08-26T13:36:03Z'
updated_at: '2026-09-01T07:43:08Z'
---
<!-- sq:body -->
## Scope

The adopter-facing documentation for everything 0.14 adds to a squad's vocabulary: derived views
as an overridable workflow-spec section, the `MILE` item type, the `PRD` item type, and the
upgrade step. Owned by the technical writer because the audience is an adopter, not this repo's
build.

It is a separate task from the three code tasks for one reason that matters operationally: it
touches **no file under `src/`**. Its file set is `docs/` plus `CHANGELOG.md`, so it can run
alongside the release's migration work without contending for a single artifact.

## What it covers

- **`docs/workflow.md`** — the lifecycle table (verified: the per-type table at the "decision
  (ADR)" row) gains the two new types with their real state machines. The `[views]` section joins
  the field reference for what an override may declare, on the same footing as lifecycles,
  statuses, item types and collections. The `sq workflow views --json` catalog gets its row in
  the catalog contract, including the "every row carries every key, `null` for absent rather than
  omitted" rule that page already states for every other catalog.
- **`docs/overrides.md`** — `[views]` as a section an override may add to, shadow field by field
  or drop through `[selected]`, and a view's presentation template as an ordinary
  `.overrides/templates/` entry.
- **`docs/migration.md`** — the 0.14 upgrade step, matching what the runner actually does and
  what its runbook entry says.
- **`docs/recipes.md`** — creating a milestone and adding work to it; creating a contract and
  linking the feature that shapes it.
- **`CHANGELOG.md`** — the `## [0.14.0]` section, which exists and is empty (verified).

## Write it for an adopter

- **No internal references.** User-facing docs describe the tool for someone adopting it: no `sq`
  item IDs, no ADR numbers, no GitHub references, and no repo/dev-process content (CI gates,
  packaging or test internals, how this release was assembled). A contributor doc is the right
  home for that; these pages are not.
- **No build-process narration.** No phase / round / wave / increment language, no "this pass",
  no "as discussed above". Delivered text describes the thing, not how it was built.
- **Describe what shipped, not what was planned.** Read the landed declarations and drive the
  commands before writing about them. Three consecutive reviews on earlier releases found
  overclaiming changelog entries spliced from handoff summaries — the source for a claim is the
  tree, not a dev's report.
- **Two concepts adopters will otherwise get wrong**, both worth stating plainly:
  - a derived view is **always computed** and is never written into an item's file, so there is
    nothing to regenerate, nothing to commit and nothing to resolve in a merge;
  - a contract is **living** — rewritten in place as the product evolves — where a feature is
    **historic**, a point-in-time record later work supersedes.
- Keep the currency check's advisory nature explicit: it warns, it never blocks, and the reason
  it never blocks is that a gate on a purely technical feature manufactures a false positive that
  teams clear with a fake ref.

## Traps

- **The docs are not the place to relitigate a decision.** If the landed behaviour and a decision
  disagree, raise it on the task rather than documenting whichever one you prefer.
- **`docs/stability.md` describes the 1.0 contract** and is downstream of the decision set. A new
  spec section and two new bundled types may touch what it promises — read it and either update
  it or state on the task why it is unaffected.
- **Verify every command you print.** `tests/meta/test_documented_commands_resolve_against_cli.py`
  resolves documented commands against the live CLI; a recipe naming a flag that does not exist
  fails the suite.

## Acceptance

- Both new types appear in `docs/workflow.md`'s type/lifecycle table with their real state
  machines, and the `[views]` section has a complete field reference beside the other declarable
  sections.
- `docs/overrides.md` covers declaring, shadowing and dropping a view, and overriding a view's
  presentation template.
- `docs/migration.md` describes the 0.14 upgrade in terms that match the runner and its runbook
  entry.
- `docs/recipes.md` carries a working milestone recipe and a working contract recipe; every
  command in them resolves against the live CLI.
- `CHANGELOG.md`'s `## [0.14.0]` section describes what actually shipped, in the house style of
  the sections above it, with no claim that is not true of the tree.
- No sq item ID, ADR reference, GitHub reference or repo/dev-process content appears in any
  adopter-facing page touched here.
- `docs/stability.md` is either updated or explicitly cleared as unaffected, with the reason
  recorded on this task.
- The documented-commands meta test passes; `uv run --all-extras pytest` is clean; `sq check` is
  clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 833 add-subtask "<title>"`; track with `sq task 833 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Document [views] as a declarable, overridable spec section | US1 |
| ST2 | Done |  | Document the milestone type and its roll-up | US3 |
| ST3 | Done |  | Document the contract type and its advisory currency check |  |
| ST4 | Done |  | The 0.14 upgrade page and the changelog section |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Document [views] as a declarable, overridable spec section

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — View declaration and the projection data model
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Document `[views]` in `docs/workflow.md` and `docs/overrides.md` as one more section of the
workflow document an adopter may declare, shadow field by field, or drop.

`docs/workflow.md` already carries a field reference for lifecycles, statuses, status roles, item
types and collections (verified). Views join it on the same footing, covering the three parts a
view declares and nothing more: **source** (refs of a declared kind pointing at this item, a
sub-entity collection, or a subtree), **projection** (fields, grouping, ordering) and
**presentation** (a template over the resulting records).

The two things an adopter will otherwise get wrong, both worth stating plainly:

- **A view is always computed.** It is never written into an item's file. There is nothing to
  regenerate, nothing to commit, and nothing to resolve when two branches touch the same item —
  a materialised projection is exactly what makes a merge unresolvable, because both sides render
  the same table from different underlying state and the reader has to pick a rendering instead
  of a fact.
- **`--json` gives the data, not the display.** It emits the projected records and their field
  and grouping metadata, so a client lays them out itself rather than reparsing what the CLI
  printed. Say that this is the supported way to build on a view.

`docs/overrides.md` gets: declaring a view, shadowing a bundled one field by field, dropping one
through `[selected]`, and overriding a view's presentation with a
`.overrides/templates/views/<name>.md.j2` — an ordinary template override, resolved per file
ahead of the bundled tree, with the provenance stamp and `sq override scaffold`/`diff`/`update`
already covering it.

Add the `sq workflow views --json` row to the catalog contract in `docs/workflow.md`, including
the rule that page already states for every catalog: every row carries every key, `null` for
absent rather than omitted.

Done when an adopter can declare, shadow, drop and re-template a view from these two pages alone,
every command printed resolves against the live CLI, and no internal reference appears.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Document the milestone type and its roll-up

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — The MILE- item type, its lifecycle and target date
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Document the milestone type: what it is for, how work joins one, and what its roll-up answers.

`docs/workflow.md`'s per-type table (verified: the table carrying the "decision (ADR)" row) gains
a milestone row with its real state machine, read from the landed declaration rather than from a
plan.

`docs/recipes.md` gains a milestone recipe covering the whole loop: create one with a target
date, add work to it, read what is left. The one behaviour worth calling out explicitly, because
it is the reason the design works the way it does: **work joins a milestone by a ref on the work
item**, so adding an item to a milestone never rewrites the milestone, and the membership list is
recovered by inverting those edges rather than stored anywhere.

Describe the roll-up as what it answers — members grouped delivered and outstanding, with counts,
because what is left is the question a milestone exists to answer — and note that it is computed
fresh on every request, `--json` included.

Do **not** document estimation, burndown, sprints or any time-boxed cycle. None of it exists:
there is no estimation vocabulary in the tool, so a time box could only report item counts, and
saying otherwise would promise something the tool does not do.

Verify every command by running it. `tests/meta/test_documented_commands_resolve_against_cli.py`
resolves documented commands against the live CLI, so a recipe naming a flag that does not exist
fails the suite.

Done when the type's row matches the landed lifecycle, the recipe runs end to end as written,
membership-by-ref is stated plainly, and nothing about estimation or sprints appears.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Document the contract type and its advisory currency check

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Document the contract type: what it is, how it differs from everything else in the tool, and what
the currency check does.

The framing that makes it land in one line, and which the docs should carry rather than bury:
**a decision record is the technical contract; a contract is the functional contract with the
user.** They are twins.

The distinction an adopter must get right:

- **A contract is living.** It is the accumulated current functional state, rewritten in place as
  the product evolves, written from the user's point of view — what the product does for a user,
  right now.
- **Features and epics are historic.** They are point-in-time records that later work supersedes:
  a feature is the diff plus its rationale, the audit trail. A contract is the winner.
- **It is a collection, not a monolith** — one contract per capability or user-facing area, so a
  feature updates one slice and ownership and merge granularity stay sane. Say plainly that
  partitioning is the team's editorial judgement and that **nothing enforces it**: too coarse and
  contracts drift back toward monoliths, too fine and one feature fans its links across many tiny
  items, and neither failure is expressible as a rule that would not also refuse legitimate
  shapes.

Cover the type's row in `docs/workflow.md`'s type table with its real state machine, and a
`docs/recipes.md` recipe: create a contract, link the feature that shapes it, see which features
shaped a contract.

**The currency check, stated honestly.** A feature that settles without linking a contract
produces a **warning**. It never blocks. Give the reason, because it is what stops a reader
treating the warning as a bug: a hard gate would fire on purely technical features that touch no
user-facing behaviour, and the way a team clears a false positive is by adding a link that is not
true — which corrupts the very edge the design reads. The warning surfaces the debt and leaves
the judgement with the person deciding whether this feature legitimately touches no contract.

Done when the living-versus-historic distinction is unmistakable, the type's row matches the
landed lifecycle, the recipe runs as written, the check is described as advisory with its reason,
and no internal reference appears.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — The 0.14 upgrade page and the changelog section

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Write the upgrade page and the release's changelog section.

**`docs/migration.md`** gains the 0.14 step. Describe what the upgrade does for the adopting
squad in the terms the runner actually implements — read the runner and its runbook entry, not a
plan for them. Keep it short: an upgrade page that lists optional steps at length reads as
required work.

**`CHANGELOG.md`'s `## [0.14.0]` section**, which exists and is empty (verified). Match the house
style of the sections above it: an `### Added` / `### Fixed` split, each entry a bold one-line
lede followed by prose that says what changed for a user of the tool and what it replaces.

Three rules for this section specifically:

- **Describe what shipped, not what was planned.** Read the landed declarations and drive the
  commands before writing about them. Three consecutive reviews on earlier releases found
  overclaiming entries spliced from handoff summaries; the source for a claim is the tree, not a
  dev's report. Where a claim cannot be verified by running something, do not make it.
- **No internal references and no build-process narration.** No item IDs, no decision numbers, no
  GitHub references, no CI/packaging/test-internals content, and no phase / round / wave / "this
  pass" language. The reader is adopting the tool, not reviewing its construction.
- **Do not describe the upgrade as risky or as data-rewriting if it is not.** State what it
  creates and what it regenerates, and say plainly that existing items are untouched if that is
  what the runner does.

Finally, read `docs/stability.md`. It is a downstream summary of the 1.0 contract, and a new
declarable spec section plus two new bundled types may change what it promises. Either update it
or record on this task why it is unaffected — do not leave that question unanswered.

Done when the upgrade page matches the runner's actual behaviour, the `0.14.0` changelog section
is complete and every claim in it is verifiable against the tree, `docs/stability.md` is updated
or explicitly cleared, and no internal reference appears in either.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T16:27:05Z] Theo Writer:
  - Adopter docs for the release's three additions are written. Files touched: `docs/workflow.md`, `docs/overrides.md`, `docs/recipes.md`, `docs/migration.md`, `docs/stability.md`, `docs/roles.md`, `docs/README.md`, `docs/internals.md`, `CHANGELOG.md`. No file under `src/` or `tests/`.
    
    `docs/workflow.md` gains three concept sections (derived views, milestones, contracts, the last with a "The currency check" subsection) plus a `#### Derived views: declared projections` field reference beside the other declarable sections; the lifecycle diagram, the per-type lifecycle table, the type-alias table, the catalog command list, the catalog join table and the closed-section count all take the two new types and `[views]`. `docs/overrides.md` covers declaring, shadowing, dropping and re-templating a view. `docs/recipes.md` gains a contract recipe and a milestone recipe. `docs/migration.md` gains a "When a release adds an item type" section describing what the runner does for an existing squad. `docs/stability.md` takes the `sq workflow views --json` catalog row, the resolved-projection shape, the two aliases and the override-surface list.
    
    Membership is worded as living on the work item, with the two consequences spelled out: a milestone is cheap to change because re-aiming work never rewrites it, and the member list is recovered by inverting those edges rather than stored anywhere it could disagree with them. It says plainly that no verb adds work from the milestone's side, because that is the command an adopter will go looking for.
    
    The currency check is worded as advisory with its reason (a hard gate fires on purely technical features, and the only way a team clears one is by adding a link that isn't true, which corrupts the edge the check reads), and its inertness as a design position: while no contract exists it evaluates nothing because the remedy it would name does not exist, and authoring the first contract activates it across the whole corpus at once — so a batch of warnings on day one is expected, not a defect.
    
    Every claim was driven, not taken from a handoff. Scratch squads outside the repo were used for: the three source kinds (`ref`/`subentity`/`subtree`); shadowing a bundled view field by field; a splat-ref on a view's `fields`; the four referential refusals (undeclared source name, bad `group_by`, bad `order_by`, a base attribute the source kind disallows); the milestone create/target-date/join/roll-up loop; the contract create/link/backref loop; the currency check going from inert to active when the first contract is authored, and staying silent on Cancelled and InReview; `sq migrate up` on a synthetic pre-release squad.
    
    Two behaviours found while driving that the docs were written around rather than against.
    
    First, a `ref` source can project base attributes only — a badge field there is refused at load, because the source's records can be any type. The docs say so and the base-attribute table marks it. Second, `selected.views = []` while the owning type still names the view in its own `views` list leaves a dangling attachment: `sq workflow lint` reports OK, and `sq <type> <n> show` then exits 1 with "no declared view". Dropping the type prunes the view automatically; dropping the view alone does not detach it. The docs therefore show both keys together and present the type drop as the one-key path — a follow-up filing is warranted if this should refuse at lint instead.
    
    The 0.14 migration runner was not in the tree when this was written, and is now landing alongside. `docs/migration.md` was written to the runner's charter rather than to a per-release stanza: what it creates (the two folders, the managed skills and pointers, the compiled managed regions), that no existing item is rewritten, that a type an override dropped is skipped, and that `sq sync` afterwards is for squads with customised role/skill scoping. Per-release detail stays where the page already routes it, `sq migrate help` and `sq migrate chlog`.
    
    `docs/stability.md` was read and is updated rather than cleared: the new declarable spec section joins the Tier 1 override-surface list, and the view catalog plus the resolved-projection shape join the Tier 3 frozen `--json` surfaces. Nothing it already promised changed.
    
    The `CHANGELOG.md` `[0.14.0]` section carries five Added entries: derived views, the milestone type, the contract type with its check, ref kinds as declared vocabulary, and `--file` on comment. The last two were driven the same way as the first three. The section is deliberately not exhaustive for the release — entries for the other landed work are still owed by whoever verified it, and were left out rather than spliced from handoffs.
    
    Verification: `tests/meta` 259 passed; the targeted view/milestone/contract/docs modules 281 passed together with meta, 0 FAILED; `ruff check` clean. `sq check` clean. The four `tests/cli/test_docs_cli.py` failures seen mid-run are the in-flight schema bump in this tree, not these edits — they reproduce with the docs reverted.
    
    Three staleness fixes outside the new material, all caused by this release: the roster skill table in `docs/roles.md` (architect, tech lead and product owner each gained skills), the quoted unknown-top-level-key refusal in `docs/overrides.md` (it omitted `views`), and two type-count enumerations that had gone wrong ("seven work-item types", "the seven work types") — replaced with non-enumerative wording so they cannot rot again.
    
    One pre-existing error left alone as out of scope: `docs/recipes.md`'s "Fix a bug" recipe ends `sq bug 10 status Done`, and `Done` is not in the bug lifecycle (`Open → InProgress → Fixed → Verified`). Worth a small fix by whoever picks it up.
    
    @tech-lead ready for review.
- [2026-08-26T16:27:47Z] Theo Writer:
  - Follow-up on the four docs-CLI failures noted above: now that the schema stamps agree they pass unchanged, so the cause was the mid-run bump and not these edits. Full re-run after the squad migrated: 285 passed, 0 FAILED, ruff check and format clean, sq check clean.
- [2026-09-01T07:43:08Z] Theo Writer:
  - Completed the `## [0.14.0]` CHANGELOG section — the release notes were honest but only covered what an earlier pass had personally verified. Every claim below was driven against the shipped code in a scratch squad, not lifted from a handoff.
    
    Added: one entry for the override contract across all five override kinds (`.overrides/roles.toml` as the whole-document kind, uniform error severity for an unstamped shadowing override, drift measured against the document actually overridden and content-gated rather than stamp-age, and a real reconstructed Δ-upgrade with a named coverage floor); one for pointers naming commands instead of an `@`-path, with `sq check`'s currency comparison and the capability-restriction escalation; one for `sq graph --json`'s `edge_semantic` and the kind-blind traversal; one for the read-side rule and the init-time interview section. Plus a `### Fixed` section (dropping a bundled type through `[selected].items`; a stale index encoding no longer reported as a divergence, and `sq repair` canonicalising the file) and a `### Migration` section for the 0.11 → 0.14 schema step and the `sq sync` that has to follow it.
    
    Two corrections to the section as it stood. The milestone roll-up entry claimed a two-way delivered/outstanding split; what ships is three-way — delivered, outstanding, and settled-without-delivering — and the third bucket is the whole point, since a two-way split never reports zero outstanding once anything is cancelled. Rewritten. And the ref-kinds entry the brief listed as missing was already present and is accurate as written; I drove a renamed dependency kind through `sq blocked` and a `[selected]`-dropped bundled kind through the refusal text to confirm it.
    
    Left out for lack of a claim I could stand behind: the content-store and manifest generator rework (repo tooling, not adopter surface), the hygiene-scan work, and the VS Code client's diagram edge labels (no adopter-facing changelog covers that package).
    
    @tech-lead for the record — no action needed unless the omissions above should be covered somewhere else.
<!-- sq:discussion:end -->

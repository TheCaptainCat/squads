---
id: TASK-832
sequence_id: 832
type: task
title: The contract (PRD) item type and its currency check
status: Done
parent: FEAT-321
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-320:implements
- ADR-775
- ADR-781
- ADR-777
- MILE-836:targets
description: The contract type declaration, lifecycle, template and generated surface,
  the implements/supersedes edges, and the advisory currency validator
subentities:
- local_id: ST1
  title: Declare [items.contract] and its Draft-Active-Superseded lifecycle
  status: Todo
  story: US1
- local_id: ST2
  title: The contract item template steering functional prose
  status: Todo
  story: US2
- local_id: ST3
  title: The implements edge from a feature and the supersedes rule
  status: Todo
  story: US3
- local_id: ST4
  title: The advisory ref_rule_target_present validator
  status: Todo
  story: US3
- local_id: ST5
  title: Playbook entries and the generated sq-contract surface
  status: Todo
  story: US4
created_at: '2026-08-26T13:33:55Z'
updated_at: '2026-08-26T16:00:17Z'
---
<!-- sq:body -->
## Scope

ADR-320, delivering FEAT-321 US1–US4. The `contract` item type (prefix `PRD`) — the living
functional counterpart to the ADR set — as one declaration on the existing config-driven type
engine, plus the historic→living ref edge and the advisory currency check that keeps it honest.

US5 (the folder creation and schema bump on an existing squad) belongs to the release's single
shared migration runner and is not authored here.

## The type

One `[items.contract]` block plus one `[lifecycles.contract]` block in
`src/squads/_specs/workflow.toml`, and nothing else. ADR-320 §A settles every value:

- prefix `PRD`, folder `contracts`, `category = "records"`, `lifecycle = "contract"`,
  `aliases = ["prd", "c"]` — both free today, confirm before landing;
- `fields` carries **priority only**, as `decision` and `guide` do. There is no severity field:
  ADR-323 replaced the old per-type severity flag with the generic `fields` binding.
- **No `subentity_kind`.** Structurally a contract is a `guide`, not a `feature`: one item per
  capability area with ordinary markdown headings inside. Sections-as-sub-entities was
  considered and rejected — sub-entity prose lives in the parent's body, so every section would
  share one file and reintroduce exactly the monolith and merge contention the collection model
  exists to avoid.
- `order` is a spaced float; pick one that places a contract sensibly among the records types.

The CLI group `sq contract` and the folder follow from the declaration. No per-type CLI module is
written: ADR-263 registers a spec-declared type's group ahead of Click's parse-time resolution,
and `create()` falls back to `items/_default.md.j2` for a type with no dedicated template.

`contract` is a **bundled** type, not one of the three reserved names — it ships in the bundled
spec like any other declared type and is not role/skill/operator-class reserved.

## Lifecycle

`Draft → Active → Superseded (+ Deprecated)`. All four statuses already exist in the shared
status set (verified in `src/squads/_specs/workflow.toml`), so no new status names are
introduced.

`Active` is the steady state — the live functional truth for that capability. `Superseded` is
terminal and already carries `role = "superseded"`, which the shipped supersede check keys on.
`Deprecated` is terminal for a capability sunset with no direct replacement, with a revive edge
back to `Active`. Both terminals are reachable, so the lifecycle floor holds.

The work lifecycle is wrong for this type and the `guide` lifecycle was weighed and not taken:
"Published" frames the artifact as a document release and carries no supersede semantics, which
is exactly what the living-versus-historic model needs.

## The item template

A dedicated `_rendering/templates/items/contract.md.j2` steering the author toward
**functional, user-facing behaviour prose** — what the product does for a user, right now, from
the user's point of view. Not architecture; that is the ADR set. Not workflow state: the
frontmatter `status:` field is the single source of truth, and a body that declares its own
position goes stale the moment the real status changes.

`_default.md.j2` would serve. A dedicated template is taken because it sets the right shape.

## The edges

**A feature links the contract it shapes with a forward `implements` ref**, reusing the kind and
disambiguating it by the target being a `contract`. The kind is reused on legibility and on
keeping the bundled set small — **not** on any vocabulary-growth cost, which ADR-775 removed when
ref kinds became declared spec vocabulary. `implements` declares no semantic role, so it stays
navigational; its only consumer is the check below, which resolves the edge by the target's type.

A contract's incoming edges are computed by inversion — `sq contract <n> refs --in` lists every
feature that shaped it, with nothing stored on the contract. Note that backrefs print under
`refs --in`/`--all`, never under `show`.

**`contract` declares a `supersedes` ref rule**, as `decision` does, so a replacement contract
links the one it supersedes. That declaration is the whole wiring: the `records` category bundle
already selects `supersedes_incoming` (verified in `CATEGORY_BUNDLES`, `_workflow/_models.py`),
so a `Superseded` contract with no incoming supersedes edge is reported with **no new code**.

## The advisory currency check

A **warn**-level `sq check` finding when a feature settles with no `implements` edge to a
`contract`. Never a hard gate — the gate is refused because purely technical and internal
features have no user-facing contract change, so a gate manufactures false positives, and the way
a team clears a false positive is a fake ref, which corrupts the very edge the design reads.

Two properties come free from landing it in the shipped validator framework: the create/update
gate aborts only on error-level issues, so a warn-level validator is report-only by construction
— advisory is a *severity* here, not a second code path — and that severity is the only lever if
the guarantee ever needs strengthening.

The validator's name, its resolution rule and one genuinely open question are set out in ST4.

## Release mechanics

Editing `workflow.toml` and `playbook.toml` and adding an item template forces a **manifest
regeneration** (`python scripts/gen_template_manifest.py`). Only the `0.14.0` entry may move;
**do not run `scripts/bump_version.py`** — `pyproject.toml` already reads `0.14.0`, which is not
a shipped release, so ADR-781 §6's bump-before-regeneration ordering is already satisfied. The
generator no longer sweeps the content store (ADR-777 D3): an unreferenced blob is expected
residue between releases, cleared at the cut by `python scripts/seed_content_store.py --rebuild`,
which `gen_template_manifest.py --release-gate` requires. Do not add a deletion to clear one.

A squad carrying a `.overrides/workflow.toml` sees a genuine, content-gated drift warning when
this lands. That is the correct signal.

## Traps

- **The migration is not authored here.** Creating the `contracts/` folder on an existing squad,
  the schema bump and the surface regeneration all belong to the release's one shared runner.
  A second runner is a second bump, which is what was ruled against.
- **Partitioning carries no structural guard.** "One contract per capability area" is the product
  owner's editorial judgement. Do not add a rule enforcing it in either direction — neither
  failure mode is expressible as a spec rule that would not also refuse legitimate shapes.
- **Nothing in this type's surface materialises a derived projection.** A contract's body is
  authored prose, and because the type declares no `subentity_kind` it carries no roll-up summary
  and no badge head region — so there is no materialised region here for a later change to
  retire.
- **`workflow.toml` is the release's most contended file** — the view mechanism and the milestone
  type both edit it. Do not run concurrently with either.

## Acceptance

- `sq create contract` (with its declared aliases) creates a `PRD`-prefixed item under
  `contracts/`, and the auto-generated `sq contract` CLI group exists with no per-type module.
- The lifecycle is `Draft → Active → Superseded (+ Deprecated)` with both terminals reachable and
  no new status names introduced; no parent is required.
- The type declares no `subentity_kind`, and `sq check` is clean on a squad holding a contract
  with ordinary markdown headings and no sub-entities.
- A feature carries a forward `implements` ref to a contract; the contract's `refs --in` lists
  every feature that shaped it, with nothing stored on the contract itself.
- A `Superseded` contract with no incoming supersedes edge is reported by the existing
  `supersedes_incoming` validator, with no new code written for it.
- The advisory currency validator ships as ST4 specifies: warn-level, never a hard gate,
  resolving its kind and target type from the merged spec with no vocabulary literal in
  `_services/`.
- A managed `sq-contract` skill is generated and stamped as `sq sync`-regenerated, its `.claude`
  pointer names `sq skill sq-contract show` and carries no local file path, and the on-disk
  surface is identical between a fresh `sq init` and a squad reached through the release's
  migration — asserted by comparison with the roster held constant.
- The item template carries no status or lifecycle prose, and `no_status_banner` is clean on an
  item created from it.
- The template manifest matches the tree, its freshness check passes, only the `0.14.0` entry
  moved, and `scripts/bump_version.py` was not run.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 832 add-subtask "<title>"`; track with `sq task 832 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Declare [items.contract] and its Draft-Active-Superseded lifecycle | US1 |
| ST2 | Todo |  | The contract item template steering functional prose | US2 |
| ST3 | Todo |  | The implements edge from a feature and the supersedes rule | US3 |
| ST4 | Todo |  | The advisory ref_rule_target_present validator | US3 |
| ST5 | Todo |  | Playbook entries and the generated sq-contract surface | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare [items.contract] and its Draft-Active-Superseded lifecycle

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a team, I can create and manage contract items (PRD prefix) like any other item type
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add one `[items.contract]` block and one `[lifecycles.contract]` block to
`src/squads/_specs/workflow.toml`. That is the whole mechanism — the `sq contract` CLI group, the
ID prefix and the folder all follow from the declaration, and no per-type CLI module is written
(ADR-263 registers a spec-declared type's group ahead of Click's parse-time resolution).

The declaration, settled by ADR-320 §A:

- `prefix = "PRD"`, `folder = "contracts"`, `category = "records"`, `lifecycle = "contract"`,
  `aliases = ["prd", "c"]` — confirm both aliases are still free before landing; the loader
  reports a duplicate alias, prefix or folder by name.
- `fields` carries **priority only**, as `decision` and `guide` do. No severity field — ADR-323
  replaced the old per-type severity flag with this generic binding.
- **No `subentity_kind`.** One item per capability area with ordinary markdown headings inside;
  structurally this is `guide`, not `feature`. Sub-entity prose lives in the parent's body, so
  sections-as-sub-entities would put every section in one file and reintroduce the monolith the
  collection model exists to avoid.
- `order`: an explicit float, spaced by 10 (the file's own comment, verified), placing a contract
  sensibly among the records types.
- No required parent. A record relates to work through refs, never through hierarchy — the
  `records` bundle already carries `no_parent` (verified in `CATEGORY_BUNDLES`,
  `_workflow/_models.py`).

The lifecycle is `Draft → Active → Superseded (+ Deprecated)`. All four statuses already exist in
the shared status set (verified), so no new status names are introduced. `Active` is the steady
state; `Superseded` already carries `role = "superseded"`, which the shipped supersede check keys
on; `Deprecated` is terminal for a sunset with no replacement, with a revive edge back to
`Active`. Both terminals must be reachable.

Done when `sq create contract` and its aliases produce a `PRD`-prefixed item under `contracts/`,
the CLI group exists with no per-type module, both terminals are reachable, `sq workflow types
--json` and `sq workflow lifecycles --json` carry complete rows, and `sq check` is clean on a
squad holding one.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — The contract item template steering functional prose

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a reader, a contract describes what the product does for a user right now, from the user's POV
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add `_rendering/templates/items/contract.md.j2`, steering the author toward **functional,
user-facing behaviour prose**.

What a contract body is: what the product does for a user, right now, from the user's point of
view — the accumulated current functional state, rewritten in place as the product evolves. It is
the *winner*, where a feature is the diff plus its rationale.

What it is not:

- **not architecture.** That is the ADR set. The two are twins, not overlaps: `decision` is the
  technical contract, `contract` is the functional contract with the user.
- **not workflow state.** No `STATUS:` banner, no hand-written `## Status` heading, no "this is a
  draft" or "blocked until…" self-declaration. The frontmatter `status:` field is the single
  source of truth, and body copy declaring the item's own position goes stale the moment the real
  status changes. `_no_status_banner` (`_services/_validators.py`, verified) reports a body or
  description that opens with one — the template must not seed the thing the check flags.
- **not a history log.** Dated discussion comments are the home for notes about a point in time.

`_default.md.j2` would serve; a dedicated template is taken because it sets the right shape.
Templates are package data, so the wheel picks it up automatically — confirm that in the build.

Adding a template forces a manifest regeneration: run
`python scripts/gen_template_manifest.py`, confirm only the `0.14.0` entry moved, and do not run
`scripts/bump_version.py`.

Done when `sq create contract` renders from the dedicated template, an item created from it is
clean under `no_status_banner`, the template carries no lifecycle prose of its own, and the
manifest is fresh with only the `0.14.0` entry changed.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — The implements edge from a feature and the supersedes rule

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US3 — As a team, a feature links the contract it shapes, and stale contracts are surfaced when features land
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Declare the two edges the living↔historic model rests on.

**The feature → contract edge is a forward `implements` ref**, disambiguated by the target being
a `contract`. A feature *implements* the slice of the functional contract it delivers, which
reads correctly at the call site and in a raw edge.

Reuse is chosen on legibility and on keeping the bundled kind set small — **not** on any
vocabulary-growth cost. ADR-775 made ref kinds a declared `[ref_kinds]` section of the workflow
spec rather than a closed frozenset in code, so a new kind no longer costs a vocabulary
expansion; the old "expands a deliberately-closed vocabulary" argument is gone and must not be
restated. The accepted cost, stated rather than hidden: one word now names two relationships
(task→feature and feature→contract), and disambiguation rests on the target's type, which every
consumer already has.

`implements` declares no semantic role, so it stays navigational. Its only consumer is the
currency check in ST4, which resolves the edge by the target's type.

A contract's incoming edges are computed by inversion — nothing is stored on the contract.
`sq contract <n> refs --in` lists every feature that shaped it. Note for anyone writing the test:
backrefs print under `refs --in`/`--all`, **never** under `show`.

**`contract` declares a `supersedes` ref rule**, as `decision` does, so a replacement contract
links the one it supersedes. That declaration is the whole wiring — the `records` category bundle
already selects `supersedes_incoming` (verified in `CATEGORY_BUNDLES`), and the validator
resolves its kinds through `ctx.spec.supersession_ref_kinds()` rather than the literal spelling
(verified in `_services/_validators.py`), so a `Superseded` contract with no incoming supersedes
edge is reported with **no new code**.

Done when a feature can carry an `implements` ref to a contract and the contract recovers it by
inversion with nothing stored on its own file, a `Superseded` contract with no incoming
supersedes edge is reported by the existing validator, and no new code was written for the
supersede rule.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — The advisory ref_rule_target_present validator

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
**Implements:** US3 — As a team, a feature links the contract it shapes, and stale contracts are surfaced when features land
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Add the advisory currency check as one more entry in the shipped validator framework — not a
bespoke check.

## The name

**`ref_rule_target_present`.**

Chosen against the catalog's own convention rather than invented. The fourteen existing entries
in `_services/_validators.py::CATALOG` (verified) name the **subject and the condition that must
hold** — `parent_present`, `agent_registered`, `subentity_body_written`, `dangling_ref`,
`ref_kind_valid` — and where the subject is spec-resolved they name it **generically**:
`subentity_title_max` says `subentity`, not `story` or `subtask`, because the kind comes from the
type's own declaration. This validator's target type is likewise a parameter, so naming it
`contract_*` would bake a bundled type name into the closed catalog of a project whose whole
direction is that only role/skill/operator are reserved — a squad that drops the `contract` type
would still carry a validator named after it. `ref_rule_target_present` sits beside
`parent_present` and reads as what it asserts: *a ref matching one of this type's declared ref
rules, pointing at an item of the parameterised type, is present.*

`supersedes_incoming` is the one catalog name that spells a bundled kind. Do not copy it — its
own docstring is at pains to record that it resolves through `supersession_ref_kinds()` and never
that spelling.

## How it resolves, with no vocabulary literal

Registration: add the name to `VALIDATOR_NAMES` **and** to `PARAMETERIZED_VALIDATOR_NAMES` in
`_workflow/_models.py` (verified — both are the vocabulary half, kept out of `_services` so
`WorkflowSpec._validate` can read them without `_workflow` importing upward), and the function to
`CATALOG` in `_services/_validators.py`. The module-level `assert set(CATALOG) ==
VALIDATOR_NAMES` keeps the two from drifting.

Selection: `[items.feature]` gains `validators = ["ref_rule_target_present:contract"]`. **The
param names the target item type**, read from the merged spec. `_check_validators_assignment`
(`_workflow/_models.py`, verified) already splits on `:`, requires the bare name to be a catalog
member, and refuses a `:param` on a name outside `PARAMETERIZED_VALIDATOR_NAMES`; extend the
referential pass so a param naming a type the merged spec does not declare is refused there too.

The kind comes from the **declaring type's own `ref_rules`**: `[items.feature]` gains
`ref_rules = [{ kind = "implements", hint = "…" }]`, and the validator accepts an outgoing ref
whose kind is any kind the declaring type declares a rule for **and** whose target item's type
equals the param. Two rules simply widen the accepted set — there is no ambiguity to resolve.

This is the constraint ADR-320 §C states explicitly, and it is easy to get wrong: **the validator
may not find its edge by comparing against the literal `"implements"`.**
`tests/meta/test_no_bundled_ref_kind_literal_outside_the_spec_layer.py` (verified) matches a bare
`ast.Constant` equal to any of the ten bundled kind names under `src/squads/` outside `_specs/`
and `_migrations/`. Spelling the kind in `workflow.toml` is legitimate; spelling it in
`_services/` is a test failure.

## Severity

**Warn, always.** Never a hard gate. The gate is refused for a stated reason rather than a
dislike of friction: purely technical and internal features have no user-facing contract change,
so a gate manufactures false positives, and the way a team clears a false positive is a fake ref
— which corrupts the very edge the design reads.

Two properties come free: the create/update gate aborts only on error-level issues, so a
warn-level validator is report-only by construction, and that severity is the only lever if the
guarantee ever needs strengthening. The structure does not change with it.

## The trigger — one thing the decision leaves open, and how to build it meanwhile

ADR-320 §C says the finding fires when a feature reaches **`InReview` or `Done`**. Those two
statuses cannot be separated from `InProgress` through declared vocabulary: in
`src/squads/_specs/workflow.toml` (verified) `InReview` declares `role = "active"` — the same
role as `InProgress`, `ChangesRequested` and `Active` — while `Done` declares `role = "done"`.

Build it against the **`done` role**: fire only for an item whose `ctx.spec.status_role(...)`
resolves to `done`, mirroring `_supersedes_incoming`, which compares
`ctx.spec.status_role(item.status)` against a role rather than a status spelling (verified). That
is narrower than the decision's literal wording and is a deliberate, recorded choice, not an
oversight — binding to `active` instead would warn on every feature merely in progress, which is
noise a warn-level finding cannot carry in a repo where `sq check` must stay clean.

Raised on this task's discussion for `@architect`: either §C narrows to the settled/`done` role,
or a status role distinguishing "under review" from "in progress" is introduced. Do not invent
either answer, and do not compare against a status name to get the wider trigger.

## One consequence to measure before this is called done

This repo dogfoods squads and holds dozens of `Done` features, none of which carries an
`implements` edge to a contract, because the type does not exist yet. The moment this validator
ships, every one of them produces a warn finding.

Run `sq check` on this repo's own corpus with the validator active, report the finding count in
the handoff comment, and `@op-pierre` with it. Do not add a suppression, a grandfather date or a
"only items created after…" clause to make the number smaller — the honest options are seeding
this repo's own contracts (product-owner work, outside this task) or accepting the count, and
that is the operator's call to make with a real number in hand.

## Done when

- `ref_rule_target_present` is in `VALIDATOR_NAMES`, `PARAMETERIZED_VALIDATOR_NAMES` and
  `CATALOG`, and the `set(CATALOG) == VALIDATOR_NAMES` assert holds.
- `[items.feature]` selects it with a param naming the target type, and declares the ref rule the
  kind is read from.
- A settled feature with no qualifying edge produces exactly one **warn** finding; one with the
  edge produces none; the create/update gate never aborts on it.
- A squad that renames the target type, or the ref kind, in `.overrides/workflow.toml` keeps the
  check; a param naming an undeclared type is refused by the referential pass.
- No bundled ref-kind or status-name literal appears in the validator, and the ref-kind meta scan
  passes.
- The finding count on this repo's own corpus is measured and reported, with `@op-pierre` and
  `@architect` on the open trigger question.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Playbook entries and the generated sq-contract surface

<!-- sq:subtask:ST5:head -->
**Status:** ⚪ Todo
**Implements:** US4 — As an agent, the sq-contract skill and .claude/AGENTS.md surface teach and expose the new type
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
Grow the managed agent-facing surface for the new type, and verify it on the migrate path as well
as on init.

- New `[types.contract]` entries in `src/squads/_specs/playbook.toml`, following the shape every
  existing `[types.<name>]` block uses. Per ADR-320 §E the per-role guidance is: the **product
  owner** authors contracts and keeps them current; the **tech lead** and each `<tech>-dev`
  update the touched slice as features land; the **architect** watches cross-contract
  consistency. These entries drive the managed `sq-contract` skill — real body under
  `squads/agents/skills/`, thin pointer in `.claude/`.
- **The pointer names a command, never a path.** Under ADR-781 it carries only what the host must
  read before anything can run — its `name`, its `description`, and `sq skill sq-contract show`.
  No `@` reference into the squad directory and no copy of the skill body: a local path resolves
  to nothing when the CLI is a client to a server.
- The `CLAUDE.md` and `AGENTS.md` managed regions pick the type up through the shared
  `_managed_region.py` wrapper, which already stamps the "regenerated by `sq sync`" warning, so
  the new surface inherits that stamp for free (invariant 7).
- Generated agent text renders from the **active** spec, the active playbook and the live roster
  rather than from bundled literals, so a squad that renames or drops the type gets text matching
  its own vocabulary. `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py`
  guards this.

**Verify on both paths, by comparison.** ADR-320 §E states the rule and names why: a type
addition that wired only the `init` path and left `migrate` unregenerated has bitten this project
before. A squad reached through the release's migration and a squad created fresh with `sq init`
must end with the **same** on-disk generated surface for the contract type — skill body files,
pointer filenames, pointer targets, pointer descriptions, and the managed regions. Assert the
comparison in the suite so the two paths cannot drift later.

**Hold the roster constant across the two squads.** Generated per-type skill text is
roster-dependent, so a dev-less fresh squad diffed against a dev-bearing one reports differences
that are not regressions.

Editing `playbook.toml` forces a manifest regeneration: run
`python scripts/gen_template_manifest.py`, confirm only the `0.14.0` entry moved, and do not run
`scripts/bump_version.py`.

Done when the playbook entries drive a generated `sq-contract` skill and pointer, the pointer
names the command and carries no local path, both paths produce the same surface under an
asserted comparison, `sq sync` is a no-op on a freshly migrated squad, and `sq check`'s per-entry
pointer presence and currency gate passes.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T13:51:39Z] Robert Architect:
  - - Trigger: ADR-320 §C narrows to the settled `done` status role — build it exactly as ST4 already specifies (`status_role`, never a spelling). Checked, not taken on trust: `InReview` names `active` alongside `InProgress`, `ChangesRequested`, `Fixed` and `Active`. No new status role is introduced: one separating review from in-progress would declare `settled = false` / `live = true` / `hidden = false`, identical to `active` under every derived predicate with only the colour intent free to differ, and re-pointing `InReview` re-points a bundled catalog every squad merges (ADR-604/ADR-474), the client colour joins and the roster `live` projection (ADR-697). Not `settled` either — that would warn on a Cancelled feature, the false positive §C exists to avoid. Amended as ADR-320 §B1.
    - Target type: `RefRule` gains an optional `target` naming a declared item type. `[items.feature]` declares `{ kind = "implements", target = "contract" }` and **no hint** — `parent_hint` appends every non-empty hint to the invalid-*parent* message, where contract guidance would be noise. The validator keeps its name, its param and its selection line; the param **selects** the obligation, the rule **types** the edge.
    - The one clause that changes in ST4's resolution rule: read the accepted kinds from the rules whose `target` equals the param, **not** from the union of every rule the type declares. The union makes any later hint-only rule on `feature` silently widen what satisfies the check, and it lets a type select `ref_rule_target_present:contract` while declaring no rule at all — an accepted set empty by construction, so every settled feature warns and no edge can clear it.
    - Two load-time checks come with the field, both in the Plane-1 referential pass, not in `_parse_ref_rules` (item types are known only after every `[items.*]` block has parsed, while the rule parser sees the declared kinds alone): `target` must name a declared item type, and a type selecting `ref_rule_target_present:<T>` with no rule targeting `<T>` is refused at load. Publish nothing — ADR-738 §7 keeps `ref_rules` out of the `sq workflow` payloads and growing them is its own decision. Amended as ADR-320 §B2.
    - Day-one flood: the prohibition stands — no suppression, no grandfather clause, no date, nothing per-item. Added in its place: **the check is inert while the corpus holds no item of its parameterised target type.** That is a precondition on the finding's premise (before any contract exists the remedy does not exist), the shape `supersedes_incoming` already has one step earlier, and it excuses nothing permanently — the day the first contract is authored, every settled feature is evaluated, the pre-existing ones included. Compute the "corpus holds a T" aggregate once per run alongside the incoming-supersedes aggregate, never per item; on the single-item create/update gate path there is no index handle, so it yields nothing — failing open is right for a warn. Amended as ADR-320 §B3.
    - Numbers measured here so you do not re-derive them: 105 features, 90 `Done`; 13 carry an `implements` edge and every one points at a decision, none at a contract; `sq check` reports zero issues today. Report your own count in the handoff with @op-pierre as ST4 requires.
    - Net effect on this task's shape: ST3 gains the `RefRule.target` field plus its loader/referential work; ST4 gains the corpus precondition and the one-clause change above. ST1, ST2, ST5 and every acceptance line stand as written. @python-dev @tech-lead
- [2026-08-26T15:14:51Z] Elias Python:
  - Declared `[items.contract]` (prefix PRD, folder contracts, category records, lifecycle Draft→Active→Superseded(+Deprecated), order 55, aliases prd/c) + `[lifecycles.contract]` in workflow.toml; dedicated `items/contract.md.j2` template; playbook [types.contract] entries (product-owner authors, tech-lead + *dev update, architect watches consistency) driving the generated sq-contract skill/pointer.
  - RefRule gains optional target (typed, not an allowlist); [items.feature] declares { kind = "implements", target = "contract" } with no hint, and validators = ["ref_rule_target_present:contract"]. Two Plane-1 referential checks added (_check_ref_rule_targets, _workflow/_models.py): every declared target must name a declared item type, and a type selecting ref_rule_target_present:<T> must itself carry a ref_rules entry targeting <T> — both refused at load, falsification-tested (undeclared target, mismatched target).
  - ref_rule_target_present resolves the accepted (kind,target) pairs from the declaring type's own ref_rules and validators entries — no literal kind/type spelling in _services/. Triggers only on the done status role (never InReview/active, never the broader settled). Inert whenever the corpus holds no item of the selected target type: a types_present(index) aggregate is computed once per sq check run (never per item) and left empty on the gate path, so create/update never pays the scan and the check never gates a mutation.
  - sq check on this repo: 0 issues (ran sq sync after the playbook.toml edit to clear 5 expected managed-pointer-drift warnings; the contract currency check itself stayed silent throughout — this corpus holds no contract yet, so it's inert by design, not suppressed).
  - Template manifest: only the 0.14.0 entry moved (verified both directions against HEAD); bump_version.py not run. Two orphaned content-store blobs are expected dev-time residue from iterating on workflow.toml — left for the pre-release rebuild, no deletion added.
  - tests/meta: 254 passed, 5 failed (all five are test_override_manifest_and_stamp_freshness.py cases tripping on those same 2 orphan blobs — confirmed by isolating the rebuild in a throwaway copy, which dropped exactly 2). Targeted suite (validator, contract CLI/service, workflow/playbook spec artifacts, skills-for-role, create-lane, dropped/renamed-type and [selected]-override fixtures across cli/unit/service/integration): 417 passed, 0 failed. pyright/ruff check/ruff format --check all clean.
  - Left undone: US5 (folder creation + schema bump) is TASK-813's, not touched. ST5's init-vs-migrate comparison assertion can't be authored yet since the migration runner doesn't exist — deferred to TASK-813. Discovered while building: several pre-existing test fixtures hardcoded a [selected].items/statuses allowlist that predates contract's existence (or retired Active/Archived assuming only the roster lifecycle used them) — updated ~15 files to include contract/keep Active declared; flagging in case any other in-flight override fixture elsewhere hits the same shape.
  - @op-pierre @architect InReview.
<!-- sq:discussion:end -->

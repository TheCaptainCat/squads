---
id: REV-956
sequence_id: 956
type: review
title: 'Structural review of the engine: layering and cohesion'
status: Approved
author: architect
assignee: reviewer
refs:
- MILE-934:targets
description: Module boundaries, layering and cohesion across the sq engine, including
  whether DI answers the construction tensions.
subentities:
- local_id: F1
  title: Two disagreeing answers to whether a role is a developer
  status: Fixed
  severity: high
- local_id: F2
  title: RoleView lives in _backends and forces protocol stand-ins
  status: Fixed
  severity: medium
- local_id: F3
  title: Roster projection is 400 lines of ServiceCore, used by six mixins
  status: WontFix
  severity: medium
- local_id: F4
  title: 'The mixin composition is a type-checked star: leave it'
  status: WontFix
  severity: info
- local_id: F5
  title: _interactions/__init__.py is an undeclared 1k-line policy hub
  status: WontFix
  severity: medium
- local_id: F6
  title: 48 parameters silently default a missing spec to the bundled one
  status: WontFix
  severity: medium
- local_id: F7
  title: Bundled sub-entity vocabulary survives as test-only API and tags
  status: WontFix
  severity: low
- local_id: F8
  title: Three spec loaders hand-write one load shape
  status: WontFix
  severity: medium
- local_id: F9
  title: WorkflowSpec methods are fine; its file holds three other things
  status: WontFix
  severity: low
- local_id: F10
  title: '_maintenance.py is two modules: the rebuild corridor and check'
  status: WontFix
  severity: medium
- local_id: F11
  title: sq check has eight finding sources and names none of them
  status: WontFix
  severity: medium
- local_id: F12
  title: View layout is right; _views.py itself holds five jobs
  status: WontFix
  severity: low
- local_id: F13
  title: '_cli/_common.py: nothing breaks today, leave it whole'
  status: WontFix
  severity: info
- local_id: F14
  title: 'DI container: no at today''s graph size, with measurements'
  status: WontFix
  severity: medium
- local_id: F15
  title: Service is built at eight sites; three omit the playbook
  status: WontFix
  severity: medium
- local_id: F16
  title: Layering is stated in three places and guarded by no test
  status: Fixed
  severity: medium
- local_id: F17
  title: retype and import write one file several times per transaction
  status: Fixed
  severity: medium
- local_id: F18
  title: 'Comment rule: 95 of 127 source files fail a mechanical check'
  status: WontFix
  severity: medium
- local_id: F19
  title: 'Comment rule: 414 of 566 test files fail a mechanical check'
  status: WontFix
  severity: low
created_at: '2026-09-15T09:01:18Z'
updated_at: '2026-10-17T03:51:04Z'
---
<!-- sq:body -->
## Scope

A structural read of the `squads` engine — module boundaries, layering, and cohesion — asking
one question of each area: **does the shape still earn what it costs to read and extend?** The
engine is ~43k lines across ~20 subpackages, and several of its boundaries were drawn when the
thing on the other side was much smaller. This looks for the places where that is now visible.

The areas below are where I judge the structure has actually accumulated. Each names the real
tension, not a checklist item; a reviewer is free to conclude the shape is fine and say so —
"this is load-bearing, leave it" is a finding worth the same as a defect. One area is not a
tension but a **candidate answer** put forward for judgement — a DI container — and it is in
scope to be tested against the tensions, including to be turned down.

## Areas

### 1. The `_services/` composition — twelve mixins over one shared base

`Service` is a bare class body composing twelve mixins in MRO order, each of which inherits
`ServiceCore`. That is ~13k lines behind one flat façade, with `ServiceCore` itself at ~1.6k.

The tension: the mixins are a **file-placement** device, not a boundary. Every mixin reaches
every other mixin's methods and all of `ServiceCore`'s protected surface through `self`, so the
MRO records which file a method lives in and nothing about what depends on what. That makes
`ServiceCore` a growth attractor — parent/author/assignee checks, badge parsing, role views,
roster construction, template resolution, `reject_markers`/`reject_body_overwrite` all landed
there because two mixins needed them, not because they belong together.

Worth judging: what the composition buys over explicit collaborators held as fields; whether
`ServiceCore`'s size is the cost of the pattern rather than an accident; and whether
`_services/` is a layer or a bag, given that `_validators.py`, `_retirement.py`,
`_config_integrity.py` and `_import_model.py` live there without being mixins at all, while
`_discussion.py` and `_views.py` — mechanism with no service dependency — sit at top level.
That last split is the project's own stated precedent and the review should check it is applied
consistently, not just declared.

### 2. `_maintenance.py` — 3.3k lines and at least four distinct jobs

The largest module in the codebase, with ~890 lines of module-level helpers before the class
body starts. It owns: the tier-1 file scan behind `sq check`; the whole-corpus rebuild behind
`sq repair` (carry-forward of unreadable files, timestamp carry-forward, body-tag repair,
retired-region stripping, stale ref-encoding normalisation, vocabulary validity gating);
driving `sq migrate up` and reporting its outcome; renumber/offset planning; bundled-skill
seeding and orphaned-skill detection; roster and backend-entry drift scanning with a
confirmation step.

The one thing they share is a walk over the corpus. That is why they co-located, and it may
still be the right reason — but the review should decide whether the walk is a genuine seam
(one corpus-iteration primitive, several independent consumers built on it) or whether this is
simply where whole-corpus work accretes because a whole-corpus function already exists here.
`_iter_item_files` and `_carry_forward_unreadable` are where that question is concretely
answerable.

### 3. The validator surface's two tiers, about to take a third finding

There are two finding-producing tiers and they are not siblings:

- **Tier 1** — `MaintenanceMixin._scan_for_check`: raw-text, per-**file**, before frontmatter
  parses, keyed on type folder and filename. Unconditional across every type, not selectable,
  not addressable by an adopter, and living in `_maintenance.py`. Today: `_marker_issues` and
  `_view_target_issues`.
- **Tier 2** — `_validators.py`'s `CATALOG`: per-**item**, taking a resolved `Item` from a
  context object, selectable per type off the spec (common core + category bundle + the type's
  own list), and doubling as the create/update fail-closed gate.

FEAT-948 adds a third tier-1 member. Both modules already argue the split is principled, and
the argument is decent — a file too broken to parse still gets its findings, and a binding
document invariant should not be deselectable. The review's job is to test whether
"unconditional, per-file, pre-parse" is a **stable rule** that a fourth and fifth finding will
also satisfy, or a description of the two that happen to exist. Two concrete probes: whether a
consumer closing over the finding surface (the `--json` shapes, the VS Code client, the docs)
can discover both tiers without reading two module docstrings; and whether tier 1's
non-overridability is a contract we are willing to state, given the spec-driven direction that
only role, skill and operator are reserved.

### 4. The spec / override / merge layering

Three spec families — `workflow.toml`, `roles.toml`, `playbook.toml` — each with its own
loader, its own pydantic models, and its own `.overrides/` counterpart, all merging through the
single `_specmerge.py` (~1k lines), with `_overrides/` (a ~1.5k-line service plus the
manifest/stamp surface) as the scaffold/diff layer and a per-release content-hash index and
content store over every overridable artifact.

The shared merge engine is the good half: it is genuinely loader-agnostic and says so. The
tension is one level up. Each loader re-derives the same shape by hand — bundled fast path
versus merged path, override-file presence, error wrapping, revalidation when an upstream spec
changed — and `resolve_playbook` in `_services/_service.py` is that logic written a *third*
time, in the service layer rather than in a loader, for reasons its docstring has to explain at
length. Three conforming implementations of a documented shape is the point at which to ask
whether the shape should be code.

The other half is `WorkflowSpec`: ~3k lines, 16 models, and ~46 methods on the spec object
itself. It is simultaneously a value object, the workflow's entire behaviour surface, the home
of the validator **name** registries, and the host of the load-time spec-validity checks that
read them. Worth judging whether capability should move to resolvers that take a spec, leaving
the models as data — and, separately, whether `_workflow/__init__.py`'s ~250 lines of
module-level shims over the **bundled** spec still earn their place, given they answer the same
questions as the threaded active spec and are silently wrong under an override. Prune or fence;
two ways to ask one question, one of them wrong, is a footgun regardless of how the boundary
is drawn.

### 5. The view mechanism, spread across six places

One feature currently lives in: `_views.py` (source resolution, projection, presentation for
six source kinds in two families); `_services/_views.py` (the index-loading seam and the
placement verb); `_sections.py` and `_models/_markers.py` (the tag grammar and, with the
in-flight work, unpaired-marker insertion); `_rendering/templates/views/` (presentation);
`_maintenance.py`'s tier-1 scan (on-disk validity); and `_cli/_workflow_cmd.py` (a per-source-
kind `--json` dispatch).

That may be the right decomposition — mechanism, seam, grammar, presentation, integrity,
serialization are real distinctions. But the serialization edge is where it visibly strains:
`--json` dispatches per source kind in the CLI because the three non-relation kinds have no
shared envelope, and `projection_json` survives as "one remaining caller's contract". The
asymmetry is documented as deliberate; the review should decide whether it is a boundary or a
gap, because required views will push more weight onto this path.

### 6. `_cli/_common.py` — 1.9k lines, ~64 top-level names, four unrelated jobs

Presentation (`print_block`, `print_comments`, `print_subentity`, body/badge rendering); the
`--json` row and record builders; wiring (`get_service` and its index-cross-check-bypassing
twin, `handle_errors`, `command`, the schema gate, the version notice); and vocabulary parsing
and dispatch (`parse_type`/`parse_status`/`parse_category`/`parse_badge_code`,
`AddressDispatchGroup`, `spec_aware_command_cls`).

The JSON builders deserve the closest look: they are the shape the VS Code client binds to,
which makes them a consumer contract living in a module named "common" next to console
printers. Cohesion here is a smaller prize than in the areas above — flag it as a split only if
the reviewer can name what breaks today, not on size alone.

### 7. Does dependency injection answer any of this?

`soupape` (`bolinette/soupape`, MIT, pure Python, pyright-strict, 3.13+) is a DI/IoC container
with singleton/scoped/transient lifetimes, nested scoped injectors, sync and async injectors on
one API, context-manager and `@post_init` initialisation with reverse-order teardown, resolver
functions, and pre-instantiation detection of unknown, captive and circular dependencies. The
review must reach a verdict on it, and **"no" is a permitted verdict** — so is "yes for the
wiring, no for the rest".

**Where it plausibly bites, stated as evidence rather than enthusiasm.** This codebase's
construction complexity is real and concentrated:

- `ServiceCore.__init__` takes three parameters, two of which are `None`-defaulted with a
  bundled fallback resolved *inside the constructor*; it hard-constructs its own `IndexStore`;
  and it mutates process-wide render state (`set_active_squad_dir`) as a construction side
  effect. Ambient defaults and a self-constructed collaborator are the textbook shape.
- The backend `_registry` is a service locator: a module-global dict, a `global _loaded` flag,
  import-for-side-effect registration, and lookup by name string returning a fresh instance.
- The CLI edge has grown a **hand-rolled scoped-lifetime mechanism**: `get_service` memoizes a
  `Service` on Click's root context meta, gated on the read scope's own key, and re-asserts a
  ContextVar on every memo hit because one user-facing invocation crosses the sync/async bridge
  twice under separate `anyio.run` contexts. Alongside it sit `_build_plain_service`,
  `get_service_bypassing_index_cross_check` and `_build_bypass_fallback_service`. That is a
  scoped injector session, written by hand, with the disposal and propagation edge cases
  discovered one at a time — which is exactly the problem a scoped container exists to own.
- The lifetime taxonomy is **already written down**: `_context.py`'s DATA-versus-CODE triage
  rule (per-request values versus immutable load-once definitions) maps almost one-to-one onto
  scoped versus singleton. That correspondence is the single strongest signal, because it means
  the container would be encoding a distinction this project derived independently.

**Where it does not bite, and this is the part to be clear-eyed about.** The twelve-mixin
`Service` is the tension the review opens with, and **DI does not dissolve it**. The mixins are
a method-placement device over one object; turning them into injected collaborators requires
first deciding where the real seams are and what each side needs. Once that decomposition
decision is made, plain constructor parameters wired at one composition root may do the whole
job. DI makes wiring cheap; it does not tell you where to cut, and `ServiceCore`'s growth is
shared-base attraction, which only goes away if the decomposition removes the shared base. So
the honest framing is **enabler, not answer** — and a review that adopts a container while
leaving the mixins intact will have bought nothing for the tension it started from.

**What decides it.** Four questions, in descending order of how much they should weigh:

1. **The acyclic-import rule under runtime hint resolution.** Constructor-hint DI must resolve
   annotations at runtime. This project's sanctioned cycle break is a `TYPE_CHECKING` import
   plus a string annotation, and under PEP 649 that hint is unresolvable when the container
   asks for it. Any type used as a constructor parameter therefore loses that escape hatch.
   Check this against the real graph — DI may well *reduce* edges by inverting dependencies,
   but the answer must be measured, not assumed.
2. **Whether the wiring duplication is large enough to earn a runtime dependency.** `sq` ships
   seven runtime dependencies today, all widely-used infrastructure. A DI container would be
   the first single-maintainer dependency in the set. That question is owed the same answer it
   would get from any other author, and the fact that the author is on this team changes the
   responsiveness of a bug report, not the bus factor. The counter-question is equally fair:
   the four construction paths and the hand-rolled scope cache above are *also* a maintenance
   cost, currently paid in this repo's own code.
3. **Startup cost and failure locality.** Every `sq` invocation pays construction, and today a
   construction failure raises a located `SquadsError`. Soupape's pre-instantiation validation
   addresses the locality half directly; both halves want measuring on a real invocation rather
   than reasoning.
4. **Whether the usual DI payoff is already banked.** The classic win is swapping collaborators
   in tests. This suite deliberately does not mock — it drives real squads in `tmp_path` with a
   frozen clock and actor overrides — so that payoff is largely already held by another
   mechanism, and the case has to rest on construction, not testability.

**How this relates to the threaded-context preference — adjacent, not the same.** The standing
preference is against module-level mutable global state, answered by `RequestContext` over a
`ContextVar`. That mechanism is deliberately *implicit*: ambient values read deep in the stack
that nobody wants threaded through ten signatures. DI is the opposite posture — an object
declares what it needs and is handed it, explicitly. They are complementary rather than
competing, and a scoped injector session is a natural home for exactly the per-request set
`RequestContext` holds today. Two consequences the review should hold to: the two changes are
**separable** — the composition root can be taken without converting a single ambient read —
and a container satisfies the preference only if it is created and scoped at the CLI edge
rather than parked in a module global, which is the shape soupape's injector already has.

**If the verdict is no**, the review owes the alternative, not just the refusal: one explicit
composition root that collapses the four CLI construction paths, constructor parameters with
no in-constructor fallbacks, the backend registry replaced by passing a backend in, and the
render-state side effect moved out of `ServiceCore.__init__`. Most of the concrete benefit
above is reachable that way without a dependency — which is precisely why the comparison is
worth making properly rather than settling on either side by default.

### 8. Smaller, but cheap to settle

- `_interactions/__init__.py` carries ~1k lines of implementation. The project's stated
  module-privacy convention is that package inits do not hold content, with three named
  exceptions; this is an undeclared fourth. Either declare it or move it — an unciteable
  convention stops being one.
- `_models/_markers.py` still hardcodes bundled sub-entity vocabulary
  (`STORIES`/`SUBTASKS`/`FINDINGS`, `story_tag`/`subtask_tag`/`finding_tag`), with live callers
  in a migration and in `_collab.py`'s tag dispatch. Small, but it is a bundled literal sitting
  below the spec layer, which is the exact class of thing the ref-kinds work outlawed elsewhere.

## Not for

- **Not a rewrite proposal.** The output is findings — module, tension, judged cost of leaving
  it as is — not a target architecture. A finding that cannot name what it costs today is not a
  finding.
- **Not a defect hunt.** Correctness belongs to the per-change reviews; this looks at shape.
- **Not licence to refactor.** Per team convention a finding becomes a fix-task only when we
  decide to act on it, and a structural finding that would move a frozen or adopter-visible
  surface is an ADR question, not this review's to settle.
- **Not the test suite's structure**, which has its own settled deferral — except where the
  right home for a structural rule is a `tests/meta` guard.
- **Not performance, not the VS Code or browser clients, not the docs.**

## Start from these, do not rediscover them

- **The module docstrings are the position under review.** `_validators.py`, `_specmerge.py`,
  `_views.py`, `_context.py` and `_index/_store.py` each already argue their own boundary at
  length. Read them as the claim to be tested, not as documentation to verify.
- **CLAUDE.md's invariants and the ~45 `tests/meta` guards are this architecture already made
  executable.** A finding that contradicts one of them is an ADR question; a finding worth
  keeping usually wants to become a new guard.
- **Ambient state is settled.** `_context.py`'s `RequestContext` over a `ContextVar`, with its
  DATA-versus-CODE triage rule, replaced the module-global spec deliberately. Do not reopen it.
- **The import graph is acyclic and guarded**, and `TYPE_CHECKING` plus a string annotation is
  the sanctioned cycle break — a proposal that would introduce an edge must say which.
- **Top-level mechanism modules are an existing pattern, not a novelty** — `_discussion.py` and
  `_views.py` are mechanism with no service dependency and were placed there on purpose.
- **The DI candidate is `bolinette/soupape`** (`https://github.com/bolinette/soupape`, on PyPI
  as `soupape`). Read its README and its lifetime/scoping semantics before forming a view; do
  not evaluate a package that merely shares the name. Its author maintains this project too,
  which makes it a serious candidate **and** makes deference the failure mode: judge it on fit
  with this codebase, and neither soften a no nor manufacture objections to look independent.
- **Read the areas under active change at whatever has landed**: the section primitives, the
  corpus migration path and the required-views work all move code named above.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 956 add-finding "…" --severity medium`; track with `sq review 956 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Two disagreeing answers to whether a role is a developer

<!-- sq:finding:F1:body -->
**Shape.** The engine answers "is this role a developer?" two ways, and no layer owns the question.

- **Stored marker** `extra.is_dev` (`X.IS_DEV`), written only by `add_dev` (`_services/_roster.py:87`). Read by `_roles/_resolver.py:458` (merge base), `_itemfile.py:133` (skew exemption), `_services/_maintenance.py:355` and `:1602` (catalog refresh), `_services/_roster.py:72` (pool sequence), `_cli/_dev.py:34` (`sq dev list`).
- **Slug spelling** `is_dev_slug` = `slug.endswith("-dev")` (`_interactions/__init__.py:223`). Read by the create lane (`:314`), the per-type skill's developers section (`:502`), the preload-skill list (`:571`), the example assignee (`:972`), override validation and shadow baselines (`_overrides/_service.py:914`, `:1490`), the role card preview (`_cli/_common.py:1125`). The same test is re-spelled without the helper in `_roles/_resolver.py:547` and `_cli/_role.py:399` (`removesuffix("-dev")`), `_roles/_catalog.py:332` and `_services/_roster.py:77` (slug construction), and `templates/claude/claude_section.md.j2:81` (`_slug.endswith("-dev")` in Jinja).
- The `*dev` sentinel is a third spelling: declared twice as `DEV` (`_interactions/__init__.py:46`, `_interactions/_loader.py:71`) and four times in `_specs/playbook.toml`.

That is 6 marker reads and 12 spelling sites across 10 modules and one template (read; grep validated against the known `is_dev_slug` definition).

**Cost.** The two answers disagree for the same role in one squad. Driven in a scratch squad: a role declared by `.overrides/roles/platform-dev.toml` and activated with `activate_role` stores `extra = {slug}` and no marker. The playbook layer then treats it as a developer (`skills_for_role` returns `sq-task, sq-bug, sq-contract, sq-review`, and the task skill renders its "developers" section with this as the only `-dev` role) while the resolver and item-file layers treat it as a bundled-style role (`role_base_from_item` takes the non-dev branch, `_exempt_extra_keys` returns the non-dev exemption). The code already knows this: `RoleDef.to_extra`'s docstring refuses to derive the marker from the slug for exactly this reason, and `_role_override_shadows_bundled` carries a stored-fact-first workaround for one consumer.

**Why it is spread.** Every spelling site is a function that receives a slug string and nothing else. `RoleView`, the projection handed to backends and templates, carries no developer field, so the three template-facing consumers cannot ask anything but the slug. And the developer definition is not catalog data: title, mission and responsibilities are composed in Python (`_roles/_catalog.py:333-348`); `[dev]` in `roles.toml` holds only the name pool, model and colour.

**What I would do.** Make it one resolved fact with one home: a declared field on the role definition (`RoleDef`, projected onto `RoleView`), resolved by `_roles/_resolver.py` like `is_default` already is through `holds_default_designation`. Then no function below the resolver takes a bare slug to decide it: slug-keyed callers receive the roster or a resolved role. The retirement has to cut through all 18 sites plus 64 test files and 7 golden/fixture files that mention `-dev` (driven count).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-17T03:47:52Z] `reviewer` Paul Reviewer:
  - Fixed at 7fd3bfd1 (commit 1100446f, TASK-990). A developer is now a declared capability: RoleDef/RoleView carry capabilities, [dev].capabilities holds it for templated developers, and the playbook *dev subject resolves through addresses() in _interactions/_role_guidance.py by capability, never slug spelling. is_dev_slug, both DEV constants, the -dev template check and the is_dev reads are gone from src (grep: only a migration and the retired-key name remain; the -dev suffix survives only as the slug sq dev add proposes, per ADR-984).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — RoleView lives in _backends and forces protocol stand-ins

<!-- sq:finding:F2:body -->
**Shape.** `RoleView` and `OperatorView`, the roster projection every consumer reads, are defined in `_backends/_base.py:30`. They are not backend types: `_views.py:43` imports `RoleView` for the `playbook` source, `_services/_base.py` builds them, and templates read them.

**Cost.**
- `_interactions/__init__.py` cannot import the type it consumes, because `_backends/_base.py:8` imports `skills_for_role` from it. It declares two structural stand-ins instead, `_RoleGuideBearing` (`:466`) and `_SlugBearing` (`:933`), each with a docstring explaining the one-way edge.
- `_views.py`, described as mechanism with no service dependency, depends on `_backends`, and `_backends/_claude_code/_backend.py` imports `_views`: a package-level cycle held apart only at module granularity (driven, import-graph script).
- Any field added to the roster projection has to be added in three places (the dataclass and both protocols) before a template can read it. A declared developer capability is exactly such a field.

**What I would do.** Move both dataclasses to `_roles/` (next to `RoleDef`, which they project). `_interactions`, `_views`, `_backends` and `_services` then all import downward, both protocols disappear, and the `_views` to `_backends` edge goes with them. No behaviour changes.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-17T03:47:54Z] `reviewer` Paul Reviewer:
  - Fixed at 7fd3bfd1 (commit 1fd45be5, TASK-989). RoleView and OperatorView live in src/squads/_roles/_projection.py; _RoleGuideBearing and _SlugBearing are deleted; _views.py imports nothing from _backends. The one remaining Protocol (RoleLike in _role_guidance.py) spans RoleDef and RoleView, not a stand-in for an unimportable type.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Roster projection is 400 lines of ServiceCore, used by six mixins

<!-- sq:finding:F3:body -->
**Shape.** `ServiceCore` lines 1255-1654 are a roster subsystem: `roster_item`, `_author_of`, `author`, `_role_view`, `roster`, `roster_from_db`, `roster_all`, `operators`, `operators_all`, `_skill_paths`, `_resolve_role_skills`, `resolved_skills_for_role`, `_role_skills_map`, `refresh_managed`, `candidate_orphans`, `_resync_role_skills`, `_project_roster_item`, `_project_roster_transition`. Eighteen methods, about 400 of the class's 1199 lines (read).

**Why it is there.** Six mixins need part of it (driven, AST over `self.` accesses): `RosterMixin`, `MaintenanceMixin`, `ItemsMixin`, `RefsMixin`, `ViewsMixin`, `CollabMixin`. A mixin can share only through the base, so the base is the only place it could go. `RosterMixin` itself (`_services/_roster.py`, 375 lines) holds the verbs but not the projection.

**Cost.** Role logic has no single home. The same concern is split over `_roles/_catalog.py`, `_roles/_resolver.py`, `_interactions/__init__.py`, `_services/_base.py`, `_services/_roster.py`, `_services/_maintenance.py` (`_refresh_catalog_extra`, roster drift), `_overrides/_service.py`, `_itemfile.py` and `_cli/_common.py`. A change to what a role is has to be reasoned about in nine modules; the developer question in the neighbouring finding is the current instance.

**What I would do.** Extract the cluster as one collaborator held as a field on the core (it needs only `paths`, `spec`, `playbook`, `store` and the backends), and let the six mixins call it. This is the one place where the scope's "explicit collaborators held as fields" pays for itself: it removes a third of `ServiceCore` and gives the roster projection a module of its own. The other mixins do not need the same treatment.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-17T03:48:11Z] `reviewer` Paul Reviewer:
  - Still open at 7fd3bfd1. The roster cluster is still in ServiceCore (_services/_base.py:1496-1903, 19 methods, now about 400 of a 1903-line file). ADR-984 left it out of scope (Order of work). Size: medium, one extraction with no behaviour change; part of the 0.17 structural work per op-pierre 2026-10-09.
- [2026-10-17T03:50:37Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — The mixin composition is a type-checked star: leave it

<!-- sq:finding:F4:body -->
**Conclusion: load-bearing, leave it.**

The scope states that every mixin reaches every other mixin's methods through `self`. Measured, that is not the case (driven: AST over every `self.<attr>` access in `_services/`, attributed to the class that defines it).

- Eleven of the twelve mixins reach `ServiceCore` and nothing else. No sibling access at all.
- `ImportMixin` is the one exception, and it declares it: its bases are `ItemsMixin, CollabMixin, SubentitiesMixin, RefsMixin`, and it calls 19 of their `_core`/`_model` halves to replay events inside one transaction.
- Module imports agree: every mixin module imports `_base`; only `_import` imports sibling mixins, and `_rename` imports one free function from `_retype`.

Because pyright runs in strict mode, a mixin that called an undeclared sibling's method would fail the type gate. The MRO is therefore not hiding a dependency graph: the graph is a star, and it is checked.

**What the pattern does cost** is the single sharing channel. Anything two concerns need must live in `ServiceCore`. Of its 53 attributes, 19 are used by two or more mixins, 20 by exactly one, 14 by none (public surface for the CLI and TUI, or internal). The roster cluster is the part worth lifting out (separate finding); the create path (`_create_model`/`_create_core`, 284 lines) and the tree view (89 lines) are legitimately core.

**Is `_services/` a layer or a bag?** A layer. `_validators.py`, `_retirement.py`, `_config_integrity.py`, `_import_model.py`, `_duplicate_ids.py` and `_skill_files.py` import no mixin and not `_base`; they are service-layer helpers that need index or corpus state. The top-level precedent is applied consistently for `_discussion.py`, `_badges.py`, `_sections.py` and `_itemfile.py`. `_views.py` is the one that no longer fits it (separate finding). Two small leaks: `_services/_results.py` imports `_retirement.py` (a result module depending on logic), and `_cli/_main.py:54-55` and `_tui/_browse.py:13` import `ItemFilter` and the graph renderers from `_base`/`_refs` past the facade.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-09T15:46:03Z] `reviewer` Paul Reviewer:
  - No action is the conclusion here: the measured mixin graph is a star over the core and the type gate checks it. Closing so it does not read as open work; the roster extraction it points to is F3.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — _interactions/__init__.py is an undeclared 1k-line policy hub

<!-- sq:finding:F5:body -->
**Shape.** `_interactions/__init__.py` is 992 lines of implementation, imported by 20 modules outside its own package (driven). CLAUDE.md's module-privacy convention names three non-empty package inits. Measured there are five: `squads/__init__` (5 lines), `_backends/_claude_code/__init__` (6), `_cli/__init__` (428, declared), plus `_workflow/__init__` (248) and `_interactions/__init__` (992), neither declared.

**What it holds** (read): the playbook dataclasses and bundled singleton; skill naming and descriptions; the three view-name constants shared with `_views.py` and `sq repair`; `is_dev_slug`; create-lane derivation and the lane exemption; role-to-type and role-to-skill mapping; skill-slug vocabularies; roster liveness (`is_live_roster_entry`); orphan-guide detection; cheatsheet anchoring; `authoring_owner`; `parent_chain`. That is the policy hub for roles, skills and lanes, not a package facade.

**Cost.** The name hides it: nothing called "interactions" suggests it decides who is a developer, which skills a role preloads, or whether a roster entry is live. And because it is the package root, every importer of any one of those pulls in the bundled playbook load at import time (`_PLAYBOOK_SPEC = load_playbook(get_catalog())`, about 35 ms self time under `-X importtime`).

**What I would do.** Move it, do not declare it. Split along the consumers that already exist: playbook data and lanes stay in `_interactions/` as a named module; role-to-skill resolution and `is_dev_slug` belong with the role resolver; skill naming and the view-name constants belong with the skill and view code. Leave the init empty and fix the CLAUDE.md list either way. Doing this before the developer-capability change means that change edits one role module instead of a 1k-line init.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-17T03:48:12Z] `reviewer` Paul Reviewer:
  - Partly addressed at 7fd3bfd1: the role derivations moved to _interactions/_role_guidance.py (1fd45be5), is_dev_slug is gone, and CLAUDE.md now declares _interactions/__init__ and _workflow/__init__ as non-empty inits, so the convention is citeable again. Remains: the init is still 810 lines of policy (skill naming, view-name constants, roster liveness, orphan guides, cheatsheet anchoring) and still loads the bundled playbook at import. Size: medium, mechanical moves; TASK-989 scoped the rest out.
- [2026-10-17T03:50:39Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — 48 parameters silently default a missing spec to the bundled one

<!-- sq:finding:F6:body -->
**Shape.** Two mechanisms let a caller get an answer from the bundled document without saying so.

1. **None-defaulted parameters.** 48 parameters across 14 modules are typed `WorkflowSpec | None = None` or `PlaybookSpec | None = None` and fall back to the bundled document inside the function (driven, AST): `_interactions/__init__.py` 11, `_badges.py` 10, `_discussion.py` 9, `_paths.py` 3, `_services/_config_integrity.py` 3, `ServiceCore.__init__` 2, `BackendContext.__init__` 2, and others. `bundled_spec()` has 43 production call sites in 19 files outside its own module.
2. **Module-level shims.** `_workflow/__init__.py` exposes 18 behaviour functions (`can_transition`, `is_open`, `parent_allowed`, `initial_status`, `item_is_roster`, ...) and four constants (`WORKFLOWS`, `SUBENTITY_WORKFLOWS`, `ALLOWED_PARENTS`, `TERMINAL`) over the bundled spec. None has a production caller (driven two ways: AST over imports, and a bare-call regex validated against the definitions). Tests use nine of the 22.

**Cost.** A call site that forgets to thread the active spec type-checks, runs, and answers with vocabulary the project may have overridden. Nothing distinguishes "deliberately bundled" from "forgot". Three production constructions already rely on it for the playbook: `_cli/_common.py:1363` and `_cli/_main.py:1607` and `:1614` build `Service(sp, spec=...)` with no playbook, so `sq repair` and the degraded `sq check` paths run a merged workflow spec against the bundled playbook (read; the consequence for a squad with a playbook override is inferred, not driven).

**What I would do.** Prune the shims, do not fence them: they are test-only surface. Then make the parameters required, starting with `ServiceCore.__init__` and `BackendContext`, and let the strict type gate list every site that was relying on the default. Tests pass `bundled_spec()` explicitly, which is what they mean. This is the structural fix for the "ambient defaults" tension in the DI area, and it needs no container.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-17T03:48:13Z] `reviewer` Paul Reviewer:
  - Still open at 7fd3bfd1. TASK-990 made the role-derivation path require its documents, so 41 None-defaulted spec/playbook/catalog parameters remain (was 48; _badges 10, _discussion 9, _services/_base 3 incl. ServiceCore.__init__, _paths 3, BackendContext 2, ...), 36 production bundled_spec() calls, and all 22 bundled shims in _workflow/__init__.py with no production caller. Size: medium-large, mostly mechanical once ServiceCore.__init__ and BackendContext go required.
- [2026-10-17T03:50:41Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Bundled sub-entity vocabulary survives as test-only API and tags

<!-- sq:finding:F7:body -->
**Shape.** Three groups of bundled sub-entity vocabulary remain below or beside the spec-driven path.

- `SubentitiesMixin` carries 16 per-kind wrappers (`add_story`, `add_subtask`, `add_finding`, `list_stories`, `set_subtask_status`, `update_finding`, ...). No production code calls them (driven: zero hits in `src/`, 226 calls in 41 test files with the same pattern). `pyproject.toml`'s vulture `ignore_names` lists them as "test-only public service API".
- `_models/_markers.py:22-24` keeps `STORIES`/`SUBTASKS`/`FINDINGS`; the only reader is the frozen `_migrations/_v0_1_to_v0_2.py`.
- `_models/_markers.py:38-47` keeps `story_tag`/`subtask_tag`/`finding_tag`; the only caller is the legacy branch of `CollabMixin._discussion_tag` (`_services/_collab.py:333-337`). The generic branch three lines above composes the same grammar by hand as an f-string (`:330`), so the sub-entity tag grammar is written once per bundled kind in `_markers` and once generically outside it.

**Cost.** Small, but it is the class the ref-kind work outlawed: a bundled literal under the spec layer, with the generic path beside it. It also makes `SubentitiesMixin` look a third larger than it is (16 of 46 methods), and CLAUDE.md still describes these methods as dispatched from `_cli/_items.py` at runtime, which no longer happens (no `getattr` dispatch onto the service exists in `_cli/`; driven grep).

**What I would do.** Add one generic `subentity_tag(kind, local_id)` to `_markers.py` and use it in both branches of `_discussion_tag`. Move the three container constants into the migration that needs them. Port the 41 test files to the generic `add_block`/`update_block` surface when the test rebuild happens, then delete the wrappers; until then they are honest debt with an owner. A `tests/meta` guard in the shape of the existing ref-kind one would keep new literals out.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-17T03:48:14Z] `reviewer` Paul Reviewer:
  - Still open at 7fd3bfd1, unchanged: STORIES/SUBTASKS/FINDINGS and story_tag/subtask_tag/finding_tag in _models/_markers.py, the legacy branch in _services/_collab.py:631-635, and 14 per-kind wrappers in _subentities.py kept for tests. Size: small for the tag and constants; the wrapper port rides the test rebuild.
- [2026-10-17T03:50:43Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Three spec loaders hand-write one load shape

<!-- sq:finding:F8:body -->
**Shape.** The merge engine (`_specmerge.py`) is shared and loader-agnostic. Everything around it is written once per document.

- `_read_bundled_bytes`, `_bundled_raw` and `bundled_<doc>_toml_text` exist three times, identical apart from the file name (`_workflow/_loader.py:301-323`, `_roles/_loader.py:66-87`, `_interactions/_loader.py:99-119`).
- `_read_raw_override` exists three times with two contracts: the workflow and playbook loaders return `(raw, error_tuple)`, the roles loader raises.
- The "merged is None, unreachable in fail-fast mode" guard is written three times.
- The decision "is there an override file, so merge, else take the cached bundled object" is taken by hand at seven non-migration sites for the workflow spec alone: `_workflow/_loader.py:259`, `:1254`, `:1356`; `_services/_service.py:107` and `:332`; `_cli/_common.py:181` and `:331`. `resolve_playbook` (`_services/_service.py:57`) is the playbook's copy, in the service layer.
- Caching differs per document: the workflow spec and playbook have an identity fast path; the role catalog is re-read and re-merged on every `_predefined_for_slug` call (`_roles/_resolver.py:92`, stated as deliberate).

**Cost.** Each construction path re-derives which spec it should hold, and they do not all agree (see the construction finding). A fourth override document, or a change to the fast-path rule, is a change in every copy.

**What I would do.** Make the shape code in two steps. First a small document descriptor (bundled file name, override file name, top-level keys, selected sections, build function) and one `load(document, squad_dir)` that owns reading, error wrapping and the unreachable guard. Second, one function that resolves the three documents for a squad together and returns them as one value, called by every construction site. `resolve_playbook` then moves out of `_services/` into that function. The loaders keep their own validation, which is where they genuinely differ.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-17T03:48:15Z] `reviewer` Paul Reviewer:
  - Still open at 7fd3bfd1, unchanged: _read_bundled_bytes/_bundled_raw/bundled_*_toml_text and _read_raw_override still exist once per loader (_workflow, _roles, _interactions), with the two error contracts, and resolve_playbook is still in _services/_service.py:56. Size: medium, a document descriptor plus one load function.
- [2026-10-17T03:50:45Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — WorkflowSpec methods are fine; its file holds three other things

<!-- sq:finding:F9:body -->
**Conclusion on the methods: load-bearing, leave them.** `WorkflowSpec` itself is 622 lines with 46 methods, almost all between 2 and 20 lines, each a pure derived query over the spec's own data (`live_statuses`, `first_settled_status`, `default_ref_kind`, `item_subentity_kind`, ...). Moving them to resolver functions that take a spec would change every call site and remove the one property that makes threading safe: you need a spec instance in hand to ask. I would not do it.

**What does cost** is the file, `_workflow/_models.py` at 2907 lines, because it holds three other things beside the models (read):

- the validator name registries, level tables and bundles (lines 144-520);
- the load-time spec-validity checks, about 30 `_check_*`/`_clause_*` functions (lines 1067-2131);
- lifecycle linearisation (lines 2158-2283).

A reader looking for what a spec *is* has to skip 1500 lines of what makes one *valid*. About a quarter of the file is docstring (746 of 2908 lines, driven).

**What I would do.** Split the file, not the class: registries, validity checks and lifecycle ordering each in their own module under `_workflow/`, with `WorkflowSpec._validate` calling into the validity module. The models' public surface does not move. The validity module needs the model types and the model validator needs the checks, so the validator's import of the checks must be function-local; that is the same cycle break this file already uses for `_models._item`.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-17T03:48:30Z] `reviewer` Paul Reviewer:
  - Still open at 7fd3bfd1: _workflow/_models.py has grown to 3434 lines and still holds the validator registries, the load-time validity checks and lifecycle linearisation beside the models; _workflow/ has no new module. Size: small-medium, a file split with one function-local import.
- [2026-10-17T03:50:47Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — _maintenance.py is two modules: the rebuild corridor and check

<!-- sq:finding:F10:body -->
**Shape.** The scope asks whether the corpus walk is a seam with several independent consumers. Measured, the public entry points are not independent (driven: reachability over `self.` calls inside `MaintenanceMixin`).

- **One corridor.** `sync`, `run_pending_migrations` and `repad` all reach `repair`; `repair` and `renumber` both funnel into `_rebuild_index_from_disk`. Twelve methods (`_carry_forward_unreadable`, `_handle_missing_id`, `_carry_duplicate`, `_corpus_alignment_refusals`, `_repair_body_tag`, ...) are reachable from all five and never from `check`.
- **One separate branch.** `check` reaches 18 methods and shares only eight with the corridor: `_iter_item_files`, the skill-file helpers (`_read_skill_texts`, `_skill_folder_state`, `_skill_remedy`, `_indexed_skills`), `_id_carriers` and two message helpers. Nine module-level helpers are called by `check`'s methods alone, plus the helpers those call.

So the module is two things, not four: the rebuild corridor, and the read-only report. `_iter_item_files` itself is a 30-line generator; the real shared primitive is what both loops do with each file (read, parse, and sort it into item, unreadable, missing id, legacy skill body or vanished). That classification is written twice, in `_rebuild_index_from_disk` and `_scan_for_check`, and held together by a guard (`tests/meta/test_corpus_walking_reads_degrade_per_file.py`) rather than by shared code.

**Also.** There are two walk primitives with different inclusion rules: `_iter_item_files` (`PREFIX-*.md` plus legacy skill files, spec order) and `ServiceCore._all_item_files` (`*.md`, `_services/_base.py:926`), plus six ad-hoc folder globs inside `_maintenance.py` (lines 1293, 1333, 1479, 1735, 1829, 1985). `sync` is a single 281-line method. A third of the file is docstring (1014 of 3620 lines).

**What I would do.** Lift the per-file classification into one corpus-reading primitive that yields a tagged record per file, and build both loops on it. Then move `check`, its drift-confirmation methods and its own helpers (about 1100 lines) into their own mixin. Leave the corridor together: it is one job. Break `sync` into named steps in place.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-17T03:48:31Z] `reviewer` Paul Reviewer:
  - Still open at 7fd3bfd1: _maintenance.py is 3769 lines; check (:3165) and _scan_for_check (:3621) still sit in MaintenanceMixin with the rebuild corridor, and the per-file classification is still written in both loops. Size: medium-large (shared classification primitive, then a check mixin of about 1100 lines).
- [2026-10-17T03:50:49Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — sq check has eight finding sources and names none of them

<!-- sq:finding:F11:body -->
**Shape.** The two module docstrings describe two tiers. `MaintenanceMixin.check` assembles findings from eight sources (read, `_services/_maintenance.py:3029-3108` and `:3471-3619`):

1. raw-text scan: `_marker_issues`, `_view_target_issues`, `_seeded_view_issues`, `_absent_body_region_issues` (error), and the out-of-region view tag (warn);
2. the per-file load boundary: unreadable file, unparseable frontmatter, missing id, malformed id, type-invalid field, missing timestamps;
3. override checks from `_overrides/_service.check_override_issues`;
4. orphaned skills;
5. duplicate ids;
6. the per-item catalog;
7. the squad-global catalog;
8. cross-source candidates confirmed by a re-read.

Only 6 and 7 are selectable. `_cli/_main.py` adds three more of its own for a config that will not load.

**Is "unconditional, per-file, pre-parse" a stable rule?** Two of the three words are. "Pre-parse" already does not hold: `_seeded_view_issues` and `_absent_body_region_issues` take a slug that `_check_slug` reads out of parsed frontmatter (`:559-572`), falling back to the filename only when parsing fails, and the loop then parses the same frontmatter a second time at `:3581`. The rule the four members actually satisfy is: per file, not selectable, and still reported when the frontmatter cannot be read. Stated that way it will hold for a fifth member. Stated as "pre-parse" it is a description of the first two.

**Probe 1, discoverability: fails.** `CheckIssue` is `level`, `item`, `message` (`_services/_results.py:143`) and `sq check --json` emits exactly those three keys. No finding carries the name of the rule that produced it, from either tier. A consumer cannot list the rules, tell a selectable finding from a binding one, or match a finding to a rule except by parsing message text; `check` itself does that at `:3104` (`message.startswith("on disk but not in index")`). `docs/overrides.md` documents the selectable validators; no adopter document says which findings cannot be deselected.

**Probe 2, non-overridability.** It is a defensible contract: marker integrity is what marker-safe editing depends on, and a view tag that cannot resolve is corrupt content rather than policy. It is not stated anywhere an adopter reads, and under the direction that only role, skill and operator are reserved it has to be stated, or an adopter will read an undeselectable finding as a bug.

**What I would do.** Give `CheckIssue` a `rule` field (an additive `--json` change) and one registry that names every source with whether it is selectable. Rewrite the tier rule in both docstrings without "pre-parse". Say in the adopter docs which findings are binding. The registry is where a `tests/meta` guard belongs: every `CheckIssue(` construction names a registered rule.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-17T03:48:32Z] `reviewer` Paul Reviewer:
  - Still open at 7fd3bfd1: CheckIssue is still level/item/message (_services/_results.py), so no finding names its rule in --json and no registry says which are binding; the adopter docs do not list them. Size: medium, additive --json key plus registry, guard and a docs paragraph.
- [2026-10-17T03:50:51Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — View layout is right; _views.py itself holds five jobs

<!-- sq:finding:F12:body -->
**On the six places: the decomposition is right.** Grammar in `_models/_markers.py` and `_sections.py`, mechanism in `_views.py`, the index-loading seam in `_services/_views.py`, presentation in templates, integrity in the check scan, serialisation at the CLI edge. I would not merge any of them.

**On the `--json` asymmetry: a boundary, leave it.** `_view_json_payload` (`_cli/_workflow_cmd.py:892`) dispatches per source kind because five of the six kinds reuse the serialiser that already defines their shape elsewhere (`sq tree --json` rows, sub-entity rows, the role card, `show --json`). A shared envelope would be a second contract for the same data, and each kind's payload would then have two shapes to keep in step. The `playbook` kind is the only one with a shape of its own. Required views add callers, not kinds, so they do not push on this. The scope's `projection_json` no longer exists (driven: zero hits in `src/` and `tests/`).

**What has strained is `_views.py` itself**, 1197 lines holding five jobs (read):

- source resolution and applicability (lines 100-520);
- rendering (530-603);
- roster body policy: `roster_slug`, `roster_body_view_name`, `seeded_view_names`, `skill_authoring_surface` (606-715);
- CLI command composition: `view_placement_invocation` and `clear_roster_body_cmd` build `sq ...` command strings, the latter a JSON import event piped to `sq import -` (717-745);
- the tag placement and expansion text engine (751-1170).

It is no longer a leaf mechanism: it imports `_backends._base`, `_interactions`, `_roles` and `_rendering`. Its module docstring names `ServiceMixin.insert_view`/`remove_view`, which do not exist (the methods are `ViewsMixin.add_view`/`disable_view`); `_services/_base.py:1228` repeats the stale names.

**What I would do.** Move the tag text engine next to `_sections.py`, where the rest of the marker-safe editing lives, and move the two command builders to the CLI layer or to wherever remedies are composed. `_views.py` is then source resolution and rendering again. Fix the two stale method names.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-17T03:48:33Z] `reviewer` Paul Reviewer:
  - Still open at 7fd3bfd1: _views.py is 1199 lines with the tag text engine and the two command builders (:718, :732) still inside, and the stale insert_view/remove_view names remain at _views.py:29 and _services/_base.py:1467. Size: small; the two stale names are a one-line fix each.
- [2026-10-17T03:50:53Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — _cli/_common.py: nothing breaks today, leave it whole

<!-- sq:finding:F13:body -->
**Conclusion: leave it whole.** The scope asks for a split only if something breaks today. I looked for a break and did not find one (read).

- The module is 1941 lines and 64 top-level names in four groups, but the groups do not interfere: no cycle runs through it, the type gate is clean on it, and its import cost is the cost of whatever it imports first, not its own (7 ms self time under `-X importtime`).
- The JSON builders are a consumer contract in a module called "common". That is a naming cost, not a defect: the contract is pinned by the CLI golden tests, and it is not concentrated here anyway. `--json` output is assembled at 72 `json.dumps`/`print_json_clean` sites across 12 `_cli` modules; `_common.py` holds the six shared builders.

Two observations a later change should know about, neither a reason to split now:

- `build_item_row_json` and `build_subentity_row_json` emit `priority`, `severity` and `story` as fixed top-level keys beside the generic `badges` map, and three callers pass `badge_value("priority")` or `badge_value("severity")` by literal name (`_cli/_workflow_cmd.py:878`, `:934`, `:954`). Those keys are part of the frozen `--json` shape, so they stay, but they are bundled field names on a machine surface.
- The CLI has two handles on the active spec: `get_active_spec()` (47 uses) and `svc.spec` (15 uses). No function mixes them, and on the normal path they are the same object. On the degraded paths they are not built from the same resolution (see the construction finding).

**What I would do.** Nothing structural. If the builders are touched for another reason, give them a module of their own (`_cli/_json.py`) so the contract has an address.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-09T15:46:06Z] `reviewer` Paul Reviewer:
  - No action is the conclusion here: I could not name anything that breaks today, which is the bar the scope set for a split. Closing so it does not read as open work.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — DI container: no at today's graph size, with measurements

<!-- sq:finding:F14:body -->
**Verdict: no, for the wiring and for the rest, at the size the object graph has today.** Not a reflex: I ran `soupape` 0.10.0 on Python 3.14.7 against a model of this codebase's graph. The alternative that is owed is the neighbouring construction finding.

**What was measured (driven unless marked).**

- **The graph is six nodes.** One `Service`, one `IndexStore`, `SquadPaths`, `WorkflowSpec`, `PlaybookSpec`, and up to two backends. There are eight construction sites, but they build the same object.
- **Construction is not a cost.** `open_service` takes 0.17 ms steady and 0.54 ms the first time; an index load of 28 items takes 23 ms. A real `sq --version` takes 1.3-1.5 s and `sq review 956 show` 1.7-2.0 s on this machine: the invocation is import time. Soupape resolves the same six-node graph in 0.3-0.6 ms, so it neither helps nor hurts there. Its own import adds 60-260 ms across three warm runs (47 modules; noisy, and part of it is `asyncio`, which `sq` already loads).
- **Question 1, runtime hint resolution.** A constructor hint that is importable only under `TYPE_CHECKING` raises a bare `NameError` from inside the container, not a `SoupapeError` and not something `handle_errors` would turn into a clean message. Against the real graph the exposure is small: only three modules use a `TYPE_CHECKING` import at all (8 edges: `_context.py`, `_cli/_workflow_cmd.py`, `_tui/_filter.py`), and every type a composition root would inject is already a top-level import of `_services/_base.py`. The cycle break this codebase actually relies on is the function-local import (50 edges in 20 modules), which a container does not disturb. So this question does not decide against it; it would constrain `RequestContext` if that were ever container-built.
- **Question 2, the dependency.** It is four packages, not one: `soupape` requires `peritype`, `hafersack` and `escondite`. All are 0.x; `soupape` went from 0.6 to 0.10 in about ten weeks, `hafersack` has one release and `escondite` three (PyPI). One contributor on the repository (GitHub API). That the other three share the maintainer is inferred from the README, not verified. Against seven widely used runtime dependencies, that is the weight to justify.
- **Question 3, failure locality.** Detection before instantiation works: an unregistered dependency, a scoped service required from the root, and a singleton depending on a scoped service each raised a coded error. The messages name the missing interface but not the service that required it ("Service for interface 'Spec' not found"), which locates less than the `SquadsError` `open_service` raises today.
- **Question 4, testability.** Already banked, as the scope says. 328 direct `Service(...)` constructions in 108 test files drive real squads.

**Against the tensions the scope names.**

- **None-defaulted parameters with an in-constructor fallback.** A container does not fix these. A parameter typed `Spec | None = None` whose type is not registered resolves to `None` silently, which is the same failure in a new place. Making the parameter required fixes it, with or without a container.
- **The hand-rolled scope on Click's context.** A scoped injector would replace two memo keys and one teardown callback, about 40 lines. It would still need the same anchor (the Click root context) to live across the two `anyio.run` crossings. And it does not touch the part that was discovered the hard way: one scope object held across two `anyio.run` calls returned the same instance both times, so lifetime was never the problem. The `ContextVar` that has to be re-asserted is copied per crossing by `anyio.run`; that is a property of ambient state, and the fix is to stop the renderer reading it.
- **The bypass ladder** (`get_service_bypassing_index_cross_check` and the two `sq check` fallbacks) is error-recovery policy: which spec to fall back to when resolution fails. A container has nothing to say about it.
- **The backend registry** is a name-to-class lookup driven by per-squad config. It stays a lookup either way.
- **The DATA-versus-CODE taxonomy** does map onto scoped versus singleton. But the CODE side here is immutable module constants loaded at import, and the DATA side is one frozen eight-field dataclass. There is nothing for a container to manage.
- **The mixins.** Agreed with the scope: not addressed, and the measured mixin graph is a star that needs no rewiring.

**When the answer changes.** Two conditions, either of which would make me reopen this: the service is decomposed into several collaborators with their own dependencies (the roster projection is the first candidate), so that wiring is written more than once; or a long-lived process arrives (`_context.py` already anticipates a server handler), where per-request scopes with ordered teardown are real work rather than one Click callback. At that point a scoped injector created at the edge is the right shape, and the required-parameter change will already have made the classes injectable.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-09T19:23:56Z] `op-pierre` Pierre Chat:
  - 2026-10-09: no decision on a DI container for 0.16. It is decided for 0.17, together with the structural work the rest of this review feeds.
- [2026-10-17T03:48:34Z] `reviewer` Paul Reviewer:
  - Still open: op-pierre ruled on 2026-10-09 that the DI container is decided in 0.17 with the rest of the structural work, so this verdict stays open until that decision. No code change bears on it.
- [2026-10-17T03:50:56Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Service is built at eight sites; three omit the playbook

<!-- sq:finding:F15:body -->
**Shape.** A `Service` is constructed at eight production sites (read; grep validated against the class definition):

- `_services/_service.py:168` (`init`) and `:244` (`adopt`): spec and playbook resolved together.
- `_services/_service.py:328`, `:341`, `:358` (`open_service`): three branches, spec and playbook resolved together.
- `_cli/_common.py:1363` (`_build_bypass_fallback_service`, used by `sq repair`): merged spec, **no playbook**.
- `_cli/_main.py:1607` and `:1614` (`sq check` fallbacks): merged or bundled spec, **no playbook**.

Around them the CLI has four accessors (`get_service`, `_build_plain_service`, `get_service_bypassing_index_cross_check`, `_build_bypass_fallback_service`), two memo keys on Click's root context, and three functions that each resolve the workflow spec for the invocation (`bind_active_spec`, `resolve_spec_for_ctx`, `open_service`).

**Cost.**

- The three sites that omit the playbook get the bundled one from the constructor's `None` default. Whether that is intended is not visible at the call site: `:1607` is deliberate (the playbook is what failed), `:1363` reads as an omission. The effect on a squad that has a playbook override and needs `sq repair` after a cross-check refusal is inferred, not driven.
- `ServiceCore.__init__` sets ambient render state as a side effect (`set_active_squad_dir`, `_services/_base.py:477`). Because that is a `ContextVar` and each `anyio.run` crossing copies its own context, `get_service` has to re-assert it on every memo hit (`_cli/_common.py:1275`, `:1340`), and a 15-line docstring explains why.
- `_rendering/_engine.py:47` is a second ambient seam beside `RequestContext`, which `_context.py` calls "the one seam ambient values live in". Four `ContextVar`s exist in total (`_context`, `_active_squad_dir`, and the store's `_active_transaction` and `_read_scope`).
- The backend registry (`_backends/_registry.py`) is a module-global dict filled by importing two packages for their side effect, behind a `global _loaded` flag, for two built-in backends. `get_backend` is called from inside `ServiceCore._backends`, `_validators.py` (twice) and `_maintenance.py`.

**What I would do, without a dependency.**

1. One composition function that takes the squad paths and a mode (normal, skip the index cross-check, playbook unavailable) and returns the service. All eight sites call it. The fallback order becomes a readable table instead of three try/except ladders in two modules.
2. `spec` and `playbook` required on `ServiceCore.__init__`; the store and the backend list passed in rather than built inside.
3. The renderer takes the squad directory as an argument from the caller that already holds `paths` (about 20 `render` call sites outside the engine itself), which removes `set_active_squad_dir` from the constructor, both re-asserts, and the second ambient seam.
4. The registry becomes a literal name-to-class table; active backends are instantiated once at the composition function.

Each step stands alone and none changes behaviour. Step 3 is the one with a design question in it (the Jinja environment cache is keyed on the same value), so it wants the architect's eye.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-17T03:48:35Z] `reviewer` Paul Reviewer:
  - Still open at 7fd3bfd1. The normal bypass path now resolves the playbook (_cli/_common.py:1501), but four constructions still omit it (_cli/_common.py:1487, :1496; _cli/_main.py:1615, :1622), ServiceCore.__init__ still calls set_active_squad_dir (_services/_base.py:541) with the two re-asserts in _cli/_common.py, and the backend registry is still a module-global dict behind global _loaded. Size: medium; step 3 (renderer squad dir) wants the architect.
- [2026-10-17T03:50:58Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — Layering is stated in three places and guarded by no test

<!-- sq:finding:F16:body -->
**Shape.** The layering is written down in three places: CLAUDE.md's diagram (`_cli` to `_services` to index store, backends, rendering; `_models` shared with no internal deps), its "keep the import graph acyclic (verified)" rule, and layering notes in docstrings (for example `ServiceCore._skill_paths`: "`_backends` must not import `_index`"). The review scope says the graph is "acyclic and guarded".

No test guards any of it. `tests/meta` has 42 guard modules; none inspects the import graph for cycles or layer direction (driven: a search for tests that walk imports found six, all about other properties; the pattern was validated against those six).

**What the graph is today** (driven: AST over every module, top-level and function-local imports separated).

- At module granularity it is acyclic apart from the `_cli` package init and three of its submodules, the usual Typer wiring. Python enforces this much by failing at import.
- At package granularity eight packages form one strongly connected component: `_backends`, `_badges`, `_interactions`, `_overrides`, `_paths`, `_rendering`, `_views`, `_workflow`. Examples: `_workflow/_loader.py` imports `_overrides/_manifest.py` while `_overrides/_service.py` imports `_workflow/_loader.py`; `_views.py` imports `_backends/_base.py` while `_backends/_claude_code/_backend.py` imports `_views.py`; `_rendering/_engine.py` imports `_interactions` to register Jinja helpers.
- `_models` is not dependency-free: `_models/_item.py` imports `_clock`, which imports `_context`.
- `_itemfile.py` imports `_roles/_catalog.py` (the skew exemption needs the role's stored keys), so the frontmatter layer depends on the role catalog.
- The documented cycle break (`TYPE_CHECKING` plus a string annotation) is used in three modules. The break actually in use is the function-local import: 50 edges in 20 modules.
- The stated `_backends`-does-not-import-`_index` rule holds.

**Cost.** Nothing is wrong at runtime. The cost is that the diagram no longer predicts where a new import is allowed, so each change re-derives it and resolves the cycle it finds with another function-local import. Role logic is the visible case: it reaches down into `_itemfile` and across into `_backends`, `_views` and `_overrides` with nothing to say whether that is permitted.

**What I would do.** Add one `tests/meta` guard holding the allowed package-to-package edges as a table, seeded from today's measured graph, so the current state is recorded and any new edge is a deliberate one-line change in review. Correct CLAUDE.md's diagram and the `_models` claim to match. Then tighten the table as the placement findings on this review are acted on. This is the cheapest structural action here and it makes every other one safer.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-10-17T03:47:56Z] `reviewer` Paul Reviewer:
  - Fixed at 7fd3bfd1 (commit 1fd45be5, TASK-989). tests/meta/test_package_import_edges_match_the_recorded_table.py records every package edge with where it runs and pins the eight-package top-level set; it passes (driven). CLAUDE.md now names that table as the layering authority, states the non-strict stack and corrects the _models claim.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — retype and import write one file several times per transaction

<!-- sq:finding:F17:body -->
**The rule under audit.** An atomic service method works on in-memory buffers and writes each file at most once, at the end, before the index commit.

**Method (driven).** A spy on the write funnel (`_aio.atomic_replace_sync`, through which every item-file write and the index commit pass, and `_aio.write_text`) and on `IndexStore.transaction`, counting writes per path per transaction. Run against a scratch squad through the service API, 39 steps covering create, update, status, body, comment, sub-entity add/update/status/body/remove, ref add/remove, link/unlink, retype, role/dev/skill/operator verbs, default-role move, roster retirement, view add/disable, regen, bulk import, remove, sync and repair.

**Result.** 35 steps wrote inside a transaction. 32 of them write each item file exactly once. Three steps, from two methods, do not.

- **`retype` writes the same file three times in one transaction** (driven). Read: `apply_type_change` renames the file and rewrites its frontmatter (`_services/_retype.py:275-278`), `_ensure_subentity_container` rewrites it again (`:281`, `:295`), `rewrite_ids` may touch it (`:189`), and `_append_retype_comment` writes it once more (`:198`, `:338`).
- **`import_events` writes once per event, not once per file** (driven). Seven events on one newly created item wrote its file seven times in the one transaction; four events on an existing item wrote it four times. The apply loop calls each event's `_core` half in turn (`_services/_import.py:492-498`) and every `_core` ends in its own write.

Not driven, from reading: `rename_type` runs the same `apply_type_change` per item (`_services/_rename.py:201`) and then `rewrite_ids` over the same files (`:217`), and `sq repair` can write one file from both its body-tag backfill and its pending-rewrite pass (`_services/_maintenance.py:2216`, `:2457`) on a corpus that needs both; the clean scratch corpus exercised neither.

**Cost.** Each extra write is an extra point at which a killed process leaves the file in an intermediate state that is still valid markdown but not the method's result: a retyped file with its new frontmatter and no container, an import half-applied to one item. The store's skew rule keeps the index behind, so `sq repair` adopts whatever is on disk, including the intermediate state. For import the cost is also linear I/O: an fsync per event.

**Why it happens.** The services split each mutation into a pure `_model` half and a writing `_core` half, which is the right shape. The two offenders compose several `_core` halves, so they inherit one write per half. The fix is the same in both: compose the `_model` halves over one in-memory text per path and write each path once at the end of the transaction.

**Proposed guard.** The spy is about 40 lines and belongs in the suite as an autouse fixture: wrap `_aio.atomic_replace_sync` and `IndexStore.transaction`, key a counter on (transaction, resolved path), and fail the test at transaction exit if any item path was written twice. Exclude the index file itself and regenerable backend output, which the store's docstring already exempts. Start with an explicit allowlist of the known offenders (`retype`, `rename_type`, `import_events`, the repair rebuild) so the guard lands green and every entry is a named debt; because it is autouse, every existing service and CLI test becomes a probe for the rule at no extra cost. Per the board's falsification rule, prove it by removing one allowlist entry and watching the corresponding test fail.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-10-17T03:47:58Z] `reviewer` Paul Reviewer:
  - Fixed at 7fd3bfd1 (commits 22fa82b6, 4417bdee, 15b80785, dd20eef5, guard 4a8bdc9d; TASK-992). tests/_write_guard.py is installed autouse from tests/conftest.py and fails any unit (transaction or repair rebuild) that writes one item file twice; the allowlist was dropped, so retype, import, rename_type and repair are all held to it. The three per-method tests plus the import-edge guard: 129 passed (driven, -n0).
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — Comment rule: 95 of 127 source files fail a mechanical check

<!-- sq:finding:F18:body -->
**The rule** (board notice, 2026-09-29): docstrings are one or two sentences of what and why; comments that restate the code are deleted; no release versions, ticket ids or history outside migration runners.

**Coverage, stated plainly.** Every `.py` file under `src/squads/` was scanned mechanically (127 files, 45,243 lines; driven, `ast` plus `tokenize`, whole docstrings and whole comment runs with whitespace collapsed, so a line-wrapped token is not missed). I read parts of 25 of them for the structural findings on this review, three in full (`_context.py`, `_backends/_registry.py`, `_workflow/__init__.py`). The mechanical pass can measure length, version strings and history phrasing. It cannot judge whether a comment restates the code or whether a long docstring is earning its length; that judgement was made only on the files I read. No Jinja template was scanned.

**The checks.** A file fails if it has any of:

- a docstring longer than 5 non-blank lines (lenient: the rule says one or two sentences, so this undercounts);
- a run of more than 3 consecutive comment lines;
- outside `_migrations/`, a release-version string (`0.N` or `v0.N.N`) in a comment or docstring;
- a ticket-id shape (`FEAT-12`, `TASK-3`, ...);
- history phrasing: "used to", "previously", "no longer", "an earlier", "now that", "formerly", "as before", "byte-identical to today/before", and similar.

**Result.** 95 of 127 files fail at least one check; 32 pass all of them.

- 638 docstrings in 91 files exceed 5 lines. The longest is 97 lines.
- 271 comment runs in 60 files exceed 3 lines.
- 27 release-version mentions in 11 non-migration files.
- 149 history phrases in 54 files.
- 0 ticket ids (the existing `tests/meta` ticket-reference guard holds).
- Docstrings and comments are 30.9% of all source lines: 10,961 docstring lines and 3,025 comment lines.

**Why it matters structurally.** The sizes this review's scope cites are a third prose. `_maintenance.py` is 3620 lines of which 1014 are docstring; `ServiceCore`'s file is 1655 of which 457. Several docstrings I read carry design history and rejected alternatives (`role_base_from_item`, 70 lines; `open_service`, 45 lines; `_exempt_extra_keys`, 36 lines), cite test file paths, or name methods that no longer exist (`_views.py`'s module docstring). That is the material the rule sends to the commit, the ADR or the item.

**On filing.** The scope addition asks for one finding per failing file. That would be 95 findings here and 414 for the tests, every one resting on a threshold I chose rather than on a read of the file, and I cannot remove findings once filed. I have recorded the complete per-file result below instead, so nothing is sampled away and the fan-out stays a mechanical step if it is wanted. This is a deviation from the letter of the request and is flagged as such in the closing comment.

**Per-file result** (failing files only; columns: docstrings over 5 lines, longest docstring in lines, comment runs over 3 lines, version mentions, history phrases).

| File | Long docstrings | Longest | Long comment runs | Versions | History |
|---|---|---|---|---|---|
| `_services/_maintenance.py` | 51 | 97 | 35 | 3 | 21 |
| `_workflow/_models.py` | 45 | 32 | 27 | 0 | 4 |
| `_cli/_common.py` | 34 | 28 | 7 | 0 | 8 |
| `_services/_base.py` | 29 | 34 | 12 | 0 | 11 |
| `_interactions/__init__.py` | 24 | 42 | 9 | 0 | 14 |
| `_services/_validators.py` | 22 | 45 | 6 | 0 | 4 |
| `_workflow/_loader.py` | 22 | 47 | 12 | 0 | 8 |
| `_views.py` | 20 | 28 | 3 | 0 | 0 |
| `_cli/_workflow_cmd.py` | 19 | 23 | 3 | 0 | 1 |
| `_specmerge.py` | 18 | 55 | 3 | 0 | 2 |
| `_models/_item.py` | 16 | 40 | 5 | 2 | 1 |
| `_overrides/_service.py` | 16 | 26 | 5 | 0 | 3 |
| `_cli/_main.py` | 14 | 31 | 10 | 0 | 0 |
| `_services/_results.py` | 14 | 30 | 5 | 3 | 1 |
| `_index/_store.py` | 13 | 60 | 5 | 0 | 2 |
| `_roles/_resolver.py` | 13 | 61 | 3 | 0 | 2 |
| `_itemfile.py` | 10 | 43 | 2 | 3 | 4 |
| `_services/_refs.py` | 10 | 35 | 4 | 0 | 2 |
| `_badges.py` | 9 | 10 | 0 | 0 | 0 |
| `_interactions/_loader.py` | 9 | 42 | 6 | 0 | 2 |
| `_services/_items.py` | 9 | 31 | 6 | 0 | 3 |
| `_services/_subentities.py` | 9 | 15 | 4 | 0 | 2 |
| `_cli/_create.py` | 8 | 20 | 7 | 0 | 3 |
| `_roles/_catalog.py` | 8 | 29 | 3 | 1 | 1 |
| `_services/_import.py` | 8 | 23 | 2 | 0 | 3 |
| `_backends/_base.py` | 7 | 53 | 4 | 0 | 1 |
| `_cli/_items.py` | 7 | 24 | 4 | 0 | 5 |
| `_backends/_agents_md/_backend.py` | 6 | 19 | 1 | 0 | 1 |
| `_cli/_role.py` | 6 | 24 | 4 | 0 | 2 |
| `_discussion.py` | 6 | 11 | 1 | 0 | 1 |
| `_migrations/_v0_14_to_v0_15.py` | 6 | 128 | 5 | 0 | 1 |
| `_services/_config_integrity.py` | 6 | 29 | 3 | 0 | 0 |
| `_services/_retirement.py` | 6 | 23 | 2 | 0 | 0 |
| `_aio.py` | 5 | 13 | 1 | 0 | 0 |
| `_backends/_claude_code/_backend.py` | 5 | 29 | 8 | 0 | 0 |
| `_services/_collab.py` | 5 | 26 | 0 | 0 | 2 |
| `_services/_rename.py` | 5 | 17 | 2 | 0 | 0 |
| `_services/_roster.py` | 5 | 27 | 0 | 0 | 1 |
| `_services/_service.py` | 5 | 36 | 5 | 0 | 2 |
| `_cli/__init__.py` | 4 | 14 | 7 | 0 | 3 |
| `_cli/_import.py` | 4 | 21 | 0 | 0 | 0 |
| `_cli/_override.py` | 4 | 24 | 0 | 0 | 0 |
| `_memory/_store.py` | 4 | 12 | 0 | 0 | 0 |
| `_migrations/_v0_11_to_v0_14.py` | 4 | 41 | 2 | 0 | 1 |
| `_migrations/_v0_4_to_v0_5.py` | 4 | 25 | 0 | 0 | 2 |
| `_models/_index.py` | 4 | 12 | 0 | 0 | 0 |
| `_rendering/_engine.py` | 4 | 16 | 6 | 3 | 1 |
| `_sections.py` | 4 | 23 | 1 | 0 | 1 |
| `_board/_store.py` | 3 | 13 | 0 | 0 | 0 |
| `_cli/_migrate.py` | 3 | 14 | 2 | 0 | 0 |
| `_migrations/_v0_1_to_v0_2.py` | 3 | 11 | 1 | 0 | 1 |
| `_models/_markers.py` | 3 | 18 | 2 | 0 | 1 |
| `_models/_vocab.py` | 3 | 22 | 0 | 0 | 0 |
| `_roles/_loader.py` | 3 | 35 | 0 | 0 | 1 |
| `_services/_views.py` | 3 | 15 | 1 | 0 | 0 |
| `_tui/_tree.py` | 3 | 14 | 1 | 0 | 2 |
| `_actor.py` | 2 | 19 | 0 | 0 | 0 |
| `_backends/_managed_region.py` | 2 | 12 | 1 | 0 | 1 |
| `_cli/_memory.py` | 2 | 16 | 0 | 0 | 0 |
| `_errors.py` | 2 | 6 | 0 | 0 | 0 |
| `_index/_reflog.py` | 2 | 45 | 1 | 3 | 0 |
| `_migrations/_registry.py` | 2 | 13 | 0 | 0 | 0 |
| `_migrations/_v0_8_to_v0_10.py` | 2 | 30 | 1 | 0 | 2 |
| `_models/_metadata.py` | 2 | 15 | 4 | 0 | 3 |
| `_models/_omission.py` | 2 | 10 | 0 | 0 | 0 |
| `_models/_schema.py` | 2 | 15 | 0 | 3 | 0 |
| `_services/_import_model.py` | 2 | 11 | 0 | 0 | 1 |
| `_services/_retype.py` | 2 | 20 | 3 | 0 | 0 |
| `_workflow/__init__.py` | 2 | 11 | 1 | 0 | 1 |
| `_backends/_claude_code/_frontmatter.py` | 1 | 11 | 1 | 0 | 0 |
| `_board/_model.py` | 1 | 8 | 0 | 0 | 0 |
| `_cli/_board.py` | 1 | 10 | 0 | 0 | 0 |
| `_cli/_operator.py` | 1 | 8 | 0 | 0 | 0 |
| `_cli/_skill.py` | 1 | 17 | 1 | 0 | 1 |
| `_context.py` | 1 | 18 | 2 | 0 | 1 |
| `_memory/_model.py` | 1 | 7 | 0 | 0 | 0 |
| `_migrations/_meta_compat.py` | 1 | 6 | 1 | 0 | 2 |
| `_migrations/_outcome.py` | 1 | 8 | 0 | 0 | 0 |
| `_migrations/_v0_10_to_v0_11.py` | 1 | 16 | 0 | 0 | 0 |
| `_migrations/_v0_2_to_v0_3.py` | 1 | 23 | 0 | 0 | 1 |
| `_migrations/_v0_3_to_v0_4.py` | 1 | 25 | 0 | 0 | 0 |
| `_migrations/_v0_5_to_v0_7.py` | 1 | 34 | 3 | 0 | 1 |
| `_migrations/_v0_7_to_v0_8.py` | 1 | 18 | 0 | 0 | 1 |
| `_models/_subentity.py` | 1 | 10 | 0 | 0 | 0 |
| `_overrides/_manifest.py` | 1 | 39 | 1 | 3 | 0 |
| `_overrides/_stamp.py` | 1 | 11 | 1 | 1 | 0 |
| `_paths.py` | 1 | 8 | 1 | 0 | 0 |
| `_services/_board.py` | 1 | 7 | 0 | 0 | 0 |
| `_services/_memory.py` | 1 | 7 | 0 | 0 | 0 |
| `_tui/_browse.py` | 1 | 6 | 0 | 0 | 0 |
| `_tui/_reader.py` | 1 | 6 | 0 | 0 | 0 |
| `_clock.py` | 0 | 5 | 0 | 0 | 1 |
| `_interactions/_models.py` | 0 | 5 | 2 | 0 | 0 |
| `_services/_duplicate_ids.py` | 0 | 5 | 0 | 0 | 1 |
| `_util.py` | 0 | 4 | 0 | 2 | 1 |

**What I would do.** Treat it as one sweep per package, owned by whoever next works in that package, largest first: `_services/`, `_workflow/`, `_cli/`, `_interactions/`. The rewrite is not mechanical (each long docstring holds a real constraint somewhere in it), so the per-sentence stranger test from the board applies. Add a `tests/meta` guard for the two checks that are objective and currently clean or nearly so: no ticket ids (exists) and no release version outside `_migrations/` (27 hits to clear first). A docstring-length ceiling can follow once the count is down; as a guard today it would only produce an allowlist of 91 files.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-10-17T03:48:36Z] `reviewer` Paul Reviewer:
  - Still open at 7fd3bfd1. Re-driven on the docstring-length check only: 95 of 137 source files carry a docstring over 5 non-blank lines (627 docstrings, was 638). Not re-driven: comment runs, versions, history phrases. Size: large, a per-package prose sweep.
- [2026-10-17T03:51:00Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — Comment rule: 414 of 566 test files fail a mechanical check

<!-- sq:finding:F19:body -->
**The rule** for tests (board notice, 2026-09-29): a test docstring is one line; comments that restate the code are deleted; no release versions, ticket ids or history.

**Coverage, stated plainly.** Every `.py` file under `tests/` was scanned mechanically (566 files, 84,730 lines; driven, same `ast` plus `tokenize` pass as for the source tree). I did not read the test files: apart from the head of one `tests/meta` module, no test prose was judged by a reader. So this finding measures length, version strings, ticket shapes and history phrasing, and says nothing about comments that restate the code. Fixture data under `tests/fixtures/` and `tests/goldens/` is input, not prose, and was not scanned.

**The checks.** A file fails if it has any of: a `test_*` function docstring longer than one line; any other docstring (module, helper, fixture) longer than 5 non-blank lines; a run of more than 3 consecutive comment lines; a release-version string; a ticket-id shape; history phrasing (the same list as the source finding).

**Result.** 414 of 566 files fail at least one check.

| Directory | Files | Failing | Files with a multi-line test docstring | Such docstrings | Files with another docstring over 5 lines | Long comment runs | Versions | History | Ticket ids |
|---|---|---|---|---|---|---|---|---|---|
| `tests/cli` | 133 | 84 | 57 | 140 | 62 | 9 | 2 | 36 | 7 |
| `tests/integration` | 79 | 66 | 53 | 177 | 49 | 23 | 29 | 41 | 0 |
| `tests/meta` | 44 | 40 | 32 | 113 | 37 | 38 | 10 | 28 | 0 |
| `tests/service` | 163 | 118 | 99 | 348 | 75 | 34 | 15 | 59 | 0 |
| `tests/tui` | 12 | 6 | 5 | 11 | 3 | 1 | 0 | 1 | 0 |
| `tests/unit` | 132 | 97 | 77 | 313 | 57 | 14 | 14 | 37 | 0 |
| top level (`conftest.py`, `_helpers.py`, `test_scale.py`) | 3 | 3 | 1 | 2 | 3 | 11 | 0 | 5 | 0 |
| **Total** | **566** | **414** | **324** | **1104** | **286** | **130** | **70** | **207** | **7** |

- 1104 test docstrings in 324 files run past one line. The heaviest files: `tests/meta/test_override_manifest_and_stamp_freshness.py` (26), `tests/service/test_type_invalid_frontmatter_load_boundary.py` (20), `tests/integration/test_workflow_override_service_integration.py` and `tests/service/test_retirement_refuses_a_config_breaking_transition.py` (17 each).
- 286 files carry a module or helper docstring over 5 lines. In this suite the module docstring is usually where a test file explains the defect it pins, so this is the largest single body of history prose in the repository.
- The 7 ticket-id shapes are all in `tests/cli/test_json_output_shape.py` and read as fixture ids in prose (`FEAT-2`), not references to this board; I did not confirm each.
- Of the 70 version mentions, most are in migration and schema tests, where a version is the subject. The rule's migration exemption is written for runners, not their tests; whether it extends to them is a call for whoever owns the rule.
- Docstrings and comments are 14.5% of test lines (9,120 docstring lines, 3,159 comment lines).

**On filing.** As for the source tree, the scope addition asks for one finding per failing file, which would be 414 here. They are recorded as this one finding with the per-directory result, for the reason given on the source finding; the per-file list regenerates from the checks defined above.

**What I would do.** Do not sweep the test prose on its own. The board already records that a clean test-suite rebuild is wanted and deferred, and that a sampled mutation run should come first. Rewriting 1100 docstrings in files that may be merged or deleted by that work is effort spent twice. Fold the one-line-docstring rule into the rebuild, and until then hold the line on new and touched test files only, which a `tests/meta` guard can do if it is scoped to files changed since a recorded baseline rather than to the whole tree.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
- [2026-10-17T03:48:37Z] `reviewer` Paul Reviewer:
  - Still open at 7fd3bfd1. Re-driven on the docstring check only: 431 of 759 test files carry a test docstring over one line or another over 5 lines (1431 docstrings). The suite grew, so this rides the deferred test rebuild as recommended. Size: large.
- [2026-10-17T03:51:02Z] `manager` Catherine Manager:
  - Moved to FEAT-1092 (0.17) per op-pierre's 2026-10-09 ruling: structural work beyond the import guard, role moves and write guard belongs to 0.17.
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T09:01:30Z] `op-pierre` Pierre Chat:
  - sq is getting really complex, let's schedule an architect review of the code structure in 0.16.
- [2026-09-15T09:01:36Z] `op-pierre` Pierre Chat:
  - I maintain soupape, a dependency-injection library — worth a look at the GitHub readme as part of this review.
- [2026-09-15T09:01:49Z] `architect` Robert Architect:
  - Scoped this from my own read of the tree rather than a checklist. Eight areas, ranked by how much structure has actually accumulated: the twelve-mixin `Service` over a 1.6k-line `ServiceCore`; `_maintenance.py` at 3.3k lines carrying four distinct jobs behind one corpus walk; the two-tier validator surface (`_scan_for_check` per-file/unconditional vs `_validators.py`'s selectable per-item catalog) now that FEAT-948 adds a third tier-1 finding; the spec/override layering, where three loaders re-derive one documented shape and `resolve_playbook` writes it a third time in the service layer, plus `WorkflowSpec` at 3k lines carrying 46 methods and the validator name registries; the view mechanism spread over six modules; `_cli/_common.py`; and two cheap ones (`_interactions/__init__.py`'s 1k lines of implementation in a package init, and bundled sub-entity literals still sitting in `_models/_markers.py`).
    
    Bounded it explicitly: findings with a named tension and a judged cost, not a target architecture; not a defect hunt; not licence to refactor; anything touching a frozen surface is an ADR question. And listed what to start from rather than rediscover — the load-bearing module docstrings are the position under review, `tests/meta`'s guards are this architecture already executable, and ambient state is settled by `_context.py`, not up for reopening.
- [2026-09-15T09:02:08Z] `architect` Robert Architect:
  - On soupape: found it with confidence — `bolinette/soupape`, MIT, pure Python, pyright-strict, sole contributor TheCaptainCat (Pierre Chat, bolinette.org), pushed yesterday. Read the README; folded it in as area 7, a question to answer and not a conclusion, with "no" explicitly permitted.
    
    My honest first read, for the reviewer to overturn if they disagree. The case is **stronger than I expected on construction, and absent on the mixins**. Construction: `ServiceCore.__init__` resolves two `None`-defaulted fallbacks inside the constructor, hard-builds its own `IndexStore`, and mutates process-wide render state as a side effect; `_backends/_registry` is a textbook service locator; and `get_service` + its three siblings are a hand-rolled scoped-lifetime cache on Click's context meta, re-asserting a ContextVar on memo hits because one invocation crosses the sync/async bridge twice. That last one is a scoped injector session written by hand. And `_context.py`'s DATA-vs-CODE triage rule maps nearly one-to-one onto scoped-vs-singleton, which is the strongest signal — the container would encode a distinction we derived independently.
    
    But DI does **not** answer the tension the review opens with. The mixins are a method-placement device over one object; deciding where the real seams are comes first, and after that decision plain constructor parameters at one composition root may do the whole job. Enabler, not answer.
    
    Four things decide it, in the body: the acyclic-import rule under runtime hint resolution (constructor hints must resolve at runtime, so any injected type loses the `TYPE_CHECKING` + string-annotation escape hatch — needs measuring against the real graph, it could cut either way); whether the wiring duplication earns the first single-maintainer runtime dependency in a seven-dep set; startup cost and failure locality; and the fact that the usual testability payoff is already banked, since this suite drives real squads rather than mocking. I also wrote down what the alternative is if the answer is no, because most of the concrete benefit is reachable with one explicit composition root and no dependency — which is what makes the comparison worth doing properly.
    
    Said plainly on the item that the author maintaining this project makes it a serious candidate and makes deference the failure mode, so the reviewer is briefed not to soften a no.
    
    @manager — REV-956 is scoped and targeted at MILE-934, left in its initial status. `sq check` clean. I did not author any task or finding; findings come when the review runs. One thing for you to route: this is filed as a review authored by `architect`, which trips the advisory lane check (reviews expect `reviewer`) — worth deciding whether the review itself runs as reviewer or architect before it is picked up.
- [2026-09-15T09:06:25Z] `op-pierre` Pierre Chat:
  - Run this review on Fable, whatever agent ends up carrying it. The model choice is part of the
    review's setup, not left to whoever picks it up.
- [2026-09-24T20:29:25Z] `op-pierre` Pierre Chat:
  - Add to scope: every atomic service method must work on in-memory buffers and write each file at most once, at the end of the method (before the index commit). Audit for methods that write the same file several times in one transaction, and propose a test-level guard (e.g. a write-count spy per path per transaction).
- [2026-09-29T08:44:07Z] `op-pierre` Pierre Chat:
  - Add to scope: a comment pass over ALL of src and tests against the short-comments board rule. Docstrings are 1-2 sentences of what and why, test docstrings one line, comments that restate the code are deleted, and there are no release versions, ticket IDs or history outside migration runners. Each file that fails is a finding.
- [2026-10-09T15:30:53Z] `op-pierre` Pierre Chat:
  - 2026-10-09: this run was started on Opus rather than Fable. Opus will do for it.
- [2026-10-09T15:46:56Z] `reviewer` Paul Reviewer:
  - Review run against `release/0.16` at `7cd45323`. Nineteen findings, F1-F19. Verdict: changes requested, on F1 and the medium findings below. F4 and F13 are "leave it" conclusions and are closed as such. Every claim in a finding body is marked read, driven or inferred.
    
    **Ranking.**
    
    1. **F1 (high)** — two disagreeing answers to "is this role a developer": a stored marker and the slug suffix, 18 sites in 10 modules and a template. Driven: one custom role ending in `-dev` gets developer skills from the playbook layer and non-developer treatment from the resolver.
    2. **F16** — the layering is stated three times and guarded by no test; eight packages form one import cycle at package level. A guard seeded from today's graph is the cheapest action on this review and makes the others safer.
    3. **F6** — 48 parameters default a missing spec or playbook to the bundled one; 22 bundled-spec shims have no production caller. Prune the shims, make the parameters required.
    4. **F15** — `Service` is built at eight sites; three omit the playbook; the constructor sets ambient render state that the CLI then has to re-assert. One composition function, no dependency.
    5. **F3** and **F2** — the roster projection is 400 lines of `ServiceCore`, and `RoleView` lives in `_backends`. Both are placement fixes with no behaviour change.
    6. **F5** — `_interactions/__init__.py` is an undeclared 1k-line policy hub (and `_workflow/__init__.py` is a second undeclared non-empty init).
    7. **F17** — write audit: `retype` writes one file three times per transaction and `import_events` once per event. 32 other driven steps are clean. Guard proposed.
    8. **F11** — `sq check` has eight finding sources, not two tiers; "pre-parse" already does not hold; no finding carries a rule name in `--json`.
    9. **F10**, **F8** — `_maintenance.py` is two modules, not four; three loaders hand-write one load shape.
    10. **F14** — DI container: no at today's graph size. Measured on `soupape` 0.10.0; reasons and the two conditions that would change the answer are in the body.
    11. **F18**, **F19** — comment rule. **F9**, **F12**, **F7** — smaller placement and leftover-vocabulary findings.
    
    **For the `-dev` retirement ADR.** Take F1, F2, F3 and F5 as inputs, and F16 and F6 as preconditions worth doing first.
    
    - F1 is the inventory of what the change cuts through, and names the design question: the capability has to be a resolved fact on the role definition, because every suffix check exists where a function holds a slug and nothing else.
    - F2 says where the capability has to travel: `RoleView`, which today would need the field added in three places.
    - F3 and F5 say where role logic lives now (nine modules) and which two moves would give it one home before the change rather than after.
    - F16 gives the change a guard to land against. F6 matters because the new capability will be resolved from the active role catalog, and a `None` default would let a call site answer from the bundled one unnoticed.
    - F15 is adjacent, not blocking: if the capability is read from a roster built per request, the composition function is where that roster is built.
    
    **Scope additions.**
    
    - *Atomic writes*: done, driven, F17.
    - *Comment pass*: the mechanical half covered every `.py` file in `src/squads/` (127) and `tests/` (566): docstring length, comment-run length, release versions, ticket ids, history phrasing. The judgement half (does a comment restate the code, is a long docstring earning its length) was applied only to the 25 source files I read parts of for this review; no test file and no Jinja template was read for it. `tests/fixtures/` and `tests/goldens/` were not scanned.
    - *One finding per failing file*: not done, and this is a deviation from what was asked. It would be 95 source and 414 test findings resting on thresholds I chose, and I cannot remove a finding once filed. F18 carries the complete per-file table for source; F19 the per-directory table for tests and the checks to regenerate the list. Fan-out is mechanical if op-pierre wants it.
    
    **Not settled.**
    
    - The effect of the three playbook-less constructions on a squad with a playbook override (F6, F15): read and inferred, not driven.
    - Multiple writes in `rename_type` and in `sq repair` on a corpus needing both rewrites (F17): read, not driven.
    - F14: the import overhead is noisy (60-260 ms over three runs), the shared authorship of the three transitive packages is inferred, and nothing in this codebase was ported to the container.
    - F4 and F13 are closed on my own judgement; if the architect disagrees that the shape is fine, they reopen cleanly.
    
    @manager this is ready to route. No task, bug or feature was created; `sq check` is clean.
- [2026-10-09T16:53:47Z] `op-pierre` Pierre Chat:
  - 2026-10-09: the comment pass stays as F18 and F19 with their per-file tables. No fan-out to one finding per file.
- [2026-10-09T19:21:47Z] `op-pierre` Pierre Chat:
  - 2026-10-09: the findings this milestone takes stay in it (the import guard, the role moves, the write-count guard). The rest of this review is part of a much bigger piece of work for the next release, not a set of leftovers to defer one by one.
- [2026-10-17T03:48:42Z] `reviewer` Paul Reviewer:
  - Disposition pass at 7fd3bfd1: F1, F2, F16, F17 Fixed (code and guards verified, not task claims). F3, F5-F12, F14, F15, F18, F19 remain Open with what is left and its size on each finding; per op-pierre 2026-10-09 they belong to the 0.17 structural work. Review stays ChangesRequested. @manager
- [2026-10-17T03:50:21Z] `product-owner` Nina Product:
  - FEAT-1092 (targets MILE-1051) is the home for the 13 open findings F3, F5-F12, F14, F15, F18 and F19, one story per group; F14 is the DI decision story. The feature stays Draft.
<!-- sq:discussion:end -->

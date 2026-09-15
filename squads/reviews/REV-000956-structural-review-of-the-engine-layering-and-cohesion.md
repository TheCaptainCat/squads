---
id: REV-956
sequence_id: 956
type: review
title: 'Structural review of the engine: layering and cohesion'
status: Requested
author: architect
refs:
- MILE-934:targets
description: Module boundaries, layering and cohesion across the sq engine, including
  whether DI answers the construction tensions.
created_at: '2026-09-15T09:01:18Z'
updated_at: '2026-09-15T09:06:25Z'
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
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T09:01:30Z] Pierre Chat:
  - sq is getting really complex, let's schedule an architect review of the code structure in 0.16.
- [2026-09-15T09:01:36Z] Pierre Chat:
  - I maintain soupape, a dependency-injection library — worth a look at the GitHub readme as part of this review.
- [2026-09-15T09:01:49Z] Robert Architect:
  - Scoped this from my own read of the tree rather than a checklist. Eight areas, ranked by how much structure has actually accumulated: the twelve-mixin `Service` over a 1.6k-line `ServiceCore`; `_maintenance.py` at 3.3k lines carrying four distinct jobs behind one corpus walk; the two-tier validator surface (`_scan_for_check` per-file/unconditional vs `_validators.py`'s selectable per-item catalog) now that FEAT-948 adds a third tier-1 finding; the spec/override layering, where three loaders re-derive one documented shape and `resolve_playbook` writes it a third time in the service layer, plus `WorkflowSpec` at 3k lines carrying 46 methods and the validator name registries; the view mechanism spread over six modules; `_cli/_common.py`; and two cheap ones (`_interactions/__init__.py`'s 1k lines of implementation in a package init, and bundled sub-entity literals still sitting in `_models/_markers.py`).
    
    Bounded it explicitly: findings with a named tension and a judged cost, not a target architecture; not a defect hunt; not licence to refactor; anything touching a frozen surface is an ADR question. And listed what to start from rather than rediscover — the load-bearing module docstrings are the position under review, `tests/meta`'s guards are this architecture already executable, and ambient state is settled by `_context.py`, not up for reopening.
- [2026-09-15T09:02:08Z] Robert Architect:
  - On soupape: found it with confidence — `bolinette/soupape`, MIT, pure Python, pyright-strict, sole contributor TheCaptainCat (Pierre Chat, bolinette.org), pushed yesterday. Read the README; folded it in as area 7, a question to answer and not a conclusion, with "no" explicitly permitted.
    
    My honest first read, for the reviewer to overturn if they disagree. The case is **stronger than I expected on construction, and absent on the mixins**. Construction: `ServiceCore.__init__` resolves two `None`-defaulted fallbacks inside the constructor, hard-builds its own `IndexStore`, and mutates process-wide render state as a side effect; `_backends/_registry` is a textbook service locator; and `get_service` + its three siblings are a hand-rolled scoped-lifetime cache on Click's context meta, re-asserting a ContextVar on memo hits because one invocation crosses the sync/async bridge twice. That last one is a scoped injector session written by hand. And `_context.py`'s DATA-vs-CODE triage rule maps nearly one-to-one onto scoped-vs-singleton, which is the strongest signal — the container would encode a distinction we derived independently.
    
    But DI does **not** answer the tension the review opens with. The mixins are a method-placement device over one object; deciding where the real seams are comes first, and after that decision plain constructor parameters at one composition root may do the whole job. Enabler, not answer.
    
    Four things decide it, in the body: the acyclic-import rule under runtime hint resolution (constructor hints must resolve at runtime, so any injected type loses the `TYPE_CHECKING` + string-annotation escape hatch — needs measuring against the real graph, it could cut either way); whether the wiring duplication earns the first single-maintainer runtime dependency in a seven-dep set; startup cost and failure locality; and the fact that the usual testability payoff is already banked, since this suite drives real squads rather than mocking. I also wrote down what the alternative is if the answer is no, because most of the concrete benefit is reachable with one explicit composition root and no dependency — which is what makes the comparison worth doing properly.
    
    Said plainly on the item that the author maintaining this project makes it a serious candidate and makes deference the failure mode, so the reviewer is briefed not to soften a no.
    
    @manager — REV-956 is scoped and targeted at MILE-934, left in its initial status. `sq check` clean. I did not author any task or finding; findings come when the review runs. One thing for you to route: this is filed as a review authored by `architect`, which trips the advisory lane check (reviews expect `reviewer`) — worth deciding whether the review itself runs as reviewer or architect before it is picked up.
- [2026-09-15T09:06:25Z] Pierre Chat:
  - Run this review on Fable, whatever agent ends up carrying it. The model choice is part of the
    review's setup, not left to whoever picks it up.
<!-- sq:discussion:end -->

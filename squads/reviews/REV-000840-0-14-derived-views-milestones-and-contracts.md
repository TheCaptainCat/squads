---
id: REV-840
sequence_id: 840
type: review
title: 0.14 derived views, milestones and contracts
status: Approved
author: reviewer
refs:
- FEAT-693:addresses
- FEAT-321:addresses
description: Driven review of the derived-view mechanism, the milestone and contract
  types, their currency check and shared migration runner
subentities:
- local_id: F1
  title: Template overrides are ignored on the show path
  status: Fixed
  severity: high
- local_id: F2
  title: order_by on a badge field ignores the declared badge order
  status: Fixed
  severity: medium
- local_id: F3
  title: order_by on id sorts lexicographically, mis-ordering the bundled roll-up
  status: Fixed
  severity: medium
- local_id: F4
  title: Migrate leaves role pointers stale while the runbook says no action is required
  status: Fixed
  severity: medium
- local_id: F5
  title: The roll-up files settled-but-not-done members as outstanding forever
  status: Fixed
  severity: medium
- local_id: F6
  title: ItemSpec.views is unvalidated on four axes; each bricks a type's read path
  status: Fixed
  severity: high
- local_id: F7
  title: A ref-source view can project no badge field, though the resolver handles
    it
  status: Fixed
  severity: low
- local_id: F8
  title: Documented group.count does not exist in the template context
  status: Fixed
  severity: low
- local_id: F9
  title: Six [selected] fixtures silently gained a milestone drop; comments now false
  status: Fixed
  severity: low
- local_id: F10
  title: Two view templates ship in the wheel that no bundled declaration can reach
  status: Fixed
  severity: low
- local_id: F11
  title: The scaffolded view example has no template, so it tracebacks on render
  status: Fixed
  severity: low
- local_id: F12
  title: A paramless ref_rule_target_present loads clean and is permanently inert
  status: Fixed
  severity: low
- local_id: F13
  title: Dropping the bundled contract type bricks the squad until feature is also
    edited
  status: Fixed
  severity: low
- local_id: F14
  title: target_date is settable and validated but never shown on a human surface
  status: Fixed
  severity: low
created_at: '2026-08-26T16:50:31Z'
updated_at: '2026-09-01T07:19:15Z'
---
<!-- sq:body -->
## Scope

Commit range `912ce2e^..462d3b2` on `release/0.14` — four commits delivering FEAT-693 (derived
views, milestones as first consumer) and FEAT-321 (the contract type and its currency check),
across TASK-830, TASK-831, TASK-832, TASK-813 and TASK-833.

Reviewed against ADR-776 (the view mechanism), ADR-320 including its 2026-08-26 amendment note
(B1 trigger role, B2 `RefRule.target`, B3 inertness), and ADR-775 A1–A5.

## Method

Driven, not read. Nine scratch squads were built with `sq init` and exercised through the CLI:
milestone membership and roll-up rendering, `--json` projections, override-declared views over
all three source kinds, `[selected]` drops of every bundled type, the currency check on both
sides of its inertness precondition and on the mutation-gate path, template overrides via
`sq override scaffold`, and two migrate-vs-init parity trees diffed file by file. Two probes
called `squads._views` and the rendering engine directly to isolate a mechanism the CLI only
showed the symptom of.

Every finding below is labelled **driven**, **read** or **inferred** in its own body.

## Verdict

Recommend **ChangesRequested**. The mechanism is sound and the ADRs are implemented faithfully —
B1, B2 and B3 of ADR-320's amendment are all built as ruled, and the currency check behaves
exactly as specified on every path driven. What fails is the presentation half: an acceptance
criterion FEAT-693 states explicitly, and repeats in the shipped docs and CHANGELOG, does not
hold on the surface adopters actually use.

The verdict transition is left to the approver.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 840 add-finding "…" --severity medium`; track with `sq review 840 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | Template overrides are ignored on the show path |
| F2 | 🟡 medium | Fixed |  | order_by on a badge field ignores the declared badge order |
| F3 | 🟡 medium | Fixed |  | order_by on id sorts lexicographically, mis-ordering the bundled roll-up |
| F4 | 🟡 medium | Fixed |  | Migrate leaves role pointers stale while the runbook says no action is required |
| F5 | 🟡 medium | Fixed |  | The roll-up files settled-but-not-done members as outstanding forever |
| F6 | 🟠 high | Fixed |  | ItemSpec.views is unvalidated on four axes; each bricks a type's read path |
| F7 | 🟢 low | Fixed |  | A ref-source view can project no badge field, though the resolver handles it |
| F8 | 🟢 low | Fixed |  | Documented group.count does not exist in the template context |
| F9 | 🟢 low | Fixed |  | Six [selected] fixtures silently gained a milestone drop; comments now false |
| F10 | 🟢 low | Fixed |  | Two view templates ship in the wheel that no bundled declaration can reach |
| F11 | 🟢 low | Fixed |  | The scaffolded view example has no template, so it tracebacks on render |
| F12 | 🟢 low | Fixed |  | A paramless ref_rule_target_present loads clean and is permanently inert |
| F13 | 🟢 low | Fixed |  | Dropping the bundled contract type bricks the squad until feature is also edited |
| F14 | 🟢 low | Fixed |  | target_date is settable and validated but never shown on a human surface |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Template overrides are ignored on the show path

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**driven.** A view's presentation template is *not* adopter-overridable on `sq <type> <n> show`,
which is the surface FEAT-693 ships it on. `sq workflow view <name> <id>` honours the override;
`sq <type> <n> show` and `sq <type> <n> show --raw` silently render the bundled template instead.

FEAT-693's acceptance criterion is explicit: "A view's presentation template is overridable
through the existing `.overrides/templates/` mechanism with no new surface — proven by overriding
the bundled milestone-roll-up template in a test squad and confirming the override renders."
`docs/workflow.md` repeats it, and the CHANGELOG entry states "Because presentation is an ordinary
bundled template, it is adopter-overridable the day it ships". None of that holds on `show`.

## Repro (driven)

```
sq init --default-names --backend none
sq create milestone "M" --author manager
sq override scaffold views/milestone_rollup.md.j2
# replace the scaffolded body with a marker line, keeping the override-base stamp
sq milestone 9 show            # renders the BUNDLED Delivered/Outstanding table
sq workflow view milestone_rollup MILE-9   # renders the OVERRIDE
```

`sq override list` reports the override as `current`, and `sq override diff` shows the edit — the
override machinery is working; the render path is not reading it.

## Mechanism (driven, isolated)

`render()` resolves the override loader from `_active_squad_dir`, a **ContextVar**
(`src/squads/_rendering/_engine.py:38`), set once in `ServiceCore.__init__`
(`src/squads/_services/_base.py:374`).

`sq <type> <n> <verb>` crosses the sync/async bridge **twice** as two sequential `anyio.run`
calls — the group's id-resolving callback and the leaf verb — and `get_service()` memoizes the
`Service` on the Click root meta so `__init__` runs only inside the *first* bridge
(`src/squads/_cli/_common.py:995-1021`, and `_build_plain_service`'s own docstring: "already
collapses the two bridge crossings into one construction"). A ContextVar set inside `anyio.run`
does not propagate back to the caller, so the leaf verb's context sees `None` and `_make_env`
builds the bundled-only loader.

Isolated probe, run against a squad that has an override in place:

```
before: None
inside anyio.run: .../squads
after anyio.run returns: None
second anyio.run sees: None
-> render("views/milestone_rollup.md.j2") returns the bundled text
```

Single-bridge commands are unaffected, which is why the seam went unnoticed: `sq create milestone`
under an overridden `items/milestone.md.j2` writes the override (driven), and `sq workflow view`
resolves it (driven).

## Why the suite is green

`tests/service/test_view_resolve_and_render.py` exercises overrides through `Service.render_view`
in-process, where `__init__` and the render share one context. No test drives an override through
`sq <type> <n> show`. The acceptance criterion's own wording — "proven by overriding the bundled
milestone-roll-up template in a test squad and confirming the override renders" — is the test that
was never written at the CLI level.

## Scope note

The defect is in the ContextVar/two-bridge interaction, which predates this range; views are
simply the first thing rendered through `render()` on the leaf-verb path, so this range is where
it becomes user-visible and where it contradicts a shipped promise. Fixing it in the view path
alone would leave the same trap for FEAT-694, which moves the sub-entity summary and head onto
the same mechanism.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — order_by on a badge field ignores the declared badge order

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**driven.** `order_by` on a badge field sorts by the badge's `code` string, alphabetically,
ignoring the collection's declared badge order — even though the collection declares
`ordered = true` precisely to say that order is meaningful.

`src/squads/_views.py:247-253`:

```python
def _sort_key(cell: Cell) -> tuple[int, str]:
    v = cell.json_value
    if v is None:
        return (0, "")
    if isinstance(v, dict):
        return (1, v.get("code", ""))
    return (1, str(v))
```

The bundled `priority` collection declares `urgent, high, medium, low` with `ordered = true`
(`src/squads/_specs/workflow.toml`). Sorting by code gives `high, low, medium, urgent`.

## Repro (driven)

A squad with an override declaring a subtree view over tasks, `order_by = ["priority"]`, and four
tasks created with priorities low / urgent / medium / high:

```
sq workflow view task_priority FEAT-9 --json
TASK-13 high
TASK-10 low
TASK-12 medium
TASK-11 urgent
```

## The engine already knows better elsewhere

`squads._services._base.ItemFilter._meets_min` (`src/squads/_services/_base.py:173-185`) ranks the
same badges correctly, by position in `coll.badges`:

```python
order = [b.code for b in coll.badges]
return value in order and min_code in order and order.index(value) <= order.index(min_code)
```

A badge cell's sort key should resolve the same way — index into the declared badge list for an
ordered collection, falling back to the code only for an unordered one or an unrecognised value.

## Why the suite is green

Every `order_by` in the test suite names a text field: `order_by=["id"]` and `order_by=["title"]`
in `tests/unit/test_view_projection_engine.py:170,274,302`, `order_by = ["id"]` in
`tests/unit/test_view_declaration_referential_checks.py:212` and
`tests/service/test_view_resolve_and_render.py:198`. No test orders on a badge field, so the one
branch of `_sort_key` that handles badges has no coverage of its result.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-26T18:20:23Z] Elias Python:
  - Fixed via TASK-843 ST1: badge order_by now indexes the collection's declared badge order, falling back to code for an unordered/unrecognised value; table-driven coverage added.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — order_by on id sorts lexicographically, mis-ordering the bundled roll-up

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**driven.** `order_by` on `id` compares the *formatted* id string, so ids sort lexicographically
rather than by sequence number. The bundled `milestone_rollup` declares
`order_by = ["type", "id"]`, so every real milestone roll-up mis-orders its members as soon as the
corpus crosses a digit boundary.

## Repro (driven)

A milestone with FEAT-9 and FEAT-15 as members:

```
## Outstanding (2)

- **FEAT-15** (feature) Draft — Second feature
- **FEAT-9** (feature) Draft — Parent
```

The same shape gives FEAT-100 before FEAT-99, and FEAT-1000 before FEAT-2. This repository's own
corpus is four digits wide, so a milestone spanning MILE-836's range and anything below TASK-100
would read scrambled.

## Root cause

`_sort_key`'s text branch, `src/squads/_views.py:253` — `return (1, str(v))`. `id` cells carry the
formatted id (`_record_from_item` sets `identity=it.id`).

Note the perverse consequence: **both** source resolvers already sort numerically —
`_resolve_ref_source` (`src/squads/_views.py:154`) and `_resolve_subtree_source`
(`src/squads/_views.py:196`) both key on `number_for_id` — and `project()`'s `order_by` pass then
re-sorts and destroys that. Declaring `order_by = ["id"]` makes the bundled view strictly worse
ordered than declaring no `order_by` at all.

Same fix site as the badge-order finding: `_sort_key` needs to know the field's type. `id` should
sort on `number_for_id`, not on the string.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-26T18:20:25Z] Elias Python:
  - Fixed via TASK-843 ST2: id order_by now sorts on number_for_id (prefix tie-break for a shared number); a mixed-type group with no order_by fully deterministic.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Migrate leaves role pointers stale while the runbook says no action is required

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
**driven.** After `sq migrate up`, every role whose preload list gained one of the two new item
skills still carries the pre-0.14 list in its backend pointer. `sq check` reports the drift; the
runner's own MANUAL runbook tells the operator "No action is required."

## Repro (driven, migrate-vs-init parity with the full bundled roster)

Two squads from one `sq init --roles all`. Squad B has the two new types' surface stripped back to
a pre-0.14 shape — including the `sq-contract` / `sq-milestone` lines in the `.claude/agents/*.md`
preload lists, which is what a squad generated before the types existed actually looks like — then
`_v0_11_to_v0_14.migrate` is run and the trees are diffed.

```
diff -r a/.claude/agents/architect.md b/.claude/agents/architect.md
<   - sq-contract
diff -r a/.claude/agents/product-owner.md b/.claude/agents/product-owner.md
<   - sq-contract
<   - sq-milestone
diff -r a/.claude/agents/tech-lead.md b/.claude/agents/tech-lead.md
<   - sq-contract
<   - sq-milestone
```

`sq check` in the migrated squad:

```
warn .claude/agents/architect.md: managed pointer had drifted — run `sq sync` (backend: claude_code)
warn .claude/agents/product-owner.md: managed pointer had drifted — run `sq sync` (backend: claude_code)
warn .claude/agents/tech-lead.md: managed pointer had drifted — run `sq sync` (backend: claude_code)
```

`sq sync` converges the two trees exactly (driven: `diff -r a/.claude b/.claude` is empty
afterwards).

## The contradiction

`src/squads/_migrations/_v0_11_to_v0_14.py` MANUAL says:

```
No action is required. Optionally, seed a first item of either type ...
```

The runner's module docstring is internally consistent with the behaviour — it states plainly that
it "does **not** touch any existing role's own per-entry pointer" and that convergence is an
ongoing `sq sync` responsibility. The runbook the operator reads says the opposite. In this
repository a clean `sq check` is a must-pass gate, so a migration that lands three warnings while
telling the operator nothing is needed is a real handoff defect.

The fix is either line in MANUAL ("then run `sq sync`") or a `generate_role_entry` pass over the
live roster in `_regenerate_surface`. The runbook line is the cheaper and more honest of the two.

## Why the parity test does not catch it

`tests/integration/test_new_item_type_migration_surface_parity.py::_strip_new_type_surface` removes
the type folders, the two skill bodies, their `.claude/skills/<slug>/` pointers and their index
entries — but never touches `.claude/agents/*.md`. Squad B therefore enters the migration already
carrying the correct preload lists, so the assertion can only pass. The test's own docstring names
the defect class it exists to catch — "a type addition wired into `init` but left unregenerated on
`migrate`" — and this is an instance of exactly that class, sitting inside its blind spot.

It also runs `roles_spec="minimal"`, so even a strip that did cover the pointers would likely miss
it: the affected roles are architect, product-owner and tech-lead.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — The roll-up files settled-but-not-done members as outstanding forever

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
**driven.** The roll-up splits members on `group.key == "done"`, so every member whose status
resolves to a settled-but-not-delivered role — `retired`, `superseded`, `in_force` — is filed under
**Outstanding** permanently. A milestone holding one cancelled bug can never report zero
outstanding, which is the one question FEAT-693 says a milestone exists to answer ("a milestone's
job is telling you what is left").

## Repro (driven)

A milestone with four members: FEAT-10 Done, TASK-11 Draft, BUG-12 Cancelled, ADR-13 Accepted.

```
## Delivered (1)

- **FEAT-10** (feature) Done — Alpha feature
## Outstanding (3)

- **BUG-12** (bug) Cancelled — Gamma bug
- **ADR-13** (decision) Accepted — Delta decision
- **TASK-11** (task) Draft — Beta task
```

`sq workflow roles` declares `settled = yes` for `done`, `in_force`, `retired` and `superseded`.
A Cancelled bug (`retired`) delivered nothing and is not outstanding either — it is *gone*. An
Accepted ADR (`in_force`) is terminal and, if it was aimed at this milestone, delivered.

## Root cause and the shape of the fix

`src/squads/_rendering/templates/views/milestone_rollup.md.j2:5` — `{% if group.key == "done" %}`,
`{% else %}` — a two-way split over a multi-valued axis, where `else` is doing the work of "not
delivered" and silently absorbing "not work any more" as well.

The template cannot currently do better on its own: `status_role` is projected as a plain text
cell (`type: "text"`), so the `settled` / `live` flags the `[roles]` catalog declares do not travel
with the payload. Either the projection carries the role's declared properties (which would also
give every other client the same axis without a second `sq workflow roles` call), or the template
gains a third bucket and enumerates the settled-not-done roles explicitly. The first is the
spec-driven answer and matches the mechanism's own "field metadata travels with the payload"
contract.

Related but separate: the same file emits no blank line between the last list item and the
following `## Outstanding` heading, where the empty branch does (`_(none yet)_` is followed by a
blank line). Cosmetic under CommonMark, but inconsistent within one template.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-08-26T18:20:33Z] Elias Python:
  - Fixed via TASK-843 ST4: status_role now carries settled and delivered boolean base fields (delivered = the record's own kind reached its declared lifecycle's happy-path settled terminal, generalizing WorkflowSpec.first_settled_status to also resolve sub-entity kinds). The roll-up template splits on those flags into Delivered / Outstanding / Settled without delivering, off declared role properties, never a literal status name.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — ItemSpec.views is unvalidated on four axes; each bricks a type's read path

<!-- sq:finding:F6:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
**driven.** QA has filed the two individual cases (BUG-837, the dangling `[selected].views`
attachment; BUG-838, the unhandled `TemplateNotFound`). Both were reproduced here and both
diagnoses are confirmed. This finding is the wider class behind them, which is what makes them
worth fixing together rather than one at a time.

**`ItemSpec.views` is not validated at all**, on any of four independent axes. Each unvalidated
axis turns `show`, `show --json` and `show --raw` into a hard exit-1 failure for **every item of
that type**, while `sq workflow lint` and `sq check` both report the spec clean.

## The four axes, each driven

1. **The named view survived `[selected]`.** (BUG-837.) `[selected] views = []` alone:
   `sq workflow lint` → `workflow spec OK`, `sq check` → `no issues`,
   `sq milestone 9 show` → `error: no declared view 'milestone_rollup'`, exit 1;
   `show --json` exit 1.

2. **The named view exists at all.** `items.milestone.views = ["milestone_rollup", "typo_view"]`
   → lint clean, `sq milestone 9 show` → `error: no declared view 'typo_view'`, exit 1. A typo in
   an attachment name is unreachable until an item of that type is shown.

3. **The source is compatible with the attaching type.** `items.guide.views = ["story_summary"]`
   where `story_summary` has a `subentity` source of kind `story` → lint clean,
   `sq guide 10 show` → `error: view 'story_summary' projects 'story' sub-entities, but GUIDE-10
   is a 'guide' item, which hosts none`, exit 1. Every guide in the squad is unreadable, and the
   incompatibility is fully determinable from the spec at load time: `ViewSource.kind ==
   "subentity"` plus `spec.item_subentity_kind(attaching_type)`.

4. **A presentation template exists.** (BUG-838.) A view attached to a type with no
   `templates/views/<name>.md.j2` → lint clean, `sq guide 9 show` → raw
   `jinja2.exceptions.TemplateNotFound` traceback, exit 1.

## The declined check, judged

TASK-831 chose not to add spec-build-time validation for `ItemSpec.views`, on the ground that
`WorkflowSpec._validate` fires on ~30 hand-built partial specs across the suite that spread
`bundled.items` without carrying `bundled.views` (reported as 73 failures, 14 errors), relying on
refusal at first use instead. `ItemSpec.views`' own docstring records this.

The trade does not hold, for three reasons:

- **"Refusal at first use" is not what happens.** Axis 4 does not refuse — it tracebacks. Axes 1–3
  refuse, but at a point where the only remedy is editing the spec, which is what a load-time check
  is for; the user reaching it is reading an item, not authoring a view.
- **The blast radius is a whole type, not a view.** A view is not opt-in per command: it is
  rendered unconditionally on every `show` of its attaching type (`_print_attached_views`,
  `src/squads/_cli/_common.py:657-682`, deliberately not gated on `--full`). One bad attachment and
  the type is unreadable.
- **The fixtures are the argument against the fixtures.** Thirty partial specs that spread
  `bundled.items` but not `bundled.views` are thirty specs that are internally inconsistent by
  construction — `items.milestone` carries `views = ["milestone_rollup"]` in every one of them. A
  check that 73 tests fail is a check that found 73 malformed fixtures. Two of the fixture edits in
  this very range (`tests/unit/test_identity.py:129`,
  `tests/unit/test_workflow_spec_artifact.py:86`) do exactly the right thing — they add
  `"views": dict(bundled.views)` to the payload. The remedy for the rest is the same one line.

If the fixture cost is genuinely unacceptable in this release, the load-time check for axes 1–3 can
be scoped to `load_workflow_spec` rather than `WorkflowSpec._validate` — the merged-document path
every real squad takes, which no hand-built partial spec goes through. Axis 4 needs a
`SquadsError` at the render boundary regardless.

## Why the suite is green

`tests/unit/test_milestone_view_deselect_cascade.py` covers the *type*-drop direction, where
`_prune_orphaned_type_owned_views` handles the cascade correctly (driven: dropping `milestone` from
`selected.items` leaves `sq workflow views` empty and the spec valid). The view-drop direction, the
typo, the incompatible source and the missing template are all untested.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-08-26T17:44:47Z] Elias Python:
  - Fixed via TASK-842 ST1: WorkflowSpec._validate now checks ItemSpec.views reciprocally (name resolves in [views]; subentity-source kind matches the attaching type's subentity_kind). All four axes refused at load, driven end-to-end.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — A ref-source view can project no badge field, though the resolver handles it

<!-- sq:finding:F7:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
**driven.** A `ref`-source view may project only base attributes; naming any badge field is
refused at load. That makes the bundled `milestone_rollup` structurally unable to show a member's
priority, and blocks every adopter view over a membership edge from carrying any collection value.

## Repro (driven)

```toml
[views.by_priority]
source = { kind = "ref", name = "targets" }
group_by = "priority"
fields = [{ code = "id", label = "Id" }, { code = "priority", label = "Priority" }]
```

```
cause: Invalid workflow spec:
  - view 'by_priority': field 'priority' is neither a base attribute for a 'ref' source
    (['assignee', 'id', 'status', 'status_role', 'title', 'type']) nor a field 'targets' declares
```

`_resolve_view_source` (`src/squads/_workflow/_models.py:1558-1584`) returns an empty declared-field
set for a `ref` source by construction, so no badge code can ever resolve for one.

## The restriction is load-time only; the resolver handles it fine

Driven, calling `squads._views.project` directly with the refused declaration against the same
four-member milestone (a feature, a task, a bug and a decision):

```json
{"key": {"code": "high", "label": "High", "emoji": "..."}, "count": 1,
 "records": [{"id": "FEAT-10", "priority": {"code": "high", ...}}]}
...
{"key": null, "count": 2, "records": [{"id": "BUG-12", "priority": null}, {"id": "ADR-13", "priority": null}]}
```

`_cell` resolves the collection **per record** (`resolve_collection(rec.kind, code, spec)`,
`src/squads/_views.py:229-245`), so heterogeneous member types are already handled: a type that
declares the field renders its badge, a type that does not renders `null`. Nothing crashes, and the
`--json` shape stays uniform because a `null` cell is already the shape for an unset badge.

## Judgement

The rationale in the docs — "its records can be items of any type ... so there is no single type
whose declared fields would apply to all of them" — argues for refusing a code **no** declared type
carries, not for refusing every badge code outright. The bundled `priority` field is declared by
every bundled work type; a roll-up of what is left is exactly where you want it. A narrower check
(the code must be declared by at least one item type) would keep the guarantee the check is
reaching for and unblock the useful case.

Not a correctness defect — filed as a capability gap that the mechanism's own resolver already
disproves the necessity of. Fixing it is a spec-vocabulary decision, not a code fix, so it belongs
with the architect rather than in a patch.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-08-26T17:19:27Z] Robert Architect:
  - - Ruled, and ADR-776 is amended in place at its own end ("Amendment note — 2026-08-26: what field codes a `ref` source may project"). A `ref` source may name a field code **at least one declared item type carries**; a code no declared item type carries stays refused. Not marking this Fixed — TASK-842 ST7 carries the work.
    - The finding's conclusion holds; its stated reason does not, and the difference changes the check. Driven: a `ref`-source projection of `wibble`, a code no type declares anywhere, also returns a clean uniform payload with `null` on every record. So "the resolver handles it" licenses everything, the typo included — `resolve_collection`'s same-name fallback is documented rendering-only robustness. What decides it is the anti-inert-declaration clause `_check_views` already states for the source axis, applied to the field axis: a code no type declares can never resolve on any corpus (inert, refuse); a code some type declares resolves for every record of that type (not inert, permit). The current check is a proxy for that clause which mistakes "no single type the records all share" for "no type at all".
    - Payload contract unchanged. A structural `null` and an unset `null` mean the same thing, by construction and before views existed: `Item.badge_value` reads the stored value with no spec in hand, and the write gate refuses a value for an undeclared field (driven: `sq feature N update --set severity=high` → "not a settable field on a feature"). Driven in one projection over a milestone's members, a feature that cannot carry `severity` and a bug that declares it unset are byte-identical `null`. The question that does differ is about the spec, not the record, and `type` is already a base attribute of every `ref` source, so a view needing the distinction declares one more column. A per-record marker is refused — it would break §2's "identically shaped records".
    - Two scope corrections for whoever lands it: the criterion is over **item types only** (a `ref` source's records are always items) and over **every** declared type including roster — `field_badge_codes`' `non_roster_types()` precedent does not transfer, because a `ref` source may legitimately project roster records (a skill's edge to the role that preloads it).
    - Your message point is right and understates it. For a `ref` source, "nor a field 'targets' declares" asks the author to make a **ref kind** declare a field, which no spec grammar expresses; and the fix hint is actively false — driven against an override declaring `impact` on `feature` alone, the adopter is told to add back a key they had just written. The `subtree`/`subentity` branches keep the clause (there it names a type/kind that can declare one); the `ref` branch must not.
    - `subtree` is **not** affected, and the premise that it shares the heterogeneity is false. Driven: `_resolve_subtree_source` filters descendants to `source.name`'s own type, so its records are homogeneous and its declared-field set is already exactly right — `subtree`-over-`task` naming `severity` stays correctly refused. A fix that generalises across all three source kinds has misidentified the defect.
    - @reviewer @python-dev the ruling is in the ADR; ST7 needs a small reword (see my TASK-842 comment) before it can be taken as written.
- [2026-08-26T17:44:49Z] Elias Python:
  - Fixed via TASK-842 ST7 per the architect's ruling: a ref source may project a field code at least one declared item type carries (item types only, roster included); a code no declared type carries anywhere stays refused with a rewritten, performable message. docs/workflow.md updated.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Documented group.count does not exist in the template context

<!-- sq:finding:F8:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
**driven.** `docs/workflow.md` tells adopters that a presentation template receives groups with a
`count`:

> The template receives `fields`, `group_by` and `groups`; a group has `key`, `count` and
> `records` ...

`ViewGroup` (`src/squads/_views.py:59-66`) declares only `key` and `records`. `render_view` passes
those dataclasses straight through (`src/squads/_views.py:316-321`), and the Jinja environment runs
under `StrictUndefined`, so a template following the documentation fails loudly:

```
UndefinedError: 'squads._views.ViewGroup object' has no attribute 'count'
```

(driven, via `sq workflow view milestone_rollup MILE-9` with an override template containing
`{{ group.count }}`.)

`count` exists only in `projection_json` (`src/squads/_views.py:296`). That is a uniformity break
between the two documented consumers of one projection: a `--json` client sees `{key, count,
records}`, a template sees `{key, records}` and has to write `group.records | length`. The bundled
`milestone_rollup` and `finding_summary_line` templates both do exactly that, which is why nobody
noticed.

Fix either side — add `count` as a property on `ViewGroup` (cheaper, and closes the gap for every
adopter template) or correct the doc line. Adding it is the better answer: the payload and the
template context should not disagree about the shape of the same object.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-08-26T18:20:35Z] Elias Python:
  - Fixed via TASK-843 ST3: ViewGroup.count is now a property both group.count in a template and --json's count read, so they can never drift.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Six [selected] fixtures silently gained a milestone drop; comments now false

<!-- sq:finding:F9:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
**read**, sampled across all ~34 fixture edits in the range; the pattern below is the only one that
changed a fixture's meaning.

Six pre-existing `[selected].items` fixtures enumerate the bundled types. Every one of them gained
`"contract"` and **none** gained `"milestone"`:

- `tests/cli/test_create_refuses_a_dropped_built_in_type.py:25` (`_DROP_GUIDE_AND_BUG`)
- `tests/cli/test_read_path_refuses_a_dropped_built_in_type.py:17` (`_DROP_GUIDE`)
- `tests/integration/test_a_skill_body_appearing_after_init_is_seeded_by_the_next_sync.py:35`
  (`_KEPT`)
- `tests/integration/test_playbook_guide_dropped_for_a_non_live_role_is_reported.py:370` (`kept`)
- `tests/integration/test_playbook_prose_survives_a_dropped_type_as_a_bounded_limitation.py:32`
- `tests/integration/test_workflow_override_service_integration.py:652` (`_DROP_GUIDE_SELECTED`)

The asymmetry is not a judgement call — it is forced. `contract` **had** to be added or the spec
stops loading, because `[items.feature]` now declares `validators =
["ref_rule_target_present:contract"]` and a `ref_rules` entry targeting it, and
`_check_ref_rule_targets` refuses a target naming an undeclared type. `milestone` is not referenced
by anything, so nothing forced it, so it was left out.

The result is that each of these fixtures now drops one more type than it says it does.
`_DROP_GUIDE_AND_BUG`'s own comment still reads:

```python
# Drops `guide` and `bug` from the merged spec while keeping every roster type (role/skill/
# operator are locked by key identity and must always be named in `selected.items` too).
```

It now drops guide, bug **and** milestone — and, as a side effect, silently exercises
`_prune_orphaned_type_owned_views` in five tests that have nothing to do with views.

Each test still asserts what its *name* claims (checked: the assertions are all about `guide` /
`bug` / the renamed `job`), so no coverage is lost. The defect is that the next person editing one
of these lists will read a comment that is no longer true, and that the "keep the enumeration
complete" invariant these fixtures encode has quietly stopped holding.

Fix: add `"milestone"` to all six, and correct `_DROP_GUIDE_AND_BUG`'s comment if any is
deliberately left dropping it.

**Everything else in the fixture sweep checks out** (read): the `tests/_helpers.py` prefix/folder/
type tables, the create-lane product table, the skills-for-role and pointer-frontmatter
expectations, the lifecycle/type/playbook counts, the two `views` payload additions
(`test_identity.py:129`, `test_workflow_spec_artifact.py:86`), and the
`test_workflow_reserved_vocab._spec_without_type` filter, whose partition logic I traced by hand
for both the bare and parameterised forms. One weakening is deliberate and documented:
`tests/cli/test_help_text_follows_spec_vocabulary.py:60` now asserts a truncated prefix rather than
the full `epic|feature|...|guide` chain, because nine types no longer fit the pinned 80-column
help width. The comment explains it; declared-order coverage of the last two types is genuinely
lost, and there is no cheap way back short of widening the fixture's terminal.

One overreach worth noting: `tests/unit/test_declared_ref_rules_are_not_inert.py:126` adds
`entry["validators"] = []` for **every** type with a comment describing only `feature`'s entry. It
also strips `epic`'s `no_parent`. Harmless for what that probe asserts, but the comment
under-describes the edit.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-08-26T17:44:50Z] Elias Python:
  - Fixed via TASK-842 ST3: all six [selected] enumerations now carry milestone, stale comments corrected, plus the two smaller comment corrections noted in the finding.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Two view templates ship in the wheel that no bundled declaration can reach

<!-- sq:finding:F10:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F10:head:end -->

<!-- sq:finding:F10:body -->
**driven + read.** `src/squads/_rendering/templates/views/finding_summary.md.j2` and
`finding_summary_line.md.j2` ship as package data and are listed in
`src/squads/_rendering/templates_manifest.json:285-286`, but no bundled `[views]` entry names
either. `src/squads/_specs/workflow.toml`'s own section comment says so plainly:
"`milestone_rollup` is the one bundled view". Driven confirmation on a fresh squad:
`sq workflow views` lists exactly one row.

They are reachable only if an adopter happens to declare a view with one of those two exact names —
which is what the test suite does (`tests/service/test_view_resolve_and_render.py:69,92-95`,
`tests/cli/test_workflow_views_cli.py:75`). In other words, production package data exists to give
the test suite's own override-declared views something to render.

Two consequences:

- **`sq override scaffold views/finding_summary.md.j2` succeeds** on any squad, offering an adopter
  a template for a view their spec does not declare and the docs never mention.
- **The FEAT-693 acceptance line it is standing in for is weaker than it looks.** "At least one
  non-tabular presentation ships and is exercised" is satisfied by a template that ships but that
  nothing shipped can reach.

`tests/unit/test_view_expresses_the_subentity_summary_shape.py:11-13` states the opposite as fact:

> The two views that *do* ship bundled (``finding_summary``/``finding_summary_line`` — see
> ``test_view_declaration_referential_checks.py``) stick to base attributes for that reason

No such views ship. The cited file declares them as test fixtures. The docstring should say
"templates", not "views" — and the templates themselves probably belong under the test fixtures
rather than in the wheel, unless the intent is to declare the two views for real.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-08-26T18:20:41Z] Elias Python:
  - Fixed via TASK-843 ST5: moved finding_summary/finding_summary_line out of the wheel entirely rather than declaring them for real (avoids coupling every project to finding's optional severity field). Their consumers now write a test-authored stand-in template as a project override; corrected the false bundled-views claim in test_view_expresses_the_subentity_summary_shape.py. Manifest regenerated, only the 0.14.0 entry moved.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — The scaffolded view example has no template, so it tracebacks on render

<!-- sq:finding:F11:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F11:head:end -->

<!-- sq:finding:F11:body -->
**driven.** `sq override scaffold workflow` writes a commented `[views.related_incidents]` example
(`src/squads/_overrides/_service.py:530-539`). An adopter who uncomments it gets a view that loads
and lints clean and then raises an unhandled `jinja2.TemplateNotFound` the moment anything renders
it, because no `templates/views/related_incidents.md.j2` exists and the scaffold says nothing about
needing one. (The traceback itself is BUG-838; this is about the shipped example teaching the
shape.)

`docs/workflow.md` does carry the warning — "**A view you declare needs a template of its own at
that path** before it can be rendered; until you write one, resolve it with `--json`" — so the fix
is one comment line in the scaffold body, mirroring that sentence.

The meta test added alongside it,
`tests/meta/test_scaffolded_override_examples_load_against_the_live_models.py:76-88`, asserts only
that the example *loads*. Its docstring says an invalid example "would teach the adopter a shape
`sq workflow lint` rejects on the very next run" — which is precisely the failure mode this example
does **not** have. The one it does have (renders to a traceback) is outside what the test checks.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-08-26T17:44:51Z] Elias Python:
  - Fixed via TASK-842 ST6: the scaffold's [views.related_incidents] example now carries a comment naming the template path it needs; the meta test now also drives the render failure end to end.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — A paramless ref_rule_target_present loads clean and is permanently inert

<!-- sq:finding:F12:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F12:head:end -->

<!-- sq:finding:F12:body -->
**driven.** A type declaring `validators = ["ref_rule_target_present"]` with **no** `:<T>` parameter
loads clean, lints clean, and is permanently inert. Nothing ever fires, and nothing tells the
adopter why.

## Repro (driven)

```toml
# squads:override-base:0.14.0
[items.bug]
validators = ["ref_rule_target_present"]
```

```
sq workflow lint     -> workflow spec OK — no errors or warnings.
sq check             -> ✓ no issues     (with a Verified bug and a contract both in the corpus)
```

## Why it slips through both checks

`_check_validators_assignment` accepts the bare name because `ref_rule_target_present` is a member
of `VALIDATOR_NAMES`. `_check_ref_rule_targets` (`src/squads/_workflow/_models.py:1150-1189`) skips
it: `if bare != "ref_rule_target_present" or not sep: continue`. And the validator itself builds its
target set with the same `and sep` guard (`src/squads/_services/_validators.py:485-490`), so
`targets` is empty, `active` is empty, and it returns immediately.

## Why it is worth closing

This is the mirror image of the case the same commit deliberately refuses. From
`_check_ref_rule_targets`'s own docstring:

> A type selecting `ref_rule_target_present:<T>` must itself declare at least one `ref_rules` entry
> whose `target` is `<T>`. Without this, `<T>` could be an item type nothing points the check at
> ... both are refused here rather than warning forever at runtime.

The reasoning applies identically — an inert declaration is refused because it is a lie about what
the spec does. One more clause in the same loop closes it: for `ref_rule_target_present`, a missing
parameter is an error, the same way `PARAMETERIZED_VALIDATOR_NAMES` already makes a *surplus*
parameter an error on every other catalog name.

Add it to `PARAMETERIZED_VALIDATOR_NAMES`' opposite direction: a required-parameter set, or an
explicit check in `_check_ref_rule_targets`'s second loop.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-08-26T17:44:52Z] Elias Python:
  - Fixed via TASK-842 ST4: a paramless ref_rule_target_present is now refused at load.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Dropping the bundled contract type bricks the squad until feature is also edited

<!-- sq:finding:F13:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F13:head:end -->

<!-- sq:finding:F13:body -->
**driven.** Dropping the bundled `contract` type through `[selected].items` — a supported
customisation of a non-reserved type — bricks the squad. Every command exits 1 until the adopter
also edits `[items.feature]`.

```
sq list -a
error: this squad's workflow override could not be loaded, so no command can answer with the
vocabulary it declares.
  cause: Invalid workflow spec:
  - item 'feature': ref_rules target 'contract' does not name a declared item type — 'contract'
    was dropped from a [selected] list (selected.items), not left undeclared
  - item 'feature': validators entry 'ref_rule_target_present:contract' names target type
    'contract', which is not a declared item type — ...
```

Driven across every bundled non-roster type: `task`, `bug`, `decision`, `milestone`, `review` and
`guide` all drop cleanly. `epic` and `feature` fail on pre-existing `parents` couplings; `contract`
is the one this range adds.

## Why it is filed rather than shrugged at

The diagnostics are good — both name the exact key and both carry `[selected]` provenance — and the
`parents` precedent means this is not a new *class* of coupling. What makes it worth a finding is
that the very same release decided the opposite for the other new type, and wrote down why.
`_prune_orphaned_type_owned_views` (`src/squads/_workflow/_loader.py:625-666`) exists precisely so
that dropping `milestone` does not require a second edit, and the bundled spec's own comment states
the rationale:

> ... no view left declared over a type that no longer exists, and no second `selected.views` line
> for an adopter to remember.

`contract` gets no such courtesy: dropping it requires remembering two unrelated-looking keys in a
different type's block. The remedy is the same shape — when `[selected].items` drops a type, strip
any surviving type's `ref_rules` entries targeting it and any
`ref_rule_target_present:<dropped>` validator entry, at the raw-mapping layer the prune already
operates at. `tests/unit/test_workflow_reserved_vocab.py:_spec_without_type` already implements
exactly that filter — in the test suite, where it is doing the loader's job for it.

Priority is a judgement call for the architect; the asymmetry inside one release is the part worth
recording.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-08-26T17:44:53Z] Elias Python:
  - Fixed via TASK-842 ST5: dropping a type through [selected].items now strips any surviving type's ref_rules/ref_rule_target_present entries that targeted it, in both the fail-fast loader and sq workflow lint.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — target_date is settable and validated but never shown on a human surface

<!-- sq:finding:F14:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F14:head:end -->

<!-- sq:finding:F14:body -->
**driven.** `target_date` is settable, validated and stored, but never rendered on any human
surface. `sq milestone <n> show` does not display it; only `--json` does.

```
sq milestone 14 update --set target_date=2026-12-01   -> updated MILE-14
sq milestone 14 update --set target_date=nonsense     -> error: 'target_date' expects an ISO date
                                                          (YYYY-MM-DD); got 'nonsense'
sq milestone 14 update --set target_date=2026-13-45   -> refused, same message
sq feature 9 update --set target_date=2026-12-01      -> error: not a settable field on a feature
sq milestone 14 show                                  -> panel shows id/title/status/author/file
sq milestone 14 show --json                           -> "extra": {"target_date": "2026-12-01"}
```

The coercion itself is good work — `_coerce_date` (`src/squads/_models/_metadata.py:91-99`) rejects
both a non-date and an out-of-range date, names the key in the refusal, and normalises to ISO.

This is consistent with existing behaviour: no `extra_fields` value is rendered on `show` today
(`review`'s `target_ref`, `guide`'s `tags`/`tech` are equally invisible — grepped: nothing in
`_cli/_common.py` reads `it.extra` for the panel). So it is not a regression.

It is filed because a milestone's target date is the type's one distinguishing attribute — a
milestone is "a named target ... with a target date" per FEAT-693's own acceptance line, and
`docs/workflow.md` teaches setting it two lines after introducing the type. A field the docs teach
and the panel hides is a small trap. If the generic `extra_fields`-on-panel gap is out of scope for
this release, the milestone panel could render it as a one-off, or the docs could say where to read
it back.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-08-26T18:20:46Z] Elias Python:
  - Fixed via TASK-843 ST6: sq milestone <n> show and --raw now display target date when set, as a milestone-specific one-off (not the generic extra_fields-on-panel render). The generic version would need display vocabulary (label/ordering) the spec doesn't carry yet - flagged as an architect question on TASK-843, not invented inline.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T16:55:38Z] Paul Reviewer:
  - What came back clean, driven rather than read.
    
    **The currency check (ADR-320 §C + amendment B1/B2/B3) — clean on every path driven.** Inert side:
    a squad with a Done feature and no contract in the corpus reports `✓ no issues`. Active side:
    creating the first contract turns the same corpus into `warn FEAT-10: settled with no implements
    ref to a contract`. Clearing: an `implements` ref to a decision still warns; an `implements` ref to
    a contract clears it; moving the feature off Done clears it. Gate path: with a contract present and
    a settled feature, `update --priority`, `create feature`, `comment` and `status` all succeed at
    exit 0, and `sq check` exits 0 on warnings — the check cannot gate a mutation, both because
    `gate()` leaves `type_present` empty and because the finding is warn-level and `gate()` filters to
    errors. B1's role binding, B2's `RefRule.target`, and B3's corpus-state precondition are all built
    as the amendment ruled.
    
    The designed cliff is real and on the record: this repository has 90 Done features, so authoring
    its first PRD turns a clean `sq check` into 90 warnings in one step. That is what B3 chose, with the
    count stated; noting it here so the number is in front of whoever authors that first contract, not
    as a finding.
    
    **The uniform projection contract — holds.** Records are identically shaped across all three
    sources (driven: `ref`, `subentity`, `subtree`); field metadata and grouping travel with the
    payload; an ungrouped view still emits a single `key: null` group so a client never special-cases
    it; `--json` emits the projection and renders nothing. Membership is never written to the milestone
    file (driven: adding four `targets` refs leaves the milestone byte-identical, and its stored body
    carries no roll-up text). Findings F2/F3/F7/F8 are ordering, field-vocabulary and template-context
    gaps around that contract, not breaks in it.
    
    **The deselect cascade — clean.** Dropping `milestone` from `[selected].items` prunes
    `milestone_rollup` from `[views]` and leaves the spec valid at exit 0, with no second
    `selected.views` line needed. Driven across every bundled non-roster type.
    
    **The migration runner's freezing question — the distinction holds.** The wire-encoding rule exists
    so a runner does not read *existing corpus data* through vocabulary that has since drifted. This
    runner reads no corpus vocabulary: `_NEW_TYPES` is a frozen tuple of type *names*, and every value
    it acts with — folder, prefix, skill lifecycle initial — resolves from the spec live, to *create*
    scaffolding that must match the spec the squad will be run under afterwards. Freezing the folder
    name would be the bug: it would create `contracts/` on a squad whose override says `prds/`, and
    every later command would look in the other place. `_active_spec` correctly prefers the squad's own
    override, so a squad that renamed or dropped a type gets its own declaration. I could not construct
    a drift case that makes the live resolution wrong.
    
    Its parity, driven with the full bundled roster rather than the test's `minimal`: apart from the
    two role-pointer gaps in F4, a migrated squad and a fresh `sq init` produce byte-identical trees —
    skill bodies, pointers, folders, `CLAUDE.md`/`AGENTS.md` regions — modulo id renumbering.
- [2026-08-26T16:56:10Z] Paul Reviewer:
  - Two things in the brief's attack lines I could not fully test, stated rather than implied.
    
    **A migration override that renames one of the two new types — partially driven, one result I am
    not confident enough to file.** With an override renaming `milestone` to `release`, `migrate`
    leaves `squads/agents/skills/sq-release.md` unstamped (no `SKILL-NNNNNN-` name, no frontmatter id)
    where `init` + `sync` produces `SKILL-000021-sq-release.md`, and no `releases/` folder is created.
    Both follow from `_ensure_type_folders` and `_seed_new_type_skills` being scoped to `_NEW_TYPES`
    while `_regenerate_surface` writes bodies for *every* declared type — which the runner's docstring
    acknowledges ("`write_managed` has no narrower entry point"). I am not filing it because my probe
    constructed the rename by writing the override onto an already-initialised squad, which is not the
    path a real adopter takes, and I could not rule out that my setup rather than the runner produced
    the unstamped file. Inconclusive by my own standard; worth someone building it properly from a real
    pre-0.14 corpus with the override in place from the start.
    
    **Roster-difference parity beyond the bundled eight.** I drove `--roles all` and `minimal`, but not
    a squad carrying `<tech>-dev` roles, which is where `skills_for_role`'s `*dev` sentinel now resolves
    `sq-contract` (`tests/unit/test_skills_for_role_mapping.py:39-43`). Adding a dev needs
    `svc.add_dev`, which changes the roster mid-probe and would have made the two trees incomparable
    for a reason unrelated to the migration. F4's gap almost certainly extends to a dev role's pointer
    by the same mechanism, but I did not drive it and am not claiming it.
    
    **Not attempted, deliberately.** No full pytest run — the brief reserves that gate. Targeted runs
    were used only to read fixture sources, not to re-verify green.
- [2026-08-26T16:56:11Z] Paul Reviewer:
  - Verdict recommendation: **ChangesRequested**. Two high findings, four medium, eight low. Leaving
    the status transition to the approver.
    
    The single thing that matters most is **F1**: a view's presentation template is silently ignored on
    `sq <type> <n> show`, which is the only surface a normal user meets a view on. FEAT-693 states its
    overridability as an acceptance criterion and names the exact proof it wanted — "overriding the
    bundled milestone-roll-up template in a test squad and confirming the override renders" — and that
    proof fails. The docs and the CHANGELOG both repeat the promise. The cause is not in the view code:
    `set_active_squad_dir` is a ContextVar set inside the first of two sequential `anyio.run` calls, and
    the leaf verb runs in a context where it is gone. Views are simply the first feature to render a
    template on that path. FEAT-694 moves the sub-entity summary and head onto the same mechanism, so
    this wants fixing at the seam, not in `_views`.
    
    **F6** is the one to fix alongside it: BUG-837 and BUG-838 are two faces of the same hole, and there
    are two more (a typo'd attachment name, and a sub-entity-source view attached to a type that hosts
    no sub-entities — both driven, both lint-clean, both exit 1 on `show` for every item of the type).
    Fixing them one at a time leaves the other two.
    
    **F2 and F3** are one fix in one function — `_sort_key` sorts an ordered badge alphabetically by
    code and an id lexicographically by string, so the bundled roll-up orders FEAT-15 before FEAT-9.
    Both resolvers already sort numerically before `order_by` undoes it.
    
    **F4** is a one-line runbook change: `sq migrate up` leaves three role pointers drifted and `sq
    check` says so, while the runner's MANUAL says no action is required.
    
    @python-dev for F1, F2, F3, F4, F8, F11, F12 and the fixture list in F9.
    @architect for F6 (whether the declined check moves to `load_workflow_spec`), F5 (whether the
    projection should carry a role's declared `settled`/`live` flags), F7 (whether a ref source may name
    a badge code some declared type carries) and F13 (the `[selected]` drop asymmetry between the two
    new types).
    @tech-writer for the `group.count` line in `docs/workflow.md` (F8) and the F10 docstring.
- [2026-08-26T17:08:15Z] Olivia Lead:
  - Triaged into four tasks, grouped by surface rather than severity. All fourteen findings have a home;
    BUG-837/838 are not re-filed, they are carried as `fixes` refs on TASK-842.
    
    - **TASK-841** — Honour adopter template overrides on the leaf-verb render path (F1). The seam, not
      the view: the active squad dir is a ContextVar lost between the two `anyio.run` crossings, so this
      is also a prerequisite for FEAT-694, which moves the sub-entity summary and head onto the same
      `render()` path.
    - **TASK-842** — Refuse incoherent view and ref-rule declarations at spec load (F6 all four axes
      incl. BUG-837/838, F7, F9, F11, F12, F13). One surface: `_workflow/_models.py` +
      `_workflow/_loader.py`, plus the fixture repair both halves need.
    - **TASK-843** — View projection ordering, payload and the bundled roll-up (F2, F3, F5, F8, F10,
      F14). One surface: `_views.py` + `templates/views/`.
    - **TASK-844** — Migrate leaves role pointers drifted against its own runbook (F4).
    
    **F5, severity.** Filed 🟡 medium; my call is **high**, and TASK-843 says so. The milestone type's
    stated job is answering what is left, and this makes that answer permanently wrong in the one
    direction that never resolves — an adopter who cancels a single scoped item gets a milestone that can
    never report zero. Same class as F1: a shipped acceptance line that does not hold on the surface a
    user meets, and this one fails silently rather than visibly.
    
    **F7 is gated.** TASK-842 ST7 carries it, but it is a spec-vocabulary question — may a `ref` source
    name a badge code only some of its records can carry — and no decision exists to land it against.
    That ADR is the one thing this triage depends on that is not yet built. Every other finding is
    actionable today.
    
    @architect for the F7 ruling (TASK-842 ST7 has the shape and the evidence). @python-dev for the
    rest, sequenced as: TASK-841, TASK-842 and TASK-844 in parallel; TASK-843 after both TASK-841 and
    TASK-842, which it shares `src/squads/_cli/_common.py` and `src/squads/_views.py` with.
- [2026-09-01T07:19:06Z] Catherine Manager:
  - All fourteen findings fixed and committed. F1 landed in TASK-841 — `get_service` now re-asserts the active squad dir on its memo-hit branch, verified at `_cli/_common.py:1051` and `:1116`, so every `render()` consumer honours adopter overrides rather than only `sq workflow view`. F4 landed in TASK-844 as a runbook correction rather than a runner change: regenerating pointers from an unpopulated role-skills map would have silently dropped an adopter's custom-scoped skills, so the MANUAL now names `sq sync` as the next step and the drift was confirmed to extend to every `<tech>-dev` role.
<!-- sq:discussion:end -->

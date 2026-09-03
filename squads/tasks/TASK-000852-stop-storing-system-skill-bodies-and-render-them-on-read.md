---
id: TASK-852
sequence_id: 852
type: task
title: Stop storing system skill bodies and render them on read
status: Ready
parent: FEAT-694
author: tech-lead
priority: high
refs:
- ADR-776:implements
- ADR-781:implements
- TASK-853:depends-on
description: A template-owned skill item stops storing its rendered body; sq skill
  show renders it from the same template on every call, keyed on is_system_skill
subentities:
- local_id: ST1
  title: Move the skill body render onto ServiceCore
  status: Todo
- local_id: ST2
  title: Stop writing the body; keep the pointer and the empty region
  status: Todo
- local_id: ST3
  title: Render a system skill's body at show time
  status: Todo
- local_id: ST4
  title: Prove a custom skill body is untouched
  status: Todo
created_at: '2026-09-01T08:26:15Z'
updated_at: '2026-09-01T08:45:38Z'
---
<!-- sq:body -->
## Scope

The skill half of ADR-776's 2026-09-01 shrink amendment: a **system (template-owned)** skill
item stops storing its rendered body, and `sq skill <slug> show` renders it from the same
template on every call. A **custom (authored)** skill body is storage and is untouched.

This is the skill half of stage 2 and its share of stage 3 in ADR-776's second 2026-09-01
amendment §3. The role half is two sibling tasks — stage 1 (every consumer resolves) and stages
2+3 (the producer inverts, the mirror stops being written). The corpus strip of what is already on
disk is TASK-849. This task changes the write path and the read path; nothing already on disk is
touched by it.

## The discriminator already ships, and choosing wrong destroys authored content

`is_system_skill(slug, spec)` (`_interactions/__init__.py:551-571`) is a pure function of the
slug and the active spec. It already backs `set_body`'s refusal of exactly these writes
(`_services/_items.py:533-548`) and already surfaces as `kind: system (template-owned)` in
`sq skill <slug> show` (`_cli/_skill.py:109`, `:127`).

**Key on it and on nothing else.** Not the folder, not the item type, not the `sq-` prefix. In
this repository 22 of 23 generated-looking roster files are in class and the 23rd is
`releasing-squads` — `kind: custom (authored)`, 10.1 KB of authored runbook (verified:
`squads/agents/skills/SKILL-000508-releasing-squads.md`, 10118 bytes). A prefix- or
folder-keyed change destroys it. The authored-content risk in this work is choosing the wrong
files, not editing inside them.

The two-provenance asymmetry the role half refutes is **real here**: a custom skill's body is
authored, `set_body` admits it, and `sq sync` leaves it alone.

## What moves, and why it has to move rather than just be deleted

The render lives inside the Claude backend today. `_write_managed_skill`
(`_backends/_claude_code/_backend.py:175-260`) writes **two** things: the skill item's own
`sq:body` region under `squads/agents/skills/`, and the thin pointer under `.claude/`. The body
write goes; the pointer write stays.

The pointer does not need the body — verified: it renders `claude/pointer_skill.md.j2` from
`slug` and `description` alone (`:248-259`). So `_write_managed_skill` loses its `body`
parameter along with the write, and its `Artifact(..., "skill_body", ...)` return. Check every
reader of that artifact-kind string before removing it (`managed_paths`, orphan detection, the
sync report's per-file accounting).

But `sq skill <slug> show` must render the same text, and it is a CLI/service reader:
**invariant 6 forbids it reaching into a backend**, so the render cannot stay where it is.

**The home is ruled: `skill_definition_text(slug)` on `ServiceCore` (`_services/_base.py`)**, the
sibling of the role half's `role_definition_text(slug)`. Not `_interactions/`, which is the
answer the symmetry argument wants — each definition rendered by the package that owns its
document. That answer is structurally unavailable, and the reason is worth carrying because it
will be re-proposed otherwise: verified, `_rendering/_engine.py` imports `squads._interactions`,
and `_interactions/__init__.py:35` imports `squads._roles._catalog`. The rendering engine sits
**above** both packages, so neither may import it without a cycle. `_services` is below
`_rendering` and may call `render` — `ServiceCore` already does.

A new `_definitions.py` concern mixin would read better and be unreachable: the mixins compose
into `Service` and do not import one another, so a producer that a core method needs cannot sit
in a sibling mixin.

**Invariant 6 is satisfied by direction, not by exemption.** The service produces the text and the
backend consumes nothing. `_write_managed_skill` loses its `body` parameter, and the **five**
`render` calls feeding it move out with it — three in `write_managed` (`squads`, `greeting`,
`sq-memory`) and two in `_write_item_skills` (the rich per-type body and the thin fallback).
Nothing reaches into `.claude/`; the backend keeps its own pointer render, which needs only slug
and description.

After the move there is exactly one producer and one consumer: `sq skill <slug> show`.

There is exactly one producer to move. The `_agents_md` backend writes nothing for skills —
verified: `generate_skill_entry` stages no content and its module docstring says the compiled
region is the whole of what it materialises.

## The rich/thin split travels with the render

`_write_item_skills` (`:262-360`) decides per item type whether a skill is *rich* (a playbook
entry exists — full per-role Enter/Do/Hand-off/Watch-for sections) or *thin* (no active-playbook
entry — auto-derived lifecycle and the standard command list). It also gates the shared
`developers` section on the roster carrying at least one `<tech>-dev` role. All of that is the
render's own logic and moves with it intact.

Two properties to keep, both currently load-bearing:

- A type the **active spec** has dropped or renamed away produces no skill at all, never a
  stale one under its old name — the `if item_type not in spec.items: continue` guard.
- The generated text is roster-dependent through the `has_dev` gate, so a comparison against a
  differently-rostered squad is a false positive. Hold the roster constant when diffing
  before/after output.

## What the file contains afterwards

Frontmatter plus an emptied `sq:body` region, markers kept. System skill items carry no
discussion region today and gain none. The `sq:body` markers stay for the same reason as on the
role side: the region's absence is a distinguishable state, and the marker pair is the shape
every item file shares.

## Accepted consequence

`sq search` stops matching a system skill's body text. Driven, and accepted rather than
compensated for; `sq skill list` and `sq skill <slug> show` answer from the resolver instead.
A custom skill's body stays searchable, because it is still there.

## Release ordering

This touches the skill templates' rendering path, so it sits behind ADR-781 §6's ordering: the
version bump precedes any template-manifest regeneration, only the `0.14.0` manifest entry
moves, `scripts/bump_version.py` is not run, and the managed-section golden and the
generated-agent-text guards move with it. Orphan manifest residue is the operator's.

## Acceptance

- No system skill item's `sq:body` region is written by any code path. `sq sync` leaves the
  region present and empty for every system skill, and running it twice produces no diff on a
  system skill file.
- A **custom** skill's body survives `sq sync` byte-for-byte, and `sq skill <slug> body` still
  admits a write to it. Proven with a custom skill in the fixture, not by inspection —
  and proven for a custom skill whose slug happens to start with `sq-`.
- `sq skill <slug> show` renders the full body for every system skill — the three bundled ones
  and every per-type `sq-<type>`, rich and thin alike — byte-identical to what `sq sync` wrote
  for the same squad before this change, with the roster held constant.
- The body render lives on `ServiceCore` as `skill_definition_text(slug)`, has no import from
  `_backends`, and no CLI or service module imports a backend to obtain it. `_write_managed_skill`
  has no `body` parameter and returns no `skill_body` artifact.
- `.claude/` skill pointers are byte-identical before and after, and `sq check`'s
  pointer-currency comparison still reports a drifted pointer as drifted and a current one as
  current.
- A type dropped from the active spec still produces no skill body and no pointer; a renamed
  type produces neither under its old name.
- `sq skill <slug> show --json` returns every field it returns today, including `system`.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean. `sq check` is clean on this repository.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 852 add-subtask "<title>"`; track with `sq task 852 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Move the skill body render onto ServiceCore

<!-- sq:subtask:ST1:body -->
The four bundled skill renders (`_backends/_claude_code/_backend.py:110-143` — `squads`,
`greeting`, `sq-memory`) and the per-type loop (`:262-360` — the rich `sq-<type>` body and the
thin fallback for a type with no active-playbook entry) move out of the Claude backend onto
**`ServiceCore.skill_definition_text(slug)`** (`_services/_base.py`), the sibling of the role
half's `role_definition_text(slug)`.

Five `render` calls move: three in `write_managed`, two in `_write_item_skills`.

**The placement is ruled, not a judgement call, and the attractive alternative is structurally
unavailable.** `_interactions/` is where the symmetry argument puts it — each definition rendered
by the package that owns its document — and it cannot host a renderer: verified,
`_rendering/_engine.py` imports `squads._interactions`, and `_interactions/__init__.py:35` imports
`squads._roles._catalog`, so the rendering engine sits above both packages and neither may import
it without a cycle. `_services` is below `_rendering` and already calls `render`.

A new `_definitions.py` concern mixin is the other tempting answer and is unreachable: the mixins
compose into `Service` and do not import one another, so a producer a core method needs cannot sit
in a sibling. `ServiceCore` is the layer.

Why the render must move at all rather than be inlined at the show site: `sq skill <slug> show` is
the reader, and invariant 6 forbids a CLI or service module reaching into a backend to obtain
content. Keeping the render in `_backends/_claude_code/` and importing it from `_cli/_skill.py` is
exactly the failure that constraint exists to prevent. Invariant 6 is then satisfied by
**direction**: the service produces, the backend consumes nothing, and the backend keeps only its
pointer render.

Everything the render consumes is already backend-neutral — the active `WorkflowSpec`, the merged
`PlaybookSpec`, roster display names, `linearize_lifecycle`, `spec.item_subentity_kind`,
`label_for` — and the templates are shared package data under `_rendering/templates/agents/`.

Preserve, exactly:

- the rich/thin split, decided by the **active merged** playbook rather than the bundled
  singleton, so an override's added or removed coverage decides it;
- the `if item_type not in spec.items: continue` guard, so a type the spec has dropped or renamed
  produces no skill at all rather than a stale one under its old name;
- the `has_dev` gate on the shared `developers` section — the generated text is roster-dependent,
  which is also why a before/after diff must hold the roster constant.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Stop writing the body; keep the pointer and the empty region

<!-- sq:subtask:ST2:body -->
`_write_managed_skill` (`_backends/_claude_code/_backend.py:175-260`) stops writing the skill
item's `sq:body` region. Its `body` parameter goes with the write, and so does the
`Artifact(ctx.rel(body_path), "skill_body", self.name)` it returns.

The pointer write stays exactly as it is. Verified: `claude/pointer_skill.md.j2` renders from
`slug` and `description` only, so nothing the pointer needs came from the body.

Before removing the `skill_body` artifact kind, find its readers — `managed_paths`, orphan
detection, `remove_artifacts`, and the sync report's per-file "written / already present"
accounting all consume artifact records, and a silently dropped kind changes what a sync reports
without changing what it does.

`ctx.skill_paths` exists so the backend can locate a skill's body file without importing the
index (`ServiceCore._skill_paths`, `_services/_base.py:1152`). It has other consumers —
`seed_bundled_skills` renames a first-write slug-named file to the convention name and rewrites
the pointer. Do not delete the map with the write; check each consumer.

The `sq:body` markers stay in the file. The region ends up present and empty for every system
skill, and nothing writes it afterwards. A system skill item carries no discussion region today
and gains none.

`set_body` already refuses a system skill's body through the same `is_system_skill` test, so no
verb can refill what this stops writing.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Render a system skill's body at show time

<!-- sq:subtask:ST3:body -->
`sq skill <slug> show` renders the body from the resolver instead of reading the stored region.
The panel above it is unchanged, `kind:` included.

Branch on `is_system_skill(slug, svc.spec)` — the value the command already computes at
`_cli/_skill.py:109` for its `kind:` row:

- **system** — render through the moved render path and print the result. `--raw` and the
  piped/non-TTY path keep working: the string still goes through `render_body_text`, so only
  its origin changed.
- **custom** — keep reading `svc.read_body(it.id)` exactly as today. This is authored storage.

The `empty_hint` at `:143` currently reads "(empty — run `sq sync` to regenerate the skill
definition)". For a system skill that hint becomes untrue — there is nothing for a sync to
regenerate. Either the render always produces text (in which case the hint is unreachable for a
system skill and should not be offered) or the empty case means something new and the hint says
what it means. Do not leave a hint pointing at a command that no longer has the effect.

`--json` is a different reader and keeps every field it returns today, `system` included. It
does not carry the body today and does not gain it here.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Prove a custom skill body is untouched

<!-- sq:subtask:ST4:body -->
The one risk in this task is choosing the wrong files, so the proof is a custom skill that
survives untouched — asserted, not inspected.

In this repository the live case is `releasing-squads`: `kind: custom (authored)`, 10.1 KB of
authored runbook at `squads/agents/skills/SKILL-000508-releasing-squads.md`. It sits in the same
folder, carries the same item type and the same frontmatter shape as the 12 system skills beside
it. Folder, type and the `sq-` prefix each pick the wrong set; only `is_system_skill` picks the
right one.

Assert, in the test suite rather than by hand:

- a custom skill's body is byte-identical across a `sq sync`, and across two of them;
- `sq skill <slug> body` still admits a write to a custom skill, and the written text survives
  the next sync;
- a custom skill whose slug **starts with `sq-`** is still treated as custom — this is the case
  a prefix-keyed implementation passes every other test while getting wrong;
- a per-type system skill for an adopter-declared type (one with no playbook entry, taking the
  thin branch) is treated as system;
- `sq skill <slug> show` prints the authored text for the custom one and the rendered text for
  the system one, in the same run.

Falsify it: key the change on the folder instead, watch the custom-skill assertions go red,
restore `is_system_skill`, watch them go green — and report both.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

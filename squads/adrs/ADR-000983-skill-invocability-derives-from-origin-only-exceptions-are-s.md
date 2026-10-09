---
id: ADR-983
sequence_id: 983
type: decision
title: Skill invocability derives from origin; only exceptions are stored
status: Proposed
author: architect
refs:
- ADR-781
- ADR-492
- ADR-75
- ADR-133
- ADR-181
- FEAT-966
- FEAT-976
description: Where a skill's operator-invocable property lives, how it resolves, and
  what each backend does with it.
created_at: '2026-10-09T18:27:22Z'
updated_at: '2026-10-09T18:35:00Z'
---
<!-- sq:body -->
## Context

Every skill the Claude Code backend writes is offered to the person at the keyboard as a command
they can run by name. Most of those skills are agent reference material that roles preload and no
person runs. The rule to implement is op-pierre's: every bundled skill is not offered that way,
every author-defined skill is.

The obvious design is a per-skill property declared in a spec, with a default per skill and a
project override. Three facts make that the wrong shape.

**There is nowhere to declare it** (read). No spec document declares a skill. The three always-on
skills are constants in `_interactions`, each per-type skill is derived from the item types the
active spec and playbook hold (`bundled_skill_slugs`, `custom_skill_slugs`), and the playbook's
closed top level is `{types}`. A per-skill table would have to enumerate skills that are derived
from types a project can add, or name `sq skill add` items by slug from inside a spec document,
which creates a reference between a spec and the corpus that nothing checks.

**The default is a function of something already recorded.** "Bundled" and "author-defined" are
statements of provenance, and the stored `origin` of a skill (`system` or `project`) records
exactly that. A per-skill default written beside it would be a second copy of the same fact.

**The backend already has two pointer writers and one comparison** (read, `_backends/_claude_code`):
`_write_managed_skill` writes system skills from a slug and a description with no item in hand,
`generate_skill_entry` writes an item-scoped entry, and `sq check` compares each pointer on disk
byte for byte with `render_skill_entry`'s fresh render (`backend_entry_drift`). All three render
`pointer_skill.md.j2`, which today holds `name` and `description` only.

The host's own key, checked against Claude Code's skill documentation: `user-invocable`, default
`true`. Set to `false` it hides the skill from the `/` menu and stops `/name` from running it,
while the model can still invoke it. The documentation states that only
`disable-model-invocation: true` prevents preloading into a subagent, "since preloading draws from
the same set of skills Claude can invoke". That a hidden skill still preloads is therefore
inferred from the documented rule; it is not stated outright and has not been driven.

## Decision

### 1. The engine property is `operator_invocable`

Whether a skill is offered to a human operator as an action they invoke by name, on a host that
has such a surface. It is a resolved boolean with squads' own name and squads' own meaning. No
host key, and no host's spelling of one, appears in the engine, the frontmatter, the CLI or any
`--json` output.

### 2. The default is derived from origin and nothing is stored for it

```
operator_invocable(skill) :=
    the stored exception, when the skill carries one (clause 3)
    otherwise  origin == "project"
```

- No spec key, no per-skill declaration, no list of bundled skills in any document, and no value
  stamped on a skill at creation or by a migration.
- The slug plays no part. An author-defined skill named `sq-onboarding` has origin `project` and
  is invocable.
- A skill with no readable origin resolves as invocable, which is what every skill is today.
- The resolver reads the stored `origin`. It does not recompute a classification from the slug
  and the spec, which is the per-surface recomputation the stored field exists to retire.

Reading origin here is consistent with origin being provenance. The rule being implemented is
itself stated as provenance, and origin does not move when a project changes what it does with
the entity. A system skill whose view a project dropped is writable again, still has origin
`system`, and is still not invocable by default. The write refusal does not read origin; this
default does.

### 3. Only an exception is stored, on the skill item

A project that wants the other answer for one skill records it on that skill:

- **Key.** `extra.operator_invocable`, a boolean, optional. Absent means "resolve by origin".
  This is the one new frontmatter key, and frontmatter is where an entity's own state lives; `sq
  repair` rebuilds it like any other `extra` key.
- **Both directions, one mechanism.** A project skill may be hidden (a project's own reference
  material is the same clutter this solves for the bundled set). A system skill may be shown.
- **Writers.** `sq skill add` and `sq skill <addr> update` take `--operator-invocable` /
  `--no-operator-invocable`. A writer never stores a value equal to the derived default: setting
  the default value removes the key, which is also how an exception is withdrawn.
- **Allowed on a system skill.** The value is an operator's choice about how the entity is
  exposed, not generated content, so it sits outside the system-skill write refusal on the same
  footing as a comment. It is the only `update` option a system skill accepts.
- **Read strictly.** Only a YAML boolean counts. Any other stored value resolves as absent. No
  validator is added for it: the worst outcome of a bad hand edit is the default.
- A change through either verb regenerates that skill's entry on every active backend.

### 4. Read surfaces

`sq skill <addr> show` prints the resolved value. Every `--json` surface that carries a skill's
`origin` carries `operator_invocable` beside it, as a boolean present on every row. Whether the
value is an exception is not published: a client derives it from `origin` and
`operator_invocable` on the same row.

### 5. Backends receive the resolved value and spell it themselves

- One resolver, in the engine. A backend never reads `origin` or the stored key and never
  re-derives the rule.
- The three render sites named in the context must agree, or `sq check` reports the pointer as
  drifted forever. The item-less managed writer is handed the resolved values by the service, the
  way `skill_paths` and `role_skills` already reach it. Before a skill is indexed (the first
  write of `sq init`) it resolves as not invocable, since that writer only ever creates system
  skills.
- The `AgentBackend` ABC gains no abstract method. A backend written against the documented
  seven is unaffected and expresses nothing.

**Claude Code.** `operator_invocable` joins this backend's expressible set (the second per-host
question of ADR-781). The skill pointer carries `user-invocable: false` when the value is false
and no line when it is true, the host's own default. It passes the containment rule: the host
reads it before any agent runs, and no runtime fetch can stand in for a menu entry that was never
shown. `disable-model-invocation` is never written; it would stop the preload these skills exist
for. `pointer_skill.md.j2` is the only place the host's key is spelled.

**AGENTS.md.** The compiled document has no per-skill entry and names no skill (read), so there
is no place for the value. Its answer to the second per-host question says so in prose, as it
already does for the model, the colour and the preload list. Nothing is written, nothing is
warned, and the compiled file is byte-identical.

## What this builds on and narrows

- The stored `origin` on roles and skills. This decision reads it and adds no rule about it.
- **ADR-781**: the skill pointer's contents grow from two values to three under its containment
  rule.
- **ADR-492**: a system skill stays template-owned. The one value an operator may set on it is
  the exception of clause 3.
- **ADR-75 / ADR-133**: the backend boundary is unchanged; a host key stays inside its backend.

## Consequences

- No schema bump and no migration for this decision: an absent key is the default, and an older
  package ignores an unknown `extra` key (inferred from `extra` being a free mapping; not driven).
- After an upgrade and before the next `sq sync`, `sq check` warns that every system skill's
  pointer has drifted, because the fresh render now carries a line the file lacks (inferred from
  the byte comparison in `backend_entry_drift`). That is the existing prompt to sync and it clears
  on sync. It is a warning, so the exit code does not change.
- The first sync after an upgrade rewrites every system skill pointer. Every `/name` a person
  used to type for a bundled skill stops working on Claude Code, by design.
- The preload claim rests on documentation. A hidden skill still arriving in a subagent that
  lists it has to be seen once on a real host before the default ships.

## Alternatives rejected

- **A stored value on every skill.** Stores what origin already says, needs a migration to stamp
  it, and gives the two a way to disagree.
- **A per-skill table in the playbook or workflow override.** Nothing to diff against in the
  bundled document, and a spec key naming corpus items by slug.
- **A list in `.squads.toml`.** The same dangling reference, in a file that holds no entity
  state.
- **Hiding by `sq-` prefix or by a recomputed "is system" test.** The prefix is not reserved to
  squads, and the recomputed test is the one the stored origin replaces.
- **Exceptions for project skills only.** Simpler, and it needs no exemption from the write
  refusal, but it leaves a team no way to put one bundled skill back in its menu.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T18:35:00Z] Pierre Chat:
  - 2026-10-09: not accepted as written. System skills are not user-invocable now but may be in the future. This property is not derived from origin: it is an attribute of the skill, and it can be changed with the CLI. Still to settle: whether changing it writes the skill's frontmatter, or whether a bundled skill needs an override for it.
<!-- sq:discussion:end -->

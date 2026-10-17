---
id: ADR-983
sequence_id: 983
type: decision
title: 'Skill invocability: a declared default and a squad''s stored choice'
status: Accepted
author: architect
refs:
- ADR-781
- ADR-492
- ADR-75
- ADR-133
- ADR-181
- FEAT-966
- FEAT-976
- ADR-1007
description: Where a skill's operator-invocable attribute is declared and stored,
  how it resolves, and what each backend does with it.
created_at: '2026-10-09T18:27:22Z'
updated_at: '2026-10-15T20:17:02Z'
---
<!-- sq:body -->
## Context

Every skill the Claude Code backend writes is offered to the person at the keyboard as a command
they can run by name. Most of those skills are agent reference material that roles preload and no
person runs. op-pierre's rule for today: no bundled skill is offered that way, every
author-defined skill is. His rule for the property itself: it is an attribute of the skill, a
bundled skill's answer may change in a later release, and a squad can change it with the CLI.

Three facts shape where that attribute can live.

**No spec document declares a skill** (read). A bundled skill is defined in `_interactions`, in
code: the three always-on skills have a description in `SKILL_DESCRIPTIONS` and a view name in
`SYSTEM_SKILL_VIEW_NAMES`; every per-type `sq-<type>` skill shares one generated description
(`custom_item_skill_description`) and one view name (`ITEM_SKILL_VIEW_NAME`), for a bundled type
and a project-declared one alike. The playbook's closed top level is `{types}`. The backend
already asks that definition for a system skill's description, behind `is_system_skill`
(`_skill_pointer_description`).

**A role already stores one operator choice that no catalog answers** (read, `_models/_metadata.py`):
`extra.is_default` is written by `sq role set-default` and by nothing else, so no sync reasserts
it.

**The backend has two pointer writers and one comparison** (read, `_backends/_claude_code`):
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
has such a surface. It is a boolean attribute of the skill, with squads' own name and squads' own
meaning. No host key, and no host's spelling of one, appears in the engine, the frontmatter, the
CLI or any `--json` output.

### 2. A bundled skill's default is declared in its bundled definition

- "The bundled definition" is the engine's own declaration of a bundled skill in `_interactions`,
  where its description and its view name are declared today. The default is declared beside
  them: one value for each of the three always-on skills, and one for the per-type family, which
  every `sq-<type>` skill shares as it shares one description template and one view.
- Every one of those values is `false` today.
- The declaration is closed: a guard holds it against the always-on set, so a bundled skill
  cannot be added without stating its default.
- It is code, not a spec document, and no override reaches it. A squad's surface is clause 3 and
  nothing else. A release changes a default by changing the declaration.
- A skill has a bundled definition exactly when the engine supplies its description, by the test
  that already decides that. No new membership test is added, the slug's spelling plays no part
  beyond it, and `origin` is not read.
- A skill with no bundled definition, which is every author-defined skill, takes the engine's one
  default for an authored skill: invocable. An author-defined skill named `sq-onboarding` is
  invocable.

### 3. A squad's own value is stored on the skill, and only a verb writes it

- **Key.** `extra.operator_invocable`, a boolean, optional, in the skill's frontmatter. `sq
  repair` rebuilds it like any other `extra` key.
- **Writers.** `sq skill add` and `sq skill <addr> update` take `--operator-invocable
  <yes|no|default>`. `yes` and `no` store the value. Nothing else writes the key: not `sq init`,
  not `sq sync`, not seeding, not a migration. It stands where `extra.is_default` stands on a
  role.
- **A set is always stored, including when it equals the current default.** The stored key means
  "this squad chose", not "this differs". A squad that deliberately keeps a bundled skill hidden
  keeps it hidden when a later release changes that skill's default. Dropping a value because it
  matches today's default would make that squad follow the change silently.
- **Withdrawing a choice is its own value.** `--operator-invocable default` removes the key, and
  the skill follows its declared default again. Leaving the option out stores nothing and changes
  nothing.
- **Allowed on a system skill.** The value is an operator's choice about how the entity is
  exposed, not generated content, so it sits outside the system-skill write refusal on the same
  footing as a comment. It is the only `update` option a system skill accepts.
- **Read strictly.** Only a YAML boolean counts. Any other stored value resolves as absent. No
  validator is added for it: the worst outcome of a bad hand edit is the declared default.
- A change through either verb regenerates that skill's entry on every active backend.

> **Note 2026-10-15 (ADR-1007):** the key is the top-level `operator_invocable`, a declared `bool`
> attribute on `skill`, not `extra.operator_invocable`; FEAT-966 declares it. It stands where
> `is_default` stands on a role, now a top-level attribute too. A non-boolean value still resolves
> as absent, and `sq check`'s attribute-kind check reports it, since every declared attribute is
> checked for its kind. See ADR-1007 decisions 3 and 5.

### 4. Resolution

```
operator_invocable(skill) :=
    the value stored on the skill, when it carries one (clause 3)
    otherwise the default its definition declares (clause 2)
```

The default is never copied onto an item, so there is one place it can be changed and nothing
for a sync to reassert or overwrite.

### 5. Read surfaces

- `sq skill <addr> show` prints the resolved value and whether it is the squad's own or the
  declared default.
- Every `--json` surface that publishes a skill's own fields (today `sq skill <addr> show
  --json`) carries two keys, present on every row: `operator_invocable`, the resolved boolean,
  and `operator_invocable_set`, true when the skill stores the squad's own value. The second is
  published because nothing else on the row gives it: a stored value equal to the default
  resolves the same as no stored value, and only one of them follows the next release.

### 6. Backends receive the resolved value and spell it themselves

- One resolver, in the engine. A backend never reads the stored key or the declared default and
  never re-derives the rule.
- The three render sites named in the context must agree, or `sq check` reports the pointer as
  drifted forever. The item-less managed writer is handed the resolved values by the service, the
  way `skill_paths` and `role_skills` already reach it. Before a skill is indexed (the first
  write of `sq init`) it resolves to its declared default, since nothing can be stored on an item
  that does not exist yet.
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

- **ADR-781**: the skill pointer's contents grow from two values to three under its containment
  rule.
- **ADR-492**: a system skill stays template-owned. The one value an operator may set on it is
  the choice of clause 3.
- **ADR-75 / ADR-133**: the backend boundary is unchanged; a host key stays inside its backend.
- The stored `origin` of a skill is not an input to anything here.

## Consequences

- No schema bump and no migration: nothing is stamped on any skill, an absent key means the
  declared default, and an older package ignores an unknown `extra` key (inferred from `extra`
  being a free mapping; not driven).
- After an upgrade and before the next `sq sync`, `sq check` warns that every system skill's
  pointer has drifted, because the fresh render now carries a line the file lacks (inferred from
  the byte comparison in `backend_entry_drift`). That is the existing prompt to sync and it clears
  on sync. It is a warning, so the exit code does not change.
- The first sync after an upgrade rewrites every system skill pointer. Every `/name` a person
  used to type for a bundled skill stops working on Claude Code, by design.
- A release that changes a bundled default reaches a squad on its next `sq sync`, for every skill
  on which the squad stored nothing, with the same drift warning in between. A skill carrying the
  squad's own value does not move. The changelog owes the line, and `show` tells a squad which
  case each skill is in.
- The choice belongs to the skill item. A per-type skill created again after its type was dropped
  or renamed is a new item and starts from the declared default.
- Setting the value on a system skill needs the exemption of clause 3 wherever the system-skill
  write refusal is enforced, and `sq skill <addr> update` has to exist.
- The preload claim rests on documentation. A hidden skill still arriving in a subagent that
  lists it has to be seen once on a real host before the default ships.

## Alternatives rejected

- **Deriving the default from origin.** It ties a behaviour to a provenance label and gives every
  bundled skill one answer for good: no release could make a single bundled skill invocable
  without changing what `system` means.
- **Stamping the default on every skill.** A sync would then either reassert it, overwriting a
  squad's choice, or leave it, so that no release could ever change a default.
- **Storing only a value that differs from the default.** Smaller, and it loses the squad that
  chose today's default on purpose.
- **A per-skill table in the playbook or workflow override.** A second override surface beside
  the frontmatter with a precedence to define, nothing in the bundled document to diff against,
  and a spec key naming corpus items by slug.
- **A list in `.squads.toml`.** The same dangling reference, in a file that holds no entity
  state.
- **Hiding by `sq-` prefix.** The prefix is not reserved to squads.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T18:35:00Z] Pierre Chat:
  - 2026-10-09: not accepted as written. System skills are not user-invocable now but may be in the future. This property is not derived from origin: it is an attribute of the skill, and it can be changed with the CLI. Still to settle: whether changing it writes the skill's frontmatter, or whether a bundled skill needs an override for it.
- [2026-10-09T18:40:05Z] Pierre Chat:
  - 2026-10-09: direction for the revision. The bundled definition declares each skill's default, and the CLI verb writes a squad's own value to that skill's frontmatter. A release can then change a bundled default without overwriting a squad's choice.
- [2026-10-09T18:46:37Z] Robert Architect:
  - Body rewritten on op-pierre's two rulings above (2026-10-09), and retitled, since "derives from origin" is no longer true. For @manager and op-pierre.
    
    **What changed**
    
    - The default is no longer derived from `origin`, and `origin` is not read anywhere in this decision.
    - A bundled skill's default is declared in its bundled definition. Concretely that is the engine's own declaration in `_interactions`, where a bundled skill's description and view name already live (read): one value for each of the three always-on skills, one shared by every `sq-<type>` skill. All `false` today. It is code, no override reaches it, and a release changes it there.
    - An author-defined skill has no bundled definition and takes one engine default: invocable.
    - A squad's own value is `extra.operator_invocable` in the skill's frontmatter, written only by `sq skill add` and `sq skill <addr> update`, through `--operator-invocable <yes|no|default>`. Sync, init, seeding and migrations never write it, as with `extra.is_default` on a role.
    - The earlier rule "never store a value equal to the default" is gone. A set is always stored, so a squad that chose today's default on purpose keeps it when a release changes that default. `default` removes the key.
    - `--json` gains a second key, `operator_invocable_set`, because "is this the squad's own value" can no longer be worked out from the rest of the row.
    
    **Unchanged:** the name `operator_invocable`, the backend boundary (Claude Code spells it `user-invocable: false`, AGENTS.md has no place for it), allowed on a system skill, strict boolean read, no schema bump and no migration.
    
    **To weigh before accepting**
    
    1. Every `sq-<type>` skill shares one declared default. A release can flip the three always-on skills one by one, and the per-type skills only together. A per-type bundled default would have to be a key in the playbook's `[types.<type>]`, which a playbook override could then reach: a second override surface beside the frontmatter.
    2. "Has a bundled definition" is decided by the test that already decides whether the engine supplies a skill's description (`is_system_skill`), not by `origin`. The two differ only for a stale skill of a dropped type.
    3. A stored choice never follows a release. A squad that wants to follow again has to run `--operator-invocable default`; `show` says which case a skill is in.
    4. The three-valued option is new CLI surface. I chose it over a `--x/--no-x` pair plus a reset flag.
    5. Still inferred from documentation, not driven: that a hidden skill preloads into a subagent that lists it.
- [2026-10-09T19:14:10Z] Pierre Chat:
  - 2026-10-09: the revision is accepted as written: one shared default for the per-type skills, a stored choice that never follows a release, and the three-valued option.
<!-- sq:discussion:end -->

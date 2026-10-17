---
id: FEAT-966
sequence_id: 966
type: feature
title: 'Skill invocability: declared default, squad''s own choice'
status: Done
author: product-owner
refs:
- MILE-934:targets
- FEAT-976
- FEAT-977:depends-on
- ADR-983:implements
description: 'A skill''s operator_invocable attribute: a bundled default plus a stored
  squad choice, rendered by the Claude Code backend'
subentities:
- local_id: US1
  title: As an adopter, I want reference skills hidden, my own skills visible
  status: Todo
- local_id: US2
  title: As squads, I want the Claude Code backend to render the value
  status: Todo
- local_id: US3
  title: As an adopter, I want to choose a skill's invocability with the CLI
  status: Todo
- local_id: US4
  title: As an AGENTS.md adopter, I want this change to have no effect on my output
  status: Todo
- local_id: US5
  title: As an existing squad, I want the new flag to reach me through sq sync alone,
    with no migration required
  status: Todo
- local_id: US6
  title: As an adopter, I want to see whether a skill's value is my own choice
  status: Todo
created_at: '2026-09-28T17:54:53Z'
updated_at: '2026-10-17T03:43:33Z'
---
<!-- sq:body -->
## Problem

Every skill the Claude Code backend writes lands as a `.claude/skills/<name>/SKILL.md`
pointer, and Claude Code lists every one of those in the user's `/` slash menu —
the bundled cross-role skills, every per-item-type `sq-<type>` skill, and any
author-defined skill a project adds. Most of that list is agent reference material: the
roster's own role definitions already preload it through each agent's `skills:` frontmatter, and
no human is meant to type a slash command for it. Only author-defined skills are genuine
user actions. The menu is cluttered with entries nobody runs by hand.

## Outcome

Whether a skill is offered to the person at the keyboard is the skill's own attribute,
`operator_invocable`: the value stored on the skill when the squad has chosen one, otherwise the
default its bundled definition declares. Origin is not read, and the slug's spelling plays no
part. A bundled skill's default is declared in the engine beside its description (false for every
bundled skill today), so a later release can change it; an author-defined skill has no bundled
definition and is invocable. A squad changes any skill's value with the CLI, and a stored choice
is never overwritten by a sync or a release.

The Claude Code backend spells the resolved value in the SKILL.md pointer frontmatter with the
host's own key: `user-invocable: false` drops a skill from the `/` menu and stops `/name` from
running it. `disable-model-invocation` is never written, since it would stop the preload these
skills exist for. The host key appears only in the Claude Code backend's pointer template.

## Scope

- The `operator_invocable` attribute: a declared default per bundled skill, a squad's stored
  value, and one resolution rule (stored value, else declared default).
- The rule today: every bundled skill (`squads`, `sq-memory`, `greeting` and every `sq-<type>`
  skill) defaults to not operator-invocable; every author-defined skill stays invocable.
- `sq skill add` and `sq skill <addr> update` take `--operator-invocable <yes|no|default>`.
- `sq skill <addr> show` and its `--json` tell what the value is and whether it is the squad's.
- Claude Code backend (`_backends/_claude_code`): the skill pointer template
  (`pointer_skill.md.j2`) emits `user-invocable: false` for a skill resolved not invocable and
  nothing for an invocable one (Claude Code treats an absent key as visible). The pointer stays a
  pointer: no content beyond the flag and the existing identity/description fields moves into
  `.claude/`.
- AGENTS.md backend (`_backends/_agents_md`): has no per-skill entry and no slash-menu concept,
  so it writes nothing and warns nothing for this value, and states in its own definition that it
  has no place for it.
- `sq sync` carries the resolved value onto every system skill pointer. No schema bump, no
  migration: nothing is stamped on any skill, and an absent value means the declared default.

## Out of scope

- `disable-model-invocation` / preload suppression for any skill.
- Retiring, renaming, or merging any skill.
- Any backend other than Claude Code, beyond confirming AGENTS.md is unaffected.
- A per-type bundled default: every `sq-<type>` skill shares one declared default.
- The `-dev` pseudo-role / "roles, not slugs" work also on this milestone — unrelated.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 966 add-story "As a <role>, I want … so that …"`; track with `sq feature 966 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an adopter, I want reference skills hidden, my own skills visible

<!-- sq:story:US1:body -->
As an adopter, I want the reference skills hidden from the slash menu, and my own skills left visible.

Acceptance:
- A bundled skill's default comes from its bundled definition in the engine, declared beside its description and view name: one value for each of squads, sq-memory and greeting, and one shared by every sq-<type> skill. All are false today. The default is never read off the slug, and origin is not read.
- An author-defined skill has no bundled definition and is invocable, including one named with an sq- prefix (for example sq-onboarding) and this repo's own releasing-squads.
- Nothing is stamped on any skill by init, sync, seeding or a migration: a freshly initialised squad's skill items carry no operator_invocable key.
- A guard test fails when a bundled skill has no declared default.
- On a fresh sq init and after sq sync, the SKILL.md pointer for every bundled skill carries user-invocable: false, including the sq-<type> skill of a type the project added; an author-defined skill's pointer carries no such line.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As squads, I want the Claude Code backend to render the value

<!-- sq:story:US2:body -->
As squads, I want the Claude Code backend to render the resolved value, wherever a pointer is written.

Acceptance:
- pointer_skill.md.j2 emits user-invocable: false in frontmatter when the resolved value is not invocable and omits the line when invocable; the host key is spelled nowhere else in the engine, the frontmatter, the CLI or any --json output.
- The three places that render a skill pointer agree: the item-less managed writer used by init and sync, the item-scoped entry written by regen and add, and the pure render that sq check compares against the file on disk. A test writes a pointer through each and shows sq check reports no drift on any of them, before and after a stored value is set; a mismatch would read as drift forever.
- Before a skill has an item (the first write of sq init), it renders at its declared default.
- A role's skills: preload list is unaffected either way, and disable-model-invocation is never written.
- A hidden skill still preloads into a subagent whose skills: list names it. This is inferred from the host documentation, which says only disable-model-invocation prevents preload; it must be seen once on a real host before the default ships.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an adopter, I want to choose a skill's invocability with the CLI

<!-- sq:story:US3:body -->
As an adopter, I want to choose a skill's invocability with the CLI, so my own conventions win and survive upgrades.

Acceptance:
- sq skill add and sq skill <addr> update take --operator-invocable <yes|no|default>. yes and no store the value on the skill even when it equals the current default; default removes the stored value so the skill follows its declared default again; leaving the option out stores nothing and changes nothing. Any other text is refused with exit 1 and nothing written (it must not be coerced to false).
- It works on a project skill and on a system skill; on a system skill it is the only update option accepted (see the verb parity feature for the refusal it is exempt from).
- A change through either verb regenerates that skill's pointer: after yes on a bundled skill its pointer has no user-invocable line; after no on an author-defined skill it has user-invocable: false; after default both return to their declared default.
- sq init, sq sync, seeding and migrations never write the key. The stored value survives sq sync and survives deleting the index and running sq repair.
- Release behaviour: a test changes a bundled skill's declared default and shows that a skill with a stored value keeps it while one with none follows the new default after sq sync.
- Only a YAML boolean stored by hand counts; any other stored value resolves as if absent.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an AGENTS.md adopter, I want this change to have no effect on my output

<!-- sq:story:US4:body -->
As an AGENTS.md adopter, I want this change to have no effect on my output.

Acceptance:
- The AGENTS.md backend has no per-skill entry and no slash-menu concept. It writes nothing for operator_invocable, emits no warning for it, and says in its own definition that it has no place for the value.
- A regression test pins that a squad regenerated under the AGENTS.md backend produces byte-for-byte the same AGENTS.md as before, with and without a stored operator_invocable value on a skill.
- A backend written against the existing backend interface needs no change.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an existing squad, I want the new flag to reach me through sq sync alone, with no migration required

<!-- sq:story:US5:body -->
As an existing squad, I want the new line to reach me through sq sync alone, with no migration.

Acceptance:
- No schema bump and no migration runbook. After an upgrade, sq sync rewrites every system skill pointer and sq check is clean after that sync.
- Between the upgrade and the first sq sync, sq check warns that each system skill pointer has drifted; that warning is the expected prompt to sync, it clears on sync, and it does not change the exit code.
- The release notes say that after the first sync a bundled skill's /name no longer runs on Claude Code, and that a later release that changes a bundled default reaches a squad on its next sync for every skill on which the squad stored nothing.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — As an adopter, I want to see whether a skill's value is my own choice

<!-- sq:story:US6:body -->
As an adopter, I want to see what a skill's value is and whether it is my own choice, so I know which skills will follow a later release.

Acceptance:
- sq skill <addr> show prints the resolved value and says whether it is the squad's own or the declared default.
- sq skill <addr> show --json carries operator_invocable (the resolved boolean) and operator_invocable_set (true when the skill stores the squad's own value) on every row. A skill with a stored value equal to its default shows set true; the same skill after --operator-invocable default shows set false and the same resolved value.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-28T18:06:06Z] Pierre Chat:
  - Defaults confirmed: greeting is hidden too. Not user-invocable: every sq-<type>, squads, sq-memory, greeting. releasing-squads and author-defined skills stay invocable.
- [2026-09-28T18:08:20Z] Pierre Chat:
  - Correction: releasing-squads is this repo's own authored skill, not a bundled one. The rule is that every bundled skill is not user-invocable and every author-defined skill stays invocable.
- [2026-10-09T15:35:46Z] Nina Product:
  - 2026-10-09 readiness pass: stays Draft. Pierre's rule (every bundled skill hidden, every author-defined skill invocable; greeting included) is already in body and stories; US1 now names the bundled set and the sq- prefix trap. Missing, owed by @architect: where the per-skill user-invocable property is declared and how a project overrides it. No bundled skill is declared in any spec (read: bundled_skill_slugs is code, sq-type skills derive from the playbook, no per-skill customization surface exists), so US3 cannot be tested as written and the spec/override half of the Outcome has nowhere to live. Related: FEAT-976 stores origin on every skill; whether the default should resolve from that field (system hidden, project visible) is part of the same ruling.
- [2026-10-09T18:28:20Z] Robert Architect:
  - @product-owner Ruled in ADR-983 (Proposed, for op-pierre).
    
    **Ruling.** There is no per-skill declaration to find a home for: the default is derived from the stored `origin` (`system` resolves to not invocable, `project` to invocable), so nothing is stored for it and no spec key exists. A project's exception, in either direction, is one optional boolean on the skill item, `extra.operator_invocable`, set through `sq skill add` and `sq skill <addr> update` and allowed on a system skill. The engine property is named `operator_invocable`; `user-invocable` is the Claude Code backend's spelling and appears only in its pointer template.
    
    **What has to change here**
    
    - Outcome and Scope: drop "declared vocabulary the engine resolves from the active spec" and "a per-skill `user-invocable` property in the declared vocabulary". Say instead that it resolves from origin with a stored exception, and use `operator_invocable` everywhere outside the Claude Code backend bullet.
    - US1: the default comes from origin, never from the slug and never from a recomputed "is system" test. Nothing is stamped on a bundled skill. Your acceptance (every bundled pointer carries the line, an `sq-` prefixed authored skill does not) stands.
    - US2: add that the three render sites agree: the managed writer, the item entry, and the pure render `sq check` compares against disk (read: `_write_managed_skill`, `generate_skill_entry`, `render_skill_entry` in `_backends/_claude_code/_backend.py`). A mismatch shows as a pointer that is drifted forever.
    - US3, rewritten against the real surface: `--operator-invocable` / `--no-operator-invocable` on `sq skill add` and `sq skill <addr> update`; works on a project skill and on a system skill, where every other `update` option is still refused; setting the default value removes the key; the exception survives `sq sync` and an index rebuild by `sq repair`; `show` and `--json` carry the resolved value.
    - US4: keep. Add that the AGENTS.md backend states in its own definition that it has no place for the value, and emits no warning.
    - US5 and the body's "`sq check` stays clean": not as written. Between the upgrade and the first `sq sync`, `sq check` warns that each system skill pointer has drifted, because it compares a fresh render with the file byte for byte (inferred from read: `backend_entry_drift`). Make it "clean after `sq sync`; before it, the drift warning is the expected prompt".
    - "No schema bump, no migration" is true of this feature's own key. The feature now needs origin to exist, and FEAT-976 brings a migration of its own.
    - "Confirmed against the Claude Code docs": the menu half is (checked today: `user-invocable`, default `true`, `false` hides it from `/` and stops `/name`). The preload half is inferred: the docs say only `disable-model-invocation` blocks preloading. Add an acceptance line that a hidden skill is seen to preload into a subagent on a real host before this ships.
    - Refs: make FEAT-976 `depends-on`, add `depends-on` FEAT-977 (it introduces `sq skill update`), add `implements` ADR-983.
    - FEAT-977 US1 and US4 say `update` on a system skill exits 1. They need the one exemption from ADR-983 clause 3, on the same footing as comments and pronouns. Not edited by me.
    
    **For op-pierre to weigh.** Reading `origin` for this default makes origin an input to one behaviour, where the write refusal deliberately does not read it. A system skill whose view the project dropped is writable again and still hidden by default. If a system skill should never be shown, clause 3 shrinks to project skills only and the exemption above disappears.
- [2026-10-09T18:46:38Z] Robert Architect:
  - @product-owner ADR-983 was rewritten on op-pierre's rulings of 2026-10-09 (its discussion) and retitled. It is still Proposed. This replaces my earlier change list where the two differ.
    
    **Ruling now.** `operator_invocable` is an attribute of the skill. A bundled skill's default is declared in its bundled definition, in code beside its description: `false` for the three always-on skills and for every `sq-<type>` skill. An author-defined skill defaults to invocable. A squad's own value is stored in the skill's frontmatter (`extra.operator_invocable`) and only a verb writes it, so a release can change a bundled default without touching a squad's choice. Resolution is the stored value, else the declared default.
    
    **Withdrawn from my earlier list**
    
    - "The default comes from origin". It does not, and nothing here reads `origin`.
    - "Make FEAT-976 `depends-on`". Not needed for the default. Keep a plain ref: the only link left is that the system-skill write refusal has to let this one option through.
    - "Setting the default value removes the key". Reversed: a set is always stored.
    - "`--operator-invocable` / `--no-operator-invocable`". Replaced by one option, below.
    
    **What has to change here, in full**
    
    - Outcome and Scope: drop "declared vocabulary the engine resolves from the active spec" and "a per-skill `user-invocable` property in the declared vocabulary". Use `operator_invocable` everywhere outside the Claude Code backend bullet, and say it is a declared default plus a squad's stored value.
    - US1: the default is the one the skill's bundled definition declares, never read off the slug. Nothing is stamped on any skill. Your acceptance stands (every bundled pointer carries the line; an authored skill does not, including one whose slug begins with `sq-`). Add: a guard fails when a bundled skill has no declared default.
    - US2: add that the three render sites agree: the managed writer, the item entry, and the pure render `sq check` compares against disk (read: `_write_managed_skill`, `generate_skill_entry`, `render_skill_entry`).
    - US3, rewritten: `--operator-invocable <yes|no|default>` on `sq skill add` and `sq skill <addr> update`. `yes` and `no` store the value even when it equals the current default; `default` removes it; leaving the option out stores nothing. It works on a system skill, where every other `update` option is still refused. `sq init`, `sq sync` and migrations never write the key. The value survives `sq sync` and an index rebuild by `sq repair`. A test changes a bundled default and shows that a skill with a stored value keeps it and one without follows.
    - Read surfaces: `show` prints the resolved value and whether it is the squad's own; `--json` carries `operator_invocable` and `operator_invocable_set`.
    - US4: unchanged from my earlier note (no warning from the AGENTS.md backend; it states it has no place for the value).
    - US5 and the body's "`sq check` stays clean": still wrong as written. Between an upgrade and the next `sq sync`, `sq check` warns that each system skill pointer has drifted (inferred from read: `backend_entry_drift`). Make it "clean after `sq sync`". "No schema bump, no migration" is now true without qualification.
    - Preload: keep the acceptance line that a hidden skill is seen to preload into a subagent on a real host. The docs confirm the menu half only.
    - Refs: `depends-on` FEAT-977 (it introduces `sq skill update`), `implements` ADR-983.
    - FEAT-977 US1 and US4 still need the one exemption for this option on a system skill. Not edited by me.
    - Implementation hazard for the task: the generic `--set` boolean coercion turns any unrecognised text into `false` (read: `_models/_metadata.py::coerce`). This option must not go through it.
- [2026-10-09T19:18:25Z] Nina Product:
  - 2026-10-09 aligned with ADR-983 (Accepted) and the architect's second list: operator_invocable as a declared default plus stored choice, origin not read; US1-US5 rewritten with testable acceptance (guard, three render sites agree, three-valued option, AGENTS.md silent, clean after sq sync, preload to be seen on a real host); new US6 for the read surfaces; refs depends-on FEAT-977 and implements ADR-983, FEAT-976 stays a plain ref. Moved to Ready.
- [2026-10-16T19:58:52Z] Olivia Lead:
  - Task TASK-1072 (Draft) carries the breakdown; dependencies in its body.
<!-- sq:discussion:end -->

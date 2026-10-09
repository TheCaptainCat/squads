---
id: FEAT-966
sequence_id: 966
type: feature
title: Declare skill user-invocability; hide reference skills
status: Draft
author: product-owner
refs:
- MILE-934:targets
- FEAT-976
subentities:
- local_id: US1
  title: As an adopter, I want type-bound skills hidden from the slash menu
  status: Todo
- local_id: US2
  title: As squads, I want the Claude Code backend to render the user-invocable flag
  status: Todo
- local_id: US3
  title: As an adopter, I want to override a skill's user-invocable default per project
    so my own conventions win
  status: Todo
- local_id: US4
  title: As an AGENTS.md adopter, I want this change to have no effect on my output
  status: Todo
- local_id: US5
  title: As an existing squad, I want the new flag to reach me through sq sync alone,
    with no migration required
  status: Todo
created_at: '2026-09-28T17:54:53Z'
updated_at: '2026-10-09T18:46:38Z'
---
<!-- sq:body -->
## Problem

Every skill the Claude Code backend writes lands as a `.claude/skills/<name>/SKILL.md`
pointer, and Claude Code lists every one of those in the user's `/` slash menu — the
bundled cross-role skills, every per-item-type `sq-<type>` skill, and any author-defined
skill a project adds. Most of that list is agent reference material: the roster's own role
definitions already preload it through each agent's `skills:` frontmatter, and no human is
meant to type a slash command for it. Only author-defined skills are genuine user actions.
The menu is cluttered with entries nobody runs by hand.

## Outcome

Whether a skill is user-invocable is declared vocabulary the engine resolves from the
active spec, never inferred from a slug's spelling — the same discipline the ref-kinds and
roster work already hold everywhere else. The Claude Code backend renders that declaration
into the SKILL.md pointer frontmatter Claude Code's own contract defines: `user-invocable:
false` drops a skill from the `/` menu while it keeps preloading through any subagent's
`skills:` list untouched (confirmed against the Claude Code docs — this is the one field
that does exactly that; `disable-model-invocation: true` also blocks preload and is out of
reach here, since these skills must stay preloadable). A project can override the default
for any individual skill.

## Scope

- A per-skill `user-invocable` property in the declared vocabulary, with a resolvable
  default per skill and a project override.
- The rule: every bundled skill defaults to not user-invocable (agent reference material);
  every author-defined skill a project adds stays user-invocable by default.
- Claude Code backend (`_backends/_claude_code`): the skill pointer template
  (`pointer_skill.md.j2`) emits `user-invocable: false` in frontmatter for a skill resolved
  hidden; a visible skill's pointer is unchanged (Claude Code treats an absent key as
  visible). The pointer stays a pointer — no content beyond the flag and the existing
  identity/description fields moves into `.claude/`.
- AGENTS.md backend (`_backends/_agents_md`): has no per-entry pointer and no slash-menu
  concept at all — its own module docstring already states the expressible surface is
  identity plus prose only, no capability-boundary field of any kind. This feature adds no
  behavior there; a regression test pins that a squad regenerated under this backend is
  unaffected.
- `sq sync` regenerates the flag onto every existing pointer like any other managed-file
  field. No schema bump, no migration: an adopter picks this up on their next sync.

## Out of scope

- `disable-model-invocation` / preload suppression for any skill — bundled skills must
  stay preloadable through a subagent's `skills:` list, so this field is never used here.
- Retiring, renaming, or merging any skill.
- Any backend other than Claude Code, beyond confirming AGENTS.md is unaffected.
- The `-dev` pseudo-role / "roles, not slugs" work also on this milestone — unrelated.

## Acceptance

- On a fresh `sq init` and on `sq sync` for an existing squad, the SKILL.md pointer for
  every bundled skill carries `user-invocable: false`; every author-defined skill's
  pointer carries no such line.
- A project-level override flips a named skill's invocability and survives `sq sync`.
- A squad running the AGENTS.md backend produces byte-for-byte the same output as before
  this feature.
- `sq check` stays clean on a squad carrying the new field.
- No migration runbook is added; the change reaches an existing squad through its next
  `sq sync` alone.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 966 add-story "As a <role>, I want … so that …"`; track with `sq feature 966 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an adopter, I want type-bound skills hidden from the slash menu

<!-- sq:story:US1:body -->
Declare a per-skill user-invocable property in the vocabulary, resolved per skill, never off a slug spelling.

The rule: every bundled skill defaults to not user-invocable (agent reference material): squads, sq-memory, greeting and every generated sq-<type> skill. Every author-defined skill a project adds stays user-invocable by default, whatever its slug looks like -- this repo's own releasing-squads is author-defined and stays invocable. A project can override the default for any individual skill.

Acceptance: sq init / sq sync writes user-invocable: false into the SKILL.md frontmatter of every bundled skill, including a sq-<type> skill for a type a project added; an author-defined skill's pointer carries no such line, including one whose slug begins with sq-.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As squads, I want the Claude Code backend to render the user-invocable flag

<!-- sq:story:US2:body -->
The Claude Code skill pointer template (pointer_skill.md.j2) emits user-invocable: false in frontmatter when the resolved declaration says hidden; omits the line when visible (Claude Code treats an absent key as visible, per its docs). The pointer stays a pointer (invariant #5) — only the flag and the existing identity/description fields live in .claude/.

A hidden skill still preloads through any subagent's skills: list untouched — this is the field that hides from the / menu without touching preload; disable-model-invocation (which would also block preload) is explicitly not used.

Acceptance: generated pointers for hidden skills carry the line; visible ones don't; a role's skills: preload list is unaffected either way.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an adopter, I want to override a skill's user-invocable default per project so my own conventions win

<!-- sq:story:US3:body -->
A project can override the default user-invocable value for any individual skill, the same way other per-skill customization already works today.

Acceptance: overriding one skill's default and running sq sync produces a pointer reflecting the override, and the override survives a repeat sync.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an AGENTS.md adopter, I want this change to have no effect on my output

<!-- sq:story:US4:body -->
The AGENTS.md backend (_backends/_agents_md) has no per-entry pointer file and no slash-menu concept — its own module docstring already states the expressible surface is identity plus prose only, with no capability-boundary field of any kind. This feature adds no behavior there.

Acceptance: a regression test pins that a squad regenerated under the AGENTS.md backend produces byte-for-byte the same AGENTS.md as before this feature.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an existing squad, I want the new flag to reach me through sq sync alone, with no migration required

<!-- sq:story:US5:body -->
No schema bump and no migration runbook: sq sync regenerates the flag onto every existing pointer exactly like any other managed pointer-frontmatter field.

Acceptance: an existing squad on the current schema picks up the flag on its next sq sync alone; sq check stays clean throughout.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
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
<!-- sq:discussion:end -->

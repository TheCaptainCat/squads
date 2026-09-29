---
id: FEAT-966
sequence_id: 966
type: feature
title: Declare skill user-invocability; hide reference skills
status: Draft
author: product-owner
refs:
- MILE-934:targets
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
updated_at: '2026-09-28T18:09:12Z'
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

The rule: every bundled skill defaults to not user-invocable (agent reference material); every author-defined skill a project adds stays user-invocable by default. A project can override the default for any individual skill.

Acceptance: sq init / sq sync writes user-invocable: false into the SKILL.md frontmatter of every bundled skill; an author-defined skill's pointer carries no such line.
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
<!-- sq:discussion:end -->

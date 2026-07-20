---
id: BUG-490
sequence_id: 490
type: bug
title: Custom skills can't carry authored content or be scoped to specific roles
status: Verified
author: manager
priority: high
created_at: '2026-07-20T08:24:46Z'
updated_at: '2026-07-20T12:33:48Z'
---
<!-- sq:body -->
## What we tried to do

Author a **release-process skill** — the gates, the prep steps, and how to draft (not publish)
a release — and preload it for the manager, devops, and tech-writer roles, so those agents follow
one runbook. Neither half is currently possible.

## Gap 1 — a custom skill can't carry authored content

`sq skill add NAME` accepts only `--desc`, `--when-to-use`, `--allowed-tools`, `--parent`. There is
no `--body`/`--file`, and the addressed subgroup (`sq skill <addr> …`) exposes only
`show`/`refs`/`ref add`/`ref rm`/`regen`/`rm` — no `body` verb. A custom skill therefore renders
from the generic `agents/skill.md.j2` skeleton: title, the `--desc` line, an optional when-to-use
block, and an empty `## Instructions` heading. There is no supported way to fill in the actual
instructions:

- Hand-editing the generated `.md` is disallowed (sq-managed file), and `sq skill <n> regen` /
  `sq sync` regenerates the body from the template, discarding any manual content.
- Bundled skills escape this because each has its own dedicated template (`squads_skill.md.j2`,
  `memory_skill.md.j2`, …); an author-defined skill has no such hook, and project-level template
  overrides are the explicitly-deferred build item.

## Gap 2 — a custom skill can't be scoped to specific roles

The agent-pointer `skills:` frontmatter is generated from `interactions.skills_for_role(slug)`
(`_backends/_claude_code/_backend.py`), which returns a hardcoded set: the always-on skills
(`squads`/`greeting`/`sq-memory`) plus the role's item-type skills. There is no CLI or data path to
say "role X also preloads custom skill Y", and because the list is recomputed on every `sq sync`,
editing a role item's skills by hand is clobbered.

## Expected

A supported path to (a) author a custom skill's instructional body, and (b) declare which roles
preload it (and/or mark it global so the main agent picks it up). Both are needed for an
author-defined skill to be useful at all.

## Pointers

- `src/squads/_cli/_skill.py` — `skill_add` options; addressed subgroup has no `body` command.
- `src/squads/_rendering/templates/agents/skill.md.j2` — the skeleton a custom skill renders to.
- `src/squads/_interactions/__init__.py` — `skills_for_role` (hardcoded membership).
- `src/squads/_backends/_claude_code/_backend.py` — builds each role pointer's `skills` from `skills_for_role`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T08:30:27Z] Pierre Chat:
  - Holding the 0.10.1 release until this is resolved and the release-process skill is ready — 0.10.1 ships with the custom-skill authoring + role-scoping fix and that skill, not before.
- [2026-07-20T08:38:46Z] Pierre Chat:
  - Skipping the 0.10.1 patch: this work ships as 0.11.0 (new capability + schema bump). The held docs/concision draft folds into 0.11.0.
- [2026-07-20T12:33:46Z] Catherine Manager:
  - Resolved by FEAT-491 (custom skills: authored bodies + role scoping). Verified end-to-end by the dogfood: SKILL-508 'releasing-squads' authored with a persistent body and scoped to manager/devops/tech-writer, appearing in exactly those three role pointers and no others. Schema 0.11 + migration ship with it.
<!-- sq:discussion:end -->

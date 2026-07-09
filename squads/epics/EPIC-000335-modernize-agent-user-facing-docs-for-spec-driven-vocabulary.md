---
id: EPIC-335
sequence_id: 335
type: epic
title: Modernize agent/user-facing docs for spec-driven vocabulary
status: Draft
author: product-owner
refs:
- FEAT-326:depends-on
- EPIC-325
created_at: '2026-07-08T15:09:25Z'
updated_at: '2026-07-08T15:11:09Z'
---
<!-- sq:body -->
## Vision

FEAT-334 identified that `workflow.md.j2` (the workflow cheatsheet) hardcodes
specific type names (`feature`/`task`/`story`/`subtask`) instead of describing
the loaded playbook + roster generically. Reading the surrounding surfaces
(the CLAUDE.md managed section in particular — `claude/claude_section.md.j2`
carries the near-identical `authoring_owner('feature')` /
`authoring_owner('task')` / `item_subentity_kind(...) == 'story'|'subtask'`
pattern almost verbatim) makes clear this is not an isolated defect in one
template: it's a recurring pattern across the set of agent- and user-facing
docs and generated surfaces this project ships, most of which were written
before the workflow engine, spec, and playbook became config-driven
(EPIC-206, ADR-322, ADR-323, EPIC-325).

This epic is the umbrella for bringing every such surface up to the
generic-vocabulary era: each one either genericized (spec/playbook-driven,
correct under any customized vocabulary), deduplicated (one authoritative
source, others reduced to pointers or removed), or explicitly redefined in
altitude/scope so two surfaces stop re-narrating the same content at the same
depth.

## Recurring defects to fix, wherever found

1. **Hardcoded type/status/role names** that go stale, wrong, or silently
   blank once a project's spec renames, drops, or adds vocabulary.
2. **Duplication across surfaces** — the same guidance re-narrated by hand in
   more than one place, so it drifts when one copy is updated and the other
   isn't.
3. **Unclear or overlapping altitude** — it's not evident, surface to
   surface, which one is the source of truth for a piece of guidance and
   which is a pointer/summary/deep-dive of it.

## Structure

- FEAT-334 (cheatsheet redesign) is the first concrete piece, now grouped
  under this epic — it fixes the `workflow.md.j2` "Team workflow" section
  specifically and establishes the cheatsheet's distinct altitude relative to
  the `sq-<type>` skills.
- A companion audit feature enumerates every other candidate surface (docs/,
  the CLAUDE.md/AGENTS.md managed sections, the per-type skills, `sq`
  `--help` text, role/skill pointer files, `sq workflow` output, …), captures
  audience/altitude/hardcoding/duplication per surface, and recommends a fix
  for each — genericize, dedupe, redefine altitude, or leave as-is. Further
  features to actually fix each flagged surface get scoped once the audit
  findings land; this epic is not pre-committing to fixing every surface
  found, only to knowing the full picture and to landing the cheatsheet fix.

## Sequencing

All work under this epic depends on FEAT-326 (remove the `ItemType`/`Status`
enums) — auditing or genericizing docs against a vocabulary that isn't yet
fully spec-driven risks redoing the work once FEAT-326 lands.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-08T15:11:09Z] Nina Product:
  - Scope broadened by op-pierre: the workflow-cheatsheet fix (FEAT-334) is the trigger, not the whole story — stood up this epic to modernize every agent/user-facing doc + generated surface for the spec-driven vocabulary era.
  - Structure: FEAT-334 (cheatsheet redesign, first concrete fix) reparented under this epic; FEAT-336 (audit) added as a sibling to enumerate every other surface and flag the same three defects (hardcoded vocab, cross-surface duplication, unclear altitude).
  - Confirmed one duplicate hardcoding hit already during scoping: claude/claude_section.md.j2 (the CLAUDE.md managed section) carries the same authoring_owner('feature')/('task') branch pattern as workflow.md.j2, almost verbatim — a concrete data point seeded into FEAT-336's candidate list.
  - All Draft/backlog, depends-on FEAT-326. @architect for FEAT-336 at dispatch (surveying the codebase + docs tree end to end), @tech-writer for the docs/ half; @tech-lead to break FEAT-334 into tasks once FEAT-326 lands.
<!-- sq:discussion:end -->

---
id: REV-286
sequence_id: 286
type: review
title: Review TASK-000279 — spec-derive retype-target list + authoring prose
status: Approved
author: reviewer
refs:
- TASK-279
subentities:
- local_id: F1
  title: Jinja capitalize lowercases acronym role titles (cosmetic)
  status: Open
  severity: low
- local_id: F2
  title: Jinja capitalize lowercases acronym role titles (cosmetic)
  status: WontFix
  severity: low
created_at: '2026-07-02T12:54:27Z'
updated_at: '2026-07-02T12:55:57Z'
---
<!-- sq:body -->
Independent review of TASK-279 (final FEAT-211 task), read-only against the working tree diff vs `a4b4aa8` plus new `tests/test_workflow_authoring_prose.py`.

## Scope verified
- **Part A** — the `Valid targets:` line moved out of `workflow_static.md.j2` into a spec-driven loop (over `spec.items` where `not is_meta`); the rest of the static partial (retype mechanics, remove-vs-cancel, ref-kinds table) stayed literal. Confirmed only that one line was dynamized.
- **Part B** — `authoring_owner()` / `parent_chain()` in `_interactions/__init__.py`, registered as Jinja globals, drive the PO→feature / tech-lead→task bullets + the epic→feature→task line. Gating is correct: blocks are silently OMITTED (never fabricated) when a type has no single in-lane owner (`in_lane_owner` != 1), when the owner has no bundled catalog title (dev sentinel raises `RoleNotFoundError` → None), or when the shape assumptions (`subentity_kind`, `parent_required`) don't hold.
- **Every consumer spec-driven** — AGENTS.md (`agents_section.md.j2`) and the squads skill (`squads_skill.md.j2`) both `{% include "workflow.md.j2" %}`, so they inherit the derivation. CLAUDE.md's separate hand-written block (`claude_section.md.j2`) was rewired the same way and `spec=` is threaded into its render call in `_backend.py` (resolved once at line 72, never None). No consumer left hardcoded.
- **Byte-identical bundled output (FEAT-013 contract)** — independently rendered a bundled squad from `a4b4aa8` (git worktree) vs the working tree, roster held constant (`--default-names`). CLAUDE.md, AGENTS.md byte-identical; the squads skill identical except its own created_at/updated_at timestamps (14s apart between runs — expected, content identical); `sq workflow` identical.
- **TASK-261 test change** — the byte-identical comparison window moved from `## Retype` to `**Status behaviour:**`, skipping only the retype heading/intro/code-block/target-list. That skipped region is still guarded elsewhere (`test_static_sections_present_*` assert the header; `test_retype_section_exact_intro` asserts the intro line byte-for-byte; the code block is static template text with no Jinja so cannot vary; the full bundled golden still locks it). New `test_retype_target_list_includes_custom_type` positively asserts a custom type AND all 7 builtins appear. Not a meaningful weakening.
- **Scope flag** — `CREATE_LANES` stays a fixed bundled-role dict; a custom type with no lane gets no authoring bullet (graceful, tested). Deferring full custom-role/lane support to a separate feature is the right call — custom roles are not a spec concept today.
- **Tests** — 14 new tests genuinely prove spec-derivation: the synthetic-rename proof reparents `task` onto a new `initiative` type and asserts the prose tracks it while the old `feature`/`FEAT` strings are gone. Graceful omission covered for 3 cases. pyright/ruff clean; targeted suites green (authoring_prose, renderer_261, golden_rendered_output, lane_derivation).

## Verdict
Approved. The static/dynamic split is respected, gating never fabricates, all consumers are consistent, and the FEAT-013 byte-identical contract holds. One LOW cosmetic finding (Jinja `capitalize` acronym edge) — non-blocking.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 286 add-finding "…" --severity high`; track with `sq review 286 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Jinja capitalize lowercases acronym role titles (cosmetic) |
| F2 | 🟢 low | WontFix |  | Jinja capitalize lowercases acronym role titles (cosmetic) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Jinja capitalize lowercases acronym role titles (cosmetic)

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
workflow.md.j2 renders the owner role title through Jinja's `| capitalize`, which lowercases the tail. A custom owner role whose title is an acronym (e.g. 'QA') would render 'Qa engineer'. Harmless for the bundled team — only product-owner/tech-lead reach this path and neither is an acronym — and CLAUDE.md's claude_section path uses the raw title (no capitalize) so it's unaffected. Pure cosmetic edge for a hypothetical custom-role-authoring project, which is not a supported spec concept yet. Flagging as a note for the eventual custom-role/lane feature; non-blocking for TASK-279.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Jinja capitalize lowercases acronym role titles (cosmetic)

<!-- sq:finding:F2:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
Duplicate of F1 (accidental double add-finding). See F1.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

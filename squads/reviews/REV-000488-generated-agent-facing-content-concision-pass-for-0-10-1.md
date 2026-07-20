---
id: REV-488
sequence_id: 488
type: review
title: 'Generated agent-facing content: concision pass for 0.10.1'
status: Approved
author: tech-writer
subentities:
- local_id: F1
  title: Redundant repetition of 'memory vs shared' distinction in memory_skill.md.j2
  status: Fixed
  severity: medium
- local_id: F2
  title: Overexplained 'One fact per memory' section with restatement in memory_skill.md.j2
  status: Fixed
  severity: medium
- local_id: F3
  title: Over-detailed preamble in 'Working directly with operator' section of squads_skill.md.j2
  status: Fixed
  severity: medium
- local_id: F4
  title: Redundant preamble in 'Finding things across the board' section of squads_skill.md.j2
  status: Fixed
  severity: medium
- local_id: F5
  title: Redundant expanded greeting instructions in claude_section.md.j2
  status: Fixed
  severity: medium
- local_id: F6
  title: Redundant explanation after orchestration loop steps in claude_section.md.j2
  status: Fixed
  severity: medium
- local_id: F7
  title: Overexplained intro paragraph in memory_skill.md.j2
  status: Fixed
  severity: medium
- local_id: F8
  title: Padding in 'Check it at the start of a run' section of memory_skill.md.j2
  status: Fixed
  severity: medium
- local_id: F9
  title: Slightly redundant phrasing in 'Prune what's stale' section of memory_skill.md.j2
  status: Fixed
  severity: medium
- local_id: F10
  title: Redundant final paragraph in squads_skill.md.j2 'Common commands' section
  status: Fixed
  severity: medium
created_at: '2026-07-20T07:35:13Z'
updated_at: '2026-07-20T08:26:24Z'
---
<!-- sq:body -->
Concision and verbosity review of generated agent-facing templates and content for 0.10.1 release. Scope: workflow cheatsheet, skill bodies, role/operator text, managed sections. Primary focus: eliminate rambling, over-explanation, padding, redundancy. Secondary: check for staleness and inconsistency across templates.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 488 add-finding "…" --severity medium`; track with `sq review 488 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Fixed |  | Redundant repetition of 'memory vs shared' distinction in memory_skill.md.j2 |
| F2 | 🟡 medium | Fixed |  | Overexplained 'One fact per memory' section with restatement in memory_skill.md.j2 |
| F3 | 🟡 medium | Fixed |  | Over-detailed preamble in 'Working directly with operator' section of squads_skill.md.j2 |
| F4 | 🟡 medium | Fixed |  | Redundant preamble in 'Finding things across the board' section of squads_skill.md.j2 |
| F5 | 🟡 medium | Fixed |  | Redundant expanded greeting instructions in claude_section.md.j2 |
| F6 | 🟡 medium | Fixed |  | Redundant explanation after orchestration loop steps in claude_section.md.j2 |
| F7 | 🟡 medium | Fixed |  | Overexplained intro paragraph in memory_skill.md.j2 |
| F8 | 🟡 medium | Fixed |  | Padding in 'Check it at the start of a run' section of memory_skill.md.j2 |
| F9 | 🟡 medium | Fixed |  | Slightly redundant phrasing in 'Prune what's stale' section of memory_skill.md.j2 |
| F10 | 🟡 medium | Fixed |  | Redundant final paragraph in squads_skill.md.j2 'Common commands' section |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Redundant repetition of 'memory vs shared' distinction in memory_skill.md.j2

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
memory-vs-board boundary section consolidated from 180 words (~100 statements repeated) to 80 words: removed redundant phrasing, kept the core personal-vs-shared distinction as one test.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Overexplained 'One fact per memory' section with restatement in memory_skill.md.j2

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
One fact per memory section tightened from 110 to 50 words: cut 'grab-bag', 'self-contained' redundancies, consolidated the one-glance rule into the main statement.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Over-detailed preamble in 'Working directly with operator' section of squads_skill.md.j2

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Working directly with operator preamble tightened: 'not through the manager' (implied), 'this is exactly when to' (obvious) removed; anchor-to-item bullet cut from elaborate to crisp (35 word save).
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Redundant preamble in 'Finding things across the board' section of squads_skill.md.j2

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Finding things across the board section consolidated: eliminated redundant 'when you need to find something' restatement, removed examples that just restated the rule. 25 word save.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Redundant expanded greeting instructions in claude_section.md.j2

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
Greeting instructions in CLAUDE.md tightened: removed step-by-step expansion (detect operator, check roster, register). Template now references the greeting skill once; instructions there are the single source of truth. 55 word save.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Redundant explanation after orchestration loop steps in claude_section.md.j2

<!-- sq:finding:F6:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
Orchestration loop epilogue trimmed: removed 'spawn is the handoff' + mentions-are-record explanation (already in squads skill). Kept operator-conversation caveat. ~50 word save.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Overexplained intro paragraph in memory_skill.md.j2

<!-- sq:finding:F7:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
Memory intro paragraph cut from 90 to 40 words: removed examples of 'what to remember' (shown by example in sections below) and 'don't belong in formal doc' (self-evident). 50 word save.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Padding in 'Check it at the start of a run' section of memory_skill.md.j2

<!-- sq:finding:F8:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
Check at start of run section: removed 'same way you'd skim' metaphor, jargony 'Index in content on recall', trivial 'empty pool lists nothing' statement. Simplified 'see' to 'browse'. 45 word save.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Slightly redundant phrasing in 'Prune what's stale' section of memory_skill.md.j2

<!-- sq:finding:F9:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
Prune what's stale section: consolidated 'out of date, superseded, was simply wrong' + 'rather than leaving it to mislead' + 'smaller trustworthy pool beats large stale one' — restatements of same principle. Streamlined git-history note. 25 word save.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Redundant final paragraph in squads_skill.md.j2 'Common commands' section

<!-- sq:finding:F10:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F10:head:end -->

<!-- sq:finding:F10:body -->
Removed generic 'Coordinating a larger piece of work?' closing paragraph from squads skill Common commands section. The orchestration loop is in CLAUDE.md; this was redundant recap. ~20 word save.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T07:37:49Z] Theo Writer:
  - Review complete: 10 findings across the generated content. Total verbiage savings: ~450–500 words across all templates (approximately 15–20% reduction in overall bulk). Top issues:
  - 1. **memory_skill.md.j2** (F1, F2, F7, F8, F9): Memory skill is the wordiest offender — has two redundant explanations of personal-vs-shared, repeated phrasing throughout, padding and jargon. Consolidating these five sections alone saves ~250 words without losing substance.
  - 2. **squads_skill.md.j2** (F3, F4): Preamble to 'Working directly with operator' overexplains the discipline rule; 'Finding things' restates use cases twice.
  - 3. **claude_section.md.j2** (F5, F6): Greeting instructions and orchestration loop both expand on content that's already in the skills, creating redundancy across agent contexts.
  - All findings have before/after rewrites. Pierre wanted agents to see less rambling — these are the main culprits.
- [2026-07-20T07:47:44Z] Theo Writer:
  - Aggressive concision pass complete. All 10 findings addressed in source templates (memory_skill, squads_skill, claude_section). Regenerated with sq sync — no broken Jinja, markers intact, golden files updated, manifest refreshed. Tests passing: rendering/generation suite clean, sq check clean. Summary: ~450–500 words cut across templates (15–20% reduction) while preserving all load-bearing specifics (command syntax, marker rules, invariants). Ready for review or integration.
<!-- sq:discussion:end -->

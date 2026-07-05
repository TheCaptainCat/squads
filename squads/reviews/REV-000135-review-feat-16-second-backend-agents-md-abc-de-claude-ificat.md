---
id: REV-135
sequence_id: 135
type: review
title: 'Review: FEAT-16 second backend (agents_md) + ABC de-Claude-ification'
status: Approved
author: reviewer
refs:
- ADR-133:addresses
- TASK-131
- TASK-132
- FEAT-16
subentities:
- local_id: F1
  title: AGENTS.md carries no workflow/skill content; role definitions are title-only
    stubs
  status: Verified
  severity: high
- local_id: F2
  title: CLI init summary hardcodes Claude wording '(pointers + squads skill + CLAUDE.md)'
    for all backends
  status: Verified
  severity: low
- local_id: F3
  title: agents_md backend docstring claims write_managed compiles staging entries
    into AGENTS.md; it does not
  status: Verified
  severity: low
created_at: '2026-06-15T13:56:34Z'
updated_at: '2026-06-15T14:21:57Z'
---
<!-- sq:body -->
## Verdict: CHANGES REQUESTED

Independent review of FEAT-16 (TASK-131 ABC de-Claude-ification + conformance suite; TASK-132 agents_md backend). Gate is fully green: pytest all pass, pyright 0 errors, ruff check + format clean. ADR-133 (CC-001..006) is correctly and completely applied — CC-003 rename grep-clean across src/ and tests/; CC-005 claude_dir/claude_md gone from SquadPaths and the Claude backend resolves .claude/CLAUDE.md from ctx.root via local constants; CC-006 registry uses an idempotent _load_builtins() guarded by _loaded, register() preserved; CC-001/002/004 docstrings backend-neutral. Invariant 6 holds: no .claude/CLAUDE.md reference leaked into shared modules or the conformance suite; the test-file edits (project.root/'.claude') are correct, not just mechanically green; templates_manifest.json updated for the three new agents_md templates.

Blocking: F1 (high) — the shipped AGENTS.md is not the 'useful' artifact FEAT-16/US1 demands. It carries roster only; no workflow, no skill content, role definitions are title-only stubs; the richer per-role staging files are orphaned. Non-blocking: F2, F3 (low).

### (a) Is the conformance suite an honest contract test? Mostly yes, with a content gap. It asserts real structural contract: Artifact paths exist on disk (test_artifact_files_exist_on_disk would fail a hollow backend), root-relative forward-slash paths, backend-name match, ensure_scaffold + write_managed + generate_*_entry idempotency, no duplicated managed region, full round-trip leaves no orphans, and service-level sync smoke. A backend that returned fake paths or non-idempotent output fails. WEAK SPOT: it asserts roster reflection via (full_name OR slug) anywhere across all artifacts, and the clobber test no-ops on non-JSON files — so it does NOT assert that workflow or skill *content* actually lands. That is exactly the hole F1 slipped through green. Honest about shape; silent about usefulness.

### (b) Is agents_md a real, useful backend? Real, not yet useful. It is a genuinely different backend (single root file, marker-injected, no pointers), idempotent, prose-preserving, .claude-free, wired through init/sync and the registry via the ABC — confirmed live. But as shipped the one file tools read is a thin roster stub: no workflow cheatsheet, no skill bodies, title-only role definitions, orphaned staging files. It proves the ABC is implementable by a second backend (the real ABC-honesty win of this feature) but does not yet meet US1's 'valid, useful AGENTS.md carrying roster, workflow and skill content'. Close the content gap (F1) and this is a true second backend.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 135 add-finding "…" --severity high`; track with `sq review 135 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Verified |  | AGENTS.md carries no workflow/skill content; role definitions are title-only stubs |
| F2 | 🟢 low | Verified |  | CLI init summary hardcodes Claude wording '(pointers + squads skill + CLAUDE.md)' for all backends |
| F3 | 🟢 low | Verified |  | agents_md backend docstring claims write_managed compiles staging entries into AGENTS.md; it does not |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — AGENTS.md carries no workflow/skill content; role definitions are title-only stubs

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
FEAT-16 US1 acceptance: 'a valid AGENTS.md carrying roster, workflow and skill content'. Live 'sq init --backend agents_md' + sync produces an AGENTS.md with ONLY the roster + a static 'Working with squads' blurb. Missing: (1) workflow content — the tool-neutral workflow.md.j2 cheatsheet (named in TASK-132 approach) is never rendered into AGENTS.md; (2) skill content — none of the squads/greeting/per-type skill bodies appear; (3) role definitions are title-only stubs ('### Catherine Manager' / '**Role:** manager'), no mission/responsibilities.

Compounding: generate_role_entry writes RICHER per-role staging files (mission + squad path) to .agents_md/roles/*.md, but write_managed never folds them into AGENTS.md — they are orphan files no tool reads. So the one file agent tools actually consume is a thin roster stub. This is the central FEAT-16 risk (a 'genuinely useful' second backend vs a stub); as shipped it is closer to a stub.

Not an ABC violation (the conformance suite passes; the role-entry/managed-section split mirrors Claude's pointer/section split). It is a usefulness/acceptance gap. Fix: include workflow.md.j2 and at least the squads-skill summary in agents_section.md.j2, and emit role mission into the Role definitions section (the data is already in RoleView.title only — may need to widen what write_managed receives, or fold the staging files).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — CLI init summary hardcodes Claude wording '(pointers + squads skill + CLAUDE.md)' for all backends

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
src/squads/_cli/_main.py:185 — the init summary appends '[bold]agent backend:[/bold] ' + default_backend + ' (pointers + squads skill + CLAUDE.md)' unconditionally. For agents_md this prints 'agent backend: agents_md (pointers + squads skill + CLAUDE.md)' — all three parenthetical claims are false for agents_md (no pointers, no squads skill, no CLAUDE.md).

ADR-133 CC-005 step 3 told the dev to keep this line backend-neutral and said 'the backend name is sufficient'. The path leak was fixed but a Claude-specific descriptive tail was hardcoded in its place — a residual Claude-ism on the exact line the ADR called out. Fix: drop the parenthetical, or make it backend-derived.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — agents_md backend docstring claims write_managed compiles staging entries into AGENTS.md; it does not

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
src/squads/_backends/_agents_md/_backend.py module docstring (lines 3-7) states generate_role_entry/generate_skill_entry stage files 'while write_managed compiles everything into the single AGENTS.md the tools actually read.' write_managed does NOT read the staging dir; it re-renders the roster section from RoleView only. The staging files are never compiled in. Misleading docstring; tighten it or actually fold the staging entries (ties to F1).
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T14:21:57Z] Paul Reviewer:
  - RE-REVIEW VERDICT: APPROVED. All three findings verified resolved; gate fully green (798 passed, 1 skipped; pyright 0 errors; ruff check + format clean). Re-review scoped to the F1/F2/F3 fixes only — TASK-131 ABC work + ADR-133 conformance already approved and unchanged.
  - F1 (high) RESOLVED — AGENTS.md is now genuinely useful. agents_section.md.j2 does '{% include "workflow.md.j2" %}' and write_managed passes type_aliases=TYPE_ALIASES, so the full alias table + command cheatsheet render in. Role missions are folded in via _read_staging_role reading .agents_md/roles/<slug>.md. Verified empirically: minimal init+sync yields a populated AGENTS.md (Canonical alias table, 'sq create task', manager Mission 'first point of contact', '**Mission:**' heading), byte-identical on second sync. Marker-safe: managed.inject splits on the stable <!-- squads:start/end --> markers and preserves all prose outside them (test_user_prose_preserved); region never duplicated (test_managed_section_not_duplicated).
  - Staging-file design — SOUND, not a latent ordering bug. The ordering dependency (generate_role_entry before write_managed) holds on EVERY real call path: sync() loops entries then write_managed (_maintenance.py:83-89); init/adopt call activate_role (→generate_role_entry) for every role before refresh_managed (_service.py:88-91); add_role/add_dev/operator add each refresh against staging files already on disk from the prior init/sync. The mission='' fallback only fires when write_managed is called with no prior generate_role_entry — i.e. direct unit tests (TestWriteManaged) — and is honest, not papering over a coupling bug. No orphan ROLE files: remove_artifacts unlinks per-item. Note: skill staging files under .agents_md/skills/ are not folded into AGENTS.md (skills surface via the workflow cheatsheet), but they satisfy the Artifact contract (one removable file per item) the conformance suite requires — acceptable, not an orphan in the contract sense.
  - Usefulness test NON-VACUOUS. TestAgentsMdUsefulnessPin (4 tests) asserts content whose provenance is exclusively the new rendering: 'Canonical' exists ONLY in workflow.md.j2 (line 37) and 'first point of contact'/'**Mission:**' come ONLY from the staging-file fold (manager mission in _catalog.py:68, gated by {% if r.mission %}). The old roster-only stub had neither the workflow include nor mission folding, so all four would fail against it. Real assertions, not trivially-true.
  - F2 (low) RESOLVED — _cli/_main.py init summary now prints just sp.config.default_backend, no Claude-specific '(pointers + squads skill + CLAUDE.md)' tail. Backend-neutral as ADR-133 CC-005 required. F3 (low) RESOLVED — _backend.py module docstring now accurately describes staging files as compile inputs to write_managed (with the documented fallback), no longer claiming a fold that doesn't happen.
<!-- sq:discussion:end -->

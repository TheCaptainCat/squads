---
id: REV-643
sequence_id: 643
type: review
title: 'FEAT-576 CLI + adopt warnings: sq import, orphan-pointer, pre-existing CLAUDE.md'
status: Approved
author: reviewer
subentities:
- local_id: F1
  title: Claude orphan-skill warning cites <dir>/SKILL.md that may not exist
  status: WontFix
  severity: low
created_at: '2026-07-24T07:40:09Z'
updated_at: '2026-07-24T07:42:42Z'
---
<!-- sq:body -->
Independent review of the FEAT-576 surface work: `sq import` CLI (TASK-639), orphan-pointer WARN on init/adopt (TASK-634), and the pre-existing-CLAUDE.md/AGENTS.md lead-and-warn behavior (TASK-637). Scope: the uncommitted diff plus the two new test files. The `Service.import_events` engine was reviewed separately and is out of scope here.

## Gate

Clean on the touched surface: `pyright` (0/0/0), `ruff check` (all passed), `ruff format --check` (formatted). Targeted pytest green: import CLI, backend scaffold/warning integration, managed-section + marker-safe goldens, backend lifecycle/claude-code contract, and tests/meta. No SCHEMA_VERSION bump; no ticket IDs in source/tests; no "meta"; SquadsError + @handle_errors for the unreadable-file path; e() escaping on all console/table output.

## Verdict

Sound. The import contract holds (bad file exits 1 with line-numbered issues and no traceback, writes nothing; dry-run writes nothing; stable --json envelope). The orphan scan is strictly read-only with a correct superset vocabulary (no nag on legitimately-generated pointers, catches the field-report orphans). inject() preserves the brand-new and already-managed paths exactly (goldens prove it) and prepends only for pre-existing-content-with-no-markers. One cosmetic-only finding recorded.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 643 add-finding "…" --severity medium`; track with `sq review 643 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | WontFix |  | Claude orphan-skill warning cites <dir>/SKILL.md that may not exist |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Claude orphan-skill warning cites <dir>/SKILL.md that may not exist

<!-- sq:finding:F1:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
`ClaudeCodeBackend.candidate_orphans` reports an orphan skill directory as `ctx.rel(p / _SKILL_FILE)` — i.e. it points the warning at `.claude/skills/<name>/SKILL.md` even when that directory has no SKILL.md inside (it only gates on `p.is_dir()`). For a real adopter corpus the file exists, so this is cosmetic only: the emitted path could name a non-existent file for an empty orphan dir. The role-pointer and agents_md paths point at files that do exist. Non-blocking; optionally point at the directory itself when SKILL.md is absent, or keep SKILL.md as the canonical citation and accept it. Read-only safety is unaffected.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T07:40:55Z] Paul Reviewer:
  - RECOMMENDED VERDICT: Approve. Independent review of TASK-639/634/637; verdict left unset per delegation.
  - Gate: pyright 0/0/0, ruff check + format clean, targeted pytest green (import CLI, backend scaffold-warnings, managed-section/marker goldens, backend lifecycle + claude-code contract, tests/meta). No schema bump, no ticket IDs, no 'meta'. sq check clean.
  - Lead #1 (import contract + --at reuse): SOUND. Bad file -> exit 1, line-numbered 'line N: msg' via err_console, nothing written; unreadable file -> SquadsError/@handle_errors clean exit 1, no traceback; --dry-run applied=None, writes nothing; --json envelope stable (ok/applied/dry_run/op_counts/handle_to_id/handle_to_sub/created_ids/issues/warnings), prints then Exit(1) on failure. The ROOT --at reuse is robust, NOT a footgun: the sq/squads console entry point is squads._cli:main, which runs _hoist_global_options over sys.argv so 'sq import f.jsonl --at X' is rewritten to 'sq --at X import ...' and the root callback captures it into get_context().clock_override; no subcommand defines --at, values use --opt=value form. --as defaults to None -> engine applies config.default_role fallback (verified in _import.py: default_as or self.paths.config.default_role).
  - Lead #2 (orphan safety/accuracy): SOUND. Strictly READ-ONLY in both backends — only glob/iterdir + ctx.rel, never unlink/write/move (tests assert the orphan files are byte-identical afterward). Vocabulary is a correct superset: active roster slugs for pointers, SKILL items UNION bundled_skill_slugs() UNION custom_skill_slugs(spec) for skills, so a legitimately-generated sq-<type> skill or a slug-matched role pointer is never flagged (no per-init nag) and the field-report orphans (lead/project-manager/ux-ui-dev) ARE caught. Both backends consistent and each scans its own real staging layout (.claude/agents+skills, .agents_md/roles+skills). See F1 (low, cosmetic) for the empty-orphan-dir path citation.
  - Lead #3 (inject preservation): SOUND. Brand-new file -> write header+block, return False (unchanged). Already-managed (markers present) -> replace in place wherever it sits, return False (unchanged; goldens byte-identical). Prepend+warn triggers ONLY when the file pre-exists AND has real non-whitespace content AND has no markers; whitespace-only appends quietly as before. Never duplicates/reorders a managed region (second sync finds markers -> in-place replace, count stays 1; test confirms), never touches or refuses hand-written content.
  - @op-pierre / manager: recommend Approve; one low cosmetic finding (F1), non-blocking.
- [2026-07-24T07:42:40Z] Catherine Manager:
  - F1 WontFix (cosmetic): the orphan is still correctly flagged; only the cited sub-path (.../SKILL.md) is imprecise when an orphan skill dir lacks SKILL.md — a rare edge, harmless for a real adopter corpus. Leads verified: import exit-code/dry-run/--json contract + robust root-`--at` hoisting, candidate_orphans strictly read-only with a correct managed-vocabulary superset (catches real orphans, never nags generated files), inject() behavior-preserved (brand-new/already-managed unchanged; prepend+warn only for pre-existing-content-no-markers). Approving.
<!-- sq:discussion:end -->

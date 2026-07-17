---
id: REV-460
sequence_id: 460
type: review
title: sq workflow --raw clean-markdown mode
status: Approved
author: reviewer
refs:
- TASK-451
subentities:
- local_id: F1
  title: FORCE_COLOR clause not exercised by an automated test
  status: Open
  severity: low
created_at: '2026-07-17T14:11:43Z'
updated_at: '2026-07-17T14:29:35Z'
---
<!-- sq:body -->
Independent review of TASK-451 — the `sq workflow --raw` / `sq workflow show --raw` clean-markdown mode. Scope: src/squads/_cli/_workflow_cmd.py, CHANGELOG.md, tests/goldens/workflow_cheatsheet_raw.txt, tests/cli/test_workflow_raw_markdown_golden.py.

Verdict: APPROVED. The raw path opts out of rich.Markdown and prints the workflow.md.j2 render verbatim via console.print(content, markup=False, highlight=False, soft_wrap=True) — byte-identical to the sq docs / sq show --raw precedent (_main.py:932). Output is genuinely clean markdown: zero box-drawing, zero ANSI (verified piped AND under FORCE_COLOR=3 in a pty), fenced mermaid blocks and markdown tables present, for both --raw variants. Default styled path is unchanged (still Markdown(content)). Golden pins the shape; scoped + meta tests, pyright, ruff, sq check all green. One low nit below.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 460 add-finding "…" --severity medium`; track with `sq review 460 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | FORCE_COLOR clause not exercised by an automated test |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — FORCE_COLOR clause not exercised by an automated test

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The task acceptance says 'verify no escape codes even under FORCE_COLOR'. The suite's autouse _neutralize_forced_color fixture strips FORCE_COLOR/CLICOLOR_FORCE/PY_COLORS for determinism, so test_workflow_raw_has_zero_rich_chrome runs with color already disabled and isatty()=False — it cannot distinguish the raw path from the old Markdown path on the color axis (it does still pin box-drawing/ANSI absence, which is a valid regression guard).

Not blocking: the guarantee is structural — markup=False + highlight=False on plain text can emit no color regardless of FORCE_COLOR — and I verified it manually (FORCE_COLOR=3 uv run sq workflow --raw in a pty → zero chrome/ANSI). Fighting the suite-wide color-stripping to add a forced-color test isn't clearly worth it; noted so the record shows the clause was checked. Consistent with the existing sq docs / sq show --raw tests, which likewise don't force color.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T14:12:12Z] Paul Reviewer:
  - APPROVED. Clean-markdown output confirmed for both `sq workflow --raw` and `sq workflow show --raw`; default styled path unchanged; gates green (scoped+meta tests, pyright, ruff, sq check clean). One low nit (F1) on test coverage of the FORCE_COLOR clause — non-blocking, manually verified. @tech-lead core half of the raw cheatsheet is sound.
<!-- sq:discussion:end -->

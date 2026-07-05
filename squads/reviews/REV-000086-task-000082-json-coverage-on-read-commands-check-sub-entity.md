---
id: REV-86
sequence_id: 86
type: review
title: 'TASK-000082: --json coverage on read commands (check, sub-entity lists, catalog
  viewers)'
status: Approved
author: reviewer
subentities:
- local_id: F1
  title: JSON show shapes use 'file' for the path; sibling --json surfaces use 'path'
  status: Verified
  severity: medium
- local_id: F2
  title: check table path still exits 1 on errors while check --json exits 3 — same
    command, divergent exit codes
  status: Verified
  severity: medium
created_at: '2026-06-12T20:38:57Z'
updated_at: '2026-06-12T20:44:49Z'
---
<!-- sq:body -->
## Scope

Review of TASK-82's uncommitted working-tree diff in `src/squads/_cli/` (_main.py, _items.py, _role.py, _skill.py, _operator.py) + new tests in `tests/test_cli.py` (~1202-1406). Adds `--json` to: `check`, the three sub-entity list commands (stories/subtasks/findings), and the role/skill/operator catalog viewers.

## What's solid

- Correctness: every JSON path reads the same service source and applies the same filters as its table twin; no table-path behaviour changed (verified against `git show HEAD`). `check --json` emits the array then exits 3 on error-level issues and 0 otherwise (warnings-only → 0), exactly as ruled.

- Conventions: strict typing clean (pyright 0), ruff + format clean; all extra-key reads go through `X.*` (no hand-written keys); uses the `console.print_json` pattern; no Rich-markup leakage into JSON; bare `--json` option matches the prevailing declaration style.

- Shapes: `local_id` for sub-entities vs `id` for items is the right distinction; uniform sub-entity shape with nulls for inapplicable fields is parser-friendly; role show JSON mirrors the table's PREDEFINED-then-extras fallback and same error case.

- Tests: all seven+ new surfaces asserted, shapes parsed via `json.loads` (not string-matched), exit codes (0/3/0) asserted. Gate green.

## Verdict: ChangesRequested

Two MEDIUM findings, both about the 1.0 contract that TASK-84 freezes — neither is a behaviour bug, but both must be settled before goldens are cut:

- F1: `show --json` emits the path as "file"; every sibling --json surface uses "path". Rename to "path" for consistency.

- F2: `check` table path still exits 1 while `check --json` exits 3 — same command, divergent exit codes. Needs alignment (here or explicitly in TASK-83).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 86 add-finding "…" --severity high`; track with `sq review 86 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | JSON show shapes use 'file' for the path; sibling --json surfaces use 'path' |
| F2 | 🟡 medium | Verified |  | check table path still exits 1 on errors while check --json exits 3 — same command, divergent exit codes |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — JSON show shapes use 'file' for the path; sibling --json surfaces use 'path'

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The new role/skill/operator `show --json` shapes expose the markdown file path as "file" (`{"file": it.path}`).

But every other --json surface that carries an item's path emits it as "path" — `mine`, `list`, and the item `show --json` all serialize the `Item` model whose field is literally `path`. So a parser gets `path` from `sq task N show --json` and `file` from `sq operator op-x show --json`: two names for the same datum across sibling show commands.

These shapes freeze together in TASK-84 (golden files = the 1.0 contract), so the divergence becomes permanent. Recommend renaming "file" → "path" in role/skill/operator show JSON for cross-surface consistency before goldens are cut.

Medium, not high: behaviour is correct; this is contract-naming hygiene. But it must be settled before the goldens land.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — check table path still exits 1 on errors while check --json exits 3 — same command, divergent exit codes

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
`sq check --json` correctly emits the issue array then `raise typer.Exit(3)` when any error-level issue exists, exactly as the task ruled. The warnings-only and clean cases exit 0. That part is right.

But the table path of the same command (`sq check` without --json) was left at `raise typer.Exit(1)`. So identical input yields exit 1 from `sq check` and exit 3 from `sq check --json` — the exit code, which is the load-bearing CI contract (US2), now depends on the output format.

The task scopes the exit-3 doc/test work to TASK-83, so the table path's migration to 3 may legitimately belong there rather than here. Flagging so it isn't lost in the seam: either 082 aligns both paths to 3 now, or 083 must own aligning the table path. The two should not ship to 1.0 disagreeing.

Medium: the --json contract this task owns is correct; the risk is the cross-task seam leaving the table path on a stale code.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T20:39:54Z] Paul Reviewer:
  - @manager verdict: ChangesRequested on TASK-82. The delivered --json behaviour is correct, conventional, and well-tested (gate green) — the two findings are both about the contract surface TASK-84 will freeze, not behaviour bugs.
  - F1 (medium): role/skill/operator `show --json` expose the path as "file"; every other --json surface uses "path". Rename to "path" before goldens.
  - F2 (medium): `check` table path exits 1, `check --json` exits 3 — same command, divergent exit codes. Either align both to 3 here, or hand the table-path migration explicitly to TASK-83. Don't let the seam ship a disagreement to 1.0.
  - Small surface to fix; happy to re-review on the bounce. @python-dev see F1/F2 bodies for specifics.
- [2026-06-12T20:42:58Z] Elias Python:
  - F1 and F2 addressed. Changes are working-tree only (no commit).
  - F1 (medium — file→path rename): src/squads/_cli/_skill.py line 105 and src/squads/_cli/_operator.py line 99 renamed the JSON key from "file" to "path" in the --json output of skill show and operator show. The role show --json shape was already clean (no path field emitted there). Tests updated: test_skill_show_json now asserts "path" in data; test_operator_show_json docstring and assertion both updated to "path".
  - F2 (medium — check table path exit 3): src/squads/_cli/_main.py line 466 changed raise typer.Exit(1) → raise typer.Exit(3) on the table path of sq check. Both paths (--json and table) now consistently exit 3 when any error-level issue is found. Test test_check_cli_flags_index_item_with_no_file updated to assert exit_code == 3.
  - TASK-83 note: the check exit-3 implementation landed here via F2. Left a comment on TASK-83 (--as python-dev) noting remaining scope is documentation and exit-code test coverage only.
  - Gate: 387 passed, 1 skipped — pyright 0 errors — ruff clean — sq check ✓ no issues.
  - @reviewer please re-review. @manager F1/F2 fixed, TASK-82 back to Done.
- [2026-06-12T20:44:49Z] Paul Reviewer:
  - @manager APPROVED. Re-reviewed the bounce on TASK-82; both findings verified fixed, gate green (387 passed / 1 skipped, pyright 0 errors, ruff clean).
  - F1 (Verified): role/skill/operator show --json now emit "path" — _skill.py:105 and _operator.py:99 renamed file→path; role show carries no path field. All in-scope read surfaces agree on "path".
  - F2 (Verified): _main.py table path now raises typer.Exit(3); both check paths (table + --json) exit 3 on error-level issues, 0 on warnings-only or clean. Tests assert 0/3/0.
  - Residual for TASK-84 (NOT a blocker here): print_block JSON (_common.py:76) — the add-story/add-subtask/add-finding scaffold output — still emits "file" for the path. Out of TASK-82 scope and unchanged by this diff, but it's the same divergence F1 fixed, on a write-side surface. Goldens must settle it (rename file→path or document the exception) before they're cut. @python-dev flagging for the TASK-84 sweep.
<!-- sq:discussion:end -->

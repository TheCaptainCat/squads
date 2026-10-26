---
id: REV-1161
sequence_id: 1161
type: review
title: 'Review TASK-1149: stale comments, test gaps, RUF029 preview'
status: Approved
author: reviewer
refs:
- TASK-1149
description: 'Hygiene task review: src diff, new tests, ruff preview scope, v0_1 goldens'
subentities:
- local_id: F1
  title: 'Forced-colour raw test fails on the Windows CI leg: piped stdout gets legacy
    render, no ANSI'
  status: Verified
  severity: high
- local_id: F2
  title: fold_legacy_kinds no longer folds a legacy map; the name contradicts the
    corrected CLAUDE.md
  status: Verified
  severity: low
- local_id: F3
  title: Preview comment says only RUF029 changes; preview also alters selected stable
    rules
  status: Verified
  severity: low
created_at: '2026-10-26T08:52:03Z'
updated_at: '2026-10-26T09:13:23Z'
---
<!-- sq:body -->
## Scope

Commits 18a177f4 (TASK-1149 ST1, ST4 to ST10) and 90f3a9a4 (ST3, README) on release/0.17. A no-behaviour-change hygiene task: stale comments and docstrings, small test gaps, RUF029 via scoped ruff preview.

## Checked

- `src/` diff: comment and docstring edits plus the `fold_legacy_kinds` signature change. With its only live caller passing `{}`, `legacy.get(rid, kind)` was always `kind`, so dropping the parameter is behaviour-preserving. The migrations keep their own frozen copies.
- ruff: compared `ruff check src tests --ignore-noqa` under the old and new config at ruff 0.15.16. The finding set is identical except RUF029 on `_wrap_sync._async`, which replaces the old RUF100. `ruff format --check` reports 1000 files unchanged under both.
- Falsification on a scratch copy (driven): ST1 guard (12 failures when the no-body-region refusal returns instead of raising), ST4 repair padding (fails when the scan ignores stem width), ST5 workload (both tests fail without the roster skip), ST7 raw output (fails with `highlight=True` on the raw path).
- ST6 goldens: the two v0_1 skill files moved into `_shared/` (content-compared through SHARED.txt), ids shift by one for the new REV-6, nothing lost. A fresh `sq create review` carries no summary region either, so the asserted end state matches fresh creation.
- Targeted runs: tests/integration, tests/cli, tests/service at -n 4, 11073 passed; tests/meta and tests/unit pass.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1161 add-finding "…" --severity medium`; track with `sq review 1161 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Forced-colour raw test fails on the Windows CI leg: piped stdout gets legacy render, no ANSI

<!-- sq:finding:F1:body -->
`test_workflow_raw_has_no_escape_codes_even_when_colour_is_forced` (tests/cli/test_workflow_raw_markdown_golden.py) runs `sq workflow` in a subprocess with stdout captured and asserts its precondition: `"\x1b[" in run("workflow")`.

The CI matrix in .github/workflows/test.yml runs `uv run pytest` on windows-latest. There, rich 15.0.0 (the locked version) does this:

- `Console()` runs `detect_legacy_windows()`, which is `WINDOWS and not get_windows_console_features().vt`.
- On a piped stdout, `GetConsoleMode` fails, so `vt` is False and `legacy_windows` is True.
- `_check_buffer` then takes `legacy_windows_render(buffer, LegacyWindowsTerm(self.file))`, because fileno 1 is a std stream. That path styles through the Win32 console API and writes no ANSI sequences.

So the rendered form carries no `\x1b[`, the precondition fails, and the Windows leg goes red. The test is not skipped there. This is inferred from the rich source; I could not run it on Windows. The `Scripts\sq` path itself is fine: CreateProcess appends `.exe`, and `test_migrate_up_bare_subprocess_exit_parity.py` already relies on that on Windows CI.

The same precondition fails locally under `TERM=dumb` (driven: `TERM=dumb pytest` on this test fails with "precondition: forced colour styles the rendered form"). Rich treats a dumb terminal as colourless even with FORCE_COLOR set, and the test copies the caller's TERM.

Fix: skip the test on win32 with a reason, since no ANSI is emitted to a pipe on Windows at all. Also pin `TERM` (for example `xterm-256color`) in the subprocess env so the precondition does not depend on the caller's terminal.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T09:03:15Z] `python-dev` Elias Python:
  - Fixed: the test is skipped on win32 with a reason and the subprocess env pins TERM=xterm-256color. It passes with TERM=dumb in my shell.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — fold_legacy_kinds no longer folds a legacy map; the name contradicts the corrected CLAUDE.md

<!-- sq:finding:F2:body -->
`squads._models._item.fold_legacy_kinds` no longer takes or folds any legacy map. After the change it only normalises inline `ID[:kind]` refs against the default kind (its new docstring says so), but the name still says it folds legacy kinds. Four places point readers at it by that name as the fold:

- `_read_refs`
- `_is_str_list`
- the `from_frontmatter` docstring
- tests/service/test_default_ref_kind_encoding_convergence.py

The corrected CLAUDE.md now says the read path never reads the legacy map, so the name contradicts the documentation next to it.

How this misleads: a reader who greps for where `extra.ref_kinds` is folded finds a live function named for exactly that, on the read path, and concludes the opposite of what CLAUDE.md now states. That is the stale claim ST9 set out to remove.

Fix: rename it to what it does (for example `normalise_ref_kinds`) and update the callers and docstring references. The meta guard's forbidden-name list (tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py) and test_migrations.py name it too. No behaviour change.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T09:03:18Z] `python-dev` Elias Python:
  - Fixed: renamed to normalise_ref_kinds in _item.py, its four reference sites and the tests/meta and test_migrations references; the migrations' frozen _fold_legacy_kinds copy is untouched. No behaviour change.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Preview comment says only RUF029 changes; preview also alters selected stable rules

<!-- sq:finding:F3:body -->
The new pyproject.toml comment says preview is on "only so that rule runs" and that `explicit-preview-rules` "keeps every other preview rule off". That is true for preview rules. But `[tool.ruff.lint] preview = true` also turns on the preview behaviour of stable rules that are already selected. At ruff 0.15.16, `ruff rule` documents preview-gated behaviour for selected stable rules, including:

- F401: analyses all import statements, which can flag more imports.
- F811 and F822.
- SIM102 and SIM401: under preview the SIM102 fix becomes safe, so `ruff check --fix` applies it without `--unsafe-fixes`.
- UP006 and UP019.

Measured today: no difference in the finding set (diffed `--ignore-noqa` output, old config against new). So nothing is wrong now, but the comment tells the next reader the switch is inert beyond RUF029, and it is not.

How this misleads: a ruff lock bump changes a stable rule's preview behaviour. CI's `ruff check .` then reports new F401 hits, or `--fix` silently rewrites nested ifs, and the comment points the reader away from the cause.

Fix: state it in the comment. Preview also enables preview behaviour of selected stable rules, measured as no effect at the locked ruff, so re-measure on a ruff bump.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T09:03:20Z] `python-dev` Elias Python:
  - Fixed: the pyproject comment now says preview also enables preview behaviour of selected stable rules, none measured at ruff 0.15.16, re-measure on a bump.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T08:52:27Z] `reviewer` Paul Reviewer:
  - Review done; left InReview with 3 findings. @tech-lead, F1 is the one that matters: the new ST7 test should fail on the windows-latest CI leg, as traced from the rich source (not run on Windows). Skip it on win32 and pin TERM, which also fixes a local TERM=dumb failure that I did reproduce. F2 and F3 are low: a stale function name and a pyproject comment that overclaims.
    
    Two notes that are not findings:
    
    - The ST6 handoff says ensure_summary writes no summary region when there are no findings. That is not what happens. The 0.1-to-0.2 runner does insert an empty summary region, and the later repair strips it, because summary regions are retired (`_retired_region_tags`). The test asserts the correct end state, the same as a fresh `sq create review`.
    - In a migrated pre-0.2 review, the findings container lands under the prose `## Discussion` heading. That comes from the frozen released runner and is not changed here.
    
    Everything else checked out: src is behaviour-neutral, ruff adds only RUF029, and the ST1/ST4/ST5/ST7 tests each go red when I break the property they pin. The ST1 role comment was already correct.
- [2026-10-26T09:13:03Z] `reviewer` Paul Reviewer:
  - Re-checked at 7ac783a4: F1 win32 skip and TERM pin hold, the file passes under TERM=dumb; F2 rename is name-only, no stray fold_legacy_kinds left, migration code unchanged (docstring refs only); F3 comment now states the stable-rule preview effect. Targeted tests, ruff and pyright clean. All findings Fixed.
<!-- sq:discussion:end -->

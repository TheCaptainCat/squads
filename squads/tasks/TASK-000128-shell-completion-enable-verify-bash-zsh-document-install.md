---
id: TASK-000128
sequence_id: 128
type: task
title: 'Shell completion: enable, verify bash+zsh, document install'
status: Done
parent: FEAT-000017
author: tech-lead
created_at: '2026-06-15T12:10:13Z'
updated_at: '2026-06-15T12:31:51Z'
---
<!-- sq:body -->
## Approach

The Typer app is currently built with add_completion=False (src/squads/_cli/__init__.py line ~34), so `sq --install-completion` / `--show-completion` are NOT exposed. FEAT-17 wants completion verified working for bash + zsh and documented.

Step 1 — enable: flip add_completion=True on the typer.Typer(...) construction in _cli/__init__.py (this re-adds Typer/Click's built-in --install-completion / --show-completion options). Note the app is invoked through a custom main() that hoists --at/--dir (the _hoist_global_options shim); verify the completion options still parse correctly through that path. Both 'squads' and 'sq' entry points should offer completion.

Step 2 — verify: confirm `sq --show-completion bash` and `sq --show-completion zsh` emit a valid completion script (non-empty, well-formed) and that install works. A CliRunner test asserting --show-completion produces a script for each shell is the durable check; a manual smoke in a real bash/zsh shell confirms actual tab-completion (record the steps).

Step 3 — document: add a 'Shell completion' section to README.md (and/or docs/) with the install steps for bash and zsh (`sq --install-completion`, restart shell / source). There is currently NO completion documentation anywhere (grep confirms).

## Files / dirs to touch
- EDIT: src/squads/_cli/__init__.py (add_completion=True; verify interplay with main()/_hoist_global_options)
- EDIT: README.md (NEW 'Shell completion' section: bash + zsh install steps)
- POSSIBLY EDIT: docs/ (if completion belongs in the docs set shipped via `sq docs`)
- NEW/EDIT TEST: a CLI test asserting `sq --show-completion bash|zsh` emits a script (tests/test_cli.py or a small new test)

## Acceptance (from FEAT-17)
Completion install steps are documented and verified on bash and zsh.

## Note
The completion docs are FEAT-000013 (stability contract) deferral material — flag to tech-lead; do NOT file the deferral here.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 128 add-subtask "<title>"`; track with `sq task 128 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T12:18:46Z] Elias Python:
  - Implemented shell completion (FEAT-000017, TASK-000128). Three changes:
  - 1. src/squads/_cli/__init__.py: flipped add_completion=False → True on the Typer app. The _hoist_global_options shim is transparent to completion args — it only hoists --at/--dir and their values, so --show-completion and --install-completion pass through untouched.
  - 2. README.md: added 'Shell completion' section between Install and Quickstart covering bash and zsh --install-completion steps, --show-completion for inspection, and a note that completion requires sq on PATH.
  - 3. tests/test_cli.py: added test_shell_completion_scripts_are_non_empty (verifies bash and zsh emit distinct, non-empty scripts via CliRunner with TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION set) and test_hoist_global_options_does_not_break_completion_args (asserts the shim leaves completion args in place).
  - Gate: 707 passed, 1 skipped · pyright 0 errors · ruff clean · format clean.
  - @reviewer please review the CLI enable and shim verification. @qa please verify --show-completion bash/zsh via the real entry point and the README install steps.
- [2026-06-15T12:30:16Z] Paul Reviewer:
  - REV-000130: APPROVED. add_completion=True is set on the Typer app; --show-completion bash|zsh emit real, distinct, non-empty scripts (test asserts _sq_completion/complete_bash for bash and '#compdef sq'/complete_zsh for zsh). The _hoist_global_options shim only moves --at/--dir, so completion args pass through untouched — covered by a dedicated unit test asserting the shim is a no-op on --show-completion/--install-completion and still hoists a trailing --dir. README 'Shell completion' section is accurate (install steps + restart/source + show-completion). One INFO finding (F2): the README note on why 'uv run sq' completion doesn't work is slightly imprecise wording — informational only.
<!-- sq:discussion:end -->

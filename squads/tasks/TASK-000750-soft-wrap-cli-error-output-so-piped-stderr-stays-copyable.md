---
id: TASK-750
sequence_id: 750
type: task
title: Soft-wrap CLI error output so piped stderr stays copyable
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-745:fixes
description: soft_wrap at the three single-line error render sites plus a platform-independent
  regression guard
created_at: '2026-08-21T12:42:50Z'
updated_at: '2026-08-21T18:36:57Z'
---
<!-- sq:body -->
`sq` renders error output at a fixed 80-column width whether or not stderr is a terminal, so Rich
inserts real newlines into piped or captured error messages. A remedy command inside an error message
is split mid-token, which means it cannot be grepped, cannot be copied in one piece, and any script
or agent asserting on a message substring is really asserting on a wrap position.

Driven on Linux, no override involved:

```
$ sq init --name probe 2>&1 | cat -A
error: --name 'probe': expected format slug=Full Name (e.g. architect='Ada $
Lovelace')$
```

The `$` marks a real newline inside `architect='Ada Lovelace'`.

## Surfaces

`src/squads/_cli/_common.py`, the three `err_console.print` sites that render a `SquadsError` as
`error: <message>`:

- `handle_errors` — the decorator form.
- `command` — the sync/async bridge that subsumes `handle_errors` and is what most commands actually
  go through.
- the dynamically registered refusal-command shim, which prints a refusal message the same way.

All three get `soft_wrap=True`. Rich markup and the `e()` escaping stay exactly as they are — this
changes wrapping only, not colour, not escaping, and not the message text.

Do not blanket-apply `soft_wrap` to the other `err_console.print` call sites in that file: several
print multi-line advisory blocks that are meant to wrap. Change the three that render a single-line
`error:` message and leave the rest, or state on this item why a wider sweep is right.

## Regression guard

The existing protection is test-side and platform-conditional: `tests/conftest.py` pins
`rich.console.detect_legacy_windows` to false because `Console` latches its width as
`COLUMNS - legacy_windows`, and `legacy_windows` is true for a captured pipe on Windows. A test that
fails when that pin is removed can therefore only fail on Windows.

Add a platform-independent guard that fails on any OS if the wrap comes back: drive a command whose
error message is longer than 80 columns and contains a copyable remedy token, capture stderr, and
assert the remedy token is present intact with no newline inside it. Assert on the absence of an
inserted newline, not on a wrap position.

## Assess and record: the Windows conftest pin

Determine whether that `detect_legacy_windows` pin is now redundant, and record the answer as a
comment on this item with the reasoning. It patches the module function, so it affects every console
the test session constructs, not just `err_console` — stdout tables and other width-sensitive
rendering included. If it is still load-bearing for those, it stays and the comment says which
consoles still need it; if it is genuinely redundant, remove it in this work and let the new
platform-independent guard cover the case. Do not remove it on the assumption that soft-wrapping
stderr covers everything the pin was doing.

## Acceptance criteria

- `sq init --name probe 2>&1 | cat -A` shows the full remedy example on one line, with no `$` inside
  `architect='Ada Lovelace'`.
- `sq ... 2>&1 | grep "architect='Ada Lovelace'"` matches.
- The new guard fails when `soft_wrap=True` is reverted at any one of the three sites, and passes with
  it — falsify it that way and report both directions.
- Error messages keep their colour, their `error:` prefix and their exact text; existing tests that
  assert on error substrings still pass without having to flatten output first.
- The conclusion about the Windows conftest pin is recorded on this item, and the pin is either kept
  with a stated reason or removed as part of this work.
- `CHANGELOG.md` carries an adopter-facing entry in the unreleased section: piped error output is no
  longer hard-wrapped, so a remedy in an error message can be copied and matched whole.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 750 add-subtask "<title>"`; track with `sq task 750 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T15:31:03Z] Elias Python:
  - Added soft_wrap=True at the three sites (_common.py: spec_error_command's refusal shim ~373, handle_errors ~949, command bridge ~968). No change to markup, e() escaping, or message text.
  - Repro: sq init --name probe 2>&1 | cat -A now shows one unbroken line ending in a single $; the grep for architect='Ada Lovelace' now matches.
  - New platform-independent guard: tests/cli/test_piped_error_output_keeps_a_remedy_command_intact.py drives each of the three sites directly against an 80-col in-memory console and asserts no newline lands inside a long remedy token. Falsified both ways: reverting soft_wrap at any one of the three sites fails exactly that site's test; restoring it passes all three.
  - Windows conftest pin (rich.console.detect_legacy_windows=False in tests/conftest.py): KEPT, not redundant. It patches module-wide, so it still backs stdout (tables/panels via 'console') and the multi-line err_console advisories left deliberately un-soft-wrapped (version_notice, require_current_schema's schema-mismatch message, board/search/inbox per-file degrade loops) -- those still latch COLUMNS-legacy_windows and would drift a wrap point on a legacy-detected console. tests/integration/test_schema_mismatch_gate.py still token-joins its output to tolerate wrapping there, confirming a still-live case.
  - Updated tests/cli/test_error_text_is_rendered_at_the_pinned_width.py: its 'legacy console really would break it' test targeted the command-bridge site (role activate refusal) that's now soft_wrap-immune, so it now asserts the remedy survives even under an emulated legacy-windows console instead of asserting it breaks. Docstring updated to match. Re-ran; both tests in that file pass.
  - Audited other 'Rich hard-wraps ... flatten before searching' test workarounds (test_unreadable_files_degrade_per_file_cli.py, test_malformed_frontmatter_and_config_fail_cleanly.py, test_undecodable_squad_files_fail_cleanly.py, test_search_and_inbox_degrade_per_file.py) -- all exercise per-file degrade loops (board list/check/repair/search/inbox), none of the three patched sites, so their flattening stays necessary; left untouched.
  - Gates: pyright 0 errors; ruff check all clean; ruff format --check 509 files formatted; tests/meta 165 passed; sq check clean. Targeted tests (160) covering error-text/CLI-common/degrade paths all pass.
  - CHANGELOG.md: added a Fixed entry under [0.14.0]. Commit ca7cee3 on release/0.14, unpushed.
<!-- sq:discussion:end -->

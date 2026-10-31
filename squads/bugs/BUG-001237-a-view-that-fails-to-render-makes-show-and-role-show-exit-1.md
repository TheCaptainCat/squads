---
id: BUG-1237
sequence_id: 1237
type: bug
title: A view that fails to render makes show and role show exit 1
status: Verified
author: qa
refs:
- FEAT-1226
created_at: '2026-10-29T06:59:37Z'
updated_at: '2026-10-29T07:15:50Z'
priority: medium
severity: medium
---
<!-- sq:body -->
## Steps

On a scratch squad (dev tree 0.18.0; the released 0.17.0 checked too):

1. `sq init --default-names --roles all`, then `sq create milestone "Rollup test" --author product-owner` and `sq milestone 21 view add milestone_rollup`. The body now carries the `sq:view:milestone_rollup` tag.
2. Break that view's override: write an invalid Jinja template (`{% if %}`) to `squads/.overrides/templates/views/milestone_rollup.md.j2`.
3. Run `sq milestone 21 show` and `sq milestone 21 show --json`.
4. Break `views/role_definition.md.j2` the same way (every role body carries `sq:view:role_definition`) and run `sq role qa show` and `sq role qa show --json`.

## Actual

Dev tree (0.18.0), exit 1 on every command, nothing else printed:

- `sq milestone 21 show` and `show --json`: `error: view 'milestone_rollup' failed to render on MILE-21: template 'views/milestone_rollup.md.j2' failed to render: tag name expected`
- `sq role qa show` and `show --json`: `error: view 'role_definition' failed to render on ROLE-5: template 'views/role_definition.md.j2' failed to render: Expected an expression, got 'end of statement block'`

Released 0.17.0 (predates 0.18), same scenario:

- `show`: prints the header panel, then the same `error: view 'milestone_rollup' failed to render ...`, exit 1.
- `show --json`: exit 0; the tag is left in `body` and `views.milestone_rollup` holds the data. This is already the wanted behaviour, minus the warning.
- `role qa show`: header panel, then `error: view 'role_definition' failed to render ...`, exit 1. `role qa show --json`: exit 0.

So the text-mode failure predates 0.18; the `--json` failure is a 0.18 regression.

`sq check` reports an override problem for the broken template in both versions (in the scratch squads it was the missing `squads:override-base` stamp; a stamped but unrenderable template was not separately probed).

## Expected

Per the op-pierre ruling on FEAT-1226 (2026-10-29, tolerant view rendering): the command succeeds (exit 0). The tag stays exactly as written in `display.body`, a warning names the view and the error, and `sq check` keeps reporting the broken template. This holds for `show`, `role show` and every surface that expands view tags, `--json` and the API included.

## Affected surfaces

`sq <type> <n> show` and `show --json`, `sq role <slug> show` and `--json`, and any other surface that expands view tags (skills and the API view/display path). Checked directly: show and role show only; `sq skill sq-bug show` was unaffected when `role_definition` alone was broken.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T07:10:42Z] `python-dev` Elias Python:
  - Fixed on branch worktree-agent-aa2295cf21dadfa1a, commit 0f6745ae (based on release/0.18 ff598fec). @qa please verify.
    
    - Shared path: `expand_view_tags` (`_view_tags.py`) catches the render failure, leaves that tag as written, and returns `ExpandedBody(text, warnings)` with one warning per failed view. `read_body` returns it, and every read that expands tags puts the warnings on its `Response`: item show (`sq <type> <n> show`, `sq show <id>`), role, skill and operator show, and the `workflow view --json` source (self and role sources). Under `--json` the warning goes to stderr; the HTTP body carries it in `warnings`.
    - Warning text: `view 'milestone_rollup' failed to render on MILE-21: template 'views/milestone_rollup.md.j2' failed to render: tag name expected -- its tag is shown as written`.
    - Before/after on a scratch squad with broken `milestone_rollup`, `role_definition` and `item_skill` overrides: `milestone 21 show`, `show MILE-21`, `role qa show`, `skill sq-bug show` (human and `--json`) and `workflow view memory_skill MILE-21 --json` all went from exit 1 to exit 0 with the warning. `display.body` keeps `<!-- sq:view:<name> -->`. With healthy templates the output is the same before and after: exit 0, nothing on stderr.
    - `sq workflow view <name> <id>` without `--json` still exits 1 when that view's own template is broken. That command was asked to render that view, so this is not a tag expansion.
    - sq check: before the fix it did NOT report a stamped override template that fails to compile (`✓ no issues`, exit 0). The existing `override_loads` rule only checked readability and required markers. It now also compiles each override template and reports `override template does not compile: line N: <error>` (error, exit 3). Not covered: a template that compiles but fails only when it renders (e.g. an undefined attribute under StrictUndefined). No static check can see that; `show` warns about it at read time.
    - Tests: +1 check-rule breach case (`test_a_template_override_that_does_not_compile_is_an_error`), falsified by disabling the compile step. The `tests/meta` site table records the new `override_loads` site. No surface case for the warning: under the bundled spec no view template fails to render, and the F12 ruling keeps override-backed cases out of the surface suite.
    - Not changed: a failing view *transform* still raises (the `view_data` in `--json` runs transforms too).
- [2026-10-29T07:15:49Z] `qa` Mara Tester:
  - Verified on release/0.18 e5f9c187, dev tree, scratch copies. Broken override (milestone_rollup, role_definition, item_skill): milestone 21 show, show --json, role qa show, role qa show --json, skill sq-bug show, workflow view memory_skill MILE-21 --json all exit 0 with exactly one stderr warning naming view, item and error, ending "its tag is shown as written"; the json body keeps the sq:view tag. Healthy templates: same commands exit 0, stderr empty. sq check on a stamped non-compiling template: exit 3, rule override_loads, "override template does not compile: line 2". Healthy check: exit 0. Out-of-scope cases as described: a compiling template that fails at render (data.nope.missing.attr) passes check ("no issues") and warns at show; workflow view milestone_rollup MILE-21 without --json still exits 1. Not driven: a failing view transform (needs a custom transform; not checked).
<!-- sq:discussion:end -->

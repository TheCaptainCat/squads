---
id: BUG-838
sequence_id: 838
type: bug
title: A view with no presentation template raises a traceback, not a SquadsError
status: Verified
author: qa
priority: medium
refs:
- TASK-833
- MILE-836:targets
created_at: '2026-08-26T16:35:41Z'
updated_at: '2026-09-01T08:05:31Z'
---
<!-- sq:body -->
## What happens

A view declared with no presentation template at `templates/views/<name>.md.j2` passes
`sq workflow lint`. Resolving it through the CLI's default (rendered) mode then raises an
unhandled `jinja2.exceptions.TemplateNotFound` and dumps a full stack trace to the terminal
instead of a clean `error:` line.

## Repro (driven in a scratch squad)

```
sq override scaffold workflow
# append to squads/.overrides/workflow.toml:
[views.no_template_view]
source = { kind = "ref", name = "related" }

[[views.no_template_view.fields]]
code = "id"
label = "Id"

[[views.no_template_view.fields]]
code = "title"
label = "Title"
```
(no `templates/views/no_template_view.md.j2` is created)

```
$ sq workflow lint
workflow spec OK — no errors or warnings.
$ echo $?
0

$ sq create task "Test Task" --author tech-lead   # → TASK-9
$ sq workflow view no_template_view TASK-9
Traceback (most recent call last):
...
  File ".../jinja2/loaders.py", line 380, in get_source
    raise TemplateNotFound(template)
jinja2.exceptions.TemplateNotFound: views/no_template_view.md.j2
$ echo $?
1
```

No `error:` line is printed anywhere in the output — the whole surface is the raw traceback.

`--json` on the same view/item is unaffected (it skips presentation and returns the projection
cleanly at exit 0), which isolates the failure to the presentation-render path specifically.

## Expected vs actual

- Expected: per this project's own rule, a user-facing failure is a `SquadsError` that the CLI
  turns into a clean `error: …` message at exit 1 — never a raw traceback.
- Actual: `jinja2.exceptions.TemplateNotFound` propagates unhandled out of
  `squads._rendering._engine.render` through `ViewsMixin`'s rendered-mode path
  (`src/squads/_services/_views.py`, the call at the `render("views/{view_name}.md.j2", …)`
  site) and out through the CLI's `anyio.run` wrapper, exit code 1 but no `error:` line and a
  full stack trace on stderr.

## Which surface should have caught it

Both, in different ways: `sq workflow lint` validates a view's `source`/`fields`/`group_by`/
`order_by` but never checks that its presentation template file exists on disk, so a view that
can never render cleanly still lints OK. Failing that, the command surface (`sq workflow view`)
is where an unhandled `TemplateNotFound` reaches the user as a traceback rather than a
`SquadsError`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T16:36:13Z] Mara Tester:
  - Driven in a scratch squad: lint OK at exit 0, sq workflow view <name> <id> exit 1 with an unhandled jinja2.exceptions.TemplateNotFound traceback (no error: line). --json on the same view/item works cleanly, isolating it to the presentation render path.
  - @tech-lead for triage.
- [2026-08-26T17:08:17Z] Olivia Lead:
  - Triaged: TASK-842 ST2 carries this as the render-boundary axis — the one a load-time spec check cannot cover, since an override template lives on the filesystem. Grouped with BUG-837 and two further axes on the same task.
- [2026-08-26T17:45:02Z] Elias Python:
  - Fixed via TASK-842 ST2: render_view now checks has_template before rendering and raises a clean SquadsError naming both the bundled and .overrides template paths; --json is unaffected. Driven through the CLI.
- [2026-09-01T07:27:58Z] Mara Tester:
  - Verified in a scratch squad. Drove the exact original repro: a view with source+fields but no templates/views/<name>.md.j2. sq workflow lint still OK at exit 0 (expected — no items.<type>.views attachment to catch this one, matches the fix's scope). sq workflow view <name> <id> (rendered mode) now produces a clean single-line 'error: view ... has no presentation template — create one at templates/views/<name>.md.j2 (or shadow it with an adopter override at .overrides/templates/views/<name>.md.j2) ... resolve it with --json' on stderr, exit 1, no traceback (checked stdout/stderr separately, grepped for 'Traceback' — zero matches). --json on the same view/item still succeeds, exit 0, returns the projection.
<!-- sq:discussion:end -->

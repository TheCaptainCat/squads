---
id: BUG-745
sequence_id: 745
type: bug
title: Rich hard-wraps piped error output, breaking a copyable remedy
status: Verified
author: qa
description: sq inserts real newlines into stderr at 80 columns even when stderr is
  not a terminal, so a remedy command in an error message cannot be grepped or copied
  in one piece
created_at: '2026-08-20T14:21:28Z'
updated_at: '2026-08-21T16:57:35Z'
---
<!-- sq:body -->
Driven, on Linux, no override involved:

```
$ sq init --name probe 2>&1 | cat -A
error: --name 'probe': expected format slug=Full Name (e.g. architect='Ada $
Lovelace')$
```

The `$` marks a real newline. Rich renders `err_console.print` at a fixed 80-column width whether or not stderr is a terminal, so the example command an operator is told to run is split across two lines. Consequences:

- `sq ... 2>&1 | grep "architect='Ada Lovelace'"` finds nothing.
- The remedy cannot be copied in one piece from piped or captured output.
- Any script or agent that asserts on a message substring is asserting on a wrap position.

The codebase already works around this in test comments -- "Rich hard-wraps a long unbroken path at the console width with a bare newline -- flatten before searching" -- which an adopter scraping stderr cannot do.

Found by the python-dev while fixing the Windows CI failures, and deliberately not fixed there: the change is small and contained (`soft_wrap=True` on the `err_console.print` sites in `handle_errors`, `_cli/_common.py:373`, `:949`, `:968`) but it alters rendering for EVERY error message, which is not something to land on a live release PR.

Same phenomenon as the Windows failure that prompted it, one column over: Rich latches its width as `COLUMNS - legacy_windows`, and `legacy_windows` is true for a captured pipe on Windows, so the same message reflowed a word earlier there and split an assertion's literal. That was pinned test-side; this is the product half.

Worth noting what fixing this would buy beyond the defect itself: the Windows pin is currently conftest-only, so a test that fails when the pin is removed can only fail on Windows. A product-side soft-wrap would allow a platform-independent regression guard.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-20T14:21:49Z] Catherine Manager:
  - Verified myself before filing: sq init --name probe piped through cat -A shows the newline inside architect=Ada Lovelace. Not scoped to 0.13 -- the release PR is open and green-pending, and a rendering change to every error message is not a thing to slip in at this point. First candidate for 0.14.
- [2026-08-21T12:35:54Z] Pierre Chat:
  - In scope for 0.14.0: op-pierre pulled all five open bugs into the next release, overriding the earlier per-bug deferral to a later cycle.
- [2026-08-21T15:32:37Z] Catherine Manager:
  - Fix landed in ca7cee3 on release/0.14 (TASK-750). Drove the reproduction myself: sq init --name probe piped through cat -A now shows the remedy unbroken and grep for the full token matches. Falsification held at all three sites individually. Windows conftest pin kept, with reasoning recorded on the task.
  - Residual of the same defect class, driven, NOT covered by this fix: the schema-mismatch hard-stop in require_current_schema (_cli/_common.py:1011) is not soft-wrapped, and at 80 columns its remedy splits — rendering that exact message through Rich at width 80 yields "Run sq migrate \nup to upgrade it", so grep for the whole remedy fails. That is the one message every adopter with a stale squad hits, and its remedy is a command they must copy. The version notice and the per-file degrade loops share the shape. Handing to QA to file as its own bug rather than widening a task already in review.
- [2026-08-21T16:57:09Z] Mara Tester:
  - Drove the bug's exact reproduction in a throwaway dir: sq init --name probe 2>&1 | cat -A now shows the --name format error as one unbroken line; grep for the whole remedy string matches.
  - Residual of the same defect class, driven end-to-end (not just a Rich render): require_current_schema's schema-mismatch hard-stop (_cli/_common.py:1061) is NOT soft-wrapped. Built a fresh squad, set schema_version behind SCHEMA_VERSION in .squads.toml, ran COLUMNS=80 sq list piped: output is 'Run sq migrate \nup to upgrade it' — grep -c "sq migrate up" on the piped output is 0. This is the message every adopter with a stale squad hits. Filing as its own bug per the manager's handoff.
<!-- sq:discussion:end -->

---
id: BUG-745
sequence_id: 745
type: bug
title: Rich hard-wraps piped error output, breaking a copyable remedy
status: Open
author: qa
description: sq inserts real newlines into stderr at 80 columns even when stderr is
  not a terminal, so a remedy command in an error message cannot be grepped or copied
  in one piece
created_at: '2026-08-20T14:21:28Z'
updated_at: '2026-08-20T14:21:49Z'
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
<!-- sq:discussion:end -->

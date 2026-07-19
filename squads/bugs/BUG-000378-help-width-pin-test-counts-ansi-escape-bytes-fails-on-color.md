---
id: BUG-378
sequence_id: 378
type: bug
title: Help width-pin test counts ANSI escape bytes, fails on color-forcing CI
status: Verified
author: qa
created_at: '2026-07-15T21:34:25Z'
updated_at: '2026-07-19T19:05:21Z'
---
<!-- sq:body -->
`tests/cli/test_help_text_width_is_pinned.py` failed on all 3 CI OSes:

- `test_default_help_output_wraps_within_the_pinned_eighty_columns`: longest line 143 > 80
- `test_columns_genuinely_drives_the_wrap_width_proving_the_pin_is_load_bearing`: narrow max 111 > 40

Root cause: CI's console colorizes `--help` output even though the suite neutralizes the
color-forcing env vars — a known quirk already tolerated elsewhere (`tests/integration/
test_renumber_cli.py`). Rich emits ANSI SGR escape sequences into the captured help text;
both failing tests measured raw `len(line)`, which counts the invisible escape bytes
(80 visual cols renders as len 143; 40 as len 111). Confirmed locally: `FORCE_COLOR=1
COLUMNS=80` reproduces len=143 with ANSI present.

Fix: measure visual width instead of raw byte length — strip ANSI SGR codes before `len()`.
Added a shared `strip_ansi()` helper to `tests/_helpers.py` and used it in both width-pin
tests; also consolidated the pre-existing local ANSI-stripping regex in
`tests/integration/test_renumber_cli.py` to use the same shared helper. Pinned thresholds
(80 / 40) unchanged — only the measurement is now ANSI-agnostic.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T21:35:16Z] Mara Tester:
  - Fixed: added strip_ansi() to tests/_helpers.py; used it in tests/cli/test_help_text_width_is_pinned.py; consolidated the duplicate regex in tests/integration/test_renumber_cli.py to use it too.
- [2026-07-19T19:05:21Z] Mara Tester:
  - strip_ansi() present in tests/_helpers.py, used in both test_help_text_width_is_pinned.py and test_renumber_cli.py; both files pass (6 passed).
<!-- sq:discussion:end -->

---
id: BUG-1043
sequence_id: 1043
type: bug
title: override diff --json prints text when nothing drifted
status: Verified
author: qa
priority: low
refs:
- REV-1033
- MILE-1051:targets
created_at: '2026-10-16T09:09:22Z'
updated_at: '2026-10-25T11:11:49Z'
---
<!-- sq:body -->
Reproduced on the dev build in a fresh scratch squad (git-inited, `sq init`, nothing overridden).

    $ sq -C <scratch> override diff --json
    no drifted overrides found
    $ echo $?
    0

Expected: with `--json`, a JSON value on stdout, here `[]`, so a caller can `json.loads` it. Actual: a plain text line, which fails to parse.

Found while auditing the docs (REV-1033).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T11:10:59Z] `qa` Mara Tester:
  - Verified at HEAD 091bfb77: fresh squad, `sq override diff --json` prints `[]`, exit 0.
<!-- sq:discussion:end -->

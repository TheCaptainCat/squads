---
id: BUG-524
sequence_id: 524
type: bug
title: 'sq ui glance header: status text untested (US4 coverage gap)'
status: Verified
author: qa
priority: low
refs:
- FEAT-514
- TASK-519
created_at: '2026-07-21T11:48:26Z'
updated_at: '2026-07-21T14:14:21Z'
---
<!-- sq:body -->
**Gap.** FEAT-514/US4 requires status, priority, and assignee visible at a glance. The reader
panel's glance header (`_reader._glance_line`) does render all three — verified manually: for a
Draft item with priority=high and assignee=manager the rendered header text is
`⚪ Draft  ·  🟠 High  ·  manager`. Status is present and correct in the shipped code.

**But no shipped test asserts the status text appears in the header.**
`tests/tui/test_ui_app_behavior.py::test_reader_header_shows_status_priority_and_assignee_gracefully`
only asserts `"High" in header.content` and `"manager" in header.content` (plus the unassigned
fallback for a bare item) — it never checks for a status word/badge. So a future regression that
drops or breaks the status segment of `_glance_line` (e.g. a refactor that reorders `parts` and
accidentally omits the status entry) would ship silently green.

**Ask.** Add one assertion to the existing test (or a new one) checking the header contains the
item's status (e.g. `"Draft" in text`), closing the coverage gap for US4's third field.

**Severity.** Low — the underlying behaviour is correct today; this is a regression-safety gap in
the test suite, not a user-facing defect.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T11:48:42Z] Mara Tester:
  - Filed as a coverage gap (not a functional break) surfaced during EPIC-28 verification. @tech-lead please triage / route a small test addition.
- [2026-07-21T12:00:38Z] Elias Python:
  - Fixed: added an assertion that the header contains the item's status text ('Draft') alongside the existing priority/assignee checks in test_reader_header_shows_status_priority_and_assignee_gracefully.
- [2026-07-21T14:14:20Z] Catherine Manager:
  - Verified: the glance-header test now asserts the status text and the suite is green. Test-coverage fix, not operator-facing.
<!-- sq:discussion:end -->

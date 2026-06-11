---
id: BUG-000025
sequence_id: 25
type: bug
title: show prints a redundant 'Body' literal before the body
status: Done
author: op-pierre
priority: low
refs:
- FEAT-000026:relates
description: sq <type> <n> show prefixes the body with a bare 'Body' label; the body
  is self-evident after the metadata panel and usually opens with its own headings
created_at: '2026-06-10T14:52:35Z'
updated_at: '2026-06-11T13:19:34Z'
---
<!-- sq:body -->
## Observed

`sq <type> <n> show` renders the metadata panel, then a bare `Body` literal on its own line, then
the body content:

```
╰─────────────────────────────────────╯

Body
## Observed
…
```

## Expected

No `Body` label — after the metadata panel, the body is self-evidently the body, and item bodies
typically open with their own markdown headings, so the label is pure noise. (Other sections that
announce themselves, like the discussion, do so via real markdown headings that are part of the
file — that's fine; this label is the only viewer-injected literal.)

## Notes

While in there, worth a glance at whether `show` should render the body as markdown (via rich)
instead of raw text — today the `##` syntax prints verbatim. Cosmetic and separate; only the
redundant label is in scope for this bug.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T12:12:26Z] Catherine Manager:
  - Triage 2026-06-11: promoted to Ready, stays low. Quick-win batch with BUG-000030. Scope is the redundant 'Body' label only — markdown rendering of the body is FEAT-000026's domain (linked as relates).
- [2026-06-11T12:16:05Z] Olivia Lead:
  - Fix task created: TASK-000044 (low, @python-dev) — batched with BUG-000030. Drops the redundant 'Body' label; markdown rendering stays out of scope.
- [2026-06-11T12:51:04Z] Olivia Lead:
  - @qa Fix landed and reviewed (TASK-000044, Done). The redundant 'Body' literal is gone from 'sq <type> <n> show'. Please verify show output no longer carries a standalone 'Body' header while body content is intact. (Rendering body as rich markdown remains out of scope per BUG-000025/FEAT-000026.) Uncommitted in the working tree. Bug stays open until you verify.
- [2026-06-11T13:19:34Z] Mara Tester:
  - Verified fix for BUG-000025 (TASK-000044) against working tree.
  - sq bug 25 show and sq task 42 show both render the metadata panel immediately followed by the body content (## heading). No standalone 'Body' literal appears anywhere in the output.
  - Body content fully present and unchanged. Rendering body as markdown is out of scope (per BUG-000025 notes / FEAT-000026).
  - All acceptance criteria met. Closing.
<!-- sq:discussion:end -->

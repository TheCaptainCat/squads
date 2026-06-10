---
id: BUG-000025
sequence_id: 25
type: bug
title: show prints a redundant 'Body' literal before the body
status: Draft
author: op-pierre
priority: low
description: sq <type> <n> show prefixes the body with a bare 'Body' label; the body
  is self-evident after the metadata panel and usually opens with its own headings
created_at: '2026-06-10T14:52:35Z'
updated_at: '2026-06-10T14:52:36Z'
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
<!-- sq:discussion:end -->

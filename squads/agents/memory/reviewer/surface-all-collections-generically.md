---
summary: A hardcoded collection name on any machine surface is the bug — surface ALL
  spec collections generically.
created_at: '2026-07-17T20:28:43Z'
---
squads is a generic workflow engine. Every machine surface (`sq tree/list/show --json`) and every client must surface **all** spec-declared collections generically — never a hardcoded subset.

The engine is already spec-driven: `Item.badge_value(code)` reaches any declared collection (bundled `priority`/`severity` are dedicated attrs; custom ones like `impact` live in `extra`). So when a surface names a collection literally — e.g. `tree --json`'s `node()` emits `"priority": it.priority` and drops severity + customs — that hardcoding *is* the defect: the surface leaks the bundled defaults instead of reflecting the active spec.

Review lens: any collection named as a literal on a surface → check it iterates the spec's collections instead. Ties to the badge collections model (ADR-323). Root-caused as REV-448 F20.
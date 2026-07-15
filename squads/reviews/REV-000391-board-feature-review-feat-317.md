---
id: REV-391
sequence_id: 391
type: review
title: Board feature review (FEAT-317)
status: Approved
author: reviewer
refs:
- FEAT-317
description: 'Feature-level review of the bulletin board: correct + well-tested; two
  low-severity follow-ups'
subentities:
- local_id: F1
  title: Redundant frontmatter id on board notices
  status: Open
  severity: low
- local_id: F2
  title: Anti-clobber _unique_id path is untested
  status: Open
  severity: low
created_at: '2026-07-15T11:03:49Z'
updated_at: '2026-07-15T11:05:53Z'
---
<!-- sq:body -->
Feature-level review of the team bulletin board (FEAT-317: TASK-383..387), board-specific code only. Verdict: APPROVE. Behaviour is correct and meets US1-US5; gates clean (ruff/pyright/format, sq check, 44 board tests pass). Two low-severity follow-ups filed as findings below.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 391 add-finding "…" --severity medium`; track with `sq review 391 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Redundant frontmatter id on board notices |
| F2 | 🟢 low | Open |  | Anti-clobber _unique_id path is untested |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Redundant frontmatter id on board notices

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
BoardNotice.to_frontmatter_dict writes an 'id' field, but from_frontmatter takes the id from path.stem — the frontmatter 'id' is never read back (grep confirms no reader). It is fully derivable from the filename stem, and the sibling memory store (same ADR-314 tier) deliberately omits its slug from frontmatter for exactly this reason (its to_frontmatter_dict is summary/created_at/tags only). This is a 'don't store what you can derive' smell with an in-feature counterexample. Not a correctness bug (stem always wins), but it diverges from the memory sibling and stores redundant data. Recommend dropping it (update the frontmatter-shape assertion in test_post_writes_a_hash_named_markdown_file_...), or justify the divergence in the model docstring.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Anti-clobber _unique_id path is untested

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
_store._unique_id appends -2/-3 to avoid clobbering when a post hashes to an id already on disk (same author + same body + same clock second). This defensive path has no automated test, while the analogous memory slug-collision case IS pinned (test_a_repeated_fact_that_slugifies_the_same_gets_a_disambiguating_suffix). I verified it manually: posting identical (author, body) under a frozen second yields ids base and base-2, both files on disk, both listed, no clobber. Recommend a service test pinning this so a future refactor of _hash_id/_unique_id cannot silently regress it into a clobber or a lost notice.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T11:04:15Z] Paul Reviewer:
  - Verdict: APPROVE. Both findings are low-severity, non-blocking follow-ups (a derivable-data cleanup and a missing test for an already-working guard) — recording them, not gating the feature on them.
- [2026-07-15T11:05:53Z] Catherine Manager:
  - Acting on both findings before closing FEAT-317. @python-dev: F1 — drop the redundant frontmatter id from BoardNotice.to_frontmatter_dict (id is the filename stem, read via from_frontmatter(path.stem); nothing reads frontmatter['id']; align with the memory store which omits its slug). F2 — add a test pinning the _unique_id anti-clobber path (same author/body/second double-post → base + base-2, both files, both listed, no clobber), mirroring the memory slug-collision test.
<!-- sq:discussion:end -->

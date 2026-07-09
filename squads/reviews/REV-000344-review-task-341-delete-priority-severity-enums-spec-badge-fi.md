---
id: REV-344
sequence_id: 344
type: review
title: 'Review TASK-341: delete Priority/Severity enums, spec badge fields live'
status: Approved
author: reviewer
refs:
- TASK-341:addresses
subentities:
- local_id: F1
  title: Duplicate emoji-resolution logic across _common._badge_emoji and _discussion._severity_emoji/_severity_badge
  status: WontFix
  severity: low
- local_id: F2
  title: _items._parse_badge_code uses spec.collection() (raises raw KeyError) vs
    _common._parse_axis_code's graceful .get + SquadsError
  status: WontFix
  severity: low
- local_id: F3
  title: sq repair rebuilds index without _validate_badge_codes; a bogus code passes
    repair but fails next load (consistent with type/status vocab pattern, not a regression)
  status: WontFix
  severity: info
created_at: '2026-07-09T10:39:22Z'
updated_at: '2026-07-09T10:39:56Z'
---
<!-- sq:body -->
## Scope

_TODO: what is under review?_
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 344 add-finding "…" --severity high`; track with `sq review 344 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | WontFix |  | Duplicate emoji-resolution logic across _common._badge_emoji and _discussion._severity_emoji/_severity_badge |
| F2 | 🟢 low | WontFix |  | _items._parse_badge_code uses spec.collection() (raises raw KeyError) vs _common._parse_axis_code's graceful .get + SquadsError |
| F3 | 🔵 info | WontFix |  | sq repair rebuilds index without _validate_badge_codes; a bogus code passes repair but fails next load (consistent with type/status vocab pattern, not a regression) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Duplicate emoji-resolution logic across _common._badge_emoji and _discussion._severity_emoji/_severity_badge

<!-- sq:finding:F1:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
_Describe the finding, its impact, and a recommendation — free-form._
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — _items._parse_badge_code uses spec.collection() (raises raw KeyError) vs _common._parse_axis_code's graceful .get + SquadsError

<!-- sq:finding:F2:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
_Describe the finding, its impact, and a recommendation — free-form._
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — sq repair rebuilds index without _validate_badge_codes; a bogus code passes repair but fails next load (consistent with type/status vocab pattern, not a regression)

<!-- sq:finding:F3:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🔵 Info
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
_Describe the finding, its impact, and a recommendation — free-form._
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T10:39:46Z] Paul Reviewer:
  - APPROVE. Independently reviewed the uncommitted TASK-341 diff on release/0.8 (enum deletion + live spec badge fields + item-severity storage move). All 7 verify points pass.
  - Gates re-run green: pyright 0 errors, ruff check clean, ruff format clean. Targeted suites all pass (workflow_badges, load_boundary_vocab, discussion, priority_views, models, migrations, capability_flags, rendering, collab, graph, tree, workflow_spec golden-lock, reserved_types_invariants, custom_type_cli, hygiene, workflow_override/lint).
  - Verified end-to-end in a scratch squad: a legacy bug (severity under extra[X.SEVERITY], no top-level key) renders '🟠 high' with a BYTE-IDENTICAL file after repair+show (no on-disk mutation); relocates to top-level severity: and drops the extra copy on the next write; an unknown code fails closed with a clean 'error:' message, no traceback.
  - 3 findings, all LOW/info and non-blocking (marked WontFix): F1 duplicate emoji-resolution logic (TASK-342 collapses it), F2 _parse_badge_code raw KeyError vs graceful SquadsError on an unreachable path, F3 repair doesn't re-validate badge codes (consistent with existing type/status vocab seam, not a regression).
<!-- sq:discussion:end -->

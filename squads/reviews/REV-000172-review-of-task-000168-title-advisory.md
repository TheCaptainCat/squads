---
id: REV-172
sequence_id: 172
type: review
title: Review of TASK-000168 title advisory
status: Approved
author: reviewer
refs:
- TASK-168:addresses
created_at: '2026-06-23T09:29:00Z'
updated_at: '2026-06-23T09:29:18Z'
---
<!-- sq:body -->
Independent review of TASK-168 (authoring-time advisory for over-long sub-entity titles) against ADR-167. VERDICT: APPROVED — no findings.

Verified (all 8 checkpoints pass):
1. Threshold = 120, single constant TITLE_ADVISORY_MAX in _interactions.py; the only 120 literal in src/ is the constant + its docstring. No duplication.
2. Advisory/warn-and-proceed: sub-entity always created, exit 0, never gated. All three verbs (add-finding/add-subtask/add-story) route through the shared _add_block, so coverage is structural.
3. Body presence never gated — the only body check is the pre-existing reject_markers (marker safety); advisory keys solely off len(title).
4. Service does not print — warning rides on BlockResult.title_advisory; rendered only at the CLI edge in print_block, escaped via e() on the human path and included in --json.
5. Reflog delta records title_advisory only when it fires (verified in tests + code: log_delta key added only when title_advisory is not None).
6. Honesty: no enforce/guarantee/secur/forbid/prevent language in code, copy, or help; copy names the char count + the exact 'sq <type> <n> <kind> <k> body -m' fix. (grep hits were unrelated: lifecycle 'Rejected', pre-existing reject_markers.)
7. Boundary: strict '>' comparison — silent at len==120, fires at len==121. Confirmed live.
8. Tests genuinely cover above/at/below threshold, all three verbs, created-anyway, json+human, exit 0, reflog presence/absence, and wording. 38 tests pass.

Live run confirmed: 121 chars -> advisory on human + json, exit 0, finding created; 120 chars -> silent, exit 0. The advisory's body command (sq review 9 finding F1 body -m) is a valid invocation form.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 172 add-finding "…" --severity high`; track with `sq review 172 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

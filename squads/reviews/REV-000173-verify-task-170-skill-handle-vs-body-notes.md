---
id: REV-173
sequence_id: 173
type: review
title: Verify TASK-170 skill handle-vs-body notes
status: Approved
author: reviewer
refs:
- TASK-170:addresses
created_at: '2026-06-23T09:29:35Z'
updated_at: '2026-06-23T09:29:51Z'
---
<!-- sq:body -->
Independent review of TASK-170 (skill reinforcement: sub-entity titles are handles, prose in body). APPROVED — no findings.

Verified against ADR-167 and the task acceptance criteria:
- Notes live in the template source (PLAYBOOK in _interactions.py, lines 104/166/327), not hand-edited into the generated sq-*.md files.
- Idempotency (ST3): `sq sync` regenerated the managed skills and produced byte-identical output — zero new churn, same 3/2/2-line diffstat as the dev's commit.
- All three skills carry a clear, in-voice note: sq-review (finding title = handle, detail in finding body), sq-task (subtask), sq-feature (story = user-story phrase, criteria in body). Each names the body command.
- test_item_skills_teach_handle_vs_body_note asserts the three notes via specific substrings; passes and would fail if any note were removed. Full tests/test_skills.py suite green.
- Managed banners and sq markers intact; ruff check + format clean.
- Wording consistent with ADR-167 in spirit; correctly does not gate body presence (per ADR).

Note: the diff also contains TASK-168 changes (_subentities.py / _results.py / _common.py authoring-time advisory) — out of this review's scope, not assessed here.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 173 add-finding "…" --severity high`; track with `sq review 173 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

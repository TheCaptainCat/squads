---
id: REV-649
sequence_id: 649
type: review
title: 'Per-type display labels: LabelSpec + label_for resolver'
status: Approved
author: reviewer
refs:
- TASK-648
subentities:
- local_id: F1
  title: LabelForm is a bare alias, not PEP-695 type
  status: Verified
  severity: low
- local_id: F2
  title: Empty-string pin fallback is untested
  status: Verified
  severity: low
created_at: '2026-07-24T12:23:04Z'
updated_at: '2026-07-24T12:47:04Z'
---
<!-- sq:body -->
Independent review of the per-type display-label implementation (ADR-646) on release/0.12.1. Verified: label_for pin-else-derive across all four independent forms with acronym caps preserved; single-place fallback (_fallback_label); no-raise degradation for missing spec/undeclared type/absent labels/unset form; empty-string pin falls back; frozen LabelSpec with extra=forbid; additive ItemSpec.labels defaulted None; SCHEMA_VERSION unchanged (0.11, no migration); both backend call sites have spec/ctx.spec in scope and default output is byte-identical to the old .capitalize(). The excluded sub-entity-kind .title() sites (_cli/_common.py, _discussion.py, _retype.py) are a correct out-of-scope call — a different vocabulary axis. Two low-severity nits below; correctness matches ADR-646.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 649 add-finding "…" --severity medium`; track with `sq review 649 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — LabelForm is a bare alias, not PEP-695 type

<!-- sq:finding:F1:body -->
`_models/_vocab.py:33` declares `LabelForm = Literal["singular", "plural", "singular_lower", "plural_lower"]` as a bare assignment. The project convention (and an explicit operator preference) is PEP-695 `type LabelForm = Literal[...]`, matching the 5 existing aliases (_loader.py, _util.py, _validators.py, _maintenance.py, _import_model.py). Severity: low (convention/consistency, not correctness). One-line fix.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Empty-string pin fallback is untested

<!-- sq:finding:F2:body -->
The resolver correctly falls back on an empty-string pin (`return pinned if pinned else _fallback_label(...)`, and the docstring promises "present and non-empty"), but no test proves it. The four-form/partial/acronym/no-spec/undeclared/extra=forbid cases are all covered; only the empty-string-pin edge is unproven. Severity: low (coverage). Add one assertion, e.g. LabelSpec(singular="") resolves to the derived form.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T12:46:02Z] Paul Reviewer:
  - F1 fixed: LabelForm now a PEP-695 `type` alias. F2 fixed: empty-string-pin fallback test added (LabelSpec(singular='') on 'bug' resolves to 'Bug'). Fast gates + full suite green.
<!-- sq:discussion:end -->

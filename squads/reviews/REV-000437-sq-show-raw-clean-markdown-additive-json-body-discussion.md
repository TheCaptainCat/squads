---
id: REV-437
sequence_id: 437
type: review
title: sq show --raw clean markdown + additive --json body/discussion
status: Approved
author: reviewer
refs:
- TASK-434:addresses
created_at: '2026-07-16T18:25:25Z'
updated_at: '2026-07-16T18:27:57Z'
---
<!-- sq:body -->
## Scope

Independent review of the TASK-434 diff only: `src/squads/_cli/_common.py`, `_items.py`, `_main.py`, `CHANGELOG.md`, the new `item_show_raw.txt` golden + `test_show_raw_markdown_golden.py`, and the `feature_show.json` / `task_show.json` JSON goldens. Concurrent `clients/vscode/**` work ignored.

## Verdict: APPROVE

No blocking findings. The additive-only `--json` invariant and the byte-identical-across-flags invariant are both independently confirmed; `--raw` matches the architect's surface spec; the default styled path is unchanged.

## Gate: additive-only --json (verified)

Golden diffs are strictly additive: top-level `body` + `discussion` appended after `id`; per-subentity `body` appended after `extra`. Nothing renamed, removed, or destructively reordered (only trailing-comma churn on the prior last lines). `print_json_clean` re-parses + re-indents, so the intermediate `json.dumps` separator style is irrelevant; key set and insertion order are what carry, and both are preserved (existing fields from `model_dump_json`, new keys appended).

## Gate: byte-identical across flags (verified two ways)

1. `test_json_output_is_byte_identical_regardless_of_raw_or_comments_flags` passes (base == raw == comments).
2. Reproduced by hand on a fully populated task (body + subtask-with-body + comment), both entry points: `sq task 3 show --json` == `--json --raw --full --comments`, `== --json --comments`, and `sq show TASK-3 --json` == `--json --raw --full --comments`. All byte-identical. `body`/`discussion`/subentity-`body` present unconditionally.

## Ruling on the flagged judgment call (spec.fields_for vs literal 'priority')

Rendering the metadata block by iterating `spec.fields_for(type)` is the CORRECT call — endorse, do not change to a literal 'priority'. The ADR listed 'priority' illustratively (task was the example type). The generic path is more spec-correct (a bug's `severity` renders; custom collections render) and, decisively, it is byte-for-byte the same pattern the styled panel already uses (`_build_item_panel_rows` iterates `fields_for()` with the identical rationale comment and identical refs rendering). Hard-coding 'priority' would make `--raw` inconsistent with the styled surface and regress bug/custom-spec output, violating the badge-collections model.

## Other checks

- `--raw` structure matches spec: `# TYPE-N — title` H1, bold-key bullets with absent fields omitted, verbatim body, `## Discussion` with `### author — ISO-ts` under --comments (+ `_(no discussion)_` fallback), one `## Kind local_id — title` section per sub-entity under --full. Zero Rich chrome (box chars / `===` asserted absent).
- Default styled show confirmed unchanged: still emits the box panel; `raw` early-returns before the Panel path, and `styled = _is_styled()` is reached only when not raw, so it is logically identical to the prior `_is_styled() and not raw`.
- Determinism: field/ref/label order is stable, timestamps come from stored data under the frozen clock. Golden is stable.
- Conventions: raw path prints via `console.print(markup=False, highlight=False, soft_wrap=True)` (no escaping needed, no marker writes); services accessed through the ABC/service; no bare datetime; strict pyright/ruff clean on touched files; no dead code (`_subentity_pane_title_raw` still used by the styled path; the extracted `_subentity_badge_line` is shared by both).
- Refactor quality: helpers are cohesive and DRY (`_subentity_badge_line` de-dups the badge portion across styled + raw; `_raw_metadata_lines`/`_raw_subentity_sections`/`_print_item_raw`/`build_item_json` are small and single-purpose).

## Evidence

- `uv run pytest -n auto tests -k 'show or raw or json or golden'` -> 132 passed, exit 0.
- `uv run pyright` (touched files) -> 0 errors. `ruff check` -> All checks passed. `ruff format --check` -> 4 files already formatted.
- `uv run sq check` -> no issues.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 437 add-finding "…" --severity medium`; track with `sq review 437 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-16T18:26:05Z] Paul Reviewer:
  - Verdict: APPROVE, no blocking findings. Reviewer gate cleared: --json change is additive-only (goldens append body/discussion + per-subentity body, nothing renamed/removed) and byte-identical-across-flags holds — confirmed via the invariant test AND a manual diff on a populated item across both show entry points. Ruling: the spec.fields_for(type) generic metadata block is the right call (matches the styled panel's existing pattern; more spec-correct than a literal 'priority'). TASK-430 may proceed.
  - @python-dev nice work — surface spec matched exactly, clean refactor. Not changing TASK-434 status; @tech-lead / main loop to mark Done per the reviewer gate.
<!-- sq:discussion:end -->

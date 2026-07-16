---
id: TASK-434
sequence_id: 434
type: task
title: 'Core: clean sq show --raw + additive --json body/discussion keys'
status: Draft
parent: FEAT-100
author: tech-lead
assignee: python-dev
refs:
- ADR-427:addresses
created_at: '2026-07-16T15:40:21Z'
updated_at: '2026-07-16T15:41:09Z'
---
<!-- sq:body -->
## Goal

Core (Python) prerequisite that unblocks US2 (the VS Code preview, TASK-430). Fix two existing `sq show` surfaces so the extension has a clean, deterministic markdown feed and a complete structured surface. **No new flag** — fix the two surfaces that already exist. This is core Python work (Elias / python-dev), not TypeScript.

## (A) `sq show <id> --raw` — clean, preview-ready output

`--raw` must emit a deterministic, markdown-preview-clean dossier with **zero Rich chrome**: no box-drawing header panel, no space-aligned summary table, no `=== US … ===` separators. Structure:

- `# TYPE-N — <title>` (H1).
- A metadata block as a **bullet list of bold-key lines** — `- **status:** …` for status / priority / assignee / parent / author / refs / labels; **omit absent fields** (chosen over a markdown table: deterministic, no column-width ambiguity, clean omission).
- A blank line, then the **body markdown verbatim**.
- `--comments` appends `## Discussion`, each comment as `### <author> — <ISO ts>` followed by its markdown.
- `--full` appends one `## <Kind> <local_id> — <title>` section per sub-entity (badge line + body markdown).

**Only `--raw` changes.** The default styled mode keeps its Rich rendering for terminal humans — do not touch it.

## (B) `sq show <id> --json` — additive superset (new keys only)

Nothing renamed or removed. Add:

- top-level `body` — the raw body markdown;
- top-level `discussion` — an ordered list of `{author, ts, body}`;
- `body` on each object in the existing `subentities` array (currently state-only: assignee/extra/local_id/severity/status/story/title).

Include these keys **unconditionally** — not gated by `--comments`/`--full` — so the existing invariant that `show --json` is byte-identical across `--raw`/`--comments`/`--full` still holds (see `test_json_output_is_byte_identical_regardless_of_raw_or_comments_flags`).

## (C) Back-compat / changelog

- No current test or consumer asserts the box-panel chrome — the two `--raw` tests (`test_show_command_renders_body_and_subentities`, `test_body_content_source_and_mutual_exclusion_cli`) only assert body substrings (e.g. `## Section` passthrough), which the clean output preserves.
- `--raw` is human-facing plain text, **outside FEAT-15's frozen machine surface** (which froze `--json` shapes + exit codes), so the clean-output change is not a frozen-surface break. The `--json` additions are additive, so they don't break the freeze either.
- BUT `--raw` is a user-visible formatting change → a **CHANGELOG note is required** (user-facing, no internal/sq/process refs per the docs rule).

## (D) Golden-freeze (acceptance)

- **Add** a new `--raw` text golden (e.g. `item_show_raw.txt`) covering an item with body + sub-entities + a comment, deterministic under the frozen clock.
- **Update** the existing per-type `*_show.json` goldens (`feature_show.json`, `task_show.json`, and any other `show --json` golden) for the new `body`/`discussion`/subentity-`body` keys — in the **same change**.
- Both surfaces then carry FEAT-15-style golden coverage.

## Acceptance criteria

- `sq show <id> --raw` produces the exact structure above with zero Rich chrome; `--comments`/`--full` append the Discussion / sub-entity sections as specified.
- Default (non-`--raw`) `sq show` is byte-for-byte unchanged (Rich rendering intact).
- `sq show <id> --json` carries `body`, `discussion`, and per-subentity `body`, present unconditionally; byte-identical across `--raw`/`--comments`/`--full`; no key renamed or removed.
- New `--raw` text golden added; all `*_show.json` goldens updated in the same change; full suite green.
- CHANGELOG note added for the `--raw` formatting change.

## Reviewer gate (state for the review step)

Because this touches FEAT-15-frozen `*_show.json` goldens, the **reviewer must verify** the claim that the `--json` change is **additive-only** and the **byte-identical-across-flags invariant is preserved** before the extension work (TASK-430) proceeds. Treat that verification as a required gate, not a formality.

## ADR-427 constraint

Addresses ADR-427 #2 (consumer contract): US2's preview reads the **rendered** `sq show --raw`; this task makes that surface clean prose with no frontmatter or `<!-- sq:* -->` marker noise. The extension pins no schema and reads only these `sq` surfaces.

## Implementer note

sq/ticket IDs must not appear in source, especially test/golden file names — name by behavior (`item_show_raw.txt`, `test_show_raw_is_markdown_clean`, …), keep the ticket pointer in the sq task / PR.

Implements FEAT-100 (core prerequisite for story US2). Addresses ADR-427.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 434 add-subtask "<title>"`; track with `sq task 434 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

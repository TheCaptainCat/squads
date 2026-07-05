---
id: REV-130
sequence_id: 130
type: review
title: 'FEAT-17 1.0 hardening: independent gate (corpus, scale, completion, Py3.14
  ADR)'
status: Approved
parent: FEAT-17
author: reviewer
refs:
- TASK-126
- TASK-127
- TASK-128
- ADR-129
description: Independent review of the four FEAT-17 deliverables; gate run clean.
subentities:
- local_id: F1
  title: Corpus does not exercise the 0.1->0.2 review findings-skeleton path
  status: Open
  severity: low
- local_id: F2
  title: README completion claim about 'uv run sq' is slightly overstated
  status: Open
  severity: info
created_at: '2026-06-15T12:29:05Z'
updated_at: '2026-06-15T12:29:56Z'
---
<!-- sq:body -->
Independent review of FEAT-17 (1.0 hardening) across TASK-126 (migration fixture corpus), TASK-127 (scale test), TASK-128 (shell completion), and ADR-129 (Python >=3.14 floor). Built in parallel by separate agents; this is the independent gate.

Gate: uv run pytest -m 'not slow' (708 passed, 1 skipped) + uv run pytest -m slow (5 passed) + uv run pyright (0 errors) + uv run ruff check (clean) + uv run ruff format --check (clean). All green.

Non-vacuousness CONFIRMED. v0_1 fixture genuinely starts at schema 0.1 (extra.ref_kinds map, legacy '### ST1 — [ ] … (→ US1)' checkbox headings, no sequence_id, no :meta) and a real 'sq migrate up' fires BOTH runners (0.1→0.2 folds ref_kinds inline + builds :meta + summaries; 0.2→0.3 lifts :meta into the subentities frontmatter list, backfills sequence_id, renders :head, drops :meta) reaching schema 0.3. v0_2 genuinely starts at 0.2 (inline ID:kind refs, :meta regions with status/severity/story, no subentities, no sequence_id) and exercises the 0.2→0.3 runner. v0_3 is current and a legitimate no-op. The corpus is NOT a trivially-already-current set.

Verdict: APPROVED. Two non-blocking findings (low/info) recorded.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 130 add-finding "…" --severity high`; track with `sq review 130 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Corpus does not exercise the 0.1->0.2 review findings-skeleton path |
| F2 | 🔵 info | Open |  | README completion claim about 'uv run sq' is slightly overstated |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Corpus does not exercise the 0.1->0.2 review findings-skeleton path

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The 0.1->0.2 runner has a review-specific branch (_insert_findings_skeleton + ensure_summary) for legacy reviews that have free-form prose findings and NO :findings container. The corpus v0_1/reviews/ directory is empty, so no v0_1 review exercises this branch end-to-end through the corpus. v0_2's review already has a :findings container so it only covers the 0.2->0.3 finding-lift, not the 0.1->0.2 skeleton insertion. Non-blocking: that branch retains its own unit coverage in tests/test_migrations.py, and the FEAT-17 acceptance bar (every released schema migrates to current + clean check) is met. Suggestion: add a REV-* file to corpus/v0_1/reviews/ in the legacy pre-0.2 shape (a '## Findings' prose section / Summary table, no :findings markers) so the corpus covers all 0.1->0.2 transforms.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — README completion claim about 'uv run sq' is slightly overstated

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🔵 Info
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
README's Shell completion note says completion 'will not work through uv run sq because uv run wraps the entry point in a way that the shell cannot discover.' That's a reasonable practical caveat (the shell completes the binary name on PATH, and there is no 'uv run sq' binary), but the phrasing 'wraps the entry point' is imprecise — the real reason is that tab-completion keys off a command named 'sq' present on PATH, which a 'uv run' invocation is not. The install steps (--install-completion bash|zsh, restart/source) are accurate and the --show-completion scripts are verified non-empty/well-formed (test asserts _sq_completion/complete_bash for bash, '#compdef sq'/complete_zsh for zsh). Informational only; optionally tighten the wording.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

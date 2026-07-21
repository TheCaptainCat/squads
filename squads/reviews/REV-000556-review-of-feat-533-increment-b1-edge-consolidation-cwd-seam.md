---
id: REV-556
sequence_id: 556
type: review
title: 'Review of FEAT-533 Increment B1: edge consolidation + cwd seam'
status: Approved
author: reviewer
refs:
- FEAT-533
subentities:
- local_id: F1
  title: _bind_active_spec does not thread client_cwd; diverges from the other spec-resolution
    path
  status: Verified
  severity: low
created_at: '2026-07-21T22:33:52Z'
updated_at: '2026-07-21T23:11:38Z'
---
<!-- sq:body -->
Independent review of FEAT-533 Increment B1 — TASK-552 (active-spec/active-dir onto RequestContext + single-bind CLI edge consolidation) and TASK-553 (per-request cwd resolution). Reviewer did not author the code.

Verdict: APPROVE WITH NITS. The edge consolidation is correct and byte-identical for one-shot CLI: main_callback now assembles ONE bind_context(RequestContext(...)) per invocation with every field freshly computed, replacing the old mix of module-global sets (_active_dir/_active_spec) and per-field context rebinds (apply_timestamp/set_actor/seed_session). Field-by-field equivalence holds; --at forging and the invalid-timestamp exit-2 path verified end-to-end; pyright/ruff/format clean, full suite green, sq check clean.

REV-555 F1 (stale main_callback comment) — GENUINELY RESOLVED: the misleading 'same mechanism apply_timestamp uses for the clock' comment is gone; _resolve_clock_override now carries an accurate docstring and main_callback states plainly that clock is the one field deliberately inherited while actor/session/spec/dir are force-reset.

REV-555 F2 (hybrid-reset gap) — GENUINELY RESOLVED: the edge is no longer a hybrid of set_*() mutations against leftover state; it is a single fresh RequestContext bind. Clock carry-forward is preserved (prior.clock_override when --at absent) but is now an explicit, documented, single-field choice rather than an emergent gap. Concurrent-request isolation holds because the ContextVar is task-scoped; a real server binds its own fresh context per request rather than reusing the Typer callback.

One Low, forward-looking finding (F1) on a client_cwd threading inconsistency between the two spec-resolution paths. No correctness defect for one-shot CLI.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 556 add-finding "…" --severity medium`; track with `sq review 556 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Verified |  | _bind_active_spec does not thread client_cwd; diverges from the other spec-resolution path |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — _bind_active_spec does not thread client_cwd; diverges from the other spec-resolution path

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
In main_callback, active_spec is resolved via _bind_active_spec(dir), which calls resolve(dir_override) WITHOUT passing client_cwd — so it uses resolve's Path.cwd() fallback. Its sibling reach-in fix, _CustomTypeGroup._resolve_spec_for_ctx, was correctly updated to pass resolve(dir_override, client_cwd=get_context().client_cwd). Two spec-resolution paths now disagree on how they obtain the resolution base.

One-shot CLI: harmless and byte-identical. At the point _bind_active_spec runs, client_cwd is being seeded as Path.cwd() in the same breath, so both paths resolve from the identical directory. All gates + suite green confirm this.

Forward-looking failure scenario (the exact class FEAT-533 targets): if a future server/daemon ever drives this edge with client_cwd != process cwd, active_spec would be resolved from the process cwd while active_dir/get_service resolve from the client cwd — a spec/dir mismatch (wrong workflow spec applied to the right squad, or vice-versa). A server would build its own request handler rather than reuse the Typer callback, so this is not a defect in the shipped one-shot increment; recording it so the seam is threaded consistently if the edge is ever generalized. Fix is trivial: _bind_active_spec should accept/thread the same client_cwd used for the RequestContext (e.g. resolve(dir_override, client_cwd=Path.cwd()) computed once and shared).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

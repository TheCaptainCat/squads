---
id: REV-97
sequence_id: 97
type: review
title: TASK-000089 — sq override group, staleness machinery, hash manifest (FEAT-000014,
  ADR-000085 §3)
status: Approved
author: reviewer
refs:
- TASK-89:addresses
subentities:
- local_id: F1
  title: Manifest-freshness unguarded — silent drift-miss at release
  status: Fixed
  severity: medium
- local_id: F2
  title: New override list/diff --json read commands not golden-pinned
  status: Fixed
  severity: medium
- local_id: F3
  title: gen_template_manifest.py docstring exit-code claim is wrong
  status: Fixed
  severity: low
- local_id: F4
  title: Bare 'sq override diff' hides broken overrides (filters to drifted)
  status: Open
  severity: low
- local_id: F5
  title: 'Delta-upgrade blocked: base_version_template_content is hash-only'
  status: Open
  severity: low
created_at: '2026-06-12T22:00:54Z'
updated_at: '2026-06-23T09:59:44Z'
---
<!-- sq:body -->
Review of TASK-89 — the `sq override` command group, staleness stamps, per-release content-hash manifest, and `sq check` drift integration under FEAT-14, against accepted ADR-85 §3.

**Verdict: Approved.** The contract surface is faithfully implemented, the FEAT-15 exit-code contract is intact and tested, marker safety holds, and `sq migrate` is proven not to touch `.overrides/`. Suite green (540 passed, 1 skipped), pyright/ruff clean, `uv build` ships the manifest + 20 templates, and the manifest regenerates byte-stable. Findings below are all low/medium robustness + consistency gaps — none block the merge, but FINDING-1 (manifest-freshness guard) and FINDING-2 (golden-pin the new --json shapes) are worth closing before 1.0 since this is durable-contract surface.

## Verified against ADR §3 (behaviours, not just presence)
- `scaffold` stamps with the current `__version__` (0.3.0); refuses clobber without `--force`; only command that writes bodies; invalidates the engine cache so the new override is picked up.
- `diff` renders BOTH deltas: Δ-mine (override vs current bundled) and Δ-upgrade (base-version bundled vs current bundled), with a graceful "cannot recover base snapshot" message when the hash-only manifest can't reconstruct old content.
- `update` re-stamps ONLY the stamp line (verified body untouched by test) and clears the warning; bulk mode skips broken overrides.
- `list` reports current/drifted/broken state per ADR §5.
- `sq check`: missing-required-marker → error (exit 3); version-drift / unstamped → warn (exit 0). Confirmed in CLI tests test_check_exit3_on_missing_marker and test_check_exit0_on_warn_only, and the JSON path (test_cli_check_json_override_error).
- Marker safety: the `<!-- squads:override-base -->` stamp is NOT matched by `find_markers` (strict sq:-only) nor by the service's `_SQ_OPEN_RE`; TOML `#` stamp form is a standard comment. Confirmed empirically.
- `sq migrate up` leaves `.overrides/` byte- and mtime-identical (test_migrate_does_not_touch_overrides).

## FEAT-15 exit-code contract — INTACT
`_cli/_main.py::check` derives exit purely from `sum(level == "error")`; override warns feed in as `CheckIssue("warn", …)` and never reach the error count. Both human and `--json` paths preserve exit 3 on error / exit 0 on warn-only. Directly tested both ways.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 97 add-finding "…" --severity high`; track with `sq review 97 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Fixed |  | Manifest-freshness unguarded — silent drift-miss at release |
| F2 | 🟡 medium | Fixed |  | New override list/diff --json read commands not golden-pinned |
| F3 | 🟢 low | Fixed |  | gen_template_manifest.py docstring exit-code claim is wrong |
| F4 | 🟢 low | Open |  | Bare 'sq override diff' hides broken overrides (filters to drifted) |
| F5 | 🟢 low | Open |  | Delta-upgrade blocked: base_version_template_content is hash-only |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Manifest-freshness unguarded — silent drift-miss at release

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Manifest-freshness is unguarded — silent drift-miss at release. The whole feature fails OPEN if scripts/gen_template_manifest.py isn't re-run before a release that changes a template: template_changed_since() returns False for a missing/stale current-version entry, so every override silently shows no drift — exactly what the feature exists to prevent. The dev's @devops note documents the manual build step but nothing enforces it. test_manifest_loads_current_version_hashes only checks ONE template has *a* hash, not that it matches current bundled content, and not that all 20 are present. A single guard test would convert this from a release-time human-memory failure into a red build.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — New override list/diff --json read commands not golden-pinned

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
New --json read commands (override list/diff) are not golden-pinned. FEAT-15/TASK-84 established that EVERY --json read command gets a golden in tests/goldens/ pinned by test_golden_json.py, so any shape drift fails the build. override list --json and override diff --json are new read commands joining the 1.0 machine-readable surface but are only key-set-asserted in test_override_commands.py — not added to the golden suite. Consistency gap against a just-frozen convention; should be closed before 1.0.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — gen_template_manifest.py docstring exit-code claim is wrong

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
gen_template_manifest.py docstring exit-code claim is wrong. Docstring says 'Exit codes: 0 = success, 1 = error (already at this version with unchanged hashes; nothing to write...)'. The no-change path actually prints and exits 0 (correct behaviour for a no-op), so the docstring contradicts the code. Fix the docstring (exit 0 on no-op is fine to keep).
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Bare 'sq override diff' hides broken overrides (filters to drifted)

<!-- sq:finding:F4:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
diff with no name hides broken overrides. The bare 'sq override diff' path filters to STATE_DRIFTED only, so a user whose only override is BROKEN (missing marker) gets 'no drifted overrides found' with no hint that a broken override needs attention. ADR scopes bare diff to drifted, so not a contract violation, but a one-line note pointing at 'sq override list'/'sq check' for broken overrides would close the UX gap.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Delta-upgrade blocked: base_version_template_content is hash-only

<!-- sq:finding:F5:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
base_version_template_content is hash-only, so Δ-upgrade is unavailable for any genuinely-upgraded template. By design the manifest stores hashes not snapshots, so base content is recoverable only when base_hash == current_hash (i.e. unchanged) — meaning the Δ-upgrade view degrades to the '(cannot recover...)' message in exactly the case it is most needed (template changed since base). ADR §3 step 2 describes Δ-upgrade as 'reconstructed from the manifest plus the bundled archive it indexes'; the manifest indexes nothing but hashes. The code handles this gracefully and the limitation is documented in the docstring, but it is a partial fulfilment of the ADR's stated Δ-upgrade capability — flagging so it is a deliberate, recorded deferral rather than an unnoticed shortfall.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T22:01:48Z] Paul Reviewer:
  - Verdict: APPROVED. Contract surface matches ADR-85 §3, FEAT-15 exit-code contract intact and tested both ways, marker safety holds, migrate proven not to touch .overrides/, suite green, build ships the manifest, manifest regenerates byte-stable and its hashes match the installed bundle.
  - Five non-blocking findings filed (2 medium, 3 low). No open high-severity findings — approval is clean. Recommend closing F1 (manifest-freshness guard test) and F2 (golden-pin override list/diff --json) before 1.0 since this is durable-contract surface; F3-F5 are polish/recorded-deferral. @python-dev these can be picked up as follow-ups, not a re-review gate.
<!-- sq:discussion:end -->

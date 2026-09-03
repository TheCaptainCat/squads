---
id: REV-662
sequence_id: 662
type: review
title: Release version-bump script (bump_version.py)
status: Approved
author: reviewer
refs:
- TASK-661:scopes
created_at: '2026-07-27T09:58:58Z'
updated_at: '2026-07-27T10:00:29Z'
---
<!-- sq:body -->
Independent review of the release version-bump automation: the `scripts/bump_version.py` orchestrator, its pure rewrite helpers, the `tests/meta` self-test, the `gen_template_manifest.py` future-annotations removal, and the `releasing-squads` runbook Prep collapse.

## Verified
- **Pure helpers** — `read/set_pyproject_version` scope replacement to the `[project]` table (the section regex stops at the next `[…]`, so `[project.optional-dependencies]` and any same-named key elsewhere are untouched); `read/set_package_json_version` rewrite only the matched value, preserving other keys/formatting/newline. Both idempotent; both reject malformed / absent-version input.
- **Orchestration fidelity** — the 8 steps match the runbook: pyproject + package.json lockstep bump, `uv sync --all-extras`, the manifest gotcha (prior version read in step 1, `git checkout v<prior> -- <manifest>` guarded by a `git rev-parse` tag-existence check that skips-with-note when absent, then a bare `gen_template_manifest.py` run = write mode), goldens regen under `UPDATE_GOLDENS=1`, `sq sync`. Every subprocess goes through `_run`, which raises `BumpError` (non-zero exit) on failure. No CHANGELOG edit, commit, tag, or push.
- **Dry-run safety** — verified byte-identical: every `write_text` / `subprocess.run` (including the `_tag_exists` probe) sits behind a `dry_run` guard; a `0.99.0 --dry-run` left pyproject / package.json / manifest md5sums and `git status` unchanged.
- **Tests** — 11 pass; cover helper correctness/idempotency/malformed-input plus a dry-run smoke test that patches `subprocess.run` and `Path.write_text` to raise and asserts the real files are unchanged. The tests/meta placement with inline pyright ignores (scripts/ outside pyright include) is reasonable and hides no real issue.
- **Conventions** — no `from __future__ import annotations` anywhere; no ticket IDs / build-narration in script or test names; SKILL-508 markers intact, no stray content wrapper; ruff check + format + pyright clean; `sq check` clean.

No findings.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 662 add-finding "…" --severity medium`; track with `sq review 662 finding <n> update --status <Status>`._

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T09:59:45Z] Paul Reviewer:
  - Independent review of TASK-661 (branch tooling/bump-version-script). No findings — helpers correct/idempotent/reject-malformed, 8-step orchestration faithful to the runbook (manifest-gotcha order + tag-existence guard + bare gen = write mode), no CHANGELOG/commit/tag/push. Dry-run verified byte-identical (pyproject/package.json/manifest md5 + git status unchanged). 11 tests pass; ruff/pyright/sq check clean. Recommend Approve after the full suite. @manager
- [2026-07-27T10:00:27Z] Paul Reviewer:
  - Verified: dry-run byte-identical (all writes/subprocess guarded); manifest-gotcha faithful (prior read, tag-guarded checkout, regen order correct); helpers scope-correct + reject malformed input; no future-import; SKILL-508 Prep collapsed to the script call. Full suite green.
<!-- sq:discussion:end -->

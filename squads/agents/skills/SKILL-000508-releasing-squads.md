---
id: SKILL-508
sequence_id: 508
type: skill
title: Releasing squads
status: Active
author: releasing-squads
refs:
- ROLE-1:scopes
- ROLE-6:scopes
- ROLE-8:scopes
description: 'The team''s runbook for cutting a squads release: gates, prep, and drafting
  the release (the operator publishes).'
created_at: '2026-07-20T12:32:09Z'
updated_at: '2026-07-24T08:51:26Z'
extra:
  slug: releasing-squads
  description: 'The team''s runbook for cutting a squads release: gates, prep, and
    drafting the release (the operator publishes).'
  when_to_use: When preparing or cutting a squads release.
  allowed_tools: ''
---
<!-- sq:body -->
# Releasing squads

The team's runbook for cutting a squads release. Agents take it all the way to a **green,
ready-to-merge PR**, then a **ready-to-publish release draft**; the operator does the merge and the
actual GitHub publish. Never `git tag` or publish yourself.

## 1. Gates — all green before anything else

- `uv run sq check` clean for the work being released.
- **Full suite** green: `uv run --all-extras pytest -q` — run it once, redirect to a file, read the
  file. A subagent's targeted `-k` run is not the gate; the coordinating loop owns the full suite.
- `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .` clean.
  (`--all-extras` is required — a bare `uv run` prunes the optional `tui` extra and pyright floods
  with false `textual` import errors.)

## 2. Prep

- `git fetch --tags` first — local tags go stale and mislead "what's released / next version".
- **CHANGELOG.md**: move `[Unreleased]` into the new version section, Keep-a-Changelog style. Make
  sure it covers *everything* in the release — late-landing features are easy to miss.
- Bump `version` in `pyproject.toml`.
- **Template-manifest gotcha**: dev-time regens dirty the *last released* entry (the script keys by
  `__version__`). Restore it from its tag first —
  `git checkout vX.Y.Z -- src/squads/_rendering/templates_manifest.json` — then bump the version and
  regenerate (`scripts/gen_template_manifest.py`) so a clean new entry appends and the released one
  stays byte-identical to its tag.
- **Schema**: if `SCHEMA_VERSION` changed, confirm the migration is registered and `sq migrate up`
  runs clean, and add a `### Migration` note to the changelog.
- Build: `uv build` → wheel + sdist in `dist/` (templates + manifest ship as package data).

## 3. Push, open the PR, and watch the pipeline to green

- Push the release branch and open the PR into `main`:
  `gh pr create --base main --head release/X.Y --title "Release X.Y.0 - <headline tagline>" --body-file <notes>`.
  PR house style: a short narrative opener (call out schema/migration status — "No schema migration"
  when nothing bumped), then `## Added` / `## Changed` / `## Fixed` / `## Migration` with bold-lead
  bullets (the CHANGELOG's own sections). Match the last few PRs — `gh pr view <n>`.
- **Watch CI to green — do not hand off a red PR.** `gh pr checks <n>` (poll, or `gh run watch`).
  The `test` job runs a **real OS matrix (macOS/Ubuntu/Windows)** — slower, contended runners that
  surface timing/env failures a fast local machine hides (e.g. TUI async-render races that pass
  locally). If any check fails: `gh run view --job <id> --log-failed`, diagnose, fix, commit,
  re-push (CI re-runs), and loop until **every** check passes. This is the point where the coordinator
  earns the operator's one-click merge.

## 4. Hand off the PR — "CI green, ready to merge"

Stop at **green PR** and hand to the operator. Merging into `main` is theirs — that's the one click.
Everything up to a green PR is the agent's job.

## 5. After the merge — draft the release (a draft never tags or fires CI)

- `gh release create vX.Y.Z --draft --target main --title "Version X.Y.Z - <tagline>" --notes-file <notes>`
- House style: title `Version X.Y.Z - <headline tagline>`; body opens with a short narrative
  paragraph (call out schema/migration status), then bold section headers (`**Added**` / `**Changed**`
  / `**Fixed**` / `**Migration**`) with bold-lead bullets. Match the last ~3 releases —
  `gh release view <tag>`.

## 6. Hand off the release — the operator publishes

Publishing the GitHub release is theirs — it creates the tag and fires `publish.yml` (PyPI + the VS
Code Marketplace VSIX). The operator also decides the release string and any dated-commit specifics.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

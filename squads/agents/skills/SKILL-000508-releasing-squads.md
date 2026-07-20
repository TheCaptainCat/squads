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
updated_at: '2026-07-20T12:32:12Z'
extra:
  slug: releasing-squads
  description: 'The team''s runbook for cutting a squads release: gates, prep, and
    drafting the release (the operator publishes).'
  when_to_use: When preparing or cutting a squads release.
  allowed_tools: ''
---
<!-- sq:body -->
# Releasing squads

The team's runbook for cutting a squads release. Agents take it all the way to a **ready-to-publish
draft**; the operator does the actual GitHub publish. Never `git tag` or publish yourself.

## 1. Gates — all green before anything else

- `uv run sq check` clean for the work being released.
- **Full suite** green: `uv run pytest tests/ -q` — run it once, redirect to a file, read the file.
  A subagent's targeted `-k` run is not the gate; the coordinating loop owns the full suite.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean.

## 2. Prep

- `git fetch --tags` first — local tags go stale and mislead "what's released / next version".
- **CHANGELOG.md**: move `[Unreleased]` into the new version section, Keep-a-Changelog style.
- Bump `version` in `pyproject.toml`.
- **Template-manifest gotcha**: dev-time regens dirty the *last released* entry (the script keys by
  `__version__`). Restore it from its tag first —
  `git checkout vX.Y.Z -- src/squads/_rendering/templates_manifest.json` — then bump the version and
  regenerate (`scripts/gen_template_manifest.py`) so a clean new entry appends and the released one
  stays byte-identical to its tag.
- **Schema**: if `SCHEMA_VERSION` changed, confirm the migration is registered and `sq migrate up`
  runs clean, and add a `### Migration` note to the changelog.
- Build: `uv build` → wheel + sdist in `dist/` (templates + manifest ship as package data).

## 3. Draft the release (a draft never tags or fires CI)

- `gh release create vX.Y.Z --draft --target main --title "Version X.Y.Z - <tagline>" --notes-file <notes>`
- House style: title `Version X.Y.Z - <headline tagline>`; body opens with a short narrative
  paragraph (call out schema/migration status), then bold section headers (`**Added**` / `**Changed**`
  / `**Fixed**` / `**Migration**`) with bold-lead bullets. Match the last ~3 releases —
  `gh release view <tag>`.

## 4. Hand off

Stop at **"draft ready, gates green"** and hand to the operator. Publishing the GitHub release is
theirs — it creates the tag and fires `publish.yml` (PyPI + the VS Code Marketplace VSIX). The
operator also decides the release string and any dated-commit specifics.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

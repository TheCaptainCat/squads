---
id: FEAT-660
sequence_id: 660
type: feature
title: Release version-bump script
status: Done
author: tech-lead
created_at: '2026-07-27T09:43:23Z'
updated_at: '2026-07-27T10:00:30Z'
---
<!-- sq:body -->
One command performs the whole mechanical release version-bump, so a release can't
silently miss a step. The 0.12.1 cut surfaced three easy-to-forget ripples beyond
`pyproject.toml`: the VS Code extension version (`clients/vscode/package.json`), the
version-embedding goldens, and `sq sync` restamping the managed files.

A `scripts/bump_version.py` (invoked `uv run python scripts/bump_version.py X.Y.Z`)
automates exactly the mechanical bump sequence documented in the `releasing-squads`
skill Prep section: rewrite both version fields in lockstep, `uv sync` so
`squads.__version__` follows, handle the template-manifest prior-entry restore,
regenerate the version-embedding goldens, and `sq sync`.

Explicitly out of scope for the script — these stay human/manual:
- CHANGELOG prose (the release notes are authored, not generated).
- The commit gates (`pyright`/`ruff`/`pytest`) and `sq check`.
- `git commit`, `git tag`, `git push`, and the PR / GitHub publish.

## Acceptance
- Running the script with a target version rewrites `pyproject.toml` and
  `clients/vscode/package.json` to the new version, re-syncs `squads.__version__`,
  appends a clean template-manifest entry (with the prior release's entry restored
  byte-identical first), re-stamps the version-embedding goldens, and runs `sq sync`.
- The script never edits the CHANGELOG, commits, tags, or pushes.
- A `--dry-run` prints the full plan and changes no files.
- Pure version-rewrite helpers are unit-testable without invoking git/uv/sq.
- The `releasing-squads` runbook Prep points at the one command in place of the
  hand-run bump/manifest/goldens/sync bullets.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 660 add-story "As a <role>, I want … so that …"`; track with `sq feature 660 story <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

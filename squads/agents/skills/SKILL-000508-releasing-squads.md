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
updated_at: '2026-08-26T09:06:52Z'
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
- **The content-store gate is not a standalone step here** — it is the last item of §2's ordered
  sequence below, because it depends on the version bump having already landed. Do not run
  `gen_template_manifest.py --release-gate` before that sequence; see §2 for why and for what its
  two distinct failure shapes mean.

## 2. Prep

- `git fetch --tags` first — local tags go stale and mislead "what's released / next version".
- **CHANGELOG.md**: this file has no `[Unreleased]` section and has not had one for its whole
  history — the unreleased section is **named by its target version** (`## [0.13.0]`), opened as
  soon as work starts landing for it. So there is nothing to "move" at release time: check the
  section covers *everything* in the release (late-landing features are easy to miss) and that its
  heading is the version you are cutting.
- **CHANGELOG.md compare links**: the definition block at the foot of the file needs one line per
  version heading, or the heading renders as literal `[0.12.3]` text instead of a link. The
  unreleased version's line compares **from the previous tag to `HEAD`**
  (`[0.13.0]: …/compare/v0.12.3...HEAD`) — not to its own tag, which does not exist until the
  operator publishes (§6), and a link naming a tag that is not there 404s for anyone reading the
  file on `main` in the meantime. Switching it to a tag comparison is a **post-publish follow-up**
  (§7), not a prep step. Generate the block from `git tag -l` rather than typing it, and check
  afterwards that every heading has a definition, no definition is orphaned, every `vX.Y.Z` named
  is a real tag, and each line's left side is the previous version — an off-by-one here is
  invisible until someone clicks.
- **Bump the version**: `uv run python scripts/bump_version.py X.Y.Z` — bumps `pyproject.toml` and
  `clients/vscode/package.json` in lockstep, runs `uv sync --all-extras`, handles the
  template-manifest gotcha (restores the prior release's manifest entry from its tag before
  regenerating so it stays byte-identical, then appends the new entry), re-stamps the
  version-embedding goldens, and re-stamps this repo's own managed files (`sq sync` — the
  `.squads.toml` `squads_version`). Use `--dry-run` first to preview. Never edits the CHANGELOG or
  runs `git commit`/`tag`/push — those stay in this Prep section / the operator.
- **Rebuild the content store from ground truth, then gate on it — in this exact order, and only
  after the bump above:**
  1. `git fetch --tags` (again — a tag can land between the top of this list and here).
  2. `uv run python scripts/seed_content_store.py --rebuild`. It recomputes the store as the
     closure of every hash the index names — every tagged version (including the one you are
     about to cut, once its tag exists) from its own release tag, and only a version with **no
     tag at all** from the working tree — and drops whatever is not in that closure.
  3. `uv run python scripts/gen_template_manifest.py --release-gate`.

  **Why the bump has to come first.** The rebuild trusts the working tree only for a version with
  no tag. Run the rebuild *before* bumping and `[project].version` still names the *previous*,
  already-tagged release — so the rebuild would source that shipped version from the tree instead
  of its tag, rewrite its entry, and drop the shipped blob behind it. Bumping first means the
  version the rebuild would ever read from the tree is the new, still-untagged one — the only
  state that is actually safe.

  **If the rebuild refuses**, it names the version and writes nothing: `git fetch --tags` again;
  if it still refuses, investigate that tag by hand before proceeding — never skip it and move on.
  **If `--release-gate` then fails**, it names two different things and they mean different
  things: an unresolved store hash means real coverage is missing — re-run the rebuild above and
  check again; an orphaned blob (reported only under `--release-gate`) means the rebuild was not
  run, or was not run last — run it, then re-check. The generator's own remedy line
  (`gen_template_manifest.py`) never fixes a store gap; only the rebuild does.

  **What a clean gate looks like** — so typing `--check` by mistake is never read as a passed
  gate. The two success lines are worded differently on purpose and must never be
  byte-identical: `--check` states only what it verified —

      manifest v0.14.0 is current (29 artifacts); store coverage verified across all 16 indexed
      version(s) (416 index reference(s) over 85 stored blob(s))

  — while `--release-gate` adds the one property only it checks, orphan-freeness, stated
  explicitly:

      manifest v0.14.0 is current (29 artifacts); release gate passed — orphan-free, store
      coverage verified across all 16 indexed version(s) (416 index reference(s) over 85 stored
      blob(s))

  If a pasted line does not say "release gate passed", `--release-gate` was not the command that
  produced it.
- **Commit both `src/squads/_rendering/templates_manifest.json` and `content_store.json`** —
  together with the version bump and any template/spec-document changes, once the rebuild above
  has run and the gate is clean.
- **Schema**: if `SCHEMA_VERSION` changed, confirm the migration is registered and `sq migrate up`
  runs clean, and add a `### Migration` note to the changelog.
- **Install-instruction drift**: `README.md` (GitHub) and `PYPI.md` (PyPI description) each carry
  their own install command — check both still match reality (e.g. no leftover "once published"
  wording after it already has been) before cutting.
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

## 7. After it is published — close the compare-link loop

The tag now exists, so finish the two edits that could not be made before it did:

- Change the version's own definition from the `HEAD` comparison to its tag:
  `[0.13.0]: …/compare/v0.12.3...v0.13.0`.
- Add the next unreleased line pointing at the tag you just cut: `[0.14.0]: …/compare/v0.13.0...HEAD`,
  alongside the `## [0.14.0]` heading when it opens.

`git fetch --tags` first — the tag was created on the remote by the publish, so a local ref that
has not been fetched will still show the previous release as newest and send you round this loop
again. This step has been missed on consecutive releases; the symptom is a run of headings rendering
as plain text at the bottom of an otherwise correct changelog.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

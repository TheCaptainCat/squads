---
id: TASK-748
sequence_id: 748
type: task
title: Pin third-party GitHub Actions by commit SHA in all workflows
status: Done
author: tech-lead
assignee: devops
priority: medium
refs:
- BUG-743:fixes
description: 'Supply-chain hardening: immutable SHA pins with a trailing version comment
  across publish.yml, test.yml and vscode-client.yml'
created_at: '2026-08-21T12:42:40Z'
updated_at: '2026-08-21T18:36:54Z'
---
<!-- sq:body -->
Pin every third-party GitHub Action referenced from this repo's workflows to a full 40-character
commit SHA, so a moved upstream tag can no longer inject unreviewed code into a pipeline that holds
the PyPI and Marketplace credentials.

## Surfaces

All three workflow files, every `uses:` line in each:

- `.github/workflows/publish.yml` — `actions/checkout`, `actions/setup-python`, `astral-sh/setup-uv`,
  `actions/setup-node` (both jobs).
- `.github/workflows/test.yml` — `actions/checkout`, `actions/setup-python`, `astral-sh/setup-uv`
  (both jobs).
- `.github/workflows/vscode-client.yml` — `actions/checkout`, `actions/setup-node`,
  `actions/setup-python`, `astral-sh/setup-uv` (four jobs).

## Form

```yaml
- uses: owner/action@<40-hex-sha>  # vX.Y.Z
```

The trailing comment carries the human-readable version so a reader still knows which release is
pinned and a bump stays reviewable. Keep the comment on the same line as the `uses:` value.

## Constraints

- **This changes no versions.** Each SHA must be the commit the currently-pinned reference resolves
  to right now, so the pipelines run exactly the code they run today. Resolve each one against the
  upstream repository (`gh api repos/<owner>/<repo>/git/ref/tags/<tag>`, or `git ls-remote --tags`)
  rather than copying a SHA from memory or from another project.
- `actions/setup-node@v5` is a floating major, not an exact release. Resolve the concrete release
  that major currently points at and record that exact version in the trailing comment — not `v5`.
- Where the same action appears in several jobs or files, all of its pins resolve to the same SHA
  unless the versions genuinely differ today.

## Explicitly out of scope

`publish.yml` duplicates its "read core version" and "version guard" steps verbatim across its two
jobs. Sharing them needs a `needs:`-based setup job, which is a structural change to the workflow's
job graph rather than a tidy-up, and it is **not** part of this work. Leave the duplication exactly
as it stands; do not restructure the job graph while pinning.

## Acceptance criteria

- Every `uses:` line under `.github/workflows/` names a 40-hex-character SHA followed by a version
  comment. Provable by grep: no `uses:` line matching `@v` or `@main`/`@master` remains, and each
  matches `@[0-9a-f]{40}` with a trailing `# v...`.
- Each pinned SHA is verified to be the commit the named tag points at in the upstream repository,
  and the verification (action, tag, SHA) is recorded in a comment on this item so a reviewer can
  re-check it without re-resolving everything.
- The three workflow files still parse and the test workflow completes green on the branch carrying
  the change.
- No step, job, permission, trigger or action version is altered beyond the reference form itself.
- No adopter-facing changelog entry: this is repository CI plumbing, not a change to the published
  tool's behaviour.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 748 add-subtask "<title>"`; track with `sq task 748 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T12:49:32Z] Hugo Ops:
  - Pinned every uses: line in publish.yml, test.yml and vscode-client.yml to a 40-hex SHA + trailing # vX.Y.Z comment (commit 84cfa04).
  - Resolution: gh api repos/<owner>/<repo>/git/ref/tags/<tag> for each, cross-checked with git ls-remote --tags (annotated tags peeled via ^{}).
  - actions/checkout@v6.0.3 -> df4cb1c069e1874edd31b4311f1884172cec0e10 (annotated tag, peeled).
  - actions/setup-python@v6.2.0 -> a309ff8b426b58ec0e2a45f0f869d46889d02405.
  - astral-sh/setup-uv@v8.2.0 -> fac544c07dec837d0ccb6301d7b5580bf5edae39.
  - actions/setup-node@v5 -> only release under v5.x is v5.0.0 -> a0853c24544627f65ddf259abe73b1d18a591444; commented as # v5.0.0.
  - No version/behavior change, DRY refactor from BUG-743 left untouched, no changelog entry. sq check clean, YAML parses.
<!-- sq:discussion:end -->

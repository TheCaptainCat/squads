---
id: BUG-512
sequence_id: 512
type: bug
title: PyPI publish job has no tag-vs-version guard like the VSIX job does
status: Verified
author: manager
assignee: devops
priority: high
description: publish.yml's PyPI job can publish on a tag/version mismatch with no
  guard
created_at: '2026-07-21T08:44:01Z'
updated_at: '2026-07-21T08:45:49Z'
---
<!-- sq:body -->
**Gap.** In `.github/workflows/publish.yml`, the `vsix` job has a "version guard — tag must match core version" step that aborts when `github.event.release.tag_name` != `v<pyproject version>`. The `publish` (PyPI) job has **no** such guard — it goes `checkout → uv sync → regen manifest → uv build → uv publish` unconditionally.

**Risk.** If a release is cut on a commit whose `pyproject` version doesn't match the tag (e.g. publishing before pushing the bump), the PyPI job publishes whatever `pyproject` says with no check. It only failed safe recently by luck: re-uploading an already-present version is an idempotent no-op. A genuine mismatch PyPI would accept (a version not yet on PyPI) would ship silently under the wrong release.

**Fix.** Mirror the VSIX job's guard onto the PyPI job: read the core version from `pyproject.toml` and fail with a clear `::error::` when `v<version>` != the release tag, before `uv build`/`uv publish`. Keep it consistent with the existing VSIX guard's wording. Consider whether the shared 'read core version + guard' is worth factoring out vs. duplicating ~10 lines across the two jobs — duplication is acceptable if factoring adds complexity.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T08:45:03Z] Hugo Ops:
  - Mirrored the VSIX job's tag-vs-core-version guard onto the PyPI publish job (after uv sync --frozen, before uv build/uv publish), same shell/comparison, trailing clause reworded to 'publish to PyPI'. Commit 91f6ebf.
- [2026-07-21T08:45:48Z] Catherine Manager:
  - Verified: reviewed the diff (guard placed after `uv sync`, before `uv build`/`uv publish`; identical logic/wording to the VSIX guard bar the corrected 'publish to PyPI' clause), YAML parses clean, VSIX job untouched. Pushed to main as 91f6ebf.
<!-- sq:discussion:end -->

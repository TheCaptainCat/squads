---
id: BUG-743
sequence_id: 743
type: bug
title: Release workflows pin third-party actions by tag, not commit SHA
status: Open
author: devops
description: 'Supply-chain hardening: a moved tag on a third-party action would execute
  unreviewed code in the publish pipeline'
created_at: '2026-08-15T13:07:47Z'
updated_at: '2026-08-15T13:08:03Z'
---
<!-- sq:body -->
Found by devops while fixing the publish trigger, reported rather than fixed because it is a different concern. Read, not driven.

`.github/workflows/publish.yml` pins its third-party actions by tag — `actions/checkout@v6.0.3`, `actions/setup-python@v6.2.0`, `astral-sh/setup-uv@v8.2.0`, `actions/setup-node@…`. A git tag is mutable. If any of those tags were moved, the publish pipeline would execute unreviewed code with access to the PyPI and Marketplace credentials — the highest-privilege workflow in the repo. Pinning by full commit SHA makes the reference immutable; the usual practice is `uses: owner/action@<40-char-sha>  # vX.Y.Z` so the human-readable version stays visible.

Deliberately NOT scoped to 0.13. It is unrelated to the trigger gap that prompted it, it touches every workflow rather than one, and there is no evidence of an actual problem — this is hardening, not a defect with a reproduction. Worth doing, worth doing deliberately, and worth checking whether the same pattern exists in `test.yml` and `vscode-client.yml` at the same time.

Secondary observation from the same read, recorded so it is not lost: the "read core version" and "version guard" steps are duplicated verbatim across the two jobs in that workflow. Sharing them needs a `needs:`-based setup job, so it is a structural change rather than a tidy — a DRY concern, not a correctness one.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

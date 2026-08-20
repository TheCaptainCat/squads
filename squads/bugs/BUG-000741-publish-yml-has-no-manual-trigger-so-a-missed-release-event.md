---
id: BUG-741
sequence_id: 741
type: bug
title: publish.yml has no manual trigger, so a missed release event has no recovery
status: Verified
author: devops
description: The publish pipeline fires only on release:published and carries no workflow_dispatch,
  so re-running it means mutating an already-published release
created_at: '2026-08-06T21:29:45Z'
updated_at: '2026-08-15T19:55:25Z'
---
<!-- sq:body -->
Driven during the 0.12.3 release. `.github/workflows/publish.yml` declares `on: release: types: [published]` and nothing else — `grep -c workflow_dispatch` over the file returned 0. When the operator published v0.12.3, the tag was created and the release went live, but the workflow's run did not appear for about thirty minutes because a GitHub Actions incident was in progress. During that window there was no way to start the job by hand.

Correction: the run was delayed, not lost — it fired once the incident cleared, and both jobs succeeded. Verified directly: PyPI has `squads 0.12.3` (wheel + sdist), the Marketplace shows `pierre-chat.squads-vscode` at 0.12.3, and `squads-vscode-0.12.3.vsix` is attached to the release. Nothing was left unpublished and no recovery action was taken. The incident only exposed the gap — a publish pipeline whose sole trigger is an event that already fired had no recovery path that did not touch a published release, for that thirty-minute window.

The three recovery routes all cost something the release process should not:

- unpublish and republish the release, which mutates a public artifact adopters may already have seen;
- delete the release and its tag and re-cut, which is the documented recovery for a different failure (publishing before pushing) and is heavier than this warrants;
- push an empty commit and re-tag, which breaks the tag-matches-pyproject-version guard the workflow itself enforces.

Adding `workflow_dispatch` with a version or tag input gives a fourth route that mutates nothing. Re-running is already safe by design: a PyPI upload of an existing version is a no-op, and the VSIX guard fails closed rather than shipping a mismatched build — so the only thing missing was a way to ask.

Also decided at the same time: whether the job should verify, rather than assume, that both artifacts actually landed. See the fix comment for the ruling.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-06T21:30:17Z] Catherine Manager:
  - Found because the run never appeared after publish. Not caused by us -- githubstatus.com showed an Actions incident -- but the incident only exposed it. A publish pipeline whose sole trigger is an event that already fired has no recovery path that does not touch a published release.
- [2026-08-15T13:06:04Z] Hugo Ops:
  - Fixed: added workflow_dispatch (required 'tag' input) to .github/workflows/publish.yml. Introduced a workflow-level env.release_tag resolving to github.event.inputs.tag on dispatch or github.event.release.tag_name on the release event, and pointed every prior github.event.release.tag_name read at it (both version guards, the gh release upload target) plus pinned both checkout steps' ref to it explicitly, so a manual run builds the named tag's commit rather than whatever branch the dispatch UI defaults to. Tag-vs-pyproject-version guard is unchanged in substance — still fails closed, now against env.release_tag. No permissions widened.
  - Ruling on verification (read, not driven): added a fail-closed post-publish check to the PyPI job only -- polls the public, unauthenticated https://pypi.org/pypi/squads/<version>/json a few times and fails the job if the version isn't there. No new credentials, low risk of false failure (PyPI's index reflects an upload near-instantly). Deliberately did NOT add an equivalent Marketplace-listing check: the public extensionquery API works (verified read-only against the live 0.12.3 listing) but Marketplace publish-to-index has propagation lag that a same-run assertion can't distinguish from a real failure -- gating on it risks flaking a legitimate publish. The existing 'gh release upload' and 'vsce publish' steps already fail loudly on a real error; a Marketplace-listing audit belongs in a separate, slower check if wanted, not bolted onto this run.
  - Validated statically: actionlint (fetched to scratch, not installed in-repo) reports 0 issues; also parsed with PyYAML. Traced all 3 github.event.release.tag_name references (2 guards + 1 gh release upload) -- none remain; all read env.release_tag now. Could not execute the workflow (operator-only); every behavioral claim above is read/inferred from GH Actions docs and static tooling, not driven.
- [2026-08-15T19:55:25Z] Catherine Manager:
  - Verified statically, and stating the limit plainly: I cannot fire a release to exercise this, so nothing here is driven. Read: workflow_dispatch present with a required tag input, the release_tag resolver branches on github.event_name, both checkout steps pin ref to env.release_tag (2 occurrences), and exactly one github.event.release.tag_name reference survives outside comments -- inside the resolver itself, which is correct. The manual path will not be genuinely exercised until someone dispatches it.
<!-- sq:discussion:end -->

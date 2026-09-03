---
id: TASK-682
sequence_id: 682
type: task
title: VSIX packaging ships with no LICENSE text
status: Done
author: devops
created_at: '2026-07-28T12:35:03Z'
updated_at: '2026-07-29T08:26:06Z'
---
<!-- sq:body -->
The 0.12.2 VSIX job logged:

```
Warning: LICENSE, LICENSE.md, or LICENSE.txt not found
```

`vsce package` runs with `working-directory: clients/vscode`, which has no LICENSE file (none
tracked there). The root `LICENSE` exists and `package.json` declares `"license": "MIT"`, so this
is cosmetic (the manifest still claims MIT) rather than a licensing hole — but the Marketplace
listing ships with no license text behind it.

## Fix

Added a step in `.github/workflows/publish.yml`'s `vsix` job, right before the `package VSIX`
step and following the same pattern already used one step above it for `MARKETPLACE.md` →
`README.md`:

```yaml
- name: copy root LICENSE for the VSIX
  working-directory: clients/vscode
  run: cp ../../LICENSE LICENSE
```

Copies the root `LICENSE` into the ephemeral CI checkout of `clients/vscode/` right before
packaging. One committed source of truth (root `LICENSE`); nothing to keep in sync.

### Alternatives considered

- **Committed `clients/vscode/LICENSE`.** Simplest, but a second copy of the license text that
  can silently drift from the root file whenever it's updated (license year, holder, terms).
  Rejected for the same reason the README swap doesn't commit a second README.
- **Symlink `clients/vscode/LICENSE -> ../../LICENSE`.** Avoids duplication, but `vsce`'s
  packaging behavior on symlinked license files isn't something to bet a release on without
  testing against the packaged `.vsix` (dereferenced vs. skipped vs. broken-link). Rejected as an
  unverified precedent for the sake of avoiding a one-line CI copy.
- **Point `vsce` at a parent path (`files`/`.vscodeignore`).** `vsce` resolves the license
  relative to the manifest's own directory; there's no supported option to point it at a path
  outside `clients/vscode/`. Not viable.

### Verification

Verified locally, not just reasoned: built the VSIX in a scratch copy of `clients/vscode`
(`node_modules` symlinked, real `out/`/`media/mermaid.min.js` from a real compile) via
`npx @vscode/vsce package --no-dependencies`.

- Without a LICENSE file: `WARNING  LICENSE, LICENSE.md, or LICENSE.txt not found` — reproduces
  the 0.12.2 log line.
- After `cp <root>/LICENSE ./LICENSE`: the warning is gone, and `unzip -l` on the resulting
  `.vsix` shows `extension/LICENSE.txt` included (vsce normalizes the packaged filename).
- Confirmed `clients/vscode/.vscodeignore` has no pattern that would exclude a `LICENSE` file.

### Other warnings in the 0.12.2 `vsix` job log

Pulled the full `package VSIX` step log via `gh run view <run-id> --log` for the 0.12.2 publish
run. The LICENSE line is the only `##[warning]`-level warning. The only other notable line is
informational, not a warning annotation, and is expected: `The file
extension/media/mermaid.min.js is large (3.4 MB)` — mermaid.js is deliberately vendored into the
webview bundle; nothing to act on.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 682 add-subtask "<title>"`; track with `sq task 682 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

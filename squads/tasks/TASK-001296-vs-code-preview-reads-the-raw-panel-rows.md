---
id: TASK-1296
sequence_id: 1296
type: task
title: VS Code preview reads the --raw panel rows
status: InProgress
parent: FEAT-1290
author: tech-lead
assignee: typescript-dev
refs:
- ADR-1294:implements
- TASK-1295
description: Preview and skew canary follow the panel-row show --raw header
subentities:
- local_id: ST1
  title: Preview metadata bullets accept labels with spaces
  status: Done
  assignee: typescript-dev
  maps_to: US7
- local_id: ST2
  title: Regenerate the raw fixture and update the skew canary
  status: Done
  assignee: typescript-dev
  maps_to: US7
created_at: '2026-11-04T21:46:37Z'
updated_at: '2026-11-05T03:10:11Z'
---
<!-- sq:body -->
## Goal

Keep the VS Code item preview working with the `sq show <id> --raw` header of ADR-1294 §1 as amended by op-pierre's ruling of 2026-11-04 (comment c30d364 on ADR-1294): the `# <id> — <title>` heading, then the styled panel's rows as a `- **<label>:** <value>` list, then the body. The YAML header of the earlier ruling never reaches the preview.

The shape stays the one `splitDossierMarkdown` in `clients/vscode/src/domain/previewDocument.ts` already splits (heading, bullets, body), now built from the panel's rows (TASK-1295 ST11). Two things change for the preview:

- **Labels.** `DOSSIER_METADATA_BULLET` (`/^- \*\*[\w-]+:\*\* /`) accepts only one-word labels. The panel's rows include labels with spaces (a declared attribute's label, such as the milestone's "target date"), so the pattern must accept them or the header stops at the first such row and the rest of the list renders as body.
- **Field set.** The list now carries a `type` row and the panel's rows (`file`, attribute labels, no session rows). The header renders whatever bullets it gets; no code names a field, so nothing else moves.

`sq show <id> --raw` on a role, skill or operator ID goes through the item renderer, so the preview always gets the item shape.

ST2 also brings the skew canary up to the 0.20 `--json` shapes of discussion entries and operator rows, which fail the vscode-client CI job.

## Dependency

TASK-1295 ST11 is Done, and no later TASK-1295 subtask changes `show --raw`, `show --json` or the roster rows, so this task can run now, beside TASK-1295. It touches only `clients/vscode/` and ships in 0.20, since the canary runs against the matching `sq`.

## Rounds

One round, ST1 and ST2, one typescript-dev.

## Gates

The extension's own build, lint and test commands (`clients/vscode/package.json`), the canary against the dev-tree `sq`. No commit.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1296 add-subtask "<title>"`; track with `sq task 1296 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Preview metadata bullets accept labels with spaces

<!-- sq:subtask:ST1:body -->
Story US7.

- `src/domain/previewDocument.ts`: `DOSSIER_METADATA_BULLET` accepts a label with spaces (`- **target date:** …`), still anchored at the line start and ending at `:**`. The split order (heading, bullets, body) and the fallback do not change.
- Unit tests (`test/previewDocument.test.ts`): a dossier whose list holds a label with a space splits with that row in the header; a body that starts with a bullet resembling a metadata row is still not taken for the header.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Regenerate the raw fixture and update the skew canary

<!-- sq:subtask:ST2:body -->
Story US7.

- Regenerate `test/fixtures/show-raw.txt` from the dev-tree `sq show <id> --raw` on a scratch squad, an item with a badge, refs with a kind and a declared attribute whose label has a space.
- `test/canary/skewCanary.test.ts`: `assertCleanMarkdownDossier` accepts a bullet label with spaces and asserts the `- **type:** ` row and no badge glyph on the badge row, beside its existing checks (heading first, no box-drawing chrome, no `===` pane titles).

**`--json` shapes the canary lags.** The skew canary failed on the release PR (vscode-client run 41932646410, job 126933159321) on two exact-key assertions. Both changes come from the 0.20 external sources (ADR-1274); the client reads none of the new keys, so only the canary's key lists and the committed fixtures move.

- **Discussion entries** (`sq show --json`, `comments --json`) carry five more keys after `body`: `attributes`, `source`, `author_url`, `identity` and `trusted`. A tracker-written comment and a local one share one entry shape and one `author` form (ADR-1274 §5: the matched operator slug, the name, `via <source>`, `@<handle>`). On a comment no source wrote they are `{}`, `null`, `null`, `null` and `true` (`Comment` in `src/squads/_api/_dto/_items.py`).
  - `DISCUSSION_ENTRY_KEYS` (`skewCanary.test.ts:557`) gains the five keys.
  - The self-test table under "the discussion-entry key assertion" (`:574-583`): "the full set" payload carries the five keys so it still passes, and the failing shapes stay failing.
  - Regenerate the discussion entries in `test/fixtures/show-json.json` so the committed fixture has the live shape.
- **Operator list rows** (`sq operator list --json`) carry `identities`, the tracker user IDs by source name (ADR-1274 §3, `OperatorRow` in `src/squads/_api/_dto/_operators.py`). Role rows are unchanged: the role assertion at `:1068` passed before the operator one failed at `:1105`.
  - `OPERATOR_LIST_KEYS` (`:1059`) gains `identities`. `isSqRosterIdentity` already accepts the extra key.
- Run `npm run test:canary` against the dev-tree `sq`: both cases pass, and each fails again when its new key is removed from the list.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T22:34:22Z, edited 2026-11-04T22:35:27Z] `tech-lead` Olivia Lead:
  - Rescoped for the panel-row --raw header (op-pierre, c30d364 on ADR-1294). Not cancellable: the heading-first split stays, but the bullet pattern rejects labels with spaces (the milestone's "target date"), so the header would stop at that row. ST1 widens the pattern, ST2 the fixture and canary. Status left at Draft.
- [2026-11-04T22:38:48Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-04), after FEAT-1290: the VS Code preview stops parsing the raw dossier. It builds the header from sq show --json and reads the body with show --raw --no-header (views rendered), so the client parses no text format. ADR-427 §2 is narrowed then. Until then TASK-1296 only widens the bullet label pattern.
- [2026-11-04T23:37:57Z] `tech-lead` Olivia Lead:
  - ST2 now also covers the vscode-client skew canary failure on the release PR (job 126933159321): `sq show --json` discussion entries carry `attributes`, `source`, `author_url`, `identity` and `trusted` (one entry shape and `author` form for tracker and local comments, ADR-1274 §5), and `sq operator list --json` rows carry `identities` (ADR-1274 §3); role rows are unchanged. The depends-on ref to TASK-1295 is now related: ST11 is Done and nothing later in TASK-1295 changes what this task reads, so it can run now. Status left at Draft. @manager
- [2026-11-04T23:43:46Z] `typescript-dev` Ada Typescript:
  - ST1 and ST2 done, nothing committed. Files: clients/vscode/src/domain/previewDocument.ts (bullet pattern now /^- \*\*[\w][\w -]*:\*\* /), test/previewDocument.test.ts, test/markdown.test.ts, test/canary/skewCanary.test.ts, test/fixtures/show-raw.txt (regenerated from the dev sq on a scratch milestone: type row, target date, refs with a kind), test/fixtures/show-json.json (discussion entries carry the five new keys).
  - Gates: npm run check clean, npm test 768/768, npm run test:canary 92/92 against the dev sq (0.20.0, .venv/bin on PATH as CI does). Removing trusted or identities from the canary lists makes it fail; restored. The 'no .squads.toml found' line is the canary's own probe that it runs outside any squad, not a failure. sq check clean.
- [2026-11-05T03:10:11Z] `typescript-dev` Ada Typescript:
  - REV-1307 F1 and F2 fixed under clients/vscode/ only, uncommitted. Gates: npm run check clean, npm test 770/770, npm run test:canary 92/92. Each new test fails when its fix is reverted. @reviewer ready for re-review.
<!-- sq:discussion:end -->

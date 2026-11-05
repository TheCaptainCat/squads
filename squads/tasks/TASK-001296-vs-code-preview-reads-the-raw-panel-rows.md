---
id: TASK-1296
sequence_id: 1296
type: task
title: VS Code preview reads the --raw panel rows
status: Draft
parent: FEAT-1290
author: tech-lead
assignee: typescript-dev
refs:
- ADR-1294:implements
- TASK-1295:depends-on
description: Preview and skew canary follow the panel-row show --raw header
subentities:
- local_id: ST1
  title: Preview metadata bullets accept labels with spaces
  status: Todo
  assignee: typescript-dev
  maps_to: US7
- local_id: ST2
  title: Regenerate the raw fixture and update the skew canary
  status: Todo
  assignee: typescript-dev
  maps_to: US7
created_at: '2026-11-04T21:46:37Z'
updated_at: '2026-11-04T22:38:48Z'
---
<!-- sq:body -->
## Goal

Keep the VS Code item preview working with the `sq show <id> --raw` header of ADR-1294 §1 as amended by op-pierre's ruling of 2026-11-04 (comment c30d364 on ADR-1294): the `# <id> — <title>` heading, then the styled panel's rows as a `- **<label>:** <value>` list, then the body. The YAML header of the earlier ruling never reaches the preview.

The shape stays the one `splitDossierMarkdown` in `clients/vscode/src/domain/previewDocument.ts` already splits (heading, bullets, body), now built from the panel's rows (TASK-1295 ST11). Two things change for the preview:

- **Labels.** `DOSSIER_METADATA_BULLET` (`/^- \*\*[\w-]+:\*\* /`) accepts only one-word labels. The panel's rows include labels with spaces (a declared attribute's label, such as the milestone's "target date"), so the pattern must accept them or the header stops at the first such row and the rest of the list renders as body.
- **Field set.** The list now carries a `type` row and the panel's rows (`file`, attribute labels, no session rows). The header renders whatever bullets it gets; no code names a field, so nothing else moves.

`sq show <id> --raw` on a role, skill or operator ID goes through the item renderer, so the preview always gets the item shape.

## Dependency

After TASK-1295 ST11 lands. Ships in 0.20 with it, since the canary runs against the matching `sq`.

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
<!-- sq:discussion:end -->

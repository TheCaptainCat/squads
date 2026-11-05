---
id: TASK-1314
sequence_id: 1314
type: task
title: VS Code board panel reads summaries and shows a body
status: Done
parent: FEAT-1311
author: tech-lead
assignee: typescript-dev
refs:
- ADR-1312:implements
description: 'Client side of ADR-1312: summaries in the board panel, body through
  board show'
created_at: '2026-11-05T07:21:32Z'
updated_at: '2026-11-05T09:29:39Z'
---
<!-- sq:body -->
## Goal

The VS Code client reads the board as ADR-1312 §3 shapes it: the board panel lists each notice's
summary from `sq board list --json` and loads a notice's body on demand through `sq board show
<n> --json`. FEAT-1311 US4, last bullet. Start after the Python task's round 1 (ST1, ST2) is
committed: that is when the JSON lands.

## Behaviour

- `sq board list --json` rows are `{n, id, summary, author, posted_at, until}`; `body` is gone.
  `sq board show <n> --json` is `{n, id, summary, author, posted_at, until, body}`, `body` is
  `""` when the notice has none.
- The board panel shows one entry per notice, newest first as today: summary (a multi-line
  summary renders as written), author, posted time, expiry. No body until asked.
- Opening a notice (a click on its entry) runs `sq board show <n> --json` with the row's `n` and
  renders the body under that entry, through `renderMarkdownToHtml` (it escapes), in the same
  panel. A notice with an empty body says so in one line.
- `n` is a position in the listing, not an id: when the returned `id` differs from the row's `id`
  (the board changed since the list), the panel re-lists and shows a one-line note instead of
  the wrong body. A failed `show` (exit 1, a spawn error) renders the failure message in place of
  the body, the way `renderBoardHtml` renders a failed list.
- The partial-listing note (exit 4, omissions) is unchanged.

## Files

- `clients/vscode/src/types.ts`: `SqBoardNotice` drops `body`, gains `summary`; a
  `SqBoardNoticeDetail` adds `body`.
- `clients/vscode/src/sqAdapter.ts`: `isSqBoardNotice` reads `summary`; `isSqBoardNoticeDetail`;
  `getBoardNotice(runner, invocation, workspaceRoot, n)` running `['board', 'show', String(n),
  '--json']`. Follow the skew rule the memory-list guard documents for a field an older `sq`
  lacks.
- `clients/vscode/src/domain/boardView.ts`: render summaries, an expandable entry per notice, the
  body block; the module comment stops saying the full body comes back inline.
- `clients/vscode/src/domain/previewMessages.ts`: an `openNotice {n, id}` message and its parser,
  same shape as `parseOpenItemMessage`.
- `clients/vscode/src/itemPreviewManager.ts`: the board panel's `onDidReceiveMessage` handles
  `openNotice` (fetch, id check, render); the class comment on the board panel.
- `clients/vscode/README.md`: the `boardView` and `itemPreviewManager.ts` rows.

## Tests

- Unit (`npm test`): `test/boardView.test.ts` (summaries only in the list, body on demand, the id
  mismatch note, an empty body, escaping of summary and body); `test/sqAdapter.test.ts` (both
  guards accept the new shapes and reject a missing `summary` or a non-string `body`);
  `test/previewMessages.test.ts` (the new parser). About 8 new cases.
- Canary (`npm run test:canary`, `test/canary/skewCanary.test.ts`): the scratch squad posts one
  notice with a summary and a body; `sq board list --json` and `sq board show 1 --json` each
  pass an exact key-set assertion (not a superset: board notice 10) and the adapter's guard; add
  the committed fixtures `test/fixtures/board-list.json` and `test/fixtures/board-show.json` and
  assert they still conform, as the other surfaces do. List both commands in the file's header
  comment.

## Gates

`npm run check && npm test && npm run test:canary` in `clients/vscode`, the canary against this
branch's `uv run sq` (`SQ_CANARY_CMD`). No commit. A visual check in the Extension Development
Host is the operator's (the `launch-dev-host` skill), after the main loop commits.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1314 add-subtask "<title>"`; track with `sq task 1314 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T07:40:56Z] `typescript-dev` Ada Typescript:
  - Client side of ADR-1312 is in place under clients/vscode (uncommitted).
    
    - Adapter: SqBoardNotice drops body, gains summary; SqBoardNoticeDetail adds body; isSqBoardNotice / isSqBoardNoticeDetail; getBoardNotice runs board show <n> --json. The list guard requires summary (no tolerant fallback: a row from an sq without it has nothing to display, and that sq has no board show either).
    - Panel: one entry per notice (summary as written, escaped, line breaks kept; author, posted, expiry), newest first. A click posts openNotice {n, id}; the host runs board show, compares the returned id with the row's, and re-lists with a one-line note on a mismatch. A failed show renders its message under the entry; an empty body says so in one line; a second click closes the entry. Content swaps go through the updateContent patch, so the scroll position is kept.
    - Tests: boardView (rewritten), sqAdapter, previewMessages; canary has exact key-set assertions for board list and board show (live and committed fixtures test/fixtures/board-list.json, board-show.json) plus a self-test of the assertions. Each new test was broken once by hand and failed; one mutation (id attribute escaping) survived the first pass and got its own test.
    - Gates (venv sq 0.20.0 on PATH): npm run check clean; npm test 785 passed; npm run test:canary 103 passed.
    - Not done: visual check in the Extension Development Host (operator's, after commit).
- [2026-11-05T07:41:22Z] `manager` Catherine Manager:
  - Moved back to InReview: the board panel is visual, so it waits for op-pierre's look in the Extension Development Host and a code review. Requiring summary in the list guard is accepted.
- [2026-11-05T08:59:01Z] `typescript-dev` Ada Typescript:
  - Rework after op-pierre's ruling (uncommitted, clients/vscode only).
    
    - Bodies always visible: the panel loads `sq board list --full --json` and renders each body under its summary; a notice without a body shows none. The click path is gone (openNotice, its parser, the client-script branch, getBoardNotice, the detail guard, the id check and the re-list note): nothing else used it.
    - Credits above the summary in the comment form, `<full name> (<slug>) — <timestamp>` plus the expiry, in the comment header's classes. `author_name` is optional in the guard (an older sq lacks it; the slug alone is shown then), and a non-string one is rejected.
    - Guard requires summary and body. Fixtures: board-list.json (summary row), board-list-full.json (--full), board-show.json. Canary: exact key sets for `board list --json` (no body), `board list --full --json` and `board show` (the same keys, body last), live and fixtures, plus a self-test.
    - Memory: not changed. The Roster tree lists memory summaries and a leaf click opens the entry panel, which always shows the body through `memory show`; a tree cannot show bodies inline, so `memory list --full` would only fetch text nothing displays.
    - Gates (dev sq on PATH): npm run check clean; npm test 780 passed; npm run test:canary 105 passed. Each new test was broken once by hand and failed (the escaped expiry and the empty-body fixture needed a second pass).
- [2026-11-05T09:12:34Z] `op-pierre` Pierre Chat:
  - Checked in the Extension Development Host on a copy of this squad: every notice shows its credits on top, then its summary and body; the item preview header is unchanged. Approved.
<!-- sq:discussion:end -->

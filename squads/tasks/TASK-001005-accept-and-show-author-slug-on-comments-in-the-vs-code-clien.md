---
id: TASK-1005
sequence_id: 1005
type: task
title: Accept and show author_slug on comments in the VS Code client
status: Done
parent: FEAT-980
author: tech-lead
assignee: typescript-dev
refs:
- ADR-979:implements
- TASK-1004:depends-on
description: Optional author_slug on SqDiscussionEntry, tolerant shape guard, slug
  beside the name in the preview
subentities:
- local_id: ST1
  title: Read an optional author_slug and show it in the preview
  status: Done
  maps_to: US4
created_at: '2026-10-12T06:48:44Z'
updated_at: '2026-10-16T14:38:35Z'
priority: medium
---
<!-- sq:body -->
## Scope

`sq show <id> --json` gains `author_slug` on every discussion entry, for the item and for each
sub-entity (ADR-979, decision 5). The VS Code client reads those entries as
`SqDiscussionEntry` and shows the author in the preview's comments. This task lets the client
read the new key and show the slug beside the name, and keeps it working against an older `sq`
that omits the key.

It covers the VS Code clause of story 4 of FEAT-980. The Python side is the engine task this
one depends on. Owner: the TypeScript developer.

The client parses no comment header and reads no `.md` file: nothing here touches the header
grammar.

## Approach

- `clients/vscode/src/types.ts`: `SqDiscussionEntry` gains an optional `author_slug`. Its doc
  comment says why it is optional, in one or two sentences.
- `clients/vscode/src/sqAdapter.ts`: `isSqDiscussionEntry` accepts an entry with no
  `author_slug` and one whose `author_slug` is a string, and rejects any other type for the
  key. A missing key must never blank the preview.
- `clients/vscode/src/domain/previewDocument.ts`: `buildCommentHtml` shows the name, then the
  slug in its own element, when the entry carries a slug that differs from the name. With no
  slug, or a slug equal to the name, the header renders as it does today. The slug is escaped
  like the name. Any style it needs goes in the preview's stylesheet with the existing comment
  rules.
- Fixtures under `clients/vscode/test/fixtures/` gain `author_slug` on some discussion entries
  and keep at least one entry without it.

## Tests

- **The guard, as a table of entry shapes**: no `author_slug`; a string; an empty string;
  `null`; a number; an object. For the item-level discussion and for a sub-entity's.
- **The render, as a table**: name with slug; name with no slug; slug equal to the name
  (`squads`); a name and a slug carrying characters that need escaping. Assert the HTML.
- **An older payload**: the committed `show --json` fixture without the key still passes the
  shape guard and renders its comments exactly as before.
- **The canary** (`clients/vscode/test/canary/`): `author_slug` is among the keys it knows on a
  discussion entry, and it passes against an `sq` that emits the key and one that does not.
  The handoff says which `sq` the canary resolved.
- **Falsify.** Make `author_slug` required in the guard: the older-payload test goes red. Drop
  the escaping of the slug: the escaping row goes red. Restore each, and record both.

## Acceptance

- Story 4's last clause: `SqDiscussionEntry` has an optional `author_slug`, and a payload from
  an older `sq` is still accepted.
- The preview shows the slug beside the name for an entry that carries one.
- The render is a visual change: the handoff includes how to see it in an Extension
  Development Host (the `launch-dev-host` skill) and a before and after of one comment header.

## Gates and working rules

- In `clients/vscode`: `npm run check` (typecheck, lint with no warnings, format check) and
  `npm test` are clean. Run the canary with `npm run test:canary` and report its result.
- TypeScript stays at the version the client pins. No dependency is added or bumped.
- Comments are one or two sentences, with no release versions, ticket ids or history. No
  ticket ids in source or in test names.
- No Python source, no `docs/` file and no `CHANGELOG.md` is edited here. Anything an adopter
  of the extension would notice goes in the handoff for the tech writer.
- The developer never runs `sq migrate`, `sq repair` or `sq sync` on this repository's own
  squad, with any build. A probe against a real `sq` uses a scratch squad under the session
  scratchpad: any probe script starts with `set -euo pipefail`, an absolute `cd` into its
  scratch folder, and an exit if `pwd` is under `/home/pchat/projects/squads`.
- `~/.local/bin/sq check` is clean before handback.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1005 add-subtask "<title>"`; track with `sq task 1005 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Read an optional author_slug and show it in the preview

<!-- sq:subtask:ST1:body -->
**Goal.** The client reads an optional `author_slug` on a discussion entry and shows it beside
the author's name in the preview, and an entry without the key behaves exactly as it does
today.

**Approach**

- `src/types.ts`: optional `author_slug: string` on `SqDiscussionEntry`.
- `src/sqAdapter.ts`: `isSqDiscussionEntry` treats the key as optional: absent or a string.
  `hasOptionalDiscussion` and the item-level check keep using that one guard.
- `src/domain/previewDocument.ts`: `buildCommentHtml` adds the slug element after the author
  element when the entry has a slug that differs from the name.
- `test/fixtures/show-json.json`: `author_slug` on some entries, at item and sub-entity level,
  with at least one entry left without it.

**Tests.** The guard table, the render table, the older-payload test and the canary, as the
task body lists them, in `test/sqAdapter.test.ts`, `test/previewDocument.test.ts` and
`test/canary/skewCanary.test.ts`.

**Falsify.** The two breaks the task body names, with the test that went red for each.

**Acceptance.** The task body's, in full. `npm run check` and `npm test` clean; the canary
result reported with the `sq` it ran against.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-12T06:50:42Z] `tech-lead` Olivia Lead:
  - 2026-10-12: authored for the VS Code clause of story 4 of FEAT-980. Left in Draft, no developer briefed. Depends on TASK-1004 (ST2 emits the key). Showing the slug in the preview goes one step past the story, which asks for the optional field only; the point is raised on TASK-1004 for the operator.
- [2026-10-12T06:55:29Z] `op-pierre` Pierre Chat:
  - 2026-10-12: keep the slug in the VS Code comment preview, beyond the optional field story 4 asks for.
- [2026-10-15T21:43:33Z] `manager` Catherine Manager:
  - Also in scope: the doc comment at clients/vscode/src/domain/squadDir.ts:129-131 still names --dir. Suggested text from the writer: Resolve the active squad directory for workspaceRoot, or undefined when no .squads.toml is found (mirrors _paths.py::resolve, the .squads.toml walk-up).
- [2026-10-16T08:08:58Z] `typescript-dev` Ada Typescript:
  - - Client reads an optional author_slug and shows it in the preview as a monospace span after the author name, only when non-empty and different from the name. Guard accepts absent or string, rejects null/number/object. Also fixed the stale --dir comment in squadDir.ts (now names -C).
    - Files (clients/vscode): src/types.ts, src/sqAdapter.ts (guard now exported for the canary), src/domain/previewDocument.ts (+ .sq-comment-slug rule), src/domain/squadDir.ts, test/sqAdapter.test.ts, test/previewDocument.test.ts, test/canary/skewCanary.test.ts, test/fixtures/show-json.json (slug on the first entry, second left without).
    - Gates: npm run check clean; npm test 35 files / 705 tests pass. Canary (npm run test:canary) 76 passed against the dev build .venv/bin/sq (emits author_slug, schema 0.16) and against released ~/.local/bin/sq 0.15.0 (omits it, verified by a probe).
    - Falsified: required author_slug in guard -> 5 sqAdapter tests red (key absent rows, older-payload, fixture); unescaped slug -> the escaping row red. Both restored.
    - Before: <span author>Ada Typescript</span> <span ts>...</span>. After: <span author>Ada Typescript</span> <span slug>typescript-dev</span> <span ts>...</span>.
    - Operator check in the dev host (launch-dev-host skill): preview an item whose comments were written by the 0.16 build; each header shows name, then slug, then timestamp. Older entries without a slug look as before.
    - For the tech writer: the preview now shows the author slug beside the name on comments (when sq emits it).
- [2026-10-16T08:16:12Z] `typescript-dev` Ada Typescript:
  - REV-1029 F1-F5 fixed. check clean, npm test 705 pass, canary 76 pass on .venv/bin/sq; canary now red on released 0.15.0 by design.
- [2026-10-16T14:38:35Z] `op-pierre` Pierre Chat:
  - 2026-10-16: checked the preview in the dev host; the slug shows after the author's name. Approved. Anonymous --as operator comments stay as they are.
<!-- sq:discussion:end -->

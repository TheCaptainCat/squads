---
id: TASK-444
sequence_id: 444
type: task
title: Bump VS Code client TypeScript to 6.0.3 and @types/node to 26
status: Done
parent: FEAT-100
author: manager
assignee: typescript-dev
refs:
- ADR-427:addresses
created_at: '2026-07-17T08:20:55Z'
updated_at: '2026-07-17T08:38:55Z'
---
<!-- sq:body -->
Bump clients/vscode devDependencies. typescript ^5.9.3 -> ^6.0.3: 6.0.3 is the latest STABLE TypeScript within typescript-eslint 8.64's '>=4.8.4 <6.1.0' peer cap — a full major bump while KEEPING the type-aware strict-lint gate. Do NOT go to TS7; typescript-eslint has no TS7-supporting line yet (see the typescript-dev memory + the team board notice). @types/node ^22 -> ^26: pure freshness, no gate impact. Run npm install, then npm run check + npm test; fix any new strict-type errors TS6 surfaces so the gate stays green with zero warnings. If 6.0.3 cannot be made green without weakening the lint/tsconfig strictness, fall back to 5.9.3 and report why rather than relaxing the gate. Confirm the resolved TypeScript in package-lock.json is a 6.0.x.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 444 add-subtask "<title>"`; track with `sq task 444 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T08:20:57Z] Pierre Chat:
  - I asked for this directly — the client's TypeScript pin (5.9.3) was two majors stale; move to 6.0.3, the newest that keeps the strict gate.
- [2026-07-17T08:31:02Z] Catherine Manager:
  - Implementer completed the bump (typescript ^6.0.3, @types/node ^26.1.1) then hit a transient network crash during cleanup. Verified the tree independently: pins correct, package-lock resolves TS 6.0.3, npm run check clean (zero warnings), 66/66 tests green. No TS6 strict-type breakage. Moving to InReview. @reviewer
<!-- sq:discussion:end -->

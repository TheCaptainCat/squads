---
id: TASK-464
sequence_id: 464
type: task
title: 'VS Code: discussion/comments section in the item preview'
status: Ready
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
created_at: '2026-07-17T15:34:04Z'
updated_at: '2026-07-17T15:34:07Z'
---
<!-- sq:body -->
Render the item's discussion as a collapsible section in the webview preview, from 'sq show <id> --json's 'discussion' array ([{author, ts, body}] — already exposed, no core change). Each comment: author + ISO-timestamp header, body rendered through the existing markdown.ts renderer. Reuse the webview section pattern from the children/refs graphs (TASK-453). Addresses REV-448 F14; maps to US1 (preview).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 464 add-subtask "<title>"`; track with `sq task 464 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T15:34:06Z] Pierre Chat:
  - Add comment-section display to the preview — pull the parsed discussion from sq show --json.
<!-- sq:discussion:end -->

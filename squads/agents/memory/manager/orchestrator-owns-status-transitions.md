---
summary: At dispatch, set the task InProgress yourself — don't rely on the dev subagent
  to self-transition from Ready.
created_at: '2026-07-17T15:40:05Z'
---
When you spawn a dev on a task, move it to InProgress **yourself, at that moment** — do NOT
rely on the subagent to self-transition Ready→InProgress. Subagents lag or skip it: Elias left
TASK-450 at Ready while actively building it, and Pierre flagged the stale board ("we need a real
workflow discipline here").

The orchestrator owns status transitions: **InProgress at dispatch**, InReview/Done at integration.
(Devs flipping to InReview on handoff is reliable — it's the *start*-of-work transition they miss.)
A `Ready` item must never actually be under active work.
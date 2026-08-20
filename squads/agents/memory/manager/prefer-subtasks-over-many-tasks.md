---
summary: 'Prefer subtasks over many tasks: split only by owner role or increment'
created_at: '2026-07-31T10:09:27Z'
---
Default to one task carrying subtasks for a coherent surface. Cut a second task only when it
would be owned by a different role, or when it ships in a different increment.

File-collision risk and parallel dispatch are dev-scheduling concerns, not tracking ones — a
single task's subtasks express the same work with one status to reconcile instead of several.

Say it in the breakdown brief: "prefer one task with subtasks; justify any second task by owner
role or increment, not by file overlap." When a breakdown comes back with several tasks sharing
an owner and an increment, push back before promoting them.

Learned on the roster-lifecycle feature, where one task became ten. The review fixes alone were
cut as four tasks where subtasks would have done, because the brief asked for a one-or-several
judgement and the tech lead optimised for what a dev run needs rather than what the board needs.
The cost: a dispatch cycle per task, four status reconciliations, and a feature that reads as ten
things instead of one.
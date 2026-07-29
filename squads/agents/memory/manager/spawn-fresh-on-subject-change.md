---
summary: Resume an agent to continue the same work; spawn fresh when the subject changes.
created_at: '2026-07-29T08:54:40Z'
---
Resume an agent to continue the same work; spawn fresh when the subject changes.

Resuming by id is right for iterating on one ticket or one review's findings — the carried
context is the point. When the subject changes, spawn a new agent instead.

Why: carried context goes stale and the agent reports from it confidently. Seen in one session —
a tech lead reported a task's refs as missing twice, because her context predated the commit that
added them; two agents flagged the manager's own board writes as a rogue concurrent session; and
a writer's "verified" command example passed in a context where he had run an extra setup command
he then left out of the published block, so the page shipped broken. None were reasoning
failures. Each was an old world model asserted as current.

How to hold it: resume for iteration on the same item. Spawn fresh for a different feature, a
different surface, or a different kind of work (planning, implementing, reviewing). A fresh agent
re-reads the board and the tree, which costs less than a wrong premise.
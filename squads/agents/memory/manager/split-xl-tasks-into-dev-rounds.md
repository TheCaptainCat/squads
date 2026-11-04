---
summary: Split XL tasks into developer rounds with a green checkpoint between them
created_at: '2026-11-04T14:35:49Z'
---
A developer subagent runs out of context on an XL task. Dispatch it in rounds: one fresh developer per one to three subtasks, each round leaving the gates green, and the main loop runs the full suite and commits a checkpoint before the next round.

Seen on the external sources work and again on the re-export sweep (2026-11-04): every round landed green; the one attempt to give a single developer a whole XL task ran out of context mid-way.

Brief each round with: the subtask IDs only, "stay out of the later subtasks", the fast gates, "no full suite, no commit", and "stop at a green point and say where if context runs low". Resume the same developer only to finish the same round.
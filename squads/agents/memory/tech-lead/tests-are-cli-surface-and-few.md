---
summary: Plan tests as CLI surface per ADR-1172, and few, with an expected count
created_at: '2026-10-28T19:11:54Z'
---
A task's test approach follows ADR-1172: name, for each behaviour, the surface it is observed through (sq in local mode, sq in remote mode, the daemon's command endpoint) and write it as CLI surface cases, never unit tests on internal functions. A behaviour no surface shows yet goes to the task where it becomes visible.

Keep the suite small: the previous one was deleted at about 16,000 tests. One case per behaviour plus its boundary refusals; no shape tables or cross products. State the expected number of new tests per task so review can hold it.
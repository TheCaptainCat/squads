---
summary: 'Tests are CLI surface per ADR-1172, and few: no unit tests, no shape tables'
created_at: '2026-10-28T19:09:04Z'
---
Every test follows ADR-1172: a CLI surface test through the `invoke` fixture, with `covers` markers, asserting the whole output and reading state through `show --json`. No unit tests: never call an internal function from a test. A behaviour no surface shows yet is tested where it becomes visible (the daemon's command endpoint, remote mode), not through the function behind it.

Keeping the suite small is the point. The previous suite was deleted at about 16,000 tests and 50 minutes of Windows CI. One case per behaviour plus its boundary refusals; no shape tables, no cross products, no repetition across hosts.

When briefing a dev, cite ADR-1172, name the surface each behaviour is seen through, and ask for the expected number of new tests; hold that number at review. Shape-attacking belongs to the reviewer's probes, not to the suite. A brief asking for table-driven shape tests produced 93 unit tests for one entry point on TASK-1217.
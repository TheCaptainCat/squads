---
summary: 'Tests are CLI surface per ADR-1172, and few: no unit tests, no shape tables'
created_at: '2026-10-28T19:11:54Z'
---
Every test follows ADR-1172: a CLI surface test through the `invoke` fixture, with `covers` markers, asserting the whole output line or JSON object and reading state through `show --json`. Never call an internal function, open an item file or `.squads.json`, or patch internals from a test. A behaviour no surface shows yet is tested where it becomes visible (the daemon's command endpoint, remote mode), not through the function behind it.

Keep the suite small: the previous one was deleted at about 16,000 tests and 50 minutes of Windows CI. One case per behaviour plus its boundary refusals; no shape tables, no cross products, no repetition across hosts. Falsify each case you keep. State in your handback how many tests you added. Shape-attacking belongs to review probes, not to the suite.
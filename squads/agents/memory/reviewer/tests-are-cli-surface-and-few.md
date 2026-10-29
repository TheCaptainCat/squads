---
summary: Unit tests and test growth are findings under ADR-1172
created_at: '2026-10-28T19:11:55Z'
---
Review tests against ADR-1172: a test that calls an internal function, reads squad files directly, lacks `covers` markers or asserts a substring is a finding. So is suite growth: cross products, shape tables and cases repeated across hosts are findings, because the previous suite was deleted at about 16,000 tests. Judge a fix by running sq, not by the dev's tests; attack input shapes with your own probes, which do not belong in the suite.
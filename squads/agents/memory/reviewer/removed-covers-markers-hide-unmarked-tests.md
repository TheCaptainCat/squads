---
summary: Removed covers markers hide unmarked tests
created_at: '2026-10-29T04:26:59Z'
---
Once a leaf gains any option, such as --json, the coverage guard treats a key-only covers marker on it as stale. Devs then delete the marker, and the tests of the plain run declare nothing, which the guard cannot see. In a test diff, read the removed covers lines as well as the added ones.
---
id: BUG-1189
sequence_id: 1189
type: bug
title: migrate chlog accepts non-version and reversed ranges
status: Verified
author: qa
priority: low
severity: low
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:36Z'
updated_at: '2026-10-29T20:40:14Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Commands and observed
- `sq migrate chlog a..b` prints `no manual steps for va..vb`, exit 0.
- `sq migrate chlog v0.17.0..v0.1.0` (reversed) prints `no manual steps for v0.17.0..v0.1.0`, exit 0.
- `sq migrate chlog v0.1.0..v0.17.0` prints the steps (correct).

## Expected
Refuse a bound that is not a version and a range whose start is not below its end (exit 1, message naming the expected `vFROM..vTO` form). A typo currently reads as "nothing to do", which is the same answer an operator reads as "no manual steps", and the output even invents `va`/`vb`.

## Code
`src/squads/_cli/_migrate.py` `_parse_span` only checks for the `..` separator and strips a leading v.

## Severity
low
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T20:40:14Z] `reviewer` Paul Reviewer:
  - Verified under REV-1247 (Approved at a56413b4).
<!-- sq:discussion:end -->

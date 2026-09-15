---
id: BUG-937
sequence_id: 937
type: bug
title: sq migrate chlog silently drops manual steps on a prerelease bound
status: Open
author: qa
priority: medium
refs:
- MILE-934:targets
- REV-926:addresses
created_at: '2026-09-10T08:37:16Z'
updated_at: '2026-09-10T08:38:15Z'
---
<!-- sq:body -->
## Problem

`sq migrate up` tells an operator to read manual steps with a specific `sq migrate chlog`
window, and that exact command then reports none. Driven, on a squad stamped by a prerelease
build (`schema_version = "0.11"`, `squads_version = "0.14.0rc1"`) and then migrated by the
release:

```
$ sq migrate up
  0.14.0 (schema v0.11→v0.14): Two new bundled item types, contract (PRD) and milestone …
migrated to schema v0.14; index rebuilt — run `sq sync` to refresh managed files
manual steps remain — read them with `sq migrate chlog v0.14.0rc1..v0.15.0`

$ sq migrate chlog v0.14.0rc1..v0.15.0
no manual steps for v0.14.0rc1..v0.15.0

$ sq migrate chlog v0.13.1..v0.15.0        # the truthful window, control
v0.14.0 — manual steps (schema v0.11→v0.14)   … (the steps print in full)
```

## Root cause

`sq migrate chlog`'s range filter (`_cli/_migrate.py:135`) compares with `version_tuple`, which
strips non-digit suffixes per segment instead of ordering them below the release:

```
version_tuple("0.14.0rc1") -> (0, 14, 1)      # "0rc1" -> "01" -> 1
version_tuple("0.14.0")    -> (0, 14, 0)
```

So `0.14.0rc1` compares as *greater* than `0.14.0`, and the filter `lo < m.version <= hi` with
`lo = "v0.14.0rc1"` silently excludes the `0.14.0` migration entry the operator was just told to
read.

`_cli/_migrate.py:17-23` imports this `version_tuple` from `squads._cli._common`, not from the
canonical `squads._util.version_tuple` — confirmed by reading both definitions: identical body
(same loop, same semantics), only the docstring differs. So the `_cli/_common` copy is not a
cosmetic duplicate; it is the live comparator behind `chlog`'s range filter.

`version_tuple` has four call-site regions, not two:

```
_cli/_migrate.py:135                chlog range filter          (this bug)
_overrides/_service.py:757,758,768  uncarried-base pane + floor compare
_overrides/_manifest.py:214         artifact_floor: min(candidates, key=version_tuple)
_overrides/_manifest.py:219         known_index_versions: sorted(..., key=version_tuple)
```

The two `_overrides/_manifest.py` sites use the same mis-ordering comparator for a *selection*
(`min`/`sort`), not just a label — not currently reproducible, since every key in
`templates_manifest.json` today is a clean `X.Y.Z`, but the same shape of defect. Confirmed by
reading; not independently driven since no manifest currently carries a prerelease key.

## Why this matters now, not hypothetically

This project's own release-prep workflow tags and later upgrades prerelease/rc builds (fetch
tags, cut a release branch, etc.), so a prerelease-stamped `squads_version` in `.squads.toml` is
exactly the shape this repo produces, not an edge case only an adopter could hit.

## Not release-blocking for a clean X.Y.Z cut

Every version this project has *shipped* to date is a clean `X.Y.Z` stamp, and the comparator is
correct for two clean releases compared to each other — the defect triggers specifically on a
prerelease/rc bound. It bites this project's own release-prep workflow before it bites an
adopter upgrading release-to-release.

## Verification performed

- Read both `version_tuple` definitions (`src/squads/_util.py:29`, `src/squads/_cli/_common.py:1386`)
  and the import in `src/squads/_cli/_migrate.py:17-23` — confirmed the duplicate feeds the
  `chlog` filter, not only the drift notice.
- Read all four call-site regions via `grep -rn version_tuple src/squads`.
- Drove the ordering directly: `version_tuple("0.14.0rc1") < version_tuple("0.14.0")` is `False`.
- Drove the full `sq migrate up` → `sq migrate chlog` contradiction end-to-end in a throwaway
  squad (not the live corpus), matching the reproduction above exactly, plus the truthful-window
  control.

## Closure suggestion

Delete `_cli/_common.py`'s duplicate and import `squads._util.version_tuple` (dependency-free,
no layering objection); fix the comparator itself to split a segment's suffix instead of
concatenating its digits, so a range filter gets a real ordering rather than a fail-safe
boolean. That one change closes the `chlog` filter and both `_overrides/_manifest.py` sites.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-10T08:38:15Z] Mara Tester:
  - Drove the full sq migrate up -> sq migrate chlog contradiction in a throwaway squad, matching the review's repro exactly, plus the truthful-window control.
  - Confirmed by reading: _cli/_migrate.py imports version_tuple from _cli/_common (not _util), and all four call-site regions (chlog filter, _overrides/_service.py x3, _overrides/_manifest.py x2).
  - Priority: medium. Not release-blocking for a clean X.Y.Z cut per op-pierre's ruling -- it only triggers on a prerelease-stamped squads_version, which this project's own release-prep produces.
  - Targeted 0.16 (MILE-934), addresses REV-926 (F22, F24).
<!-- sq:discussion:end -->

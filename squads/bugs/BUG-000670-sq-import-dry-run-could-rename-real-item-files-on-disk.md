---
id: BUG-670
sequence_id: 670
type: bug
title: sq import --dry-run could rename real item files on disk
status: Verified
author: qa
severity: high
created_at: '2026-07-27T15:31:48Z'
updated_at: '2026-07-27T15:32:18Z'
---
<!-- sq:body -->
## Description

`sq import --dry-run` could physically rename a real item file on disk during
its validate-only pre-pass, even though it prints "dry run — nothing written"
and applies no transaction.

The bulk importer's pre-pass (`_plan_import`) simulates every event against a
throwaway, never-persisted deep copy of the index (`shadow`) purely to collect
validation errors before deciding whether to apply anything. An `update` (or
`assign`) event carrying a title change routed through
`ItemsMixin._update_model`, whose docstring declared it "the PURE half of a
metadata update: no file I/O" — but its title-change branch called
`self._rename(db, item, title)`, and `_rename` itself performed a real
`Path.rename(old_path, new_path)` against the actual squad directory. `db`
here is a deep-copied shadow *index*, not a shadow *filesystem* — the paths
`_rename` computes (`item_file(self.paths, item)`) resolve to the real
on-disk files because `self.paths` is never shadowed. So a title-bearing
`update`/`assign` event reached out of the "simulation" and moved a real file,
whether or not `--dry-run` was even passed — including on the failure path,
since the pre-pass runs before the `dry_run`/`plan.ok` check.

## Steps to Reproduce

1. Create an item, e.g. `sq create bug "Original demo title" --author qa`
   (file `bugs/BUG-000019-original-demo-title.md`).
2. Write a JSONL file with one line:
   `{"op":"update","target":"BUG-19","title":"Renamed via dry run demo"}`
3. Run `sq import --dry-run that.jsonl`. Output: `dry run — nothing written`.
4. `ls squads/bugs/` — the file has actually been renamed to
   `BUG-000019-renamed-via-dry-run-demo.md` on disk.

## Expected vs Actual

- **Expected:** a dry run performs zero filesystem mutation; the item file
  stays exactly where it was.
- **Actual:** the file is renamed on disk while the index
  (`.squads.json`) and the file's own frontmatter both keep the *old* title
  and the *old* path — an inconsistency that outlives the dry run. Reproduced
  independently against `68a44ed^` (pre-fix): after the dry-run, `sq bug 19
  show` raises an unhandled `FileNotFoundError` (it reads the stale path from
  the index); `sq repair` re-indexes the item at its new, silently-renamed
  path, permanently keeping a rename that a dry run should never have made.

## Root cause

`ItemsMixin._update_model`/`_rename` mixed a "pure" contract (used by the
importer's shadow pre-pass) with a real `Path.rename` side effect. Fixed in
commit 68a44ed (TASK-664): `_update_model` now returns
`(item, delta, rename)` where `rename` is `(old_path, new_path) | None` and
performs no I/O; the physical move happens only in `_update_core`, which the
real apply path (`_apply_one`) calls but the shadow simulation path
(`_sim_update`/`_sim_assign`) does not.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T15:32:15Z] Mara Tester:
  - Reproduced against 68a44ed^ in a scratch worktree: a dry-run update event with a title change renamed the real file on disk (index/frontmatter kept the stale title/path) and left the item unreadable until sq repair.
  - Confirmed fixed by 68a44ed (TASK-664): _sim_update/_sim_assign now call the now-pure _update_model (no I/O); only _update_core (the real apply path) performs the physical rename. No remaining reach found.
<!-- sq:discussion:end -->

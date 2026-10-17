---
id: REV-1053
sequence_id: 1053
type: review
title: 'BUG-1040 fix: roster rm requires --purge'
status: Approved
author: reviewer
refs:
- BUG-1040
subentities:
- local_id: F1
  title: Docs and changelog still describe plain rm
  status: Fixed
  severity: medium
- local_id: F2
  title: Help epilogues still show plain rm examples
  status: Fixed
  severity: low
- local_id: F3
  title: Refusal always suggests status Archived
  status: Fixed
  severity: low
- local_id: F4
  title: New test misses pointer and service coverage
  status: Fixed
  severity: low
- local_id: F5
  title: Purge skips the archive gate and reflog
  status: WontFix
  severity: low
created_at: '2026-10-16T11:34:00Z'
updated_at: '2026-10-16T12:35:05Z'
---
<!-- sq:body -->
Scope: the roster `rm` guard on branch `worktree-agent-adaaa829aeaea66dd` (commit d3a7da9d) and the pytest `tmp_path_retention_count = 1` setting (commit 3f555de7), against the 2026-10-16 ruling that a plain `rm` refuses and says exactly what to run.

What was driven (worktree build, scratch squads, each git-inited):

- Plain `rm` on a bundled role (by slug, number, full id), a developer role (`python-dev`), a seeded and an added skill, and an operator: exit 1, message names `sq <type> <ID> rm --purge` and `sq <type> <ID> status Archived` with the right group for each type. `git status` empty afterwards; `.squads.json` and `.reflog.jsonl` byte-identical (sha256); pointers and CLAUDE.md untouched; `sq check` clean. The refusal is raised inside the transaction before any write, so it is atomic.
- Both suggested commands work as given: the full-id address resolves under each group, and Active → Archived is a declared edge of the roster lifecycle for role, skill and operator.
- `rm --purge` on role, dev role, skill and operator: file deleted, role/skill pointer deleted, CLAUDE.md roster updated. The purge path is unchanged by the diff apart from the guard.
- Wrong-type addresses (`sq operator 1 rm`, `sq role 9 rm`) still fail at address resolution before the guard, so the existing wrong-type test keeps its intent.
- Targeted tests (`-n0`): 88 passed on the branch; 89 passed on a probe merge with `release/0.16` (the branch is based on the 0.15.0 changelog commit, 65 commits behind; the merge is textually clean). ruff and pyright clean on the changed files.
- The tests switched to `--purge` keep their intent: address resolution, and an author/assignee left unregistered by a removed role.
- pytest setting: under xdist the workers take their basetemp from the controller, so only the controller prunes; pytest skips a numbered dir whose lock file is fresh, so a concurrent run's dir survives. No conflict with `tests/conftest.py`, which does not touch basetemp. Not measured: whether a full run can fill `/tmp` (tmpfs 9.6G, 7% used; existing run dirs are 2 to 7 MB). The commit is unrelated to the bug.

Findings below.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1053 add-finding "…" --severity medium`; track with `sq review 1053 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Docs and changelog still describe plain rm

<!-- sq:finding:F1:body -->
Once this branch merges, delivered docs say the opposite of the new behaviour, and there is no changelog entry.

- `docs/roles.md:146-149` (working tree, written for REV-1034 F8, which is marked Fixed) says plain `rm` "drops the entry from the index ... but leaves the item file on disk, which `sq check` then reports as an error". After this change plain `rm` writes nothing and exits 1.
- `docs/roles.md:74,125,143` and `README.md:332,335,336` still show `rm [--purge]`, so `--purge` reads as optional.
- `docs/stability.md:223` shows `sq role 2 rm   # remove`, which now always fails.
- `CHANGELOG.md` `[0.16.0]` has no entry. A command that exited 0 now exits 1, which breaks scripts that called it.

Fix: the writer updates those lines to `rm --purge` (delete) / `status Archived` (retire) and adds a Changed entry. The dev's comment on BUG-1040 hands this off, but nothing tracks it, and F8 is already marked Fixed with the old wording.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T12:34:12Z] `tech-writer` Theo Writer:
  - Fixed, uncommitted. roles.md: the three command blocks now show rm --purge. The "rm drops the index entry but leaves the file" paragraph is gone. A new section, "Removing a roster entry", quotes the driven refusal and says the retire route is offered only while the entry is live. README: role/operator/skill lines show rm --purge, and the role line names the refusal. stability.md Tier 2: the example is now rm --purge, with a paragraph on the refusal. CHANGELOG [0.16.0] Changed has a BREAKING entry (exit 0 → exit 1, with the exact message).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Help epilogues still show plain rm examples

<!-- sq:finding:F2:body -->
The `--help` epilogues still use plain `rm` as their example, and that command now always fails:

- `src/squads/_cli/_role.py:70`: `sq role ROLE-1 rm`
- `src/squads/_cli/_skill.py:66`: `sq skill SKILL-2 rm`
- `src/squads/_cli/_operator.py:45`: `sq operator 2 rm`

Driven: `sq role --help` prints `sq role ROLE-1 rm`. Fix: add `--purge` to each example. Minor, same surface: the option help says "Required: delete the file too." while Typer still lists `--purge` as an optional flag. The service's `purge: bool = False` default is now a value that can only raise. Not a defect, just a leftover.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Refusal always suggests status Archived

<!-- sq:finding:F3:body -->
The refusal always offers `status Archived` as the way to retire an entry. In some cases that route does nothing or is refused:

- Already Archived: `sq role python-dev status Archived` on an archived role exits 0 as a no-op, so the message tells the user to retire something that is already retired.
- Gate-refused: for the seeded `squads` skill, `status Archived` is refused ("every role preloads it unconditionally ... no remedy exists"). For a type-implied skill (`sq-task`) it is refused too. The message still suggests it.
- `Archived` is a literal in the service (`_services/_items.py:720`). Every other occurrence is CLI help text. Not verified: whether an adopter can rename the roster lifecycle's statuses through an override. If they can, this message names a status that does not exist.

Suggested: name the retire route only when the item is live, and resolve the target status from the item's lifecycle instead of hardcoding it. Low: the delete route in the message is always correct.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — New test misses pointer and service coverage

<!-- sq:finding:F4:body -->
`tests/cli/test_roster_rm_requires_purge_cli.py` gaps:

- Refusal branch: asserts the file exists and `sq check` passes. It does not assert that the role/skill pointer, `.squads.json` or the reflog are unchanged. `check` would catch a dropped index entry, but not a pointer deleted before the raise.
- Purge branch: asserts only that the file is gone. It does not assert that the pointer and the CLAUDE.md roster line are gone.
- No developer role in the parametrisation (driven by hand here: correct).
- No service-level test of `remove_item(purge=False)` raising `SquadsError` with no write, which CLAUDE.md asks for alongside the CLI smoke test.
- `item_id.replace("-00000", "-")` munges the padded id by hand. Asserting the expected unpadded id directly is clearer.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Purge skips the archive gate and reflog

<!-- sq:finding:F5:body -->
This was already true before the change, but `--purge` is now the only way `rm` deletes, so it carries more weight. `rm --purge` skips the retirement gate and the warnings that `status Archived` gives.

Driven:
- `sq role manager status Archived` on the default role warns that the default-role designation is gone, and warns about open assigned work. `sq role manager rm --purge` on the same role (default, author and assignee of TASK-21) prints only `removed ROLE-1`. `sq check` then warns twice that TASK-21's author/assignee is unregistered.
- `sq skill squads status Archived` is refused by the gate ("no remedy exists"), but `sq skill squads rm --purge` succeeds. `sq skill sq-task rm --purge` also succeeds.
- Roster removal writes no reflog entry (work-item `remove` does).

Not for this bug. Suggest a follow-up so a purge is checked at least as strictly as an archive (or at least warns), and so it reflogs.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T12:21:24Z] `qa` Mara Tester:
  - Home: BUG-1058 (reproduced on the dev build).
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:34:32Z] `reviewer` Paul Reviewer:
  - Verdict: ChangesRequested on F1 (medium). The guard is atomic and right for role, dev role, skill and operator, and --purge works as before. Docs and the changelog still describe the old plain rm.
  - @python-dev F2 (help epilogues) and F4 (test coverage). F3 is optional. F5 is already true without this change: suggest a follow-up item, not this branch.
  - @tech-writer F1: docs/roles.md, README.md, docs/stability.md and a [0.16.0] Changed entry.
- [2026-10-16T11:40:54Z] `python-dev` Elias Python:
  - F2, F3, F4 fixed in e639e422 on worktree-agent-adaaa829aeaea66dd. F2: epilogue examples use rm --purge, option help reworded, remove_item purge is now a required keyword. F3: the status route is named only when a dry run of the real transition on a db copy is accepted (live, edge exists, gate passes); the target comes from the lifecycle, not a literal. Falsified: forcing the suggestion on fails 3 tests (archived, gated, CLI omit). F4: refusal asserts the whole squad tree hash-identical (pointer, index, reflog, CLAUDE.md); purge asserts pointer and roster line gone; dev role row; 3 service tests. Falsified: guard removed fails 8; refusal moved after pointer removal fails 3 (role, dev role, skill rows). F1 and F5 untouched.
- [2026-10-16T12:35:04Z] `manager` Catherine Manager:
  - Approved: F1 Fixed (docs and CHANGELOG), F2–F4 Fixed, F5 WontFix with home BUG-1058. Merged as ad2cbbe9; full suite 10,643 passed, 0 failed.
<!-- sq:discussion:end -->

---
id: REV-1062
sequence_id: 1062
type: review
title: Blocked flag and blocked_has_blocker, part two
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-1001:addresses
- FEAT-901:addresses
- MILE-934:targets
description: 'Review of TASK-1001 part two: the role blocked flag and the blocked_has_blocker
  check.'
subentities:
- local_id: F1
  title: A malformed dependency ref aborts every check and write
  status: Verified
  severity: medium
- local_id: F2
  title: The sixth role key turns the VS Code skew canary red
  status: Verified
  severity: medium
- local_id: F3
  title: The refusal names ref add, which create cannot use
  status: Verified
  severity: low
- local_id: F4
  title: The role table comment does not document the flag
  status: Verified
  severity: low
- local_id: F5
  title: Strict blocked beside lenient live, settled and hidden
  status: Verified
  severity: low
- local_id: F6
  title: blocked_statuses has no caller outside its test
  status: Verified
  severity: low
- local_id: F7
  title: A hand-written self edge satisfies the check
  status: WontFix
  severity: info
created_at: '2026-10-16T13:40:55Z'
updated_at: '2026-10-16T16:20:51Z'
---
<!-- sq:body -->
Review of TASK-1001 part two: ST10 (a status role can declare `blocked = true`, the sixth key of the role catalog) and ST6 (the opt-in `blocked_has_blocker` check and the shared incoming-edge walk).

## What was reviewed

Commits `4958500d` and `6b263cff` on the branch `worktree-agent-a1e99ab918ae65efb` (`git diff 03745229..6b263cff -- src tests`); the merge `1d2f4f7b` brings in board files only. Probes were driven with the worktree's build in scratch squads under the session scratchpad, each in its own git-inited directory. Nothing ran against this repository's squad except board writes with the released tool.

## What holds (driven unless marked)

- Flag by role, not by name: with the bundled `blocked` role set to `blocked = false` and a project role `waiting` flagged, `status Blocked` is accepted with no edge and `status OnHold` (role `waiting`) is refused at `@error`.
- Renamed dependency kind: with `blocks`/`depends-on` dropped through `[selected]` and a `waits-on` kind of role `dependency`, an outgoing `waits-on` satisfies the check; the message lists `kinds: waits-on`.
- Incoming edge (`TASK-3 blocks TASK-2`) satisfies; `ref rm` of it is ungated, `sq check` then exits 3, and the item's next gated write (`update --title`) is refused while a comment is accepted.
- Self edge: `ref add` and an import `ref` op both refuse it ("an item cannot reference itself").
- Import door: a status move to Blocked is judged on the state at that event. An incoming `blocks` written earlier in the same file satisfies; one written after the move does not (line 3 refused, nothing written).
- Create door: reachable only when a lifecycle's initial status resolves to a flagged role. Plain create and a bare `--ref` are refused; `--ref FEAT-2:depends-on` is accepted.
- Load refusals: review (no flagged status), a roster type, a parameter, and a spec with no dependency kind (one refusal per selecting type, two types driven) each refuse with the expected text. `blocked = "yes"` and `blocked = 1` are refused naming the role and the key.
- Supersession half: the supersession set is built exactly as before, keyed by sequence number. `gate()` and `report()` each call `incoming_edges` once (read from the code), so the walk count per gate call is unchanged.
- The two failures in `tests/cli/test_this_repositorys_workflow_override_loads_clean_cli.py` have one cause, the bundled `workflow.toml` edit. Control: an export of `1d2f4f7b` with only `_specs/workflow.toml` reverted to `03745229` passes 4 of 4; the same export with the branch file restored fails the same 2.
- Targeted tests in the worktree, `-n0`: the new and touched test modules plus `tests/meta`, 563 passed; every test module that names the changed symbols (19 files), 359 passed. The full suite was not run here.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1062 add-finding "…" --severity medium`; track with `sq review 1062 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A malformed dependency ref aborts every check and write

<!-- sq:finding:F1:body -->
**What.** `incoming_edges()` calls `number_for_id(rid)` on every ref of a dependency kind. `number_for_id` raises `InvalidIdError` on an id whose tail is not an integer. The old supersession walk only parsed refs of a supersession kind, so a malformed dependency ref was harmless. Now it aborts the walk, and the walk runs on every `sq check` and every gated write, in every squad, whether or not any type selects `blocked_has_blocker`.

**Driven.** Scratch squad, nothing selected. `refs: [TASK-abc:depends-on]` was hand-written into TASK-3's frontmatter, then `sq repair` (rebuilt, exit 0).
- Branch build: `sq check` prints `error corpus: could not scan the corpus: malformed ID 'TASK-abc'` and exits 3. `sq task 5 update --title ...` on an unrelated item is refused with `error: malformed ID 'TASK-abc'`, exit 1. Neither names the item that holds the bad ref.
- Base build (`03745229`), same corpus: `sq check` exits 0 with `warn TASK-3: dangling ref TASK-abc`, and the update is accepted.
- The base build already fails this way for a malformed `supersedes` ref (driven), so the defect predates this change. This change widens it from the rare supersession kinds to the common dependency pair.

`ref add` and `sq import` reject such an id, so the way in is a hand edit, a merge or an external tool writing frontmatter. Frontmatter is the source of truth, and the base build degraded to a dangling-ref warning.

**Fix direction.** In the shared walk, skip a ref whose id does not parse, in both halves. `dangling_ref` already reports it. Add a row: a malformed dependency ref and a malformed supersession ref, with `sq check` reporting the dangling ref and an unrelated item's write accepted.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T13:50:17Z] Elias Python:
  - Fixed in 3be94ffc. incoming_edges skips an id that does not parse in both halves; dangling_ref reports it; sq check and an unrelated write behave as on the base build for supersedes, blocks, depends-on and related. Falsification: 6 tests red with the skip removed.
- [2026-10-16T13:57:32Z] Paul Reviewer:
  - Verified on bd37320f: scratch m (malformed depends-on) and a supersedes copy now match the base build, sq check exit 0 with warn dangling ref TASK-abc, unrelated update exit 0; with the check at @error the holder can still move to Blocked (an outgoing dangling edge counts, as designed).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — The sixth role key turns the VS Code skew canary red

<!-- sq:finding:F2:body -->
**What.** `clients/vscode/test/canary/skewCanary.test.ts:889` compares the `active` row of `sq workflow roles --json` with `toEqual` against a five-key object. `toEqual` fails on an extra defined key, so the sixth key `blocked` turns it red.

**Driven.** From the main checkout's `clients/vscode` (no file under `clients/` differs between it and the branch), `npx vitest run --config vitest.canary.config.ts -t "sq workflow roles"`:
- `SQ_CANARY_CMD=<worktree>/.venv/bin/sq` (0.16.0): 1 failed. The diff is `+ "blocked": false` on the active row.
- Control, `SQ_CANARY_CMD=~/.local/bin/sq` (0.15.0): 2 passed.

The handoff says the canary was not run. ST10 expected this break and said the client change should land with this change. It is a finding so that the merge does not go ahead without it.

**What has to move together.** The canary's exact object, `test/fixtures/roles-catalog.json` (five keys per row today), and `SqRoleCatalogEntry` / `isSqRoleCatalogEntry` in `src/sqAdapter.ts`, if the client is to read the flag. The guard ignores extra keys, so leaving it as is keeps the client working.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T13:53:43Z] Ada Typescript:
  - Fixed in the worktree: SqRoleCatalogEntry gains an optional blocked, isSqRoleCatalogEntry accepts an absent key and refuses a non-boolean, the fixture carries the key, and the canary requires it. npm run check, npm test (706) and the canary against the worktree sq (76) pass.
- [2026-10-16T13:57:34Z] Paul Reviewer:
  - Verified: the worktree client (bd37320f, scratch export) passes the full canary against the worktree sq, 76/76, and fails the roles test against 0.15.0, so the canary still catches the skew; sqAdapter tests 104/104. One wording slip, no reopen: types.ts says blocked is whether the role requires a dependency edge; the flag means the statuses wait on something else, and an edge is required only where blocked_has_blocker is selected. Worth a one-line fix with the next client change.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — The refusal names ref add, which create cannot use

<!-- sq:finding:F3:body -->
**What.** The finding text is the same at every door: `status is <S> but no dependency edge is recorded (kinds: ...) — add the blocker with `ref add``. At the create door no item exists yet to `ref add` from. The way in there is `--ref <id>:<kind>` on create, or an import `ref` event before the status event. This is the same class as REV-1010 F4, where the description message was made door-neutral.

**Driven.** Override `[roles.pending] blocked = true` (Draft, the initial status, is flagged) with `blocked_has_blocker@error` on task. `sq create task "t1"` and `sq create task "t2" --ref FEAT-2` are both refused with the `ref add` text. `--ref FEAT-2:depends-on` is accepted.

**Fix direction.** Name the edge, not one verb: for example, `record a dependency edge (`--ref <id>:<kind>` on create, `ref add` after)`. A create-door row should pin the text.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T13:50:19Z] Elias Python:
  - Fixed in 3be94ffc. The message now reads: record a dependency edge (--ref <id>:<kind> on create, ref add after); a create-door row pins it. Falsification: 38 tests red with the old text (the registry pins the message across every row).
- [2026-10-16T13:57:36Z] Paul Reviewer:
  - Verified: create in scratch e (flagged initial status) is refused with the new text naming --ref <id>:<kind> on create and ref add after; --ref FEAT-2:depends-on is accepted.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — The role table comment does not document the flag

<!-- sq:finding:F4:body -->
**What.** ST10's Approach says the comment above the role table gains one clause for the flag. The diff edits the file-header comment (line 12, the list of role keys) instead. The comment over `[roles.*]` (lines 141 to 147) still documents `settled`, `hidden`, `color` and `live`, and not `blocked`. An adopter who scaffolds the workflow override reads the role table with no word on the new key.

**Fix direction.** Add one clause, for example `` `blocked` (defaults false) marks statuses that wait on something else — the one bundled flagged role is `blocked` ``. This is a bundled-byte change, so regenerate the manifest and the content store again.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T13:50:21Z] Elias Python:
  - Fixed in 3be94ffc. blocked documented in the comment above the role table; manifest and content store regenerated from the base entries (no orphan blob). Falsification: stale manifest turned --check red plus 7 freshness tests.
- [2026-10-16T13:57:38Z] Paul Reviewer:
  - Verified by reading; gen_template_manifest --check passes. Cosmetic: the rewrap leaves a short line (warning is unused by / the bundled defaults); fold it on the next bundled edit.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Strict blocked beside lenient live, settled and hidden

<!-- sq:finding:F5:body -->
**What.** `RoleSpec.blocked` is `StrictBool`; `settled`, `hidden` and `live` stay plain `bool`. One table now has two coercion rules.

**Driven.** `[roles.active] live = "yes"` loads clean and is read as true. `live = "no"` is read as false (the roster floor then refuses three types). `[roles.blocked] blocked = "yes"` and `blocked = 1` are refused. The refusal text is pydantic's own (`Input should be a valid boolean [type=bool_type, input_value='yes', input_type=str]` plus an `errors.pydantic.dev` URL), not the loader's phrasing.

Strict on the new key is the right call: a lenient bool reads `"false"` as false but `"no"` and `"off"` in ways an adopter cannot predict. The finding is that the old booleans stay lenient with no tracked decision. An adopter who learns from `live = "yes"` that a string works is then refused on `blocked`.

**Disposition wanted.** Either a tracked follow-up that makes the three older booleans strict, which is adopter-visible and needs a lint message and a changelog line, or WontFix with the reason. Separately, the refusal could use the loader's own wording instead of pydantic's.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T13:50:24Z] Elias Python:
  - Fixed in 3be94ffc. blocked stays strict; the loader refuses a non-boolean with: Invalid role <name>: blocked must be true or false, got <value>, no pydantic text or URL. The other booleans are untouched. Falsification: 8 tests red with the loader check removed.
- [2026-10-16T13:57:40Z] Paul Reviewer:
  - Verified: blocked = "yes", 1, 0, "true" each refused as: Invalid role blocked: blocked must be true or false, got <value>; true loads clean. Keeping the older booleans lenient is the recorded choice.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — blocked_statuses has no caller outside its test

<!-- sq:finding:F6:body -->
**What.** `WorkflowSpec.blocked_statuses` (`_workflow/_models.py:2845`) has no caller in `src/`. ST6 reads `spec.role_for(status).blocked` and the load refusal uses `_status_blocked`, so the accessor that ST10 added for ST6 is read only by its own unit test. `uv run vulture` flags it, and also flags `supersedes_incoming_seqs`, which after this change has only test callers. ST6 allowed keeping that one as a thin reading, so it is acceptable if the handoff records the choice; it does.

**Fix direction.** Drop `blocked_statuses` and its test row, or have the member and the refusal read it. Do not leave a production API that only a test exercises.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T13:50:26Z] Elias Python:
  - Fixed in 3be94ffc. blocked_statuses removed (no src caller) with its test row; the registry plant reads role_for over the lifecycle states. A removal has no falsification count; ruff, pyright and the suites stay green.
- [2026-10-16T13:57:41Z] Paul Reviewer:
  - Verified: blocked_statuses is gone and vulture no longer lists it; supersedes_incoming_seqs remains as the sanctioned thin reading.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — A hand-written self edge satisfies the check

<!-- sq:finding:F7:body -->
**What.** A dependency edge from an item to itself satisfies `blocked_has_blocker`. The writers refuse a self ref (`ref add` and an import `ref` op, driven), so the only way in is a hand edit, and no check reports a self ref.

**Driven.** `refs: [TASK-5:depends-on]` written into TASK-5's own frontmatter at `status: Blocked`, then `sq repair`. `sq check` reports nothing for TASK-5, with the check selected at `@error`.

**Disposition wanted.** Either the member ignores an edge whose target is the item itself (one comparison against `sequence_id`, in both halves), or this is recorded as a limit for the docs. A self-dependency never records a real blocker.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T13:42:30Z] Catherine Manager:
  - WontFix: a self-edge can only come from a hand-edited file (ref add and import refuse it); not worth a check of its own.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T13:41:40Z] Paul Reviewer:
  - Part two reviewed: ChangesRequested on F1 (the shared incoming-edge walk parses every dependency ref id, so one malformed dependency ref aborts sq check and refuses every gated write in any squad; the base build reported it as a dangling ref) and F2 (the sixth role key turns the VS Code roles canary red, driven against the worktree build with a 0.15.0 control green). F3 to F6 low, F7 info. The two override-drift test failures have the bundled workflow.toml edit as their only cause (controlled export). @manager
- [2026-10-16T13:57:50Z] Paul Reviewer:
  - Pass 2 on 3be94ffc and bd37320f: F1 to F6 Verified, F7 WontFix accepted. No medium or worse finding is open; left InReview, approval recommended. Targeted -n0 run: 846 passed, 2 failed, both in the override-drift test the manager is handling. Two text nits are recorded on F2 (types.ts wording) and F4 (a short comment line), neither reopened. @manager
- [2026-10-16T16:20:50Z] Catherine Manager:
  - Approved on the reviewer's recommendation: F1–F6 Fixed and verified, F7 WontFix. Merged into release/0.16 as 4859f3e0; full suite 11,196 passed, 0 failed.
<!-- sq:discussion:end -->

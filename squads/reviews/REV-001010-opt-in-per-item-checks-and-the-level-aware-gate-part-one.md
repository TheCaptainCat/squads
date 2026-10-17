---
id: REV-1010
sequence_id: 1010
type: review
title: Opt-in per-item checks and the level-aware gate, part one
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-1001:addresses
- FEAT-901:addresses
- MILE-934:targets
description: 'Review of TASK-1001 part one: the gate change and seven opt-in per-item
  catalog checks, with the BUG-1003 fix.'
subentities:
- local_id: F1
  title: A pattern matching the empty string loads and fires on every item
  status: Verified
  severity: medium
- local_id: F2
  title: sq import runs warn members over the whole squad; a bad pattern hangs it
  status: Verified
  severity: medium
- local_id: F3
  title: item_title_max refusal at @error is worded as an advisory
  status: Verified
  severity: low
- local_id: F4
  title: Create refusal hint names an item id that was never allocated
  status: Verified
  severity: low
- local_id: F5
  title: item_title_max counts code points, not visible characters
  status: Verified
  severity: low
- local_id: F6
  title: body_written misses a scaffold whose interpolated field changed
  status: WontFix
  severity: low
- local_id: F7
  title: A pattern compiling with a FutureWarning prints it on every command
  status: Verified
  severity: medium
- local_id: F8
  title: Missing body region crashes body -m; new test comment says otherwise
  status: Fixed
  severity: info
- local_id: F9
  title: Import sub-status with an unnormalised target skips board debt
  status: Verified
  severity: info
created_at: '2026-10-15T19:25:04Z'
updated_at: '2026-10-15T19:44:52Z'
---
<!-- sq:body -->
Review of TASK-1001 part one: the gate change (ST11) and seven opt-in per-item checks (ST1 to ST5, ST7, ST8), with the selection proof (ST9) and the BUG-1003 fix in ST2. ST6 and ST10 are not built and are out of scope here.

## What was reviewed

The ten commits `90764251...1e95ac9f` on the branch `worktree-agent-a973dcee573f937c0`: the source changes in `_services/_validators.py`, `_workflow/_models.py`, `_rendering/_engine.py`, `_services/_base.py`, `_services/_items.py` and `_views.py`, and the 38 new or edited test modules around `tests/_selection_table.py`.

Probes were driven with the worktree's build in scratch squads under the session scratchpad. Nothing was run against this repository's squad except board writes with the released tool.

## Verified, no finding

Every line below is labelled driven, read or run.

- **Bundled bytes** (run): `git diff --name-only 90764251...HEAD` over `_specs/`, `_rendering/` (templates, manifest, content store), `_overrides/` and `scripts/` lists only `_rendering/_engine.py`, which is code. `gen_template_manifest.py --check` passes. None of the seven names occurs in `_specs/`, the templates, the manifest or the content store. The grep was checked against a known positive: `item_skill_shadowed` hits `workflow.toml` and `content_store.json`.
- **Gate by level** (driven): with `item_title_max:20@error`, a 28-character create exits 1 and writes nothing. The same title on a type at `warn` is created and reported by `sq check` (exit 0). `update`, `status` and `retype` into a selecting type are refused at `@error`. With a backtracking pattern at `warn`, a create takes 0.8 s while `sq check` hangs, so the gate skips `warn` members as claimed.
- **A member that raises at warn** (read and run): the unit test registers a raising stub under `dangling_ref`. At the bundled `warn` level the write is not aborted; at `@error` it raises. That module and the scaffold module pass (97 passed, 2 skipped).
- **No member hard-codes a level** (read): every per-item member resolves its level through `_resolved_level`, so the gate's skip and each member's own finding cannot disagree.
- **Shared body predicate and the overwrite guard** (read): `authored = not body_is_unwritten(current, pristine)` is equivalent to the old `bool(prose) and prose != pristine_prose`, including the case where no scaffold can be rendered. `scaffold_body` resolves the same template name that `_template_for` used. The guard's behaviour is unchanged.
- **Load refusals** (driven, 18 cases through `sq workflow lint`): all refused with the documented text and exit 1. The cases were: a member on `role`, `operator`; `ref_rule_target_typed` on `task`; `assignee_present` on `decision`, `guide`; an Arabic-Indic digit; a repeated `item_title_max`; an empty pattern; `a@b@error`; an invalid backreference; a parameter on `assignee_present`. `no_status_banner` on `skill` still loads. `:080`, an epic list with and without the splat, and `feature` with `ref_rule_target_typed@error` all load.
- **BUG-1003 and bare versus kinded refs** (driven): a bare edge and an edge spelled with `:related` are treated the same way (both refused at `@error`). An edge of a kind with no typed rule passes. `ref add` writes a misdirected edge, after which `sq check` exits 3, the next `update` is refused, and `ref rm` clears it.
- **Mutable-state guard and catalog guards** (run): `tests/meta` gives 345 passed. The new module constants are frozensets.
- **Import graph** (run): an AST scan of top-level `squads` imports finds only the five package-`__init__` cycles that already existed. The new `_validators -> _rendering._engine` edge closes no cycle.
- **Static gates** (run): pyright, `ruff check` and `ruff format --check` are clean.

## Findings

F1 and F2 are medium. Recommended verdict: changes requested. The rest are low or info.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1010 add-finding "…" --severity medium`; track with `sq review 1010 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A pattern matching the empty string loads and fires on every item

<!-- sq:finding:F1:body -->
**Driven.** `external_id_not_in_title` refuses a selection that cannot fire, but accepts one that fires on every item.

- `'external_id_not_in_title:x*'` passes `sq workflow lint` (exit 0). `sq check` then reports every item of the type with ``title holds `` (matches the external-id pattern `x*`)``, an empty quote. Any pattern that can match the empty string behaves this way: `x*`, `|`, `^`, `(?:)`, a bare lookahead.
- `'external_id_not_in_title: '` (a single space) also passes lint, because the required-parameter test is `not param`. It then reports every title that holds a space.
- At `@error` this refuses every create, update, status and retype of the type until the entry is removed. That is the opposite of what the refusal rule for a selection that cannot fire is protecting against, and an adopter gets no warning at load.

**Fix.** At load, refuse a pattern whose compiled form matches the empty string (`re.compile(p).search("") is not None`). Also refuse a parameter that is only whitespace. Optionally, the member could skip a zero-width match so a lookahead-only pattern reports nothing instead of an empty quote. Add the empty-match and whitespace rows to the load-refusal table in `tests/unit/test_external_id_not_in_title_entry_is_validated_at_load.py`.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-15T19:39:07Z] `reviewer` Paul Reviewer:
  - Pass 2, driven: 36 patterns tried in-process. Every pattern that matches the empty string, including under (?i), (?x), (?m) flags, alternations with an empty branch, (?:), a{0}, (?#c), negative lookarounds and \A, \Z, \B, is refused. A whitespace-only parameter gets the missing-parameter message. Zero-width-only patterns load and report nothing: \b, (?=A) and (?<=a) report nothing, and (?=A)@error accepts a create titled ABC. Verified in b60c264c.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — sq import runs warn members over the whole squad; a bad pattern hangs it

<!-- sq:finding:F2:body -->
**Driven and read.** `sq import` runs every per-item member over the whole squad, at every level, so a backtracking pattern hangs every import.

- **Read:** `ImportMixin._board_debt_findings` (`_services/_import.py`) calls `engine.report(final_db, ...)` over the entire index and only afterwards filters to the touched ids. Every `warn` member therefore runs on every item of the squad, on every import.
- **Driven:** one task carries the title `"a"*34 + "b"`, and `task` selects `'external_id_not_in_title:(a+)+$'` at `warn`. Importing one unrelated `bug` event is killed by a 15 s timeout (exit 124). The bug was already committed, because this runs after the transaction closes, so the index lock is not held. The command never returns, and a retry hangs the same way.
- The adopter sentence in the hand-off for TASK-1002 says the pattern runs "on every `sq check`, and on a gated write of an item only when its type selects the check at `@error`". `sq import` is a third place, it runs at every level, and it runs over items the import never touched. The sentence is incomplete as it stands.
- The whole-index scope existed before this change. The regex member is what turns it from wasted work into a hang.

**Fix.** Run the per-item members over the touched items only. The engine already iterates per item, so report over a sub-index or add a `report(items=...)` path. Add a test where a pathological or counted member on an untouched item is not evaluated by an import. Then correct the writer's sentence to name `sq import`: it runs the selected checks on the items it wrote, at every level, after the write commits.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-15T19:39:09Z] `reviewer` Paul Reviewer:
  - Pass 2, read and driven: report(only=) skips untouched items and the import passes its touched ids. The status, sub-status and comment door outputs are correct. The one gap, a sub-status target written unnormalised, is filed as F9 (info; the cause predates this task). There is no retype import op. Verified in 1e519734.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — item_title_max refusal at @error is worded as an advisory

<!-- sq:finding:F3:body -->
**Driven.** The `item_title_max` message opens with `advisory:`, which contradicts a refusal.

- With `item_title_max:20@error`, `sq create task "a title that is way too long"` and `sq bug 5 retype task` both print `error: advisory: title is 35 chars (threshold: 20) — an item title is a one-line handle; put the detail in the body` and exit 1. `sq check` at `@error` prints `error TASK-n: advisory: ...`.
- The prefix was copied from the sub-entity title message, which is report-only. On a member that can refuse writes it misleads the reader.

**Fix.** Drop `advisory:` from the item message; the member's unique fragment is in the rest of the text. Then re-run the pairwise fragment test.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-15T19:39:11Z] `reviewer` Paul Reviewer:
  - Pass 2, driven: the create refusal now reads: title is 6 chars (threshold: 5) ...; there is no advisory prefix. Verified in 1e519734.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Create refusal hint names an item id that was never allocated

<!-- sq:finding:F4:body -->
**Driven.** When `description_present@error` refuses a create, its fix hint names an item that does not exist.

- With `description_present@error` on `task`, `sq create task "no desc" --author manager` prints ``error: description is empty — set it with `sq task 4 update --desc "..."` `` and exits 1. TASK-4 was never written. The next create in that squad, an unrelated item, became TASK-4.
- Following the hint therefore fails, or edits the wrong item. On the create door the remedy is `--desc` on the create itself.
- `body_written` builds its message the same way, but it is report-only, so it never reaches a create refusal.

**Fix.** Make the hint door-neutral, for example "set a summary (`--desc`)". Alternatively, leave the id out when the item is not yet in the index. Pin the create-door message in the door test.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-15T19:39:13Z] `reviewer` Paul Reviewer:
  - Pass 2, driven: a create refused at @error now prints the door-neutral hint, which names no id. Verified in 1e519734.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — item_title_max counts code points, not visible characters

<!-- sq:finding:F5:body -->
**Driven.** `item_title_max` counts code points, so two spellings of the same visible title get different answers.

- With `item_title_max:10@error`, a title of six `é` written as `e` plus U+0301 is refused: `title is 12 chars (threshold: 10)`. The same six letters in NFC form (U+00E9) are accepted. A ZWJ family emoji, which displays as one glyph, counts as 5.
- The hand-off for the writer says "characters, not bytes". The build counts code points, and titles are not normalised on the way in, so the result depends on how the adopter's input method encodes the text.

**Fix.** Count `len(unicodedata.normalize("NFC", title))`. Alternatively, keep code points and have the writer say "code points" in the docs. Either way, add the decomposed row to the title-shape table.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-15T19:39:14Z] `reviewer` Paul Reviewer:
  - Pass 2, driven at item_title_max:5: six decomposed é are reported as 6 chars, five decomposed é are accepted, Hangul jamo x3 composes to 3 and is accepted, and q+U+0303 x3 (no precomposed form) counts as 6. The message carries the count after NFC. This matches the documented limit, code points after NFC. Verified in 1e519734.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — body_written misses a scaffold whose interpolated field changed

<!-- sq:finding:F6:body -->
**Driven.** `body_written` inherits a blind spot from the overwrite guard: an untouched review scaffold reads as written once `target_ref` is set.

- A review created without `target_ref` is reported unwritten. After `sq review 7 update --set target_ref=zzz`, the re-rendered scaffold gains a `**Target:**` line that the file never had. `sq check` goes silent on it, and `sq review 7 body -m "x"` is refused with "already has a body (3 lines)", even though those three lines are the untouched `## Scope` / `_TODO_` scaffold.
- The same thing happens for any template that interpolates a field which changes after creation. In the bundled templates that is `items/_default.md.j2` naming the type, so a retype hits it too, and `items/review.md.j2` reading `target_ref`.
- The dev's hand-off lists this as a limit. The guard behaved this way before this change; `body_written` now carries it into a report that adopters will rely on for exactly the review type. The ST9 count for this repository (9 reviews unwritten) is a lower bound.

**Fix.** Choose one: (a) compare the body region against the scaffold rendered with the item's fields as they were at creation; (b) count a body as unwritten when, with every interpolated line removed, it is a sub-sequence of the scaffold; or (c) accept the limit and give it a WontFix that cites the writer's doc line. Whichever you choose, add a test row with the field set after creation to `test_body_written_reports_exactly_what_a_first_body_write_would_replace.py`.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-15T19:34:50Z] `python-dev` Elias Python:
  - WontFix: the guard cannot know a field that the scaffold interpolates changed after creation (no creation-time history of target_ref, or of the type for the default template). Same limit as the body overwrite guard, stated in the writer handoff. Home: a bug to be filed by qa (routed via manager), covering both the guard and body_written.
- [2026-10-15T19:36:11Z] `qa` Mara Tester:
  - Home for this finding: BUG-1014.
- [2026-10-15T19:39:16Z] `reviewer` Paul Reviewer:
  - Pass 2: WontFix accepted. The limit is shared with the overwrite guard and now has a home, BUG-1014.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — A pattern compiling with a FutureWarning prints it on every command

<!-- sq:finding:F7:body -->
**Driven.** A pattern that compiles with a `FutureWarning` loads clean, then prints a Python warning on every command.

- `'external_id_not_in_title:[[a]]'` passes lint. On `sq check`, stderr shows `.../_workflow/_models.py:1499: FutureWarning: Possible nested set at position 1` followed by `re_compile(param)`, twice. The source path is the installed package's.
- The cause is `_check_validator_param` calling `re_compile(param)` without capturing warnings.

**Fix.** Compile under `warnings.catch_warnings(record=True)` (or with `warnings.simplefilter("error")`). Then either refuse the entry and quote the warning, as the compile-error refusal does, or report it as a lint warning. Add the row to the load table.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-15T19:39:20Z] `reviewer` Paul Reviewer:
  - Pass 2: reopened and raised to medium. **Driven.** `sq workflow lint` passes the spec that every other command refuses.
    
    - In a scratch squad whose override is `validators = ['external_id_not_in_title:[[a]]']`, `sq workflow lint` prints "workflow spec OK — no errors or warnings." and exits 0. In the same squad, `sq list` and `sq check` refuse the spec, quoting "compiles with a warning: Possible nested set at position 1 — rewrite it".
    - **Cause** (driven in-process with `-I`): `re` caches compiled patterns, and Python warns only when it first parses a pattern. When `_check_external_id_pattern` runs a second time in the same process, the cache returns the compiled pattern, no warning is caught, and the entry loads. `[[a]]`: refused on the first call, loads on the second. The lint process evidently validates the spec twice; that last step is inferred.
    - The other warnings Python's `re` emits come through the same path and fail the same way on a cache hit: the nested set, `&&`, `||` and `~~` warnings were all caught on a first compile. Because whether the refusal appears depends on what was compiled earlier in the process, the refusal is not stable. The unit row may also depend on test order under xdist (inferred).
    - **Fix:** run the warning check through something that does not use the cache. Options are `re._parser.parse(param)` under `catch_warnings`, or `re.purge()` immediately before the compile. Add a test that validates the same entry twice in one process and asserts both validations refuse, and a CLI row that asserts `sq workflow lint` exits 1.
- [2026-10-15T19:44:40Z] `reviewer` Paul Reviewer:
  - Pass 3, driven: verified in 3548f802. In-process, with the cache primed by a plain compile first, these shapes load: a leading (?i), (?x) with a # comment, (?ix), (?a), (?s), (?m), (?u), (?i)(?x) and (?i:...). These are refused on the plain compile, before the copy is made: (?L), a trailing backslash, a lone backslash, (?i without its closing parenthesis, and a(?i)b (global flags not at the start). [[a]], (?i)[[a]] and [a&&b] are refused on all four repetitions. On the CLI, sq workflow lint exits 1 on two consecutive runs for each of [[a]], (?i)[[a]] and (?x)[a&&b] # c, sq list exits 1, and no FutureWarning reaches stderr.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Missing body region crashes body -m; new test comment says otherwise

<!-- sq:finding:F8:body -->
**Driven, and the defect is pre-existing.** With no body region, `body -m` crashes with a raw `KeyError`, and a new test comment calls that "nothing to say".

- In a scratch squad, deleting the `sq:body` markers from a task file and then running `sq task 4 body -m "new prose"` ends in a rich traceback: `KeyError: "section 'body' not found"` from `_sections.replace_section`, exit 1. It is not a `SquadsError` message. `sq check` does not report the missing region either.
- This code path existed before the change; it is not caused by it. The new guard-agreement test excludes the state with the comment `#: The overwrite guard has nothing to say about a file with no body region at all.`. The comment is false: the guard path raises an unhandled exception.

**Fix.** In this task, reword the test comment to say what happens, or point it at the routed defect. Route the crash separately: a `SquadsError` naming the missing region, and possibly a `sq check` finding for a work item with no `sq:body` region.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-15T19:34:51Z] `python-dev` Elias Python:
  - Test comment corrected to say the missing-region write ends in an unhandled KeyError. The crash itself is not fixed here; qa is filing it.
- [2026-10-15T19:39:18Z] `reviewer` Paul Reviewer:
  - Pass 2, read: the test comment now states the unhandled KeyError. The crash has its home in BUG-1012. Closed for this task.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Import sub-status with an unnormalised target skips board debt

<!-- sq:finding:F9:body -->
**Driven, and the cause predates this task.** An import `sub-status` event written with an unnormalised target gets no board-debt findings.

- `_apply_one` returns `{target}` for a `sub-status` event, which is the raw token as written. Every other operation returns `item.id`. The board-debt pass keys on those ids, both its old filter and the new `report(only=...)`.
- In a scratch squad, `task` selects `description_present` and TASK-2 has no summary. Importing a `sub-status` event on TASK-2's ST1 prints the description warning when the target is written `TASK-2`. The same event with the target written `2`, `task-2` or `TASK-000002` imports cleanly (exit 0) and prints no warning. A `status` event with the target written `3` does print BUG-3's warning, because that path returns `item.id`.
- The behaviour is no worse than before `only=` was added, since the old filter on `i.item in touched_ids` dropped the same findings. But `only=` now decides which items are evaluated at all, so the spelling matters to more than the output.

**Fix.** Return the resolved item's `id` from the `sub-status` branch, as the `sub-body` branch already does. Add a row with an unnormalised target to the counted-member import test. This does not block the review.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-15T19:44:44Z] `reviewer` Paul Reviewer:
  - Pass 3, driven: verified in 3548f802. An import sub-status on TASK-2 reports the description finding for each of the spellings 2, task-2, TASK-2 and TASK-000002.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T19:25:48Z] `reviewer` Paul Reviewer:
  - 2026-10-15: review of TASK-1001 part one is filed. Recommended verdict: changes requested, on two medium findings. @manager
    
    - F1: an `external_id_not_in_title` pattern that matches the empty string (`x*`), or a pattern that is only a space, loads clean. It then reports every item, and at `@error` it refuses every write of the type. Refuse it at load.
    - F2: `sq import` runs every per-item member over the whole index (`_board_debt_findings`). With a backtracking pattern at `warn`, importing one unrelated item hangs after it commits. Scope the report to the touched items, and correct the writer's sentence about where the pattern runs.
    - Low: F3 says "advisory:" in an error refusal. F4's create-refusal hint names an id that was never allocated. F5 counts code points, not visible characters. F6: body_written misses a review scaffold once `target_ref` is set. Info: F7 a FutureWarning is printed on every command; F8 is a pre-existing KeyError on a missing body region, plus a test comment that misstates it.
    - Verified clean: no bundled byte changed (checked against a known positive), the gate skips `warn` members and refuses at `@error` on create, update, status and retype, the shared body predicate is equivalent to the old guard, 18 load refusals behave as documented, BUG-1003 is fixed for bare and kinded refs, tests/meta has 345 passed, there is no new import cycle, and pyright and ruff are clean.
    - Routing: F8's crash is pre-existing and needs its own owner. The full suite was not run.
- [2026-10-15T19:39:28Z] `reviewer` Paul Reviewer:
  - 2026-10-15, pass 2: F1 to F5 are Verified. F6 WontFix is accepted (home BUG-1014). F8 is Fixed (the test comment is corrected; the crash is in BUG-1012). F7 is reopened at medium: sq workflow lint prints spec OK and exits 0 for [[a]] while every other command refuses it, because re caches compiled patterns and warns only on the first compile. New F9 (info, cause predates this task): an import sub-status with an unnormalised target skips board debt. The review stays ChangesRequested on F7 alone; that fix is small. @manager
- [2026-10-15T19:44:52Z] `reviewer` Paul Reviewer:
  - 2026-10-15, pass 3: F7 and F9 are Verified in 3548f802 and nothing blocking remains, so the review is moved to Approved on the manager's instruction. Final state: F1 to F5, F7 and F9 Verified; F6 WontFix (BUG-1014); F8 Fixed (crash in BUG-1012). I did not run the full suite. @manager
<!-- sq:discussion:end -->

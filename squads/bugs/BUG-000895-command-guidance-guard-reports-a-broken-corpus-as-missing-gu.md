---
id: BUG-895
sequence_id: 895
type: bug
title: Command-guidance guard reports a broken corpus as missing guidance
status: Verified
author: qa
assignee: python-dev
priority: medium
severity: medium
refs:
- BUG-894
- MILE-867:targets
created_at: '2026-09-03T07:08:03Z'
updated_at: '2026-09-09T14:43:37Z'
---
<!-- sq:body -->
## Summary

**Driven.** The command-guidance guard's corpus-integrity floor is calibrated against an *empty*
carrier, but the failure shape that actually occurs is a *frontmatter-only* one. A corpus built by
reading the on-disk skill `.md` files whole passes every integrity assertion, and the broad
guidance assertion then reports shipped commands as unguided when the truth is that the corpus is
broken. That sends the next reader to write guidance which already exists.

A third part travels with it: the note recording the fix credits the character floor with catching
this. It does not. A different change in the same fix does.

## Why the shape occurs at all

**Read.** A skill definition renders at read time; the stored `.md` carries frontmatter plus an
empty `sq:body` region. So "read the skill files" — the obvious way to build an
agent-facing corpus, and the way it was in fact built once — yields files that are almost entirely
frontmatter and carry no guidance at all. This is not a hypothetical corpus, it is the one that
produced a false measurement.

## The floor does not fire

**Driven.** `_MIN_CARRIER_CHARS` is 200, documented as "an order of magnitude under the smallest
real one, so it fires on an empty or near-empty body and never on a short but genuine render".

Measured on two independent corpora:

- this repository's own squad: twelve files, smallest **349 bytes** (`sq-contract`), then 353, 372,
  377, 377
- a fresh `sq init --default-names` scratch squad: smallest **327 bytes** (`sq-bug`), largest 579

Every one of them clears 200. The marker-delimited body inside them is empty — that part *would* be
caught — but a whole-file read never reaches the body.

Driven through the shipped guard chain by substituting the corpus builder in-process, both readings:

| corpus reading | carrier sizes | `_agent_facing_corpus` | known-positive check |
| --- | --- | --- | --- |
| body region only | 0-1 chars | **refuses** (under-200 carriers) | n/a |
| whole file (frontmatter incl.) | 327-579 chars | **builds, 12,982 chars** | **passes** |

The known-positive check passes because its floor is `len(corpus) > 10_000` and the `CLAUDE.md`
managed region alone is 8,492 characters, carrying `create`/`comment`/`tree`/`check`/`discussion`
on its own. So one genuine carrier masks twelve broken ones.

For contrast, the smallest *genuine* render is 2,448 characters — the floor has an order of
magnitude of headroom it is not using.

## The broad assertion has no controls, so it misattributes

**Read.** `test_every_top_level_command_is_named_in_the_agent_facing_corpus` ends in
`assert not unnamed` and counts nothing alongside it. On the whole-file corpus above it therefore
reports a list of shipped commands as unguided.

That is the wrong finding, and it is wrong in the expensive direction: it names real commands and
points at real files, so the reader's natural next step is to add guidance to a corpus that already
contains it. An assertion that fails loudly with a plausible-but-false cause costs more than one
that does not fire.

**Driven**, the same guard's *other* new assertion does attribute correctly on the same corpus:

```
controls absent — the corpus is broken: {'repair': 0, 'graph': 0, 'renumber': 0}
```

Counting controls in the same assertion as the subject is what distinguishes "this is missing" from
"nothing is here". The broad assertion does not do it.

## The recorded mechanism is the wrong one

**Read**, the fix note: the `_agent_facing_corpus` size assertion "is the assertion that would have
caught the stub corpus — the on-disk skill `.md` bodies, empty because a definition renders at read
time".

**Driven:** it is not. On the whole-file reading the floor does not fire, and neither does the
known-positive check; the controls-in-the-same-assertion change is what catches it. The claim holds
only for a body-region read, which is not the reading that failed.

This part matters independently of the code. The floor now carries a comment asserting it guards a
failure it does not guard, so the next person to look has been told the question is settled. That is
how a gap survives a review — not because nobody checks, but because the note says checking is done.

## Expected vs actual

- **Expected:** when the corpus is broken, every assertion over it says so. When guidance is
  genuinely missing, the assertion says that instead. The two are distinguishable without rerunning
  the measurement by hand.
- **Actual:** one assertion distinguishes them; the broad one reports the broken corpus as missing
  guidance; and the integrity floor that is supposed to prevent both is calibrated for a shape that
  no longer occurs.

## Not claimed

- No fix is proposed. Whether the remedy is recalibrating the floor, giving the broad assertion its
  own controls, extracting the body region rather than the file, or some combination, is a judgement
  about what the guard should assert.
- Nothing is presently broken: the shipped corpus builder renders through the service and cannot
  produce this corpus by accident today. This is a guard-quality defect, not a live false report.

## Severity

Judged **medium**.

Not low: the failure mode is a *manufactured* finding rather than a missed one, and the manufactured
finding is actionable-looking — it names real commands, so the cost is work done against a false
premise. It is on the gate the team relies on to know that every shipped command is discoverable,
which is the exact inference this class of bug keeps invalidating. And the recorded mechanism being
wrong means the next reader has positive reason not to re-check.

Not high: it requires a change to the corpus builder to become reachable, so nothing is
misreporting today; no shipped behaviour, data or exit code is affected; and one assertion in the
same file already attributes correctly, so the information needed to diagnose it is present in a
failing run.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-08T14:47:52Z] Elias Python:
  - Fixed, in `tests/meta/test_every_cli_command_is_named_in_agent_guidance.py`. Scope stayed inside that one file — this is a guard-quality defect, not a live corpus-builder bug.
    
    **Recalibration.** `_MIN_CARRIER_CHARS` 200 → 1000. 200 was calibrated against an empty carrier, which no real corpus builder produces; the shape that occurs is frontmatter-only. Driven both ways in-process (substituting `_generated_skill_bodies` with a reading of the real on-disk skill `.md` files):
    
    | corpus reading | carrier sizes (this repo) | at floor=200 | at floor=1000 |
    |---|---|---|---|
    | whole-file (frontmatter incl.) | 377–611 chars | builds, 13,757 chars — passes | **12 carriers refused as stubs** |
    | genuine render (`_generated_skill_bodies` as shipped) | smallest 1,836 chars (`sq-decision`) | n/a | passes clean, no stub |
    
    1000 sits with headroom both sides: 1.6× above the worst measured stub, 1.8× below the smallest measured genuine render (this repo's numbers have drifted up since filing — was 2,448 at filing time, now 1,836 — the floor still clears it with margin).
    
    **Frontmatter-only case, before/after, through the real shipped `_agent_facing_corpus()`** (not a reimplementation — monkeypatched `_generated_skill_bodies`, called the real function):
    - Before (floor=200): no assertion fires; corpus builds; `test_every_top_level_command_is_named_in_the_agent_facing_corpus`'s old logic (no controls) reports `['graph', 'import', 'override', 'reflog', 'renumber', 'repair', 'search', 'workload']` as unguided — reproduces the bug exactly, all 8 are real guided commands.
    - After (floor=1000): `_agent_facing_corpus()` raises `AssertionError: carrier(s) rendered under 1000 characters: [...12 skill carriers...] — the corpus is broken, not the guidance` before the guidance assertion ever runs.
    - Healthy corpus, both before and after: green (`uv run --all-extras pytest tests/meta/test_every_cli_command_is_named_in_agent_guidance.py` → 6 passed).
    
    **Falsification of the new check, both directions**, same session, same real functions:
    1. Shipped fix (floor=1000) + frontmatter-only corpus → integrity assertion fires. Good.
    2. Broke it: reverted `_MIN_CARRIER_CHARS` to 200 in-process → integrity assertion no longer fires; **also drove the proposed controls layer against this exact corpus and it does NOT catch it either** — `create`/`comment`/`tree`/`check`/`discussion` are all present, masked by the genuine `CLAUDE.md` region's 8,449 chars — so it falls through to the same false `unguided` list as before. This proves the floor, not the controls, is load-bearing for this specific shape.
    3. Restored floor=1000 → fires again.
    
    So the fix has two layers and they are not redundant: the recalibrated floor catches *this* shape; the new controls on the broad assertion (added regardless, mirroring what `test_the_mutation_audit_command_is_named_as_an_invocation` already does for `reflog`) are a second line of defense for whatever broken-corpus shape the floor's specific threshold doesn't happen to catch — which per (2) above is not decorative, it's just not what stops this particular shape.
    
    **Corrected credit note.** The fix-note on BUG-894 credited the character floor (at 200) with catching the frontmatter-only shape; it did not, and per (2) above the controls-alone wouldn't have either — masked by `CLAUDE.md`. What actually closes the gap here is recalibrating the floor itself to sit above the measured stub range. The module docstring (lines ~65-86) is rewritten to state this precisely: body-only stubs (0-1 char) were always caught by even the old floor; frontmatter-only stubs (327-611 char) needed the raise to 1000; and the controls addition is documented as an independent second layer, not as the mechanism for this shape.
    
    **Selection.** Diff touches one file only, no src/ change (no `_specs/`, `_rendering/templates/`, `_cli/` floor triggered). Grep + whitespace-collapsed scan (`identifier_wrap_scan.py`, validated against a known positive in the same file first) for the names I introduced/changed — `_MIN_CARRIER_CHARS`, `_KNOWN_POSITIVE_TERMS`, `_agent_facing_corpus` — across all of `tests/`: only this one file references them, no wrapped hits elsewhere. Ran `tests/meta` (282 passed) and `tests/integration` (709 passed, 6 skipped) per the standing floor — both 0 `FAILED`. Gates clean: pyright 0 errors, ruff check all passed, ruff format 654 files already formatted. `sq check` clean. Did not run the full suite.
    
    **On the dossier itself:** nothing wrong in the analysis. Numbers have drifted with the repo (stub sizes now 377-611 vs the 327-579/349-377 measured at filing; genuine minimum now 1,836 vs 2,448) but that's time, not error — the shape and the conclusion both hold.
    
    @qa for verification.
- [2026-09-08T14:50:25Z] Catherine Manager:
  - Full suite green as the authoritative gate: 4976 passed, 12 skipped. The fix is the recalibration, and the falsification is what makes it trustworthy: the dev proved the floor -- not the known-positive controls -- is what catches this shape, because the controls are masked by the genuine CLAUDE.md region which alone carries all five control terms. So the controls are documented as an honest second layer for a different broken-corpus shape rather than taking credit here. That is the same false-credit error this bug was partly about, caught one level down.
- [2026-09-09T14:42:16Z] Mara Tester:
  - Verified independently, not just re-run. Drove the frontmatter-only corpus myself (whole-file read of the 12 on-disk skill .md files, monkeypatching _generated_skill_bodies in-process against the real, shipped _agent_facing_corpus()): all 12 stubs land at 377-611 chars, and the integrity floor fires first — AssertionError naming all 12 as under-1000-char carriers, "the corpus is broken, not the guidance" — before the guidance assertion ever runs. tests/meta/test_every_cli_command_is_named_in_agent_guidance.py: 6 passed, independently re-run.
  - Floor-vs-controls claim, independently reproduced (not read off the transcript): with the floor forced back to 200 over the same frontmatter-only corpus, it builds clean at 13,757 chars; the controls layer (_KNOWN_POSITIVE_TERMS) reports all 5 present — masked, as claimed, by the genuine CLAUDE.md managed region alone (8,449 chars) carrying all 5 on its own (the 12 stubs together carry only 3 of 5). The broad assertion then misreports exactly [graph, import, override, reflog, renumber, repair, search, workload] as unguided — matches the dev handback number-for-number. So: the floor is load-bearing for this shape, the controls are an honest second layer for a different one, and the corrected module docstring/credit note holds.
  - Headroom verdict on the 1000 magic number: independently measured current genuine-render floor at 1,836 chars (sq-decision) — 1.8x margin above 1000, 1.6x above the worst stub (611). That is real headroom against today shape, but it is a snapshot constant with no structural link to render content, and the min has been shrinking (2,448 -> 1,836 over this project). Nothing currently watches the gap narrowing — if a future terse rewrite of a skill body pushed a genuine render under 1000, this guard would misreport a real, guided skill as "the corpus is broken" (a false-fire, the inverse defect of the one this bug fixed, not caught by anything today). Worth a periodic re-measure, not a blocker.
- [2026-09-09T14:43:37Z] Catherine Manager:
  - Verified. Carrying one known-open rather than calling it resolved: the 1000-char floor is a point-in-time constant with no structural link to content and no drift alarm, and the minimum genuine render has been shrinking (2,448 at filing, 1,836 now). If a future terse rewrite pushed a real skill under 1000 the guard would misreport it as a broken corpus -- the false-fire inverse of the bug it just fixed, uncaught by anything today. QA flagged it; recording it here so a periodic re-measure has a home.
<!-- sq:discussion:end -->

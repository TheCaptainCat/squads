---
id: BUG-895
sequence_id: 895
type: bug
title: Command-guidance guard reports a broken corpus as missing guidance
status: Open
author: qa
priority: medium
severity: medium
refs:
- BUG-894
- MILE-867:targets
created_at: '2026-09-03T07:08:03Z'
updated_at: '2026-09-03T07:08:58Z'
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
<!-- sq:discussion:end -->

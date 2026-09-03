---
id: BUG-894
sequence_id: 894
type: bug
title: sq reflog is named in no generated surface; the guard credits a word
status: Verified
author: qa
assignee: python-dev
priority: medium
severity: medium
refs:
- BUG-872
description: sq reflog appears in no generated agent surface; the naming guard credits
  it via one ordinary-noun sentence.
created_at: '2026-09-02T14:28:22Z'
updated_at: '2026-09-03T07:09:15Z'
---
<!-- sq:body -->
## Summary

**Driven.** `sq reflog` is named in no surface squads generates. The naming guard passes it because its matcher credits a command by any prose use of its name, and one sentence in the `squads` skill uses "reflog" as an ordinary noun. `sq reflog` as an invocation appears nowhere in the generated corpus.

This is the same position the merge-collision remedy was in before it was fixed: a command whose guidance lives in human-facing files and in none of the carriers an agent reads. It is also a second instance of a limitation the guard's own docstring already records for one command, which makes the honest reading of a green run narrower than it looks.

## Environment

**Driven.** `squads 0.14.0`, branch `release/0.14` at `4214813`, bundled workflow spec, no `.overrides/`. Corpus taken from a fresh scratch squad (`sq init --default-names` plus one developer role, so the roster matches the guard's pinned fixture), nested in its own temp directory. Renders taken with `FORCE_COLOR` unset, `NO_COLOR=1`, `COLUMNS=400`; ANSI stripped character-wise in Python. Every exit code read from a bare command, never through a pipe.

## The measurement

**Driven.** Corpus is squads' generated output only: the twelve skill bodies rendered with `sq skill <slug> show` (all twelve exit 0, each asserted over 1000 characters before use) plus that squad's `CLAUDE.md` managed region taken by its `squads:start`/`squads:end` markers and asserted non-empty. **13 carriers, 1318 lines, 65,320 characters.**

Invocation-form counts over that corpus, with controls run in the same command so a zero is never trusted alone:

```
grep -c "sq reflog"    corpus.txt   ->  0
grep -c "sq repair"    corpus.txt   ->  4      (control)
grep -c "sq graph"     corpus.txt   ->  4      (control)
grep -c "sq renumber"  corpus.txt   ->  2      (control — the command already fixed)
grep -c "sq adopt"     corpus.txt   ->  0
```

Word-boundary counts — what the guard actually matches on:

```
reflog   1
adopt    2
```

The single line crediting it, in the `squads` skill:

```
normal; the reflog records a reconstructable removal line that explains each gap.
```

That sentence explains what a gap in the id sequence means. It does not name a command, give an invocation, or tell a reader that a command exists.

## Why this is the known limitation, not a new one

**Read**, `tests/meta/test_every_cli_command_is_named_in_agent_guidance.py`, which states the property and names one instance:

> Matching is by name, not by invocation — a case-insensitive word-boundary search over the corpus. That is deliberately generous: a command whose name is also an ordinary English word (`list`, `show`, `check`, `guide`) is credited by any prose use of that word, so this guard proves a name is *absent*, never that the guidance around a present name is any good.

> That generosity is live rather than hypothetical, and `adopt` is the measured case: it is credited by two uses of the ordinary English verb in the managed section's impersonation paragraph, while the string `sq adopt` appears in no generated surface.

`reflog` is a second measured case of exactly that, and the guard does not record it: **read**, `grep -n "reflog"` over that file returns nothing (exit 1), against a control of 6 hits for `renumber|adopt` in the same file. It carries no `_UNGUIDED_BY_DESIGN` entry either, so nothing states a judgement that an agent should not run it — it simply is not noticed as unguided.

The difference from `adopt` matters and is why this is filed rather than shrugged at. `adopt` has a ruling behind it: it is bootstrap-class, the same class as `init`, and the guard's docstring explains that an entry for it would fail the staleness assertion instead of recording the ruling. No such judgement exists for `reflog`. It is not exempt by decision; it is passing by coincidence.

## The guidance exists — in the wrong carrier

**Driven**, the same shape the earlier report established. `sq reflog` is named in five human-facing files and zero generated ones:

```
docs/overrides.md   1
docs/stability.md   1
docs/workflow.md   12
README.md           1
CHANGELOG.md        4
```

Control, same loop, same files: `sq repair` returns 15/15/6/3/1/4/4/5/19 across nine files — so the loop and the pattern both work, and the zero on the generated side is a real absence.

## Why it matters

**Read**, `sq reflog --help`: "Show the operation reflog — a chronological log of every mutating sq command", filterable by item, actor and op.

**Inferred.** That is the surface an agent would use to audit what another agent did to the corpus — which mutations landed, by whom, against which item. An agent that cannot discover the command cannot perform that audit, and the fallbacks it would reach for instead (git history, item counts) do not carry actor or op. The consequence is a diagnostic an agent has but cannot find, not a data-loss path.

## What is not claimed

- No fix is proposed. Whether the remedy is a line of guidance, an `_UNGUIDED_BY_DESIGN` entry with a reason, or a tightening of the matcher to an invocation form is a judgement about what the guard should assert, and the guard's docstring already records that tightening the match "would withdraw credit from several more commands whose names double as prose, each of which is its own question" — so that route is not a small change and is deliberately not being proposed here.
- The guard is not broken. It does what it documents. What is inaccurate is the inference that a green run means every shipped command is guided; it means every shipped command's *name* appears, which for at least two commands is not the same thing.

## Method note — an exit-code trap worth briefing, sibling of the pipe trap

**Driven**, during the verification pass that produced this report; recorded here because it is durable and it cost a false reading.

We already brief that a pipeline's exit code is the last element's, so `cmd | head; echo $?` reports `head`. There is a second shape with the same failure and no pipe in it:

```
grep -q PAT "$f"; echo "$(basename "$f") exit=$?"      # WRONG
```

This reports **`basename`'s** status, not grep's. Bash expands the `echo` word left to right, so the command substitution runs *before* `$?` is expanded and overwrites it. Six clean files read as six matches — an inverted result, which is worse than a lost one, because it manufactures findings rather than hiding them.

The fix is to capture the status on the line immediately after the command, before any substitution can run:

```
grep -q PAT "$f"; rc=$?
name=$(basename "$f")
echo "$name exit=$rc"                                   # RIGHT
```

The general rule: `$?` is valid only until the next command runs, and a command substitution inside the very argument you are printing counts as the next command.

**One more from the same pass, on the corpus rather than the pattern.** Validating a matcher against known positives is necessary and not sufficient. The first build of the corpus above read the on-disk `squads/agents/skills/*.md` files, whose bodies are empty stubs because a skill definition is rendered at read time. Over that corpus the matcher returned 0 for `renumber`, `graph`, `import`, `override`, `repair` and `search` while still returning non-zero for `create` — so the known-positive check passed and the zeros were still false. Assert the corpus's size as well as the pattern's behaviour; the assertions in the reproduction above (each render over 1000 characters, the managed region non-empty) exist for that reason.

## Severity

Judged **medium**.

Not low: the condition is that a shipped command is undiscoverable to every agent, which is the same defect class already accepted as worth fixing for the collision remedy; the command is the one an agent would use to audit another agent's mutations, which is a real and recurring need here; and the gate that exists to catch precisely this passes it, so the absence is not merely present but certified against.

Not high: nothing is broken, lost or corrupted, and no workflow fails — the command works and is documented for humans; the earlier report of this class had a hand recovery to show for it and this one has no incident behind it; and `reflog` is a read-only diagnostic, so the cost of not finding it is a slower or shallower audit rather than an unrecoverable state.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T14:29:34Z] Mara Tester:
  - Filed off the second residue from the BUG-872 verification. Re-measured from scratch for this report, not carried over.
    
    - `sq reflog` invocation count in the generated corpus is 0, against same-run controls of `sq repair` 4, `sq graph` 4, `sq renumber` 2. Word-boundary `reflog` is 1 — a single sentence using it as an ordinary noun to explain id-sequence gaps.
    - This is the limitation the guard's own docstring records for `adopt`, appearing a second time. The difference is that `adopt` has a ruling behind it (bootstrap class, and an entry would fail the staleness assertion); `reflog` has none — it carries no `_UNGUIDED_BY_DESIGN` entry and the guard file does not mention it at all (grep exit 1, control 6 hits for `renumber|adopt`).
    - Same wrong-carrier shape as BUG-872: named in five human-facing files, zero generated ones. Control loop over the same files finds `sq repair` in nine.
    - The guard is not broken and I am not proposing the matcher be tightened — its docstring already explains why that is its own question. What is inaccurate is reading a green run as "every shipped command is guided".
    
    Severity medium, priority medium. The command an agent would use to audit another agent's mutations is undiscoverable, and the gate built to catch exactly this certifies against it — but nothing is broken or lost, there is no incident behind it, and it is a read-only diagnostic.
    
    Two method notes are in the body rather than only in a handoff, per @manager:
    - `grep -q PAT "$f"; echo "$(basename "$f") exit=$?"` reports basename's status, not grep's — the command substitution runs before `$?` expands. Six clean files read as six matches. Capture `rc=$?` on the next line, before any substitution. Sibling of the pipe trap we already brief.
    - Validating a matcher against known positives is necessary and not sufficient: my first corpus build read the on-disk skill `.md` stubs (bodies render at read time) and returned 0 for six commands while `create` still hit, so the known-positive check passed and the zeros were false anyway. Assert the corpus size too.
    
    @tech-lead for triage.
- [2026-09-02T14:44:36Z] Elias Python:
  - Fixed. `sq reflog` has real guidance now, in the carrier that reaches the most agents per edit, and the guard asserts it at invocation strength so it cannot fall back onto the word.
    
    **Carrier: `workflow_static.md.j2`**, a new `## Operation reflog` section. Same choice as the collision guidance, for the same reason and a second one. The cheatsheet is included by both the `squads` skill body and the AGENTS.md section, so one edit reaches every agent's session-start read plus `sq workflow`. And it is the *right* reader: `migrate` went in the managed region because its reader has not gone looking, whereas an agent reaches for the reflog precisely when they have gone looking — work arrived already done and they need to know what changed. The cheatsheet is where they look. The section gives the audit framing (the question the item files and `sq check` cannot answer, because they carry the state reached rather than the moves that reached it), the five filters, and two caveats that matter to an auditor: the log is advisory, and a squad with no reflog prints empty results rather than an error — so an empty run is never on its own evidence that nothing happened.
    
    The one crediting sentence is now an invocation too: the sequence-gap line reads "`sq reflog` carries the removal line that reconstructs what each gap was" instead of using the bare noun.
    
    **Measured, before and after**, on a corpus rebuilt from the guard's own helpers — 13 carriers, every one asserted over 1000 chars before use, ANSI absence asserted:
    
    | | before | after |
    |---|---|---|
    | `sq reflog` | 0 | 6 |
    | `sq repair` (control) | 4 | 4 |
    | `sq graph` (control) | 4 | 4 |
    | `sq renumber` (control) | 2 | 2 |
    | word-boundary `reflog` | 1 | 7 |
    
    Controls unmoved either side, so the change is the subject's and not the corpus's. Driven again through the shipped surfaces rather than only the fixture: `sq workflow` and `sq skill squads show` each name it on six lines.
    
    **The guard.** Two changes, both narrow:
    
    - `test_the_mutation_audit_command_is_named_as_an_invocation` asserts `sq reflog` appears as an invocation, with `repair`/`graph`/`renumber` counted in the same assertion so a zero on the subject alongside zeros on the controls reports a broken corpus rather than missing guidance. Falsified: reverting only the template fails it with the controls reading 4/4/2. It is deliberately one targeted assertion and **not** the general tightening of the matcher — that would withdraw credit from several commands whose names double as prose, which is its own question, exactly as the guard's docstring says.
    - `_agent_facing_corpus` now asserts its own size: a carrier count floor, and a refusal of any carrier that renders near-empty. That is the assertion that would have caught the stub corpus — the on-disk skill `.md` bodies, empty because a definition renders at read time — where the known-positive check passed and every zero was false anyway.
    
    The module docstring records `reflog` as the second measured case of the name-matcher's generosity and what was decided about it, so the difference from `adopt` (which has a bootstrap-class ruling behind it, and whose entry would fail the staleness assertion) is on the record rather than left to be re-derived. No `_UNGUIDED_BY_DESIGN` entry: the judgement went the other way.
    
    **Regeneration owed to the operator**, not run here: this touches a bundled template, so `tests/meta/test_override_manifest_and_stamp_freshness.py` fails on a stale hash for `workflow_static.md.j2`, and four sibling rebuild-count tests fail off that same one drift. Confirmed as manifest-only rather than assumed — reverting just the template makes all 35 pass. The rest of the suite is green.
    
    @qa for verification.
- [2026-09-02T15:42:05Z] Mara Tester:
  - Verified. Re-measured independently — my own corpus build, not the guard's helpers — and then cross-checked against the guard.
    
    **Corpus, with its size asserted before any count was trusted** (my own trap, and the reason the first pass was wrong). Fresh scratch squad, `sq init --default-names` plus one dev role. 13 carriers: the twelve skill bodies via `sq skill <slug> show` (all exit 0) plus the `CLAUDE.md` managed region taken by its `squads:start`/`squads:end` markers. Every carrier asserted over 1000 chars and ANSI-free; smallest real render 2448 chars. **13 carriers, 1342 lines, 66,546 chars.**
    
    The stub trap re-confirmed concretely: the on-disk `squads/agents/skills/*.md` files are 327-579 chars and their marker-delimited bodies are **empty** — a definition renders at read time. That is the corpus that gave the false zeros.
    
    **Counts, before and after, driven on both** (pre-fix source extracted read-only via `git archive 0c326910^ src` and run under `PYTHONPATH` shadowing, including a pre-fix `init` so the managed region was its own):
    
    | | before | after |
    |---|---|---|
    | `sq reflog` | 0 | 6 |
    | `sq repair` (control) | 4 | 4 |
    | `sq graph` (control) | 4 | 4 |
    | `sq renumber` (control) | 2 | 2 |
    | word-boundary `reflog` | 1 | 7 |
    
    Pre-fix corpus measured 1319 lines / 65,321 chars against the 1318 / 65,320 in the body — the original measurement reproduces. Controls unmoved on both sides, so the movement is the subject's. The managed region is byte-identical pre/post (`cmp` rc=0); the whole delta is the `squads` skill, 22,582 to 23,811 chars. The one crediting sentence is now an invocation.
    
    **Shipped surfaces, not just the fixture:** `sq workflow` and `sq skill squads show` each name it on 6 lines, both exit 0.
    
    **The guidance is truthful — I drove every invocation it advertises.** `sq reflog`, `--tail 0`, `--item`, `--actor`, `--op ... --since`, `--json`, `--tree`: all exit 0. And the caveat it makes a point of: on a squad whose `.reflog.jsonl` I deleted, `sq reflog` exits **0** printing "no reflog entries", not an error — so the "an empty run is not evidence nothing happened" warning is accurate rather than decorative.
    
    **The guard's new assertions, falsified in both directions.** Running the *shipped* guard against the pre-fix templates (PYTHONPATH shadow, current `CLAUDE.md` supplied since the region is byte-identical) fails exactly one test:
    
    ```
    FAILED test_the_mutation_audit_command_is_named_as_an_invocation
    AssertionError: no generated surface names `sq reflog` as an invocation ... (controls: {'repair': 4, 'graph': 4, 'renumber': 2})
    ```
    
    The control assertion passed first, so the failure is correctly attributed. Driving the shipped function directly on synthetic corpora: controls zero + subject zero raises "controls absent - the corpus is broken"; controls present + subject zero raises the missing-guidance message; both present passes. The broken-corpus branch works as claimed.
    
    `tests/meta/` is 279 passed / 0 failed, so the manifest regeneration that was owed has landed.
    
    One correction to the fix note, in the body as a separate comment - the credited mechanism is not the one that does the work.
- [2026-09-02T15:42:25Z] Mara Tester:
  - One correction, recorded because the fix note credits the wrong mechanism. It does not change the verdict — the bug is verified — but the reasoning behind one assertion is not sound, and someone will rely on it.
    
    The note says the new `_agent_facing_corpus` size assertion "would have caught the stub corpus". **Driven: it depends entirely on how the stub corpus is read, and for the shape that actually fooled me it does not fire.**
    
    `_MIN_CARRIER_CHARS` is 200. The on-disk skill files are 327-579 chars — all comfortably above it. Two readings, both driven through the shipped guard chain by substituting the corpus builder in-process:
    
    - **Body-region read** (correct extraction): bodies are 0-1 chars, refused by the 200-char floor. Claim holds.
    - **Whole-file read** (frontmatter included — the shape my first pass used): corpus builds at **12,982 chars, no integrity assertion fires**. `test_the_matcher_is_validated_against_known_positives` also passes: its `len(corpus) > 10_000` floor is cleared, because the managed region alone is 8,492 chars and carries the known positives. So the assertion credited with catching this does not catch it, and neither does the known-positive check.
    
    What actually catches it is the **other** change: `controls absent — the corpus is broken: {'repair': 0, 'graph': 0, 'renumber': 0}`. The controls-in-the-same-assertion idea is doing the work; the character floor is not.
    
    Two things follow, both for whoever touches this next rather than for this release:
    
    - The 200-char floor is calibrated against *empty*, not against *frontmatter-only*. The smallest genuine render is 2448 chars, so the floor has an order of magnitude of headroom it is not using. It is not wrong, it is just not the guard the comment claims.
    - The controls pattern only protects the assertions that carry controls. `test_every_top_level_command_is_named_in_the_agent_facing_corpus` — the broad one — has none, so on a whole-file stub corpus it would still return its zeros as findings.
    
    Not filing this; @manager it is yours to decide whether it is worth an item. Nothing here is a regression and the shipped behaviour is correct in every state I drove.
- [2026-09-03T07:09:15Z] Mara Tester:
  - Filed as **BUG-895** (medium), `related` to this bug and `targets` MILE-867 for 0.15, per op-pierre's ruling. My earlier comment said "not filing" — superseded; comments do not survive as work.
    
    One measurement refined in the filing rather than carried across loosely: the floor clears on *both* corpora, not just the one I measured. This repository's own squad has a smallest on-disk skill file of **349 bytes** (`sq-contract`, then 353/372/377/377); a fresh `sq init --default-names` scratch squad's smallest is **327** (`sq-bug`, largest 579). `_MIN_CARRIER_CHARS` is 200, so every file on either corpus clears it. The finding does not depend on which squad you measure.
    
    The filing carries all three parts: the floor calibrated for *empty* rather than *frontmatter-only*, the broad assertion having no controls and so misattributing a broken corpus as missing guidance, and the note on this bug crediting the floor with a catch the controls change actually makes.
<!-- sq:discussion:end -->

---
id: ADR-947
sequence_id: 947
type: decision
title: 'Partial reads: a distinct exit code and an omissions report'
status: Accepted
author: architect
refs:
- REV-943:addresses
- FEAT-690:addresses
- ADR-427
- ADR-459
description: A usable-but-short --json result exits its own code 4 and names what
  it omitted in one JSON line on stderr; payload shapes unchanged.
created_at: '2026-09-14T14:08:49Z'
updated_at: '2026-09-15T07:55:07Z'
---
<!-- sq:body -->
## Context

REV-943 F2/F3 found the two clients diverging on a degraded read: the VS Code extension
under-reports a memory pool that holds an unreadable file as a *smaller* pool, and blanks the
whole board when one notice is unreadable, while `sq ui` — reading in-process — shows the
readable entries plus a "listing partial" line in both cases. op-pierre ruled the CLI contract
gets fixed in this release rather than deferred. What the ruling left open is the shape.

**The inventory is wider than two commands.** `_cli/_main.py::_report_unreadable` is already a
shared helper, and the commands that hand back a usable-but-short result are `sq inbox`,
`sq search`, `sq board list`, `sq memory <role> list` and `sq memory <role> search`. Four of the
five exit `1`; the two memory commands exit `0`. So this is not "two commands disagree" — it is
one contract with one violator.

**The posture is already documented, and memory is out of contract.** `docs/faq.md`'s exit-code
table assigns to code `1` "a command that finished only partly and named what it could not read",
and states outright that "a degraded read is a non-zero exit … a caller testing `$?` needs to see
that the answer is short". `_services/_results.py`'s `UnreadableItems` says the same in the code:
"one unreadable file degrades that file, never the answer … callers pair this with a non-zero exit
so a script still learns the answer was partial." `sq memory <role> list --json` exiting `0` on a
degraded pool is a defect against a written contract, not a second opinion about it.

**What `1` cannot say.** The extension's behaviour on the board is *compliant*, not buggy:
ADR-427 §2 binds the client to "map by the frozen table: … `1`/other runtime (show stderr)", and
`1` is the code for "squads could not complete what you asked" — a corrupt index, a schema
mismatch, an unknown ID, all of which leave stdout empty or meaningless. A client that parses
stdout after seeing `1` would be reading garbage most of the time. The defect is that `1` conflates
"here is nothing" with "here is most of it": the client has no way to tell them apart, so the
conservative reading is the only safe one, and the conservative reading blanks the board.

**Three constraints bound the answer.**

- *The payloads have nowhere to put a field.* Both shapes are bare JSON arrays
  (`_cli/_memory.py::list_memories`, `_cli/_board.py::list_notices`), as are `inbox` and `search`.
  ADR-459 records that convention deliberately ("existing `--json` read surfaces … are all bare
  JSON arrays of flat objects"). There is no top-level object to add a key to, so "just add a
  field, Tier 3 allows additions" is not available here: the only payload route is changing the
  top-level type from array to object, which is the retype Tier 3 forbids.
- *The exit-code table is a separate frozen contract* (`docs/stability.md`, `docs/faq.md`) with no
  code for a complete-as-far-as-it-got result.
- *No per-command knowledge in clients.* ADR-427 §2 makes the client a pure consumer of the frozen
  shapes and the documented table. Teaching one adapter that `board list` exit `1` is survivable
  is exactly the coupling that decision forbids, and would have to be re-invented by every future
  client.

## Decision

### 1. The class this binds

A **partial result** is what a command produces when its payload is valid and in its frozen shape,
but entries are missing because the corpus could not be fully read.

The membership test is objective: *does the command emit a result payload that a caller is meant to
consume, and can that payload come back short?* Today that is `sq inbox`, `sq search`,
`sq board list`, `sq memory <role> list`, `sq memory <role> search`, and it binds every listing
added later with the same property — this is a contract for the class, not a patch for two members.

Outside the class, and staying as they are:

- `sq check` converts an unreadable file into an error-level issue and exits `3`. That is correct
  and must not change: a clean `check` over a partly-read corpus is a *false* clean, so the
  omission has to become a finding rather than a caveat on a good answer.
- `sq repair` and `sq migrate up` emit a human report of a mutation, not a result payload. Their
  non-zero exit means "the corpus still needs attention", which is a different sentence; they keep
  exit `1`.

### 2. Exit code `4` — the result is incomplete

The frozen table grows a fifth row. `4` means: **the command did what was asked, stdout carries a
valid payload in its documented shape, and entries are missing.**

- Precedence: `1`, `2` and `3` outrank `4`. `4` is emitted only when the command would otherwise
  have exited `0`, so a partial result never masks a more specific outcome.
- The code does not depend on `--json`. A code whose value changed with an output flag would be
  indefensible; human mode returns `4` on the same condition.
- Consumer rule, and the reason for a new code rather than a reused one: `4` is the one bit that
  says *stdout is worth parsing*, available to a shell with nothing to parse. Every existing
  consumer that branches `0/1/2/3` and treats anything else as an error degrades to today's
  conservative behaviour — loudly, never with a wrong answer. ADR-427 §2's mapping rule needs a
  new row, not an exception.

### 3. The omissions report

Under `--json`, a command in the class writes to **stderr** a single compact line holding one JSON
object:

```
{"omitted":[{"code":"unreadable","source":"<identifying token>","message":"<human sentence>"}]}
```

- **`omitted`** — one entry per thing the result leaves out. The report is written only when the
  list would be non-empty, so its presence is the detail signal; a consumer treats an absent report
  and an empty `omitted` identically. There is no top-level `partial` boolean: it is exactly
  "`omitted` is non-empty", and the exit code already carries that bit for callers that cannot
  parse.
- **`code`** — the machine class of the omission. `unreadable` is the only value the bundled
  producers emit today. The set is open and grows additively, and the binding rule is what keeps it
  growable: *a consumer that does not recognise a code still treats the entry as "part of the
  result is missing"*. Nothing branches on the value to decide whether the result is partial.
- **`source`** — the thing that could not be read, as squads identifies it: an item ID where one is
  known, otherwise a squad-relative path. It is a display token; a consumer must not parse it.
  Producers must supply it **separately** from `message` rather than embedding it in the sentence,
  which is a change from today (`_memory/_store.py` and `_board/_store.py` both hand back a single
  pre-composed string).
- **`message`** — the human sentence, the same text human mode prints.
- Every key is present on every entry, `null` for absent, matching the convention the workflow
  catalogs already set.
- The report is a top-level **object**, not a bare array, precisely because the payload shapes are
  bare arrays and that is what left them with nowhere to grow. A new machine surface starts with
  room for additive keys.
- It never goes to stdout. `print_json_clean` stays the only stdout writer, and stdout stays exactly
  one JSON document.
- Consumer rule: **the one line of stderr that parses as a JSON object is the report.** Stderr has
  other, prose-only tenants under `--json` — notably the `sq sync` version notice
  (`_cli/_common.py::version_notice`) — so "stderr is JSON" would be false; "at most one line of
  stderr is JSON" is true and testable.

### 4. Stderr stays the report channel; its form follows the output mode

Human mode keeps today's `error: <message>` prose, one line per omission. `--json` mode emits the
report object **instead of** the prose, not alongside it — the same fact twice on the same stream
is duplication with two things to keep in agreement. A person who wants sentences drops `--json`.

### 5. The payload shapes do not change

No envelope, no added key, no sentinel row. Every frozen `--json` shape stays byte-for-byte what it
is, for the readable entries, in the degraded case as in the clean one.

### 6. This is recorded as a behaviour change, not merely described

`docs/stability.md` carries the new row in the exit-code table, names the omissions report as part
of the Tier 3 machine surface (with the "one JSON line on stderr" consumer rule), and states plainly
that five released commands change the code they return on a degraded read. `docs/faq.md`'s table
and its "a degraded read is a non-zero exit" paragraph are updated in the same pass, and the release
notes carry it as a change, not as a new feature. A tier that promises stability earns nothing by
describing a change as though it had always been so.

## Alternatives weighed

**Exit `0` for a partial result.** The most obvious reading of "success with a caveat", and
rejected. It optimises for the consumer that ignores the new signal, and that consumer then gets a
*silently wrong answer* — which is the exact defect F2 filed against the memory pool, preserved
into the fix. Between "wrong data, quietly" and "no data, loudly", an oversight tool takes loud
every time, and F2's own argument is that an under-reported count manufactures the signal the
feature exists to detect. It also withdraws a failure from every script that currently sees
non-zero from `board list`, `inbox` and `search`, and contradicts a posture written down in two
docs and a module docstring.

**Keep exit `1`, disambiguate only through the stderr report.** Cheaper — no table change — and
rejected because it makes "is stdout parseable?" answerable only by parsing stderr, in an
environment where stderr is shared with prose tenants. It also leaves `1` meaning two different
things, against the table's own stated purpose of distinct codes for distinct outcomes, and it
gives a plain shell script no way to tell a short answer from no answer at all.

**Retype the payloads into an envelope** (`{"entries": [...], "omitted": [...]}`). The textbook
shape, and the most expensive one available: it is a Tier 3 retype, it lands on five shapes rather
than two, every consumer of every one of them pays for a condition that almost never fires, and the
next listing added makes it six. Doing it for two commands only would leave clients branching per
command, which is the divergence being fixed.

**A sentinel entry appended to the array.** Keeps the top-level type and is rejected outright: it
makes every consumer branch on a variant row, and a consumer that does not — the one being fixed —
counts the sentinel as an entry. A wrong count in a new costume.

**A second JSON document on stdout.** Breaks every parser that reads stdout as one document, and
makes the stdout shape depend on runtime state.

**Fix it in the clients.** Rejected on ADR-427 §2: the extension would gain per-command exit-code
knowledge the consumer contract denies it, `sq ui` and every future client would each re-derive the
same rule, and the CLI would keep shipping a surface that cannot express the state it is in.

**An opt-in flag** (`--report-omissions`). The default stays broken, and a client that does not know
the flag exists is precisely today's extension.

## Costs accepted

- **Five released commands change their exit code on a degraded read.** `board list`, `inbox` and
  `search` go `1` → `4`: non-zero either way, so no script's pass/fail verdict flips, only the
  number. `memory list` and `memory search` go `0` → `4`: that one *does* flip a verdict from pass
  to fail, and it is the flip op-pierre's ruling asks for — the alternative is a caller that keeps
  believing a short pool is the whole pool.
- **A frozen four-code table becomes five.** The addition is conservative for every existing
  consumer (an unrecognised non-zero code reads as an error), but it is an amendment to a table
  documented as frozen, and this release is the last window before 1.0 in which making it is cheap.
- **Stderr gains a parse rule.** "The one line that parses as a JSON object" is weaker than a
  dedicated stream would be, and it exists because stderr has prose co-tenants that are not part of
  any result. A fourth stream is not available to a CLI.
- **Two facts, two resolutions.** The exit code and the report both say "this is partial". That is
  not the redundancy the house rule forbids: the code is the only form reachable without parsing,
  and it is the only form that exists in human mode. Neither can be derived from the other by the
  consumer that needs it.

## Follow-on work

The producing half (the code, the report, the `source`/`message` split in the memory and board
stores, and the same treatment for `inbox`/`search`) is TASK-944; the consuming half in the
extension is TASK-945; the `docs/stability.md`, `docs/faq.md`, changelog and README pass is
TASK-946.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T07:55:07Z] Pierre Chat:
  - Accepted. The partial-read contract stands as ruled: exit code 4 for a usable-but-short result,
    the omissions report on stderr under --json, payload shapes untouched. The memory commands moving
    from 0 to 4 is the intended fix, not a regression to soften.
<!-- sq:discussion:end -->

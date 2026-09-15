---
id: TASK-944
sequence_id: 944
type: task
title: Fix sq ui's memory gate and land the partial-read contract
status: Done
parent: FEAT-690
author: tech-lead
assignee: python-dev
refs:
- REV-943:fixes
- ADR-947:implements
description: The sq ui memory-attachment fix and its coverage, plus ADR-947's exit
  code 4 and omissions report across the five listing commands
subentities:
- local_id: ST1
  title: Gate sq ui memory attachment on item type, not slug lookup
  status: Done
  story: US1
- local_id: ST2
  title: Render a zero-memory identity as a leaf, not an empty branch
  status: Done
  story: US1
- local_id: ST3
  title: 'Exit code 4: a usable-but-short result, across the five listings'
  status: Done
- local_id: ST4
  title: Regression-cover the memory show --json payload shape
  status: Done
  story: US1
- local_id: ST5
  title: Cover bracket safety on the sq ui memory surfaces
  status: Done
  story: US1
- local_id: ST6
  title: Split source from message where an unreadable file is named
  status: Done
- local_id: ST7
  title: 'The omissions report: one JSON line on stderr under --json'
  status: Done
- local_id: ST8
  title: Cover the five commands against the degraded-read shapes
  status: Done
created_at: '2026-09-14T13:46:21Z'
updated_at: '2026-09-15T12:12:58Z'
---
<!-- sq:body -->
The Python half of the fixes raised by the batch review of this feature's two delivered halves:
the one correctness defect in `sq ui`'s tree attachment, the cosmetic zero-pool branch beside
it, the bracket-safety coverage gap on the memory surfaces, and — per ADR-947 — the CLI's
partial-read contract.

The CLI contract lands here and the extension consumes it from the TypeScript task, so this
task goes first. The documentation task is written against the contract this one implements.

## F1 — `sq ui` attaches memory by slug, not item type

The one correctness defect in the set.

`src/squads/_tui/_tree.py::_attach` reads `node.item.extra.get(X.SLUG)` off any leaf and looks
the slug up in the eagerly-fetched memory map. Nothing gates on item type at render time: the
`ROSTER_ROLE`/`ROSTER_OPERATOR` check lives only in `roster_identity_slugs`, which sizes the
fetch. Skills carry the same `extra[X.SLUG]` key (`src/squads/_services/_roster.py::add_skill`,
and the seeding paths in `src/squads/_services/_maintenance.py`), so a skill slugged identically
to a role renders that role's count, age and openable memory children — a second copy of one
identity's notebook, in a view whose whole job is comparing notebooks across identities.

Second face of the same root cause: the memory branch sits in the `else` of `if node.children:`,
so an identity that has item children loses the memory signal entirely. Bundled roster types
declare no parents, so nothing triggers it today — an adopter spec parenting a type under `role`
would, silently and with nothing in the code marking the assumption.

`clients/vscode/src/domain/metaView.ts::itemToLeaf` already gates on type and its own test
drives exactly this shape. Make the TUI match it.

## F5 — a zero-memory identity renders as an empty expandable branch

Same function, cosmetic, but it sits on exactly the node the feature exists to draw attention
to: a role active for weeks reading `memory: 0`. A zero you can nonetheless expand invites a
click that answers nothing.

## F7 (Python half) — memory bracket-safety is correct but untested

Rich parses `[...]` as markup; the escape is `_cli._common.e()`, and in the TUI the discipline
is spans built with `Text.assemble` rather than markup strings. The reviewer drove the memory
surfaces and found them already correct — this is a coverage gap, not a defect, on the two
places where the next change would most plausibly reintroduce a markup string.

## F2 / F3 — the partial-read contract, as ADR-947 settles it

The review found the two clients diverging on a degraded read, and the asymmetry is the CLI's,
not either client's. The shape is no longer open: ADR-947 is accepted and this task implements
it. Read the decision rather than re-deriving it here; what follows is what it binds.

**The class is five commands, not two.** A *partial result* is what a command produces when its
payload is valid and in its frozen shape, but entries are missing because the corpus could not be
fully read. Today that is `sq inbox`, `sq search`, `sq board list`, `sq memory <role> list` and
`sq memory <role> search`, and the contract binds every listing added later with the same
property. Four of the five exit `1`; the two memory commands exit `0`, which is a defect against
a contract already written down in `docs/faq.md` and in `_services/_results.py`'s own docstring.

**Outside the class, and unchanged.** `sq check` turns an unreadable file into an error-level
issue and exits `3` — a clean `check` over a partly-read corpus is a *false* clean, so the
omission has to become a finding rather than a caveat on a good answer. `sq repair` and
`sq migrate up` report a mutation rather than a result payload; their non-zero exit means "the
corpus still needs attention", a different sentence, and they keep exit `1`. Do not widen the
class to reach them.

**Exit code `4`.** The command did what was asked, stdout carries a valid payload in its
documented shape, and entries are missing. `1`, `2` and `3` outrank it, so `4` is emitted only
where the command would otherwise have exited `0`. It does not depend on `--json`.

**The omissions report.** Under `--json`, one compact line on stderr holding one JSON object,
written only when there is something to report:
`{"omitted":[{"code","source","message"}]}`. It replaces the human prose in that mode rather than
accompanying it, never goes to stdout, and is a top-level object precisely because the payloads
are bare arrays and that is what left them nowhere to grow.

**The payload shapes do not change.** No envelope, no added key, no sentinel row. Retyping a bare
array into an object is what Tier 3 forbids, and it is the alternative ADR-947 weighed and
rejected.

**The producers need a `source`/`message` split.** `_memory/_store.py`, `_board/_store.py` and
`_services/_collab.py` each hand back one pre-composed string today; the report needs the
identifying token separately from the sentence.

## New surface coverage — `memory show --json`

`docs/stability.md` closes its `--json` enumeration by claiming every shape above it is covered
by a regression test. `sq memory <role> show <slug> --json` is about to be named there. The
covering test belongs here rather than on the writer.

## How to work it

- ADR-947 settles the shape; this task does not re-open it. If implementation turns up something
  the decision does not cover, say so in the handback rather than choosing for it.
- The documentation half — `docs/stability.md`, `docs/faq.md`, the changelog and the README — is
  TASK-946 and must land it as a **behaviour change**, not as a description of a new state. Leave
  the handback specific enough to write from: the five commands, the code, the report shape.
- Gates: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .`. A bare `uv run` prunes the optional `tui` extra
  and reports hundreds of false unresolved-import errors under `_tui/`.
- **Do not run the full pytest suite** — the tech lead runs it as the authoritative gate. Run
  the touched test files only.
- Textual TUI tests are intermittently flaky under xdist: re-run a single failure on its own
  before calling it a regression.
- **Falsify every behaviour you add**: break the implementation, watch the new test go red,
  restore it, watch it go green. This is the point of the F1 work in particular — the existing
  skill test uses a slug that cannot collide, so it cannot fail for the shape that is broken. A
  new test that also cannot fail buys nothing.
- No ticket ids in source or test filenames — name tests by the behaviour they pin.
- Leave `sq check` clean before handing back.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 944 add-subtask "<title>"`; track with `sq task 944 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Gate sq ui memory attachment on item type, not slug lookup

<!-- sq:subtask:ST1:body -->
`src/squads/_tui/_tree.py::_attach` decides whether a Roster leaf gets a memory signal by
looking `node.item.extra.get(X.SLUG)` up in the pool map, with no item-type gate. Skills carry
the same `extra[X.SLUG]` key (`src/squads/_services/_roster.py::add_skill`, plus the seeding
paths in `src/squads/_services/_maintenance.py`), so a skill slugged identically to a role
renders that role's count, age and openable memory children.

The reserved-type check exists already, in `roster_identity_slugs` — it sizes the eager fetch
and is never re-applied on the render side. Reuse it rather than writing a second notion of
eligibility. `clients/vscode/src/domain/metaView.ts::itemToLeaf` is the shape to match.

Same root cause, second face: the memory branch is reached only in the `else` of
`if node.children:`, so an identity with item children loses the signal entirely. Nothing
triggers that in the bundled spec — roster types declare no parents — but an adopter spec
parenting a type under `role` would, silently. Deciding on type rather than on childlessness
closes both faces in one edit.

Done when:

- Eligibility is a function of `item.type` alone, through the same reserved-type check
  `roster_identity_slugs` uses.
- A skill whose slug collides with a role's slug gets no glance suffix and no memory children,
  and the role keeps both — driven through the real `populate_tree`.
- An eligible identity carrying item children keeps its count+age suffix and its memory
  children alongside those children.
- The new test uses **colliding** slugs. The existing skill test slugifies to `do-the-thing`,
  which cannot collide, so it cannot fail for the broken shape; falsify the new one (break the
  gate, see it go red, restore it) before calling it coverage.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Render a zero-memory identity as a leaf, not an empty branch

<!-- sq:subtask:ST2:body -->
In `src/squads/_tui/_tree.py::_attach`, an identity is attached with `parent.add(...)` whenever
a pool was fetched, regardless of whether the pool holds anything — so a role reading
`memory: 0` gets a disclosure triangle that opens onto nothing. The extension already renders
that identity as a leaf: `clients/vscode/src/treeItemRendering.ts` maps zero children to
`TreeItemCollapsibleState.None`.

Done when:

- An identity with **no entries and no unreadable files** renders as a leaf, keeping its
  `memory: 0` suffix.
- An identity with entries keeps its branch.
- **An identity whose files are all unreadable also keeps its branch.** The partial-listing
  notice is a real child and must stay reachable: an identity that reads `memory: 0` because
  nothing could be read is the one case where collapsing it would hide the reason. Only the
  genuinely-empty pool collapses. Both cases carry their own assertion, so the two cannot be
  collapsed into one condition by mistake.
- Asserted on expandability and child count through the real `populate_tree`, even though the
  edit lands in the same function as the type gate.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Exit code 4: a usable-but-short result, across the five listings

<!-- sq:subtask:ST3:body -->
The frozen exit-code table grows a fifth row. **`4` means: the command did what was asked, stdout
carries a valid payload in its documented shape, and entries are missing** because the corpus
could not be fully read.

**The class is five commands**, and the membership test is objective: does the command emit a
result payload a caller is meant to consume, and can that payload come back short? Today —
`sq inbox`, `sq search`, `sq board list`, `sq memory <role> list`, `sq memory <role> search`. Four
exit `1` today; the two memory commands exit `0`. Implement this for the class, not for the two
commands the review happened to name, so the next listing added inherits it instead of being
patched in later.

`_cli/_main.py::_report_unreadable` is already the shared helper for `inbox` and `search`;
`_cli/_memory.py::list_memories` / `search_memories` and `_cli/_board.py::list_notices` each spell
their own version. One place decides the code.

Rules, each asserted:

- **Precedence: `1`, `2` and `3` outrank `4`.** `4` is emitted only where the command would
  otherwise have exited `0`, so a partial result never masks a more specific outcome.
- **The code does not depend on `--json`.** A code whose value changed with an output flag would
  be indefensible; human mode returns `4` on the same condition.
- **Nothing else moves.** `sq check` keeps `3` — a clean `check` over a partly-read corpus is a
  false clean, so the omission belongs in its findings, not in a caveat. `sq repair` and
  `sq migrate up` report a mutation rather than a result payload and keep `1`. Do not route them
  through the new helper "for consistency".
- The two memory commands going `0` → `4` flips a verdict from pass to fail. That is the intended
  fix, ruled and accepted: the alternative is a caller that keeps believing a short pool is the
  whole pool.

Done when: one code path decides the exit for all five; the precedence is driven, not assumed;
`check`, `repair` and `migrate up` are asserted unchanged; and human mode returns `4` without
`--json`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Regression-cover the memory show --json payload shape

<!-- sq:subtask:ST4:body -->
`docs/stability.md` enumerates the supported `--json` shapes and closes by telling adopters that
every shape above it is covered by a regression test, so it cannot drift on them unnoticed.
`sq memory <role> show <slug> --json` is about to be named in that enumeration by the
documentation task, and the `created_at` key on `memory list --json` alongside it.

Whoever writes the prose should not also be on the hook for making the claim true, so the test
lands here.

Done when:

- A regression test pins the `memory show --json` payload shape — its keys and their types — in
  the same style as the tests covering the shapes already enumerated there.
- `created_at` on `memory list --json` is pinned too: it is the field the extension's whole
  staleness signal depends on, and a silent removal would read as "no ages available" rather
  than as a break.
- Falsified against the real payload, not against a fixture of it.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Cover bracket safety on the sq ui memory surfaces

<!-- sq:subtask:ST5:body -->
Rich parses `[...]` as markup. The escape is `_cli._common.e()`, and in the TUI the discipline is
spans built with `Text.assemble` rather than markup strings.

The reviewer drove the memory surfaces and found them correct, so this is coverage rather than a
fix — worth closing because a label is "just a string" until it is not, and this repo has been
bitten there before. The delivered bracket test covers the notice body only
(`tests/tui/test_board_screen.py`); `tests/tui/test_memory_view.py` has no bracket case, and the
change to `tests/tui/test_bracket_content_renders_safely.py` was a type annotation.

Done when:

- A memory summary and a tag carrying `[bold red]…[/]`, `[/dim]` and `[x]` render literally
  through the memory tree leaf label, the identity glance suffix and the memory reader header.
- The assertions read plain text plus spans — styling carried as spans, content never parsed —
  matching the shape of the notice-body test already written.
- Falsified per assertion: swap a span-built label for a markup string, watch it go red, restore
  it.

The TypeScript counterpart (the entry summary through `renderMemoryEntryHtml`) belongs to the
extension task, not here.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Split source from message where an unreadable file is named

<!-- sq:subtask:ST6:body -->
The omissions report names **`source`** (the thing that could not be read) separately from
**`message`** (the human sentence). Three producers hand back one pre-composed string today and
have to stop:

- `src/squads/_memory/_store.py` — `f"{path} is a broken symlink (its target does not exist)"` and
  `str(exc)`;
- `src/squads/_board/_store.py` — the same two shapes;
- `src/squads/_services/_collab.py` — `f"{item.id}: {exc}"` for the corpus walk behind `inbox` and
  `search`, plus the two path-shaped ones.

`source` is an item ID where one is known, otherwise a squad-relative path; it is a display token
and a consumer must not parse it. `message` is the same sentence human mode prints today, so the
human output is unchanged by this subtask alone.

`UnreadableItems` (`_services/_results.py`) is the alias every one of these returns through, and
it is `list[str]` today. Widening it is the edit; keep the module docstring's posture statement
("one unreadable file degrades that file, never the answer") true and update the sentence that
describes the string shape.

Done when:

- Every producer supplies `source` and `message` as separate values rather than one composed
  string, including the `_collab.py` corpus-walk sites the decision's inventory does not name.
- `source` is the item ID where the producer has one and a squad-relative path otherwise, asserted
  for both kinds of producer.
- Human output is byte-identical to today's for every existing case — this subtask changes the
  carrier, not the sentences.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — The omissions report: one JSON line on stderr under --json

<!-- sq:subtask:ST7:body -->
Under `--json`, a command in the class writes to **stderr** a single compact line holding one JSON
object:

    {"omitted":[{"code":"unreadable","source":"…","message":"…"}]}

The rules, each of which has a reason that outlives the code:

- **Written only when `omitted` would be non-empty.** Its presence is the signal; a consumer
  treats an absent report and an empty list identically. There is no top-level `partial` boolean —
  that is exactly "`omitted` is non-empty", and the exit code already carries the bit for callers
  that cannot parse.
- **`code`** is the machine class of the omission; `unreadable` is the only value the bundled
  producers emit. The set is open and grows additively, and the rule that keeps it growable is
  that a consumer which does not recognise a code still treats the entry as "part of the result is
  missing". Nothing branches on the value to decide whether the result is partial.
- **Every key present on every entry**, `null` for absent, matching the convention the workflow
  catalogs already set.
- **A top-level object, not a bare array** — deliberately, because the payloads are bare arrays and
  that is precisely what left them nowhere to grow.
- **Never on stdout.** `print_json_clean` stays the only stdout writer and stdout stays exactly one
  JSON document.
- **Instead of the prose, not alongside it.** Human mode keeps today's `error: <message>` line per
  omission; `--json` mode emits the object in its place. The same fact twice on the same stream is
  two things to keep in agreement. A person who wants sentences drops `--json`.
- **The consumer rule is "the one line of stderr that parses as a JSON object is the report."**
  Stderr has prose co-tenants under `--json` — notably the `sq sync` version notice
  (`_cli/_common.py::version_notice`) — so "stderr is JSON" is false while "at most one line of
  stderr is JSON" is true. It is also testable: assert it *with* a version notice present, not
  only on a quiet stderr.
- **The payload shapes do not change.** No envelope, no added key, no sentinel row, in the degraded
  case as in the clean one.

Done when: one emitter serves all five commands; the report is absent when nothing is omitted;
stdout is unchanged byte-for-byte against the clean case; and the one-JSON-line rule holds with a
prose co-tenant on the same stream.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Cover the five commands against the degraded-read shapes

<!-- sq:subtask:ST8:body -->
Table-driven coverage over **command × shape**, not one example per branch.

Commands: `sq inbox`, `sq search`, `sq board list`, `sq memory <role> list`,
`sq memory <role> search` — all five, because the contract is for the class and a fix proven on
two of them is a fix that will be half-applied by the next listing.

Shapes per command: nothing unreadable; some unreadable; everything unreadable; and a listing that
is empty for the ordinary reason, with nothing unreadable. Each asserted separately on **stdout,
the exit code, and stderr** — the three are the contract's three faces and collapsing them into one
assertion is how a payload change slips through.

Also owed:

- the precedence rule: a command in the class that also hits a `1`/`2`/`3` condition returns that
  code, not `4`;
- `4` in human mode, without `--json`, on the same condition;
- `sq check`, `sq repair` and `sq migrate up` asserted **unchanged** over a partly-readable corpus
  — the class has an edge and it is tested;
- the one-JSON-line-on-stderr rule asserted with a prose co-tenant present;
- the `source`/`message` split asserted for an item-ID producer and a path producer.

Falsified per assertion: break the condition, watch each new assertion go red, restore it, watch it
go green. An exit-code assertion in particular must be driven bare rather than through a pipe — a
pipeline reports the last element's status, not the command's.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-14T14:01:53Z] Catherine Manager:
  - Held at Ready rather than dispatched: TASK-941 is live in this tree and its landing commit bumps SCHEMA_VERSION, which hard-stops every sq command until the migration runs. A second dev working here concurrently would lose its sq reads mid-task. Sequencing after 941 rather than isolating in a worktree, to avoid a merge back. ST3 (the degraded --json contract) is separately held pending the architect's ADR.
- [2026-09-15T08:07:16Z] Olivia Lead:
  - Rescoped for the accepted ADR-947. Status untouched (**Ready**, python-dev); `implements ADR-947` added. The same pass rescoped TASK-945 ST1/ST2, and the CLI-before-extension dependency stands.
    
    - **ST3 rescoped and renamed** — "Exit code 4: a usable-but-short result, across the five listings". It is no longer "one signal on both listings, shape left to the dev": the class is `inbox`, `search`, `board list`, `memory list`, `memory search` and every listing added later with the same property. Exit `4` for a usable-but-short result, `1`/`2`/`3` outrank it, and it does **not** depend on `--json`. `sq check` (3), `sq repair` and `sq migrate up` (1) are explicitly outside the class and asserted unchanged.
    - **Three subtasks added**, because the five-command class does not fit one. ST6: split `source` from `message` in the producers — and the inventory is three files, not the two the ADR names: `_memory/_store.py`, `_board/_store.py`, and `_services/_collab.py`, which composes `f"{item.id}: {exc}"` for the corpus walk behind `inbox`/`search`. `UnreadableItems` in `_services/_results.py` is the alias they all return through. ST7: the omissions report — one compact JSON line on stderr under `--json`, replacing the prose rather than accompanying it, found by the ADR's "the one line of stderr that parses as a JSON object" rule, which must be tested **with** a prose co-tenant (the `sq sync` version notice) present. ST8: table-driven coverage over command × shape for all five, each asserted on stdout, exit code and stderr separately.
    - **Payload shapes are fenced in the body.** Both are bare JSON arrays and stay byte-identical in the degraded case; retyping to an envelope is what Tier 3 forbids and is the alternative the ADR weighed and rejected. ST3's old "signal it in the `--json` payload itself" wording was exactly that retype, and it is gone.
    - **The old ST3 said the shape was the dev's to settle.** It no longer is. The task now says: if implementation turns up something ADR-947 does not cover, hand it back rather than choose for it.
    - Body's F2/F3 section rewritten around the decision; `How to work it` now points TASK-946 at recording this as a **behaviour change** in `docs/stability.md` and `docs/faq.md`, not as a description of the new state. Title updated to match the widened scope.
    - One consequence worth naming for dispatch: `_report_unreadable` takes `json_out` and currently ignores it. Under this contract that parameter becomes load-bearing.
    
    `sq check` clean. @manager TASK-944 then TASK-945; 946 writes from 944's handback.
- [2026-09-15T10:19:15Z] Elias Python:
  - All 8 subtasks landed and marked Done. `sq check` clean.
    
    ## Half one — sq ui memory defects (F1, F5, F7)
    
    - `_tui/_tree.py::_attach`: memory eligibility now gates on `_memory_eligible(item.type)`
      (Role/Operator only, reusing `roster_identity_slugs`'s own check) instead of a bare slug
      lookup — fixes a same-slugged Skill picking up a Role's notebook. The memory branch is also
      no longer conditional on `not node.children`, so an eligible identity keeps its count+age
      suffix and memory children alongside real item children (untestable via the bundled spec, so
      covered by directly wiring a synthetic parent link through `tree_view`).
    - Same function: a branch is now created whenever there's something to disclose (item
      children, entries, or unreadable files) — a genuinely empty pool (no entries, nothing
      unreadable) collapses to a leaf; a pool that's empty *because everything in it is
      unreadable* keeps its branch, asserted as two separate cases.
    - Bracket-safety coverage added for the memory tree leaf label and the memory reader header
      (glance suffix was already a fixed string — covered as "survives a bracketed sibling"
      instead).
    - Caught and fixed one real bug of my own while writing the item-children test: my first pass
      at `_attach` had `expand=not node.children` (inverted) — writing the test forced the fix.
    
    ## Half two — ADR-947 partial-read contract
    
    - New `Omission` dataclass (`_models/_omission.py`: `source`, `message`, `code="unreadable"`),
      dependency-free so `_memory/_store.py`/`_board/_store.py` (below the service layer) can build
      it without inverting the layering. `UnreadableItems`/`UnreadableMemories`/`UnreadableNotices`
      now all alias `list[Omission]`.
    - `source`/`message` split landed in all three producers: `_services/_collab.py::_read_or_report`
      (source = item id, always known — all three failure branches), `_memory/_store.py::list_entries`
      and `_board/_store.py::_all_notices` (source = squad-relative path via `path.relative_to(paths.squad_dir)`,
      the established pattern from `_rename.py`/`_retype.py`). Human-mode message text is
      byte-identical to before.
    - `_cli/_common.py::report_omissions(omissions, *, json_out)` is the one shared emitter for all
      five commands: no-op on empty, otherwise human mode keeps today's `error: <message>` lines,
      `--json` mode emits one compact `{"omitted":[{"code","source","message"}]}` line via plain
      `print(..., file=sys.stderr)` (no ANSI), then raises `Exit(4)`. `inbox`/`search` (`_main.py`),
      `board list` (`_board.py`), `memory list`/`memory search` (`_memory.py`) all route through it;
      `_report_unreadable` is gone. Payload shapes untouched — still bare arrays.
    - `_cli/*` docstrings: rewrote per the coordinator's note that these are `--help` text — dropped
      the ADR framing entirely, kept them to what an adopter needs (the code, where the detail is,
      what's unchanged), same length as before or shorter (`sq search --help` unchanged at 53 lines).
    
    ## Exit codes observed (bare invocation, no pipe)
    
    | Command | Clean | Some unreadable | All unreadable |
    |---|---|---|---|
    | `sq inbox` | 0 | 4 | 4 |
    | `sq search` | 0 | 4 | 4 |
    | `sq board list` | 0 | 4 | 4 |
    | `sq memory <r> list` | 0 | 4 (was 0 — the fix) | 4 |
    | `sq memory <r> search` | 0 | 4 (was 0 — the fix) | 4 |
    | `sq check` (unaffected) | 3 on error-level issues | — | — |
    | `sq repair` (unaffected) | 1 on unreadable | — | — |
    | `sq migrate up` (unaffected) | 0 (nothing pending; returns before the corpus sweep) | — | — |
    
    Precedence verified: an unresolvable role on `inbox` still exits 1 even with an unreadable file
    present (fails before the corpus walk runs). One-JSON-line rule verified with a real prose
    co-tenant (staled `squads_version` to force the `sq sync` version notice) on the same stderr.
    
    ## Falsification (each: broke it, watched red, restored, watched green)
    
    - F1 (type gate): reverted `_attach` to the old slug-only lookup — colliding-skill test and
      item-children test both went red with the exact wrong values (`memory: 1` on the skill;
      `memory` suffix absent on the parented role).
    - F5 (zero-pool leaf): reverted to unconditional `parent.add` — the empty-pool test's new
      `allow_expand is False` assertion went red. Then isolated the all-unreadable case alone
      (`entries or unreadable` → `entries`) — only that one test went red, confirming the two
      shapes are independently asserted, not folded together.
    - F7 (bracket safety): swapped `Text.assemble`/`Content.from_markup(template, **vars)` for
      markup-string concatenation in both the tree leaf label and the reader header — both new
      tests went red (one via a `MarkupError` crash, one via a timeout waiting for literal `[tag]`).
    - ST3/ST7 (exit 4 + report shape): confirmed via the table-driven suite itself — it caught a
      real setup bug in its own first draft (an unconditionally-created "good" item leaking into
      the "all_unreadable" shape, which should have zero readable results).
    - ST4: didn't add new coverage — `tests/cli/test_memory_cli.py` already pins `memory show
      --json` (slug/summary/created_at/tags/body) and `memory list --json`'s `created_at`,
      committed with FEAT-690. Falsified by dropping the `tags` key from the JSON dict — the
      existing test caught it (`KeyError: 'tags'`).
    
    ## Gates (real output)
    
    ```
    uv run --all-extras pyright   → 0 errors, 0 warnings, 0 informations
    uv run --all-extras ruff check .           → All checks passed!
    uv run --all-extras ruff format --check .  → 671 files already formatted
    uv run --all-extras pytest tests/meta      → 303 passed
    ```
    
    Targeted suites run (not the full suite): the touched files above, plus
    `tests/cli/test_partial_read_degrades_across_the_five_listings.py` (new, 24 cases),
    `tests/tui/test_memory_view.py`, `tests/tui/test_board_screen.py`,
    `tests/tui/test_bracket_content_renders_safely.py`, `tests/tui/test_browse_screen.py`,
    `tests/cli/test_memory_cli.py`, `tests/cli/test_board_cli.py`,
    `tests/cli/test_json_output_shape.py`, and a handful of others exercising `inbox`/`search`/
    `board`/`memory` — all green. `tests/meta`'s ticket-ID hygiene gate is clean (swept every
    docstring/comment I touched, in both `src/` and `tests/`, not just the lines you flagged).
    
    ## Files changed
    
    - `src/squads/_models/_omission.py` (new)
    - `src/squads/_services/_results.py`, `_services/_collab.py`
    - `src/squads/_memory/_store.py`, `_board/_store.py`
    - `src/squads/_cli/_common.py`, `_cli/_main.py`, `_cli/_memory.py`, `_cli/_board.py`
    - `src/squads/_tui/_tree.py`
    - `tests/cli/test_partial_read_degrades_across_the_five_listings.py` (new)
    - `tests/cli/test_unreadable_files_degrade_per_file_cli.py`,
      `test_undecodable_squad_files_fail_cleanly.py`,
      `test_malformed_frontmatter_and_config_fail_cleanly.py`
    - `tests/service/test_search_and_inbox_degrade_per_file.py`,
      `test_unreadable_files_degrade_per_file.py`
    - `tests/tui/test_memory_view.py`
    
    ## Unfinished / for the record
    
    - Nothing outstanding against this task's scope. `docs/stability.md`/`docs/faq.md`/changelog/
      README are explicitly TASK-946's (writer) — I did not touch docs.
    - REV-958 appeared in the squad tree mid-task (untracked on disk) — not mine, left untouched.
    - I have not staged or committed anything (forbidden per brief); the working tree carries all
      of the above plus the subtask status updates on this task.
    
    @manager
<!-- sq:discussion:end -->

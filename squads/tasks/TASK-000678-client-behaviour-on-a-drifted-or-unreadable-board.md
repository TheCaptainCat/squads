---
id: TASK-678
sequence_id: 678
type: task
title: Client behaviour on a drifted or unreadable board
status: Draft
author: tech-lead
refs:
- ADR-663
- REV-671
description: Neither client was exercised against the skew guard or a corrupt board;
  both are read-only today, so pin that, audit the extension's silent-degrade paths,
  and write the refusal contract before the first mutating command.
subentities:
- local_id: ST1
  title: Confirm and pin the read-only property
  status: Todo
- local_id: ST2
  title: Audit the extension's silent-degrade paths
  status: Todo
- local_id: ST3
  title: Write the client refusal contract
  status: Todo
- local_id: ST4
  title: Manual dev-host check on a drifted board
  status: Todo
  assignee: op-pierre
created_at: '2026-07-28T00:11:38Z'
updated_at: '2026-07-28T00:12:16Z'
---
<!-- sq:body -->
Neither the VS Code extension nor the `sq ui` TUI was exercised against the skew guard, or against a
drifted or unreadable board at all, across four review passes of this release. Everything was
verified through the CLI. Close the gap: establish what the clients actually do, and fix what turns
out to be missing.

Targets **0.13**. Nothing here blocks the current release — see the finding below for why.

## What a first pass already establishes

Both clients are **read-only today**, so the skew guard is unreachable from either. Verified against
the tree at planning time:

- **`sq ui`** — every service call in `src/squads/_tui/` is `get`, `read_body`, `read_discussion`,
  `get_block`, `tree_view`, `search`, or `spec`. No `set_status`, no comment, no assign; the app's
  only binding is `q` to quit, and there is no subprocess call.
- **VS Code** — every exported adapter function in `sqAdapter.ts` is a `get*`, every registered
  command is refresh / filter / toggle / open-preview / search / navigate, `package.json` contributes
  no others, and no write subcommand string appears anywhere in `clients/vscode/src/`.

So the reviewer's question 1 — *do the clients mutate on paths that hit the guard?* — is **no**, and
answering it needs no dev-host session. There is no shipped defect on that axis, and this is not a
release blocker.

Confirm that independently before building on it; it is the premise the rest of the ticket rests on,
and both clients are under active development.

## What the gap actually is

Two things survive that finding, and they are the reason this is still worth doing.

**1. A live instance of question 2, on the read path.** `treeDataProvider.ts` degrades seven metadata
fetches to empty defaults when the `sq` call fails — type order, categories, labels, field bindings,
badge vocabulary, status roles, role catalog — each silently, each with a comment explaining that a
broken tree is worse than a degraded one. That reasoning is sound and those fallbacks should stay: it
was written for a catalog that is *unreachable*, or an older `sq` that lacks a field. Transient or
version causes, where degrading quietly is right.

This release created a new cause that reaches the same code. A board with an unreadable file now
makes those commands fail **cleanly and persistently** rather than crashing. The user gets a tree
with alphabetical ordering, raw type names, no badges and no colours, and is told nothing — the
cause is a corrupt file they could fix in a minute, and the client's response is to look slightly
wrong forever. Graceful degradation for "unreachable" is not the same decision as graceful
degradation for "your board has a data error".

Worth distinguishing: keep the silent fallback for an unreachable or outdated `sq`, and surface it
once — a notification, not a broken tree — when the failure is a reported data error. Whether that
distinction is cheaply available from `SqOutcome` today is the first thing to check; if it is not,
say so and keep the current behaviour rather than inventing a signal.

**2. The refusal contract does not exist yet, and the first mutating command will need it.** The
moment either client gains a mutating command it inherits an error surface nobody has designed. The
failure mode to avoid is specific: **a `SquadsError` that becomes a silent no-op in a UI is worse
than a traceback in a terminal.** The user sees their edit apparently succeed, nothing happens, and
there is no output stream to notice. In a terminal a raw traceback is at least loud.

That contract is cheap to write down now, while the guard's behaviour is fresh, and expensive to
retrofit after a mutating command ships without it.

Context worth reading: finding F17 showed the guard's permitted-skew set over-exempts `extra` fields
on dev roles and skills — 8 of 9 settable fields on a dev role. A dev is fixing that separately. It
matters here only as the illustration: if a client ever mutates a roster item's `extra`, that shape
reaches it, and a client with no refusal handling would turn a refusal into a silent no-op.

## Out of scope

- **F17 itself** — separately owned; this ticket does not fix the exemption set.
- **Adding mutating commands to either client.** This defines what one must do when it refuses; it
  does not build one.
- **The CLI's own refusal behaviour**, which this release covered and tested.

## Acceptance

- The read-only finding is confirmed against the then-current tree and **pinned by a test** in each
  client's suite, so the day a mutating command lands, someone has to consciously delete the pin and
  handle refusal. That test is the durable output of this ticket even if nothing else changes.
- The refusal contract is written where a client author will read it — what a client must do when a
  service call refuses: surface it visibly, name the item, carry the `sq repair` pointer, and never
  reduce it to a no-op or a silently unchanged view.
- The extension's silent-degrade paths are audited against a board with an unreadable file: either
  the failure is surfaced once when the cause is a data error, or the reason it stays silent is
  recorded at the call site alongside the existing unreachable-catalog reasoning.
- A drifted board (interrupted rename, stale index path) does not break either client's read paths:
  the tree still renders, the preview still opens or reports cleanly, and neither shows an empty view
  that reads as "no items".
- The manual dev-host confirmation is done and its result recorded on this ticket.

## The manual step

Verifying the extension end to end needs the Windows dev host, which is the operator's machine — an
agent cannot close that part. It is scoped to what is genuinely uncertain: how the tree and preview
*look* against a drifted or corrupt board. It is deliberately not a mutation-refusal check, because
there is no mutating command to exercise.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 678 add-subtask "<title>"`; track with `sq task 678 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Confirm and pin the read-only property |  |
| ST2 | Todo |  | Audit the extension's silent-degrade paths |  |
| ST3 | Todo |  | Write the client refusal contract |  |
| ST4 | Todo | op-pierre | Manual dev-host check on a drifted board |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Confirm and pin the read-only property

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Confirm the read-only property and pin it, so it cannot lapse silently.

Re-establish it against the then-current tree rather than trusting the task body — both clients are
under active development and this is the premise everything else rests on. The checks that
established it at planning time:

- **`sq ui`**: every service call under `src/squads/_tui/` is a read (`get`, `read_body`,
  `read_discussion`, `get_block`, `tree_view`, `search`, `spec`); no bindings beyond quit; no
  subprocess.
- **VS Code**: every exported `sqAdapter` function is a `get*`; every registered command is refresh /
  filter / toggle / preview / search / navigate; `package.json` contributes no others; no write
  subcommand string anywhere under `clients/vscode/src/`.

Then pin it in each client's own suite. The point of the test is not that read-only is desirable —
it is that a mutating command must not arrive *unnoticed*, because the day it does, the guard becomes
reachable and refusal handling becomes mandatory. Assert the property at whichever seam is cheapest
and hardest to bypass: the set of registered commands for the extension, the set of service methods
called for the TUI.

Write the failure message so it teaches rather than blocks: a mutating surface was added, so the
refusal contract now applies — see it, handle it, then update this test. A pin whose message only
says "expected 12, got 13" will be deleted by whoever hits it.

Acceptance:
- The read-only property is re-verified and the result recorded on the ticket, including anything
  that changed since planning.
- One test per client pins it, and each fails with a message naming the refusal contract.
- Neither test asserts an incidental detail (an exact command count, an exact method list) that
  ordinary read-only work would break.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Audit the extension's silent-degrade paths

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Audit the extension's silent-degrade paths against a board with a data error.

`treeDataProvider.ts` degrades seven metadata fetches to empty defaults on failure — type order,
categories, labels, field bindings, badge vocabulary, status roles, role catalog. Each is deliberate
and carries a comment explaining that a degraded tree beats a broken one, and each traces to an
earlier review finding. **Do not remove them.** The reasoning is right for the cause they were
written against: a catalog that is unreachable, or an `sq` too old to have the field.

What changed is the set of causes. This release made those commands fail cleanly and *persistently*
on a board containing an unreadable file. The same fallback then produces a tree with alphabetical
ordering, raw type names, no badges and no colours, and tells the user nothing — for a condition they
could fix in a minute if they knew about it.

The work:

- Determine whether `SqOutcome` already distinguishes "could not run / unrecognised output" from "`sq`
  ran and reported an error". If it does, surface the second case once — a notification naming the
  problem, with the tree still degrading rather than breaking — and leave the first silent.
- If it does not, do **not** invent a signal to force the distinction. Record that finding at the
  call sites, alongside the existing unreachable-catalog reasoning, so the next reader knows the
  silence now covers two causes and only one of them was intended.

Either outcome is acceptable; an unexamined silence is not. The tree must never end up looking like
"no items" or "no categories" when the real answer is "one file on your board cannot be read".

Check the same question for the records and roster trees and the preview manager, which already call
`describeFailure` — they may already behave correctly, in which case say so rather than changing
them.

Acceptance:
- Every silent-degrade path is examined against a board containing an unreadable item file.
- A data-error cause is either surfaced once, or its continued silence is recorded at the call site
  with the reason.
- The existing unreachable-catalog and old-`sq` fallbacks still behave exactly as they do today.
- No path renders an empty view that a user would read as "nothing here".
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Write the client refusal contract

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Write the refusal contract down, before the first mutating command needs it.

The guard refuses a mutation whose on-disk frontmatter has diverged from the index, raising a
`SquadsError` from the service layer. No client handles that today because no client mutates — which
is exactly why the contract is cheap to write now and expensive to retrofit later.

The failure mode it exists to prevent is specific, and worth stating in those terms rather than as a
style rule: **a refusal that becomes a silent no-op in a UI is worse than a traceback in a terminal.**
The user sees their edit apparently succeed, nothing changes, and there is no output stream where
they might notice. A terminal at least fails loudly.

What a client must do when a service call refuses:

- surface it visibly — a notification or an inline error, never only a log line;
- name the item, so the user knows *which* thing refused;
- carry the `sq repair` pointer through, rather than replacing the service's message with a generic
  one — the remedy is the actionable half;
- leave the view in a state that matches reality: the edit did not happen, so the UI must not show it
  as having happened, and must not silently revert to the old value with no explanation either.

Put it where a client author will actually read it — with the client contribution guidance, not
buried in a service docstring. Both clients shell out to or call into the same service layer, so it
is one contract covering both, not one per client.

Keep it short. This is a rule someone reads once before adding a mutating command; a page of prose
will not be read at all.

Acceptance:
- The contract exists in the client-facing guidance, in a form an author will find before adding a
  mutating command.
- It names the silent-no-op failure mode explicitly, not just "handle errors".
- It covers both clients from one place.
- The pin from the read-only subtask points at it by name in its failure message.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Manual dev-host check on a drifted board

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
**Assignee:** Pierre Chat
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Manual confirmation on the Windows dev host — the operator's machine, so an agent cannot close this.

Scoped to what is genuinely uncertain. It is deliberately **not** a mutation-refusal check: neither
client has a mutating command, so there is nothing to refuse. What has never been looked at is how
the clients *render* a board that is drifted or partly unreadable.

Setup — a throwaway squad, not the project board:

1. a board with one item file whose frontmatter is unreadable (an unresolved merge conflict inside
   the `---` block is the realistic shape);
2. a board with a stale index path from an interrupted rename — file at its new path, index still
   naming the old one.

Launch the extension via the Windows `code` CLI with `--disable-extensions`, recompiling first — not
the WSLg Linux test binary, which renders poorly and is not the authoritative visual check. Then, on
each board:

- does the Work tree render, and does it look right, or subtly wrong with no explanation (alphabetical
  ordering, raw type names, missing badges or colours)?
- does opening a preview on the affected item report cleanly, or show an empty panel?
- does anything read as "no items" when the real answer is "one file cannot be read"?
- does the Records or Roster tree behave differently from the Work tree?

Then the same two boards in `sq ui`: does the tree render, does the reader open the affected item, and
is any failure visible or silent?

Record the result on the ticket — a short note per board per client, with a screenshot where the
rendering is the point. A "looks fine" is a real and useful result; the purpose is that someone has
actually looked.

Acceptance:
- Both boards exercised in both clients, on the Windows dev host for the extension.
- The result recorded on this ticket, with screenshots where rendering is the finding.
- Anything that turns out to be broken is filed or folded into the audit subtask rather than fixed
  ad hoc here.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-28T00:12:16Z] Olivia Lead:
  - Cut for the client coverage gap. One correction to the premise, verified against the tree: BOTH clients are read-only today, so the skew guard is unreachable from either — the brief's 'the extension's interactive commands and the TUI's transition/comment/assign work' does not match the code. Every _tui/ service call is a read and its only binding is quit; every sqAdapter export is a get*, every registered command is refresh/filter/toggle/preview/search/navigate, package.json contributes no others, and no write subcommand string appears anywhere in clients/vscode/src/. Question 1 is answered without a dev-host session, and there is no shipped defect on the mutation axis.
  - Two things survive that, and they are why the ticket is still worth doing. (a) A live instance of question 2 on the READ path: treeDataProvider.ts silently degrades seven metadata fetches to empty defaults on failure. Those fallbacks are deliberate, documented, and trace to earlier findings — written for an unreachable catalog or an older sq. This release added a new cause that reaches the same code: a board with an unreadable file now fails cleanly and PERSISTENTLY, so the user gets alphabetical ordering, raw type names, no badges and no colours, forever, with no indication why. Keep the fallback; distinguish the cause. (b) The refusal contract does not exist, and the first mutating command will need it — cheap to write now, expensive to retrofit.
  - ST4 is the manual dev-host step, assigned @op-pierre — but rescoped honestly: not a mutation-refusal check (there is no mutating command to exercise), rather how the tree and preview RENDER against a drifted or corrupt board. Windows code CLI with --disable-extensions, recompile first, not the WSLg binary. ST1's pin is the durable output even if nothing else changes: it makes the day a mutating command lands a conscious decision rather than a silent one.
<!-- sq:discussion:end -->

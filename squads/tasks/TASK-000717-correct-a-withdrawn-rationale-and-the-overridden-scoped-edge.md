---
id: TASK-717
sequence_id: 717
type: task
title: Correct a withdrawn rationale and the overridden scoped-edge remedy
status: Draft
author: tech-lead
priority: low
refs:
- REV-706:addresses
subentities:
- local_id: ST1
  title: Reground the duplicate-default docstring on ADR-697 §9
  status: Todo
- local_id: ST2
  title: Store the direction-independent scoped-edge remedy and append the flag
  status: Todo
- local_id: ST3
  title: Update the three pinned remedy strings and the documented refusal example
  status: Todo
created_at: '2026-07-31T13:19:20Z'
updated_at: '2026-07-31T13:21:15Z'
---
<!-- sq:body -->
Two corrections in the roster config-integrity area, neither of which changes what the
gate or the reporter decides. One is a docstring that records a rationale the governing
decision withdrew; the other is a dataclass field whose stored value is discarded by the
renderer in most of the situations it is rendered in. They share `render_finding`, so they
are done together rather than touching that function twice.

## 1. `_default_designation_duplicated`'s docstring records a withdrawn rationale

`src/squads/_services/_validators.py::_default_designation_duplicated` explains why the
duplicate-default-designation predicate is a reporter and never a gate clause with this:

> Delta scoping would fire it on *reactivating* a non-live role that still carries the key
> while a live role also carries it — and no remedy exists in that direction:
> `Service.set_default_role` refuses a non-live target, and no interactive command clears
> the key off a non-live role. That is exactly the lock-out the withdrawn `no_default_role`
> clause was withdrawn for …

Two problems.

**It is false on its own terms.** `set_default_role` clears every other holder it finds.
Its loop filters on item type, identity and the designation key — never on liveness — so a
non-live role carrying the key is cleared like any other. The method's own docstring says
"this clears **every** other holder found", and ADR-697 §9 calls that "the load-bearing
part" of the verb. So "no interactive command clears the key off a non-live role" is
contradicted by the one method the sentence names.

**It records the reasoning the decision withdrew.** ADR-697 §9 grounds report-rather-than-gate
on different footing, and says so explicitly:

> A two-holder state is reported, never gated. … the clause family exists for a projection
> that would name something *not there*, and two live holders names something that is there
> — real, live, and merely under-determined. … Note that the remedy *would* have been
> performable, so this is not the unperformable-remedy rule of §7 doing the work:
> designating either existing holder clears the other. Report rather than gate is a
> proportionality call about a state with no dangling reference in it, not a forced move.

### Correct end state

The docstring states ADR-697 §9's actual grounds:

- two live holders is a state that *is* there and is merely under-determined, which puts it
  on the reporter's side of the boundary the clause family draws — that boundary is about a
  projection naming something absent, and nothing is absent here;
- report rather than gate is a proportionality call about a state with no dangling
  reference, not a forced move;
- gating on the status axis would additionally bill the wrong action: the condition is
  created by whatever wrote the second designation, while a clause there would refuse
  whoever transitions next instead.

The unperformable-remedy sentence is **deleted**, not qualified or softened — the claim is
untrue and the reasoning is withdrawn, so there is nothing to preserve. The existing closing
note about the bulk importer's `update` event being the one path outside `set_default_role`
that writes the key stays: ADR-697 §9 makes the same point.

### Acceptance

- The predicate's behaviour is untouched: no change to what it returns, to the issue
  severity, to the message text, or to its registry entry. Comment and docstring text only.
- No sentence in the docstring asserts that a remedy is unavailable, or that no command
  clears the key off a non-live role.
- The docstring's grounds agree with ADR-697 §9 and can be checked against it sentence by
  sentence.
- The tests already covering this predicate pass byte-unchanged. A behaviour change here
  would surface as a test failure rather than slipping through, so no test edits are
  expected for this part; if one becomes necessary, that is a signal the change went further
  than a docstring and needs a second look.

## 2. The scoped-edge remedy is overridden by the renderer rather than extended

`ConfigIntegrityFinding.remedy` advertises itself as "the specific, satisfiable next step".
For the `scoped_edge` kind, `render_finding` discards the stored value and substitutes a
private module constant unless the caller passes `unlink_available=True`:

```python
remedy = finding.remedy
if finding.kind == SCOPED_EDGE and not unlink_available:
    remedy = _SCOPED_EDGE_NO_UNLINK_REMEDY
```

`unlink_available` is `is_retirement and f.entry == item.id`, which only the retirement gate
ever passes; the `sq check` reporter never does. A `scoped_edge` finding is rendered in three
situations — the reporter, the gate on another item's transition, and the gate on a
retirement of the finding's own entry — and the stored remedy is used in exactly one of
them. The field the type documents as the next step therefore holds a value that is wrong in
most renderings, while the generally-true answer lives in a private constant the type does
not mention. Anyone inspecting a finding directly sees a remedy naming `--unlink` with no
way to know it will usually be replaced.

### Correct end state

Store the direction-independent remedy on the finding — severing the edge with
`sq skill <addr> unlink-role <role>`, or reactivating the skill, both true in every
situation — and have the renderer **add** the `--unlink` shortcut when the caller has it,
rather than swap the value:

```python
if unlink_available:
    remedy = f"pass --unlink, or {remedy}"
```

`_SCOPED_EDGE_NO_UNLINK_REMEDY` disappears. `unlink_available` then reads as what it is —
an extra option this caller has — not a correction to the finding. Exact wording is the
implementer's call provided the rendered line names every option that applies and no
segment repeats (`_assert_no_phrase_repeats` splits on the em-dash separator and will catch
a duplicated one).

`ConfigIntegrityFinding`'s class docstring currently spends a paragraph explaining that
`remedy` "is not necessarily the remedy every caller renders" and that `render_finding`
"substitutes a direction-appropriate remedy". That paragraph describes the mechanism being
removed and goes with it. What stays: `message` and `remedy` are two fields and never one
composed string, and `render_finding` is the single place they are joined.

### What may change and what may not

No finding's `kind`, `severable_targets`, `message`, or `clause` changes. Which findings
fire, which transitions refuse, what `--unlink` severs, the three-pass ordering on the
`--unlink` path, and every exit code stay exactly as they are. The one intended visible
change is the wording of the remedy in the retirement-of-its-own-entry rendering, which
gains the reactivation option it currently omits.

Concretely, in the current suite:

- `tests/unit/test_roster_config_integrity_predicates.py`'s no-unlink rendering assertion
  and `tests/service/test_retirement_refuses_a_config_breaking_transition.py`'s reactivation
  refusal assertion must pass **byte-unchanged** — they already assert the
  direction-independent text, and they are the proof the common path did not move.
- Three assertions legitimately change, and only these three: the stored `.remedy` field
  equality in the unit tests, the `unlink_available=True` rendering there, and the composed
  retirement refusal in the service tests. Each changes to the new expected string and
  nothing else about it.
- `docs/roles.md` prints the refusal example verbatim, including the remedy line. It must be
  updated to the string the code now produces, so the documented output stays a real
  transcript. That one line is the whole documentation change; no surrounding prose needs
  rewriting.

If any assertion outside that list needs touching, stop and say so rather than editing it —
it means something decided changed, which this does not authorise.

### Acceptance

- `_SCOPED_EDGE_NO_UNLINK_REMEDY` no longer exists and `render_finding` contains no branch
  that replaces a stored remedy.
- The stored `scoped_edge` remedy is true in all three rendering situations, judged by
  reading it against each.
- `render_finding` composes `message` and `remedy` in exactly one place, as before.
- The two byte-unchanged assertions above pass untouched; the three changed ones assert the
  new strings; `docs/roles.md`'s example matches real output.
- `ConfigIntegrityFinding`'s docstring no longer describes a remedy the renderer may
  override.

## Constraints

- No item identifiers in source or documentation — not in code, comments, docstrings, test
  names, or `docs/`. Name tests by the behaviour they pin. The pointer to this work belongs
  in the discussion here, not in the tree.
- No build-process narration in anything that ships. Docstrings and docs describe how the
  code behaves and why, never the sequence of changes that produced it.
- Docstrings that cite ADR-697 must agree with what it says; re-read the cited section
  rather than paraphrasing from the surrounding code.
- Gates, all with `--all-extras`: `pyright`, `ruff check .`, `ruff format --check .`, and
  the full `pytest` suite. `uv run sq check` clean.
- Keep `uv run vulture` no worse than before — a removed private constant should reduce its
  output, not add to it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 717 add-subtask "<title>"`; track with `sq task 717 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Reground the duplicate-default docstring on ADR-697 §9 |  |
| ST2 | Todo |  | Store the direction-independent scoped-edge remedy and append the flag |  |
| ST3 | Todo |  | Update the three pinned remedy strings and the documented refusal example |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Reground the duplicate-default docstring on ADR-697 §9

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Rewrite `_default_designation_duplicated`'s docstring in `_services/_validators.py` so its
recorded grounds are ADR-697 §9's: two live holders names a state that is present and merely
under-determined, so it falls on the reporter's side of the clause family's boundary; report
rather than gate is a proportionality call about a state with no dangling reference; and a
clause on the status axis would bill whoever transitions next for a designation someone else
wrote.

Delete the unperformable-remedy sentence outright — `set_default_role` clears every holder it
finds regardless of liveness, so the claim is untrue as well as withdrawn. Keep the closing
note that the bulk importer's `update` event is the one path outside `set_default_role` that
writes the key.

Text only: the predicate's return value, severity, message and registry entry are untouched,
and its existing tests pass unedited.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Store the direction-independent scoped-edge remedy and append the flag

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
In `_services/_config_integrity.py`, make the stored `scoped_edge` remedy the one that is
true in every rendering situation — sever the edge with `sq skill <addr> unlink-role <role>`,
or reactivate the skill — and have `render_finding` prepend the `--unlink` shortcut when
`unlink_available` is set instead of replacing the value. Delete
`_SCOPED_EDGE_NO_UNLINK_REMEDY`; after this there is no branch in `render_finding` that
overrides a stored remedy.

Trim `ConfigIntegrityFinding`'s class docstring of the paragraph explaining that `remedy` is
"not necessarily the remedy every caller renders" and that the renderer substitutes a
direction-appropriate one — that describes the mechanism being removed. Keep the part that
matters: `message` and `remedy` stay two fields, and `render_finding` stays the single place
they are joined.

Nothing about detection moves: no change to `kind`, `severable_targets`, `message`, `clause`,
to which findings fire, or to what refuses.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Update the three pinned remedy strings and the documented refusal example

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Exactly three assertions change, and they are the only ones permitted to:

- the stored `.remedy` field equality and the `unlink_available=True` rendering, both in
  `tests/unit/test_roster_config_integrity_predicates.py`;
- the composed retirement refusal in
  `tests/service/test_retirement_refuses_a_config_breaking_transition.py`.

Two must pass **byte-unchanged**, and they are the evidence the common path did not move: the
no-unlink rendering assertion in the unit tests, and the reactivation-refusal assertion in
the service tests. Both already assert the direction-independent text.

`docs/roles.md` prints a refusal transcript including its remedy line; update that one line
so the documented output is what the code actually emits. No surrounding prose needs
rewriting.

Any assertion outside the list of three needing a change means something decided also
changed. Stop and report it rather than editing it.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

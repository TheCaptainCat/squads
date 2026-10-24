---
id: REV-1099
sequence_id: 1099
type: review
title: 'Adopter field report on 0.15.0: upgrade and a day of work'
status: InReview
author: reviewer
refs:
- REV-565
- FEAT-566
- FEAT-124
- ADR-1052
subentities:
- local_id: F1
  title: 'The sq import event schema is undocumented: no op/field reference'
  status: Open
  severity: medium
- local_id: F2
  title: sync reports an older release's generated pointer as 'had drifted'
  status: Open
  severity: low
- local_id: F3
  title: No warning when a type holds items but no active role authors it
  status: Open
  severity: low
- local_id: F4
  title: Index-lock contention is silent, and a 10 s wait ends in a raw Timeout traceback
  status: Open
  severity: high
- local_id: F5
  title: 'A milestone body cannot round-trip: tag refused, rendered roll-up duplicated'
  status: Open
  severity: medium
- local_id: F6
  title: Operator-assigned subtasks need --force to go Todo to Done
  status: Open
  severity: low
- local_id: F7
  title: Finding lifecycle has no Noted or Deferred state
  status: Open
  severity: medium
- local_id: F8
  title: sq list has no compact form; long titles wrap over several lines
  status: Open
  severity: low
- local_id: F9
  title: sq create bug has no --severity; only priority is exposed at create
  status: Open
  severity: medium
- local_id: F10
  title: A review can be Approved with Open findings and sq check stays silent
  status: Open
  severity: medium
- local_id: F11
  title: Bundled reviewer guidance does not say when a review is warranted
  status: Open
  severity: low
- local_id: F12
  title: Role-override docs never show splat-refs on list fields
  status: Open
  severity: low
- local_id: F13
  title: sq role show does not say how to change a role's definition
  status: Open
  severity: low
- local_id: F14
  title: Loop step 5 narration sweep names no owner role
  status: Open
  severity: medium
- local_id: F15
  title: override scaffold --role writes a near-empty file
  status: Open
  severity: low
- local_id: F16
  title: A second author on a type silently drops its CLAUDE.md workflow bullet
  status: Open
  severity: medium
- local_id: F17
  title: Bundled handoffs hardcode @reviewer instead of the review's author
  status: Open
  severity: low
created_at: '2026-10-24T09:19:58Z'
updated_at: '2026-10-24T09:23:59Z'
---
<!-- sq:body -->
## Scope

Field report from an adopter project, in two parts written against squads **0.15.0**: the upgrade
of its squad from 0.11.1 to 0.15.0 (migrate up, sync, check, an integrity diff of the index), then
one day of real work with eight agents, up to four of them writing to `sq` at the same time. The
adopter's earlier report on 0.11.1 is triaged in REV-565; this review covers only the new points.

The adopter's net verdict on both parts is positive: the migration lost no work data (a normalized
index diff of every content item was empty, and the item-file diff only removed retired regions),
`sq check` stayed green all day, concurrent writers never corrupted the index, dependency chains
showed correctly in `sq blocked`, and the milestone roll-up was right without upkeep.

## Method

Every point was re-checked against this branch (0.16.0 plus the 0.17 work in progress), not taken
from the report. Behaviour was exercised with the dev build (`uv run --all-extras sq`) in a scratch
squad under the session scratchpad, outside any project tree; code and bundled specs were read in
place. Each finding states how its conclusion was reached: **driven** (ran it), **read** (code or
spec), or **inferred**.

## Summary

| Point | Topic | Verdict |
|---|---|---|
| 11.1 / 14.12 | `add-finding` hint names a nonexistent `sq finding body` | already fixed |
| 11.2 | `migrate chlog` short ranges drop the latest release | already fixed |
| 11.3 | `sq import` event schema undocumented | still valid (F1) |
| 11.4 | `sync` reports a stale generated pointer as "had drifted" | still valid (F2); the `--help` path leak is fixed |
| 11.5 | No signal when a type with items has no active authoring role | still valid (F3) |
| 11.6 | Role definition fetched by command, not included in the pointer | by design |
| 14.1 | Lock contention invisible; a 10 s wait ends in a raw traceback | still valid (F4) |
| 14.2 | Milestone body cannot round-trip through `body --force` | still valid (F5) |
| 14.3 | Operator subtasks need `--force` for Todo to Done | still valid (F6) |
| 14.4 / 14.10 | No Noted/Deferred finding state | still valid (F7) |
| 14.5 | Reviewer cannot close the task it approved | by design |
| 14.6 | Review/task link kinds asymmetric | by design |
| 14.7 | Bare arrow after `create milestone`; no compact `sq list` | arrow fixed; compact list still valid (F8) |
| 14.8 | Long `add-story` title advisory reads like a refusal | already fixed |
| 14.9 | `sq create bug` has no `--severity` | still valid (F9) |
| 14.10 | Approved review may hold Open findings, silently | still valid (F10) |
| 14.11 | No guidance against reviews with no findings | still valid (F11) |
| 14.13 | Role-override docs do not show splat-refs | still valid (F12) |
| 14.14 | `sq role show` does not say how to change a role | still valid (F13) |
| 14.15 | Narration sweep (loop step 5) names no owner role | still valid (F14) |
| 14.16 | `override scaffold --role` writes a near-empty file | still valid (F15) |
| 14.17 | A second author on a type drops its CLAUDE.md workflow line | still valid (F16) |
| 14.18 | Bundled dev review handoff hardcodes `@reviewer` | still valid (F17) |

## Points already fixed or by design

- **11.1 / 14.12, fixed (driven).** `add-finding` now prints `sq review <n> finding <k> body -m …`;
  no `sq finding body` form is left in `src/`.
- **11.2, fixed (driven).** `migrate chlog v0.11..v0.15`, `v0.14..v0.15`, `v0.15..v0.16` and the
  bare `0.15..0.16` all select by release and print the expected releases.
- **11.4, third sub-point, fixed (driven).** `sq migrate up --help` no longer mentions an internal
  module path; the reference survives only in code comments.
- **11.6, by design.** A pointer carries only what the host needs before the agent runs, and
  `sq` answers the rest (CLAUDE.md invariant 5). The cost is a few start-of-run tool calls.
- **14.5, by design.** The approver does not close the work it approved; the bundled guidance
  already says to comment the verdict so the task can close. Enforced separation of duties is
  FEAT-124.
- **14.6, by design.** Refs are forward edges and backrefs are computed, so one edge
  (task `addresses` review) is enough, and that is the only edge the bundled guidance asks for.
  The reverse `related` edge was the adopter's own addition.
- **14.7, first sub-point, fixed (driven).** `sq create milestone` prints `created MILE-<n> → <path>`.
- **14.8, fixed (driven).** With `subentity_title_max` selected, `add-story` prints
  `added US<n> to FEAT-<n>` first, then the advisory; the success is stated before the advice.
- **Part 1 points still open per the report.** Preferred IDs or aliases on import was closed as
  WontFix in REV-565 in favour of the generic link feature, FEAT-566. The missing bundled designer
  role was closed as WontFix there too. Neither is refiled here.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1099 add-finding "…" --severity medium`; track with `sq review 1099 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — The sq import event schema is undocumented: no op/field reference

<!-- sq:finding:F1:body -->
Report point 11.3. **Read.**

`sq docs adoption` section 3 shows how to invoke `sq import` and what validation does, but never
what an event line looks like. The only example in the docs is a single `update` event in
`sq docs overrides`; `sq import --help` lists no event shapes. The event model has fourteen ops
(`create`, `status`, `body`, `comment`, `ref`, `add-story`, `add-subtask`, `add-finding`, the
sub-entity status and body ops, `assign`, `update`; see `src/squads/_services/_import_model.py`),
each with its own required fields (`target` rather than `id`, `message`, `force`, ...). The adopter
found them by trial and error against the checker's messages.

Recommendation: a reference table in `docs/adoption.md` of every op with its required and
optional fields and one example line each, or a `sq import --schema` that prints it from the
model so it cannot drift.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — sync reports an older release's generated pointer as 'had drifted'

<!-- sq:finding:F2:body -->
Report point 11.4, first two sub-points. **Driven** (wording) and **read** (cause).

After an upgrade, `sq sync` reports every regenerated agent pointer as
`.claude/agents/<slug>.md: had drifted — regenerated by this sync (backend: claude_code)`, even
when nobody edited it and the content is simply the older release's generator output. Reproduced in
a scratch squad by changing a pointer and running `sync`: the message is the same whether the file
was hand-edited or just stale. The report read "drifted" as "someone tampered with it".

Cause: `_entry_drift_report` in `src/squads/_services/_maintenance.py` compares before/after
content only. Sync does know the recorded `squads_version` in `.squads.toml`, so when it is older
than the running version the line could say "outdated (generated by <old version>) — regenerated".

Related, **inferred**: after `migrate up`, which already regenerates CLAUDE.md and the skills, the
`run sq sync` instruction and the per-command "managed files at <old>" notice do not say what is
left for sync to do (the agent pointers and the version stamp), so an operator cannot tell whether
the two steps overlap.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — No warning when a type holds items but no active role authors it

<!-- sq:finding:F3:body -->
Report point 11.5. **Driven.**

Reproduction in a scratch squad: create a review, archive the `reviewer` role
(`sq role reviewer status Archived`), `sq sync`. The "Team workflow" bullet "The code reviewer
authors reviews" disappears from CLAUDE.md, and `sq check` stays clean (exit 0) although review
items exist and no active role authors the type.

The adopter hit this through an upgrade: its old CLAUDE.md listed the reviewer line for a role that
was never active; the new one lists only active roles, so the line vanished and the gap was only
visible by diffing CLAUDE.md.

Recommendation: a `sq check` warning (squad-level rule) when a type holds open items, or any items,
and no active role authors it, naming the catalog role that would (`sq role activate <slug>`).
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Index-lock contention is silent, and a 10 s wait ends in a raw Timeout traceback

<!-- sq:finding:F4:body -->
Report point 14.1. **Driven.** Worse than reported.

The index lock (`IndexStore`, `src/squads/_index/_store.py`) is a `filelock.FileLock` with a
10 s `lock_timeout`. Reproduction in a scratch squad: hold `squads/.squads.json.lock` from another
process for 14 s, then run `sq review <n> comment --as reviewer -m probe`:

- nothing is printed while it waits (11.4 s wall time);
- after 10 s it fails with an unhandled `filelock._error.Timeout` and a full Rich traceback, exit 1;
- nothing was written (the comment is absent afterwards), so the data stays safe.

So under real contention (the adopter ran four writers at once, and a 21-write loop took over
120 s) a write either waits silently, which looks like a hang, or dies with a traceback, which is
not a `SquadsError` and breaks the clean-error contract (CLAUDE.md: user-facing errors subclass
`SquadsError`). An agent seeing exit 1 and a stack trace may retry or misreport.

Recommendation: wrap the timeout as a `SquadsError` that names the lock file and says the write did
not happen and can be retried; print a one-line "waiting for the index lock…" on stderr after about
a second; consider a longer or configurable timeout. The batch-write suggestion in the report is
already served by `sq import -`. The daemon work (ADR-1052) changes this path and should carry the
same guarantees.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — A milestone body cannot round-trip: tag refused, rendered roll-up duplicated

<!-- sq:finding:F5:body -->
Report point 14.2. **Driven.** Two related defects.

1. Feeding the body back with the tag in it is refused. A body file containing the
   `sq:view:milestone_rollup` tag line (the one sq placed) gives
   `body must not contain sq marker comments ... Write the tag without its HTML-comment wrapper`,
   which does not tell the user the right fix: leave the tag out, and sq keeps it in place.
2. Feeding back the body that sq prints silently duplicates the roll-up. `show --json` returns
   the body with the view **rendered** (the Delivered / Outstanding / Settled sections), not the
   tag. Writing that text back with `sq milestone <n> body --force --file` succeeds, and the
   milestone then shows the roll-up twice: once as frozen static prose that will never update, and
   once live from the tag. `sq check` does not notice.

Reproduced on a scratch milestone (`create milestone`, `body -m`, `show --json | jq -r .body`,
`body --force --file`, `show --full`).

Recommendation: give the read surface a way to get the stored body (tags as tags), or have
`body --force` recognise and drop an unchanged rendered view; and word the refusal so it names the
fix for an already-placed view tag.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Operator-assigned subtasks need --force to go Todo to Done

<!-- sq:finding:F6:body -->
Report point 14.3. **Read.**

The bundled `subentity` lifecycle (`src/squads/_specs/workflow.toml`) allows Todo to InProgress,
Blocked or Cancelled only. A subtask assigned to an operator for a manual step is never moved to
InProgress by anyone, so closing it after the human has done it needs `--force`. Two agents at the
adopter did exactly that, which trains agents to reach for `--force` on the normal path.

Recommendation: allow Todo to Done in the bundled subtask lifecycle, or give operator-assigned
subtasks a lighter path. A project can already change this with a lifecycle override, but the
default should not require a force for an ordinary case.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Finding lifecycle has no Noted or Deferred state

<!-- sq:finding:F7:body -->
Report points 14.4 and 14.10 (second sub-point). **Read.**

The bundled `finding` lifecycle is Open to Fixed or WontFix, Fixed to Verified or Open, WontFix to
Open, and nothing else. Two ordinary outcomes have no state:

- an `info` finding that records confirmed-good points (nothing to fix), which can only stay Open
  or be forced closed;
- a finding handed to a later item, which can only be WontFix with a note saying it is really
  deferred, which misstates the decision.

Both leave Open findings behind that are not real debt, or terminal states that say the wrong
thing. Recommendation: a `Noted` (or Open to Verified for info) and a `Deferred` state, the latter
expecting a ref to the item that carries the work, so `sq check` can verify the pointer.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — sq list has no compact form; long titles wrap over several lines

<!-- sq:finding:F8:body -->
Report point 14.7, second sub-point. **Driven.**

`sq list` has no compact form: in a narrow terminal each long title wraps over three to five lines,
so a list of a few dozen decisions runs to hundreds of lines. `sq list --help` offers filters,
sorting and `--json`, but no truncation. Recommendation: a `--compact` flag (one line per item,
truncated title), or truncate by default when stdout is a terminal narrower than the table.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — sq create bug has no --severity; only priority is exposed at create

<!-- sq:finding:F9:body -->
Report point 14.9. **Driven.**

`sq create bug --severity high` fails with `No such option: --severity (Possible options:
--priority)`. Severity is a declared field of the bug type (`fields` in the bundled spec, collection
`severity`), but `create` exposes only the hardcoded `--priority`, so the creating agent wrote
severity into the body prose and left the field empty. Setting it afterwards with
`update --set severity=…` works, but `create --help` does not point there.

This is the hardcoded-collection pattern: a machine surface names one collection (priority) instead
of every field the type declares. A custom type with its own badge fields has the same gap.

Also seen, **driven**: the spec declares `default = "medium"` for the bug severity field, yet a bug
created without it stores `severity: null` (`show --json`).

Recommendation: derive `create` options (or a generic `--badge CODE=VALUE`) from the type's declared
fields, and settle whether a declared default is stored at create time.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — A review can be Approved with Open findings and sq check stays silent

<!-- sq:finding:F10:body -->
Report point 14.10, first sub-point. **Driven.**

Reproduction in a scratch squad: a review with one Open finding (body written) moves Requested to
InReview to Approved with no refusal, and `sq check` reports no issues. The bundled reviewer
guidance says "don't approve with open high findings", but nothing enforces or reports it. The
adopter found 16 Approved reviews holding 27 Open findings; most had been resolved elsewhere and
never closed.

Recommendation: a `sq check` rule warning on an Approved review that holds an Open finding (or
refusing the transition without `--force`). Related, **inferred** from the lifecycle: Approved has
no outgoing transition, so reopening a review under a stricter rule needs `--force` on each one.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Bundled reviewer guidance does not say when a review is warranted

<!-- sq:finding:F11:body -->
Report point 14.11. **Read.**

The bundled reviewer guidance for the `review` type (`src/squads/_specs/playbook.toml`) says to
open a review and drive it to a verdict, but says nothing about when a review is warranted. At the
adopter the reviewer created a review item for every approved change, including ones with no
findings; the operator found them noise, since a verdict comment on the task or bug carries the
same information.

Recommendation: decide the convention and state it in the bundled guidance, for example "open a
review when it has findings; otherwise comment the verdict on the item".
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Role-override docs never show splat-refs on list fields

<!-- sq:finding:F12:body -->
Report point 14.13. **Read.**

Splat-refs work in role overrides (the adopter used `responsibilities = ["$(*self)", "…"]` and it
resolved), but the docs never say so. In `docs/overrides.md`, "Role overrides merge by field" shows
only scalar fields, and "The override grammar: shadow, append, and drop" opens with "Your
`workflow.toml` is a delta" and uses only workflow keys. A reader concludes a role's list field can
only be replaced whole, and restates the bundled list by hand, which freezes it against upgrades.

Recommendation: state in the role-override section that the same grammar applies, with a
`responsibilities = ["$(*self)", "…"]` example.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — sq role show does not say how to change a role's definition

<!-- sq:finding:F13:body -->
Report point 14.14. **Driven.**

`sq role <slug> show` ends with the role body and says nothing about where the text comes from or
how to change it, and `sq role <slug>` has no editing verb for mission, responsibilities or model.
The operator and the manager at the adopter both expected to edit the role in place; the only route,
`sq override scaffold --role <slug>`, was found by reading the docs.

Recommendation: a one-line footer on `role show`, such as "to change mission, responsibilities or
model: sq override scaffold --role <slug>, then sq sync".
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Loop step 5 narration sweep names no owner role

<!-- sq:finding:F14:body -->
Report point 14.15. **Read.**

Step 5 of the bundled orchestration loop (`templates/claude/claude_section.md.j2`, "Sweep for
process-narration before closing") tells the coordinator to run "one final subagent pass" over
delivered text but names no role, so every squad invents an owner. The bundled `tech-writer` is the
natural one, but its spec (`src/squads/_specs/roles.toml`) lists only "Write user- and
developer-facing docs" and "Keep guides current", and it ships on `haiku`, while the sweep is a
judgement pass. The adopter activated it, appended the duty with a splat-ref and raised its model.

Recommendation: give the bundled tech-writer the sweep responsibility and name it in step 5, and
reconsider its default model for that work.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — override scaffold --role writes a near-empty file

<!-- sq:finding:F15:body -->
Report point 14.16. **Driven.**

`sq override scaffold --role tech-writer` writes two lines: the base-version stamp and
`# Role override for 'tech-writer'. Add fields to override (e.g. full_name, model).`
`scaffold --new` stubs the essential fields and lists the advanced ones as comments.

Recommendation: have `--role` write every overridable field commented out with its current bundled
value (`# model = "haiku"`, `# responsibilities = [ … ]`), plus a commented
`# responsibilities = ["$(*self)", "…"]` line showing how to append.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — A second author on a type silently drops its CLAUDE.md workflow bullet

<!-- sq:finding:F16:body -->
Report point 14.17. **Read** (cause) and **driven** (effect).

`authoring_owner` (`src/squads/_interactions/__init__.py`) returns `None` when a type has more
than one in-lane author, and `templates/claude/claude_section.md.j2` renders the "authors" bullet
only when it gets an owner. So declaring a second author on a type (the adopter added a custom role
with `authors = true` on reviews, through the playbook append idiom) silently removes that type's
line from the Team workflow region of CLAUDE.md. `sync` prints nothing and `sq check` is clean.

The bundle already shows it: `guide` declares two authors (architect and tech-writer), and neither
this repository's CLAUDE.md nor a fresh scratch squad's has a guides bullet. The dropped line was
also the region's only mention of `add-finding`; the operator read the diff as "the reviewer was
removed".

Recommendation: render the bullet for any number of authors ("The code reviewer and the UX
designer author reviews …"), and consider a note beside `authors = true` in the scaffolded
playbook that a second author changes the generated workflow list.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Bundled handoffs hardcode @reviewer instead of the review's author

<!-- sq:finding:F17:body -->
Report point 14.18. **Read.**

The bundled `*dev` guide on `review` (`src/squads/_specs/playbook.toml`) hands back with
"`@reviewer` once all findings are Fixed, for re-review", and the bug guide says "`@reviewer`/`@qa`".
When another role also authors reviews, a developer following the generated `sq-review` skill
mentions the code reviewer on a review someone else opened, and the actual author's inbox stays
empty. A project cannot fix one guide by append: changing the `*dev` line means restating the whole
`roles` array of the type without `"$(*self)"`, which freezes every bundled guide of that type.

Recommendation: word the handoff by the review's author ("mention the review's author, shown on
`show`"), and allow a playbook override to replace a single guide by slug while the rest keep
tracking the bundle.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

---
id: BUG-784
sequence_id: 784
type: bug
title: sq check does not notice missing per-entry backend pointer files
status: Verified
author: qa
severity: high
created_at: '2026-08-22T10:06:36Z'
updated_at: '2026-08-22T11:22:38Z'
---
<!-- sq:body -->
Driven end to end on a fresh throwaway squad with both backends active
(`--backend claude_code --backend agents_md`), extending the coordinator's own reproduction:

    sq init --roles minimal --backend claude_code --backend agents_md
    rm -rf .claude/agents .claude/skills .agents_md
    sq check                    -> exit 0, zero mentions of any missing pointer
    rm CLAUDE.md
    sq check                    -> exit 3, reports CLAUDE.md missing (backend_reconciled works
                                    for the one path each backend actually declares)

`_backend_reconciled` (`_services/_validators.py`) reports "managed file missing — run `sq
sync`" for every path a backend's `managed_paths(ctx)` declares. Both bundled backends declare
only their single compiled top-level document: `AgentBackend.managed_paths` for `claude_code`
returns `[CLAUDE.md, .claude/settings.json]`; for `agents_md` it returns `[AGENTS.md]` (both
read directly from `_backend.py`). Neither declares a single per-entry path, so the check never
looks for one, on either backend.

## Which generated per-entry artifacts are unreported — both backends, driven

- `claude_code`: `.claude/agents/<slug>.md` (one file per active role) and
  `.claude/skills/<slug>/SKILL.md` (one directory per managed skill).
- `agents_md`: `.agents_md/roles/<slug>.md` and `.agents_md/skills/<slug>.md` — staging files
  `write_managed` compiles `AGENTS.md` from; they are not visible in `AGENTS.md` itself, so
  their absence is invisible in two places at once.

Deleting any combination of these — one directory, all of them, both backends' sets together —
leaves `sq check` at exit 0 with no mention of any of them, confirmed above. Deleting `AGENTS.md`
or `CLAUDE.md` (the one path each backend does declare) is caught immediately, at exit 3 — this
is a scope gap in what is declared, not a defect in the comparison itself.

## Partial loss behaves exactly like total loss

Driven with two active roles (`manager`, `qa`): deleting only `qa`'s `.claude/agents/qa.md`
(leaving `manager.md` in place) is silent in exactly the same way as deleting the whole
directory — `sq check` exit 0 either way. Same result deleting only one skill's pointer
directory, and only one role's `agents_md` staging file. The check has no notion of "how many
of the roster's pointers exist"; it only ever asks about the fixed list `managed_paths`
declares, so any per-entry loss, one file or all of them, is identically invisible.

## The retired-role case, driven, and why the fix must not touch it

Retirement is a *deliberate* removal, and today it behaves correctly: retiring `qa`
(`sq role qa status Archived`) removes `.claude/agents/qa.md` and `.agents_md/roles/qa.md` via
each backend's own `remove_artifacts`, and `sq check` stays clean, exit 0, both before and after
— correctly, since a retired role having no pointer is not a fault. Reactivating it
(`sq role qa status Active`) regenerates both files and `sq check` stays clean throughout.

This is the shape any fix has to preserve, not incidentally but as a hard constraint: whatever
set of per-entry paths a widened `managed_paths` (or an equivalent probe) reports on, it must be
scoped to the roster's *currently live* entries — the same predicate `_project_roster_item`
already uses to decide who gets a pointer at all — never to every slug that ever had one.
Checking against a fixed or historical slug list would turn every retire/reactivate cycle into a
false positive on the retired side, or a false negative on the reactivated side if reactivation
raced the check. This constrains the fix; it is not itself the fix.

## What the operator sees today: nothing, anywhere, driven

With `qa`'s `.claude/agents/qa.md` deleted (not retired — just gone), checked every other
surface that might plausibly hint at the disagreement: `sq role qa show` renders a normal card
from the item, unaware the file backing its own pointer is gone; `sq list -t role` and
`sq role list` (including its "Live" column) both read the item's status field, never the
filesystem, so both show `qa` as perfectly live; `sq sync` regenerates the missing file with no
message that anything had been missing beforehand — a clean, silent fix that reveals nothing
about the fault it just corrected. `candidate_orphans` (the mechanism behind `sq init`/`adopt`'s
orphan-pointer warning) is the closest existing relative in spirit, but checks the opposite
direction — an extra pointer with no matching roster entry — and only runs at `init`/`adopt`,
never at `sq check` or `sq sync`. No surface, anywhere in the CLI, currently tells an operator
that the roster and the on-disk agent configuration disagree.

## Which exposure this was driven against

`.claude/` and `.agents_md/` are committed by default in a freshly-initialised squad — confirmed
against this throwaway squad's own `.gitignore` files (root and `squads/`), neither of which
excludes either directory. So the case driven throughout this bug is a **deleted or
hand-tidied file** in a squad whose config is already tracked — not a fresh clone. An adopter
who has gitignored `.claude/`/`.agents_md/` themselves (a real, supported choice this tool does
not forbid) would hit the same silent gap on every fresh clone, which is the sharper case: no
file was ever deleted, the pointer simply never existed on that checkout, and `sq check` would
still say nothing. That case was reasoned about, not driven — it depends on version-control
state outside what one `sq` invocation can exercise directly.

## Relationship to the currency/drift proposal in flight

A separate architect decision, currently Proposed and not yet ruled on, proposes going further
than presence: rendering each pointer fresh and diffing it against what is on disk, to catch a
pointer that exists but has drifted stale. This bug does not depend on that decision landing,
and is not superseded by it either way it is ruled: presence is the strictly weaker prerequisite
a currency check would still need (there is nothing to diff against if the file were never
checked for at all), so closing this gap does not pre-empt or conflict with that separate,
unsettled question.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T10:33:22Z] Pierre Chat:
  - Severity for the missing per-entry pointer report: warn, with error kept for the top-level managed files. An adopter who deliberately gitignores generated config made a choice, so erroring on their intent is wrong on its own merits and not only because a patch upgrade must not move their exit code. Ending the silence is the point; failing their gate is not. Raising it later would be a minor, not a patch.
- [2026-08-22T11:10:42Z] Catherine Manager:
  - Fix landed in 383d5e8 on release/0.14 (TASK-785), shipping in 0.13.1. Verified the severity split myself: with the per-entry pointers deleted and the top-level files intact, sq check emits 11 warn lines and exits 0; sq sync then reports 11 regenerations and a second sync is silent; retire and reactivate stay clean. Deleting a top-level managed file still errors at exit 3, unchanged.
  - One correction to the premise of the severity ruling, driven. An adopter who gitignores the whole .claude directory was ALREADY failing sq check at exit 3 before this change, because .claude/settings.json is a declared top-level path and reports at error. So the feared patch-bump exit-code regression did not exist for that shape - their gate was already red. The warn ruling is still right, since it avoids adding new errors, but the specific worry that motivated it was not real. Whether erroring on settings.json for an adopter who deliberately ignores generated config is itself defensible is a separate question I have not opened.
- [2026-08-22T11:21:39Z] Mara Tester:
  - Verified on 383d5e8 against this bug's own reproduction, all in throwaway squads with both backends active. Severity split, exit code asserted directly on $? (not through a pipe): per-entry pointers gone (both backends, all of .claude/agents, .claude/skills, .agents_md/roles, .agents_md/skills) -> 22 warn lines, one per entry naming its backend, EXIT_CODE=0. CLAUDE.md gone -> error, EXIT_CODE=3. AGENTS.md gone -> error, EXIT_CODE=3. .claude/settings.json gone -> error, EXIT_CODE=3 -- all three top-level paths unchanged at error.
  - agents_md staging confirmed reported: 11 of the 22 warn lines above are .agents_md/roles/<slug>.md and .agents_md/skills/<slug>.md -- the half I originally found doubly silent.
  - Partial vs total: with two live roles, deleting only qa's .claude/agents/qa.md named exactly that file (manager's untouched), EXIT_CODE=0 -- no longer collapses to whole-set behaviour.
  - Retire/reactivate driven as a full cycle on both backends (activate -> check clean -> retire -> check clean, pointers withdrawn on both -> reactivate -> check clean, pointers regenerated on both), plus the case this bug named specifically: dropped 'epic' via a workflow override (sq-epic's pointer withdrawn), sq check reported only the pre-existing skill-type-gone warning, NOT a false 'pointer missing' -- restoring the type re-materialised it and check went clean again. Not a permanent false positive.
  - sq sync reporting: each regenerated file named with its backend ('<path>: was missing — regenerated by this sync (backend: <name>)'); a second sync on the now-healthy squad is silent; captured a healthy squad's sq sync output on a worktree at 383d5e8^ (pre-fix) and on current HEAD and diffed them byte-for-byte -- identical ('synced managed files to this squads version', nothing else).
  - Value-skew rule (ADR-783): a role item with a hand-rolled title/description skew now makes sq check say 'title, description drift between frontmatter and index; run sq repair...' at warn -- it no longer claims no issues once sync has said to run sq repair. Drove the same for priority and title on a plain task (fields with no bespoke predicate before) and confirmed status still reports too -- the generalisation is real, not name-only. Exit code 0 throughout (checked directly). Zero-fire property driven: a role with an unapplied full_name/mission override (frontmatter and index still agreeing on the bundled default) is clean before sq sync AND clean after -- the pre-fix-corpus shape never false-positives.
  - Corrected premise confirmed, not taken on your word: reproduced on a real worktree at 383d5e8^ (pre-fix). Deleting the WHOLE .claude/ directory there already produced EXIT_CODE=3, from the pre-existing (and in this commit, unchanged) settings.json top-level rule -- managed_paths itself was not touched by 383d5e8, only a new managed_entry_paths method was added. So the patch-upgrade regression the warn level guards against does not exist for a fully-gitignored .claude/; it exists for the narrower shape of gitignoring only the per-entry pointer paths while settings.json/CLAUDE.md stay tracked -- confirmed that narrower shape was exit 0 pre-fix (the actual bug) and stays exit 0 post-fix (now with warn lines). Your correction holds.
<!-- sq:discussion:end -->

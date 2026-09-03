---
id: REV-881
sequence_id: 881
type: review
title: Corpus strip in the repair sweep
status: Approved
author: reviewer
refs:
- TASK-849:addresses
- ADR-776
- TASK-853
subentities:
- local_id: F1
  title: Both adopter announcements deny the role half of the sweep
  status: Fixed
  severity: high
- local_id: F2
  title: sq migrate up never announces the content it rewrote
  status: Fixed
  severity: medium
- local_id: F3
  title: A declared type shadowing an authored skill slug deletes its body
  status: Fixed
  severity: medium
- local_id: F4
  title: Four of ten skill-body corpus params pass with the sweep disabled
  status: Fixed
  severity: medium
- local_id: F5
  title: The ADR gives a false reason for authored content being unreachable
  status: Fixed
  severity: low
- local_id: F6
  title: The frozen list's own prose miscounts it and documents the wrong constant
  status: Fixed
  severity: low
- local_id: F7
  title: docs still describe sq repair as an index-only job
  status: Fixed
  severity: low
created_at: '2026-09-02T12:23:23Z'
updated_at: '2026-09-02T15:34:20Z'
---
<!-- sq:body -->
Review of the corpus strip on `release/0.14` at **b37cdc9d** ("Stripped the retired regions from
this repository's corpus"), covering TASK-849 and its seven subtasks, commits `0f51411`,
`1cf1d30`, `b37cdc9`, against ADR-776's fourth 2026-09-01 amendment.

## What I drove

Everything below was executed, not read, in scratch squads nested under the session scratchpad.
This repository's committed corpus was never written to.

- **Reproduced the corpus strip independently.** Extracted `squads/` at `1cf1d30` into a scratch
  tree with its own `.squads.toml`, ran `sq repair`, and compared against the committed `b37cdc9`
  corpus. **654 item files rewritten; only three files differ** from the commit — `.squads.json`
  and the two task files carrying board writes the manager made in the same working tree
  (`TASK-849`, `TASK-853`: status moves and new comments, verified line by line, no rewritten
  state). The committed mechanical diff is exactly what the sweep produces, with nothing added by
  hand.
- **Re-derived the census through my own scanner**, validated against a known positive first:
  **632 files carry a balanced `sq:summary` pair; 436 files carry 1545 balanced `:head` pairs**,
  kinds exactly `subtask`/`finding`/`story`. Matches the recorded numbers.
- **Checked the strip destroyed no authored content here**: for every retired region in the
  pre-strip corpus, computed whether its open marker fell inside a `:body` or `:discussion`
  region. **Zero.**
- **Idempotence on the real corpus**: a second `sq repair` reports nothing stripped and leaves
  every `.md` and the index byte-identical (only `.reflog.jsonl` grows).
- **Never-carried, proven as "no file written"** rather than "written identically": on a fresh
  squad, no `.md` mtime changes across `sq repair`.
- **`sq repair --renumber` over the pre-strip corpus** produces output byte-identical to plain
  `sq repair` — the combination the merge path will actually exercise is safe.
- **Five falsification drills**, run as pytest plugins on `PYTHONPATH` so no repository file was
  edited. Keying the body sweep on the item type reddens both `custom skill survives` params;
  disabling the skill sweep reddens 6 tests; splitting `_record_pending_rewrite` into two entries
  built from the original text reddens the composition test on "the canonicalisation discarded the
  strip"; pinning `is_dev=False` reddens the developer `model` case; leaving the removed keys on
  the parsed `Item` reddens the index-agreement test and all nine migrating corpus params. The
  mechanism is genuinely guarded.
- **Untested combinations driven by hand and found sound**: a system skill needing ref
  canonicalisation *and* body emptying composes correctly; an unbalanced retired region is skipped
  and left for `sq check`; a role whose `extra` would empty keeps `slug` and checks clean.
- Full suite at HEAD, once, to a file: **4499 passed, 8 skipped, 0 FAILED**. `sq check` clean.

## The shape of the verdict

The mechanism is right. The discriminators are the correct ones, the composition holds, the sweep
is idempotent, and the diff this repository committed is reproducible byte for byte. What is wrong
is the **announcement**, which is the entire mitigation ADR-776 §5 accepted in place of prevention —
and one genuine data-loss path the live-spec discriminator opens in the direction its own docstring
does not consider.

Findings are on their own sub-entity discussions.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 880 add-finding "…" --severity medium`; track with `sq review 880 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Both adopter announcements deny the role half of the sweep

<!-- sq:finding:F1:body -->
Both adopter-facing announcements state that no item body and no frontmatter field is touched.
`1cf1d30` then made the sweep empty **every role item's body** and remove **nine `extra` keys**
from it, and updated neither text.

**Driven.** Migrating the frozen `v0_11` fixture with `sq migrate up` (unmodified tree, HEAD):

```
--- orig/agents/roles/ROLE-000001-dev-agent.md
+++ migrated/agents/roles/ROLE-000001-dev-agent.md
@@
-  full_name: Dev Agent
@@
-# Dev Agent
-
-A minimal developer role for corpus testing.
```

That is one frontmatter field and one item body, on the path the text describes.

**What each text says, and why it is wrong.**

`_migrations/_v0_11_to_v0_14.py::MANUAL`, section "Two stored regions are removed from your item
files" — the runbook `sq migrate up` points a 0.11 adopter at:

- the heading says **two** region families; three things are removed (summary, head, and bodies),
  plus frontmatter keys;
- "What goes" lists the roll-up table, the badge line and a template-owned skill's body. **A
  role's body and its `extra` mirror are not mentioned at all.**
- "Your own content is untouched. ... So are every sub-entity's body and discussion, **every item
  body, and every frontmatter field**." Both clauses are false for a role item.

`CHANGELOG.md` (`## [0.14.0]`, `### Changed`) — the release note ADR-776 §7 names as the *only*
announcement the already-stamped population gets, since `chlog` is keyed to a transition they will
never perform:

- "removes **two** stored regions" and, in the same paragraph, "All **three** are removed" —
  internally inconsistent in its own first sentence;
- "**only a template-owned one is touched at all**" — true of skills, false of the corpus: every
  role body is emptied too, and roles are never mentioned in the entry;
- "so is every sub-entity body and discussion, **every item body, and every frontmatter field**" —
  the same false clause, copied.

Note also the `### Migration` paragraph immediately below: "**No existing item is rewritten and no
frontmatter shape changed.**" That is a true statement about the *runner* and a false one about
`sq migrate up`, which is the command the heading tells them to run — I drove 6 item files
rewritten on `v0_11`.

**Why this is the one that blocks.** ADR-776 §5 accepts "an operator gets a content diff they did
not ask for" explicitly as *announced, not prevented*. These two texts are that announcement. A
release note that promises "every frontmatter field" survives, on the release that deletes nine of
them from every role item, does not just under-describe the change — it tells an adopter the diff
they are looking at is a bug.

**Fix is text only.** ST3 wrote both while the role half was deliberately out of the build (see its
2026-09-02T10:00:46Z comment, which says so and lists the two role claims it withheld *because they
were false then*). `1cf1d30` made them true and left the withholding in place. Per house rule the
changelog prose is the tech-writer's to author, not a dev's or mine.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-09-02T12:54:35Z] Theo Writer:
  - Fixed. Both texts rewritten from the code and from my own drives, not from the reported summary — every claim below is one I ran.
    
    **What I established before writing.** On the frozen `v0_11` fixture, `sq migrate up` rewrites **six item files** (`FEAT-2`, `TASK-3`, `REV-6`, `ROLE-1`, `SKILL-7`, `SKILL-8`) plus the managed `CLAUDE.md` region, and the role file loses `extra.full_name` and its whole body. Confirms the finding.
    
    **The removed and retained sets, derived rather than copied.** `_retired_role_extra_keys` is `(RETIRED_ROLE_EXTRA_KEYS | RoleDef.extra_keys()) - RoleDef.stored_extra_keys(is_dev=…)`, intersected with what the item carries. Driven on a constructed role of each shape:
    
    - **removed from every role**: `agreements`, `can_spawn`, `color`, `description`, `full_name`, `mission`, `responsibilities`, `skills`, `title` — nine, matching F6's count against the docstring's "eight";
    - **also removed from a non-developer role**: `model`, since `stored_extra_keys(is_dev=False)` is `{slug}` alone;
    - **retained**: `slug` always, `is_default` always, and `model`/`is_dev`/`tech` on a developer role.
    
    `is_default` is the one the brief I was given did not name, and it is retained — it is absent from `RETIRED_ROLE_EXTRA_KEYS` deliberately because `sq role set-default` still writes it. Cross-checked against the committed strip on this repository's own corpus: `ROLE-000001-manager` lost ten keys including `model: opus`, and kept exactly `slug` and `is_default: true`. Both texts now state that set.
    
    **A route neither text named, and neither did the review: `sq adopt`.** `adopt` calls `Service.repair()`, so it performs the whole sweep. Driven on the `v0_11` corpus restamped to 0.14 so no runner applies: `sq adopt` rewrote the same six item files and wrote a `repair` reflog line naming them, with nothing on the console. `sq renumber` reaches it too — it calls `_rebuild_index_from_disk` directly, where the file writes happen, so it strips silently and records nothing at all (driven: after `sq renumber --from 5 --onto 100`, every retired region and every mirror key was gone, with no `stripped` anywhere in its reflog line). Both texts now say every command that rebuilds the index performs the removal, name all four, and say that only `sq repair` announces it.
    
    That matters most for the population this release cannot reach with a runbook: someone adopting squads into an existing folder of squads-native markdown meets the rewrite on their first `sq adopt`, having read neither the changelog nor `chlog`.
    
    **One claim I removed rather than corrected.** The old note justified emptying a body with "an absent region is what `sq skill <slug> show` reads as 'no item for this slug'". That is not true of this build — detail on F5's discussion, where it belongs with the other false-reason finding. Both texts now assert only what I could drive: the marker pair stays and the contents go.
    
    **Also corrected: the `### Migration` paragraph.** "No existing item is rewritten and no frontmatter shape changed" was true of the runner and false of `sq migrate up`, which is the command its own heading tells the adopter to run. It now separates the two — the runner's writes are still described as paths that did not exist, and the rebuild that follows is stated as rewriting existing items.
    
    Verified after the edit: `sq migrate chlog v0.7.0..v0.14.0` renders the new section correctly on the fixture.
- [2026-09-02T13:12:07Z] Theo Writer:
  - **Correcting my own comment above.** The build moved under it — `98ca0638` removed the skill half of the sweep and gave `sq migrate up` the strip notice — so two things I wrote an hour ago are no longer true, and both texts have been rewritten again against the code as it now stands. Re-driven from scratch on the current tree rather than adjusted:
    
    **What the sweep does now**, `sq migrate up` on the frozen `v0_11` fixture: **four** item files rewritten (`FEAT-2`, `TASK-3`, `REV-6`, `ROLE-1`), not six. `SKILL-7` and `SKILL-8` are byte-identical — `_sweep_empties_body` returns `item.type == ROSTER_ROLE` and nothing else. Both greeting's stored body and its text remain on disk, and `sq search "Detect and greet"` still matches it, while the role's mission no longer matches anything. `sq skill greeting show` renders the template definition regardless of what is stored, so the leftover bytes are inert.
    
    Every clause saying a template-owned skill body is emptied is **removed** from the CHANGELOG entry and the `MANUAL` string, not softened, and the same clause is out of the three docs that carried it. Both texts now say plainly that no skill body is touched, authored or template-owned, and say why — the two are indistinguishable on disk because the classification moves with the vocabulary and the body was written under an earlier one. The role half is unchanged and re-verified: nine mirror keys plus `model` on a non-developer role, `slug` and `is_default` retained for every role and `model`/`is_dev`/`tech` additionally for a developer.
    
    **"Only `sq repair` announces it" is also gone.** I drove all four routes on the current build rather than reasoning about which reach the sweep:
    
    - `sq repair` — strips, prints `stripped retired regions from 4 item files — review the diff`, reflog `repair` line names the ids;
    - `sq migrate up` — strips, prints the same sentence after `index rebuilt`, reflog `repair` line names the ids;
    - `sq adopt` — strips, prints **nothing** about it, reflog `repair` line names the ids;
    - `sq renumber` — strips, prints nothing, and writes only a `renumber` line: no `stripped` anywhere in its reflog.
    
    So the announcement now covers two of the four routes, and the texts say exactly that: which two print it, which one records it in the reflog only, and which one records nothing, with `git diff` named as the fallback for the last two. `sq adopt` remains the route worth flagging — it is the first command an adopter runs over an existing folder of squads-native markdown, and it rewrites it silently.
    
    Re-verified after the rewrite on the current build: fresh squad `sq repair` writes no file (byte-identical), a second `sq repair` over a stripped corpus is byte-identical, and `sq migrate chlog` renders the new section correctly.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — sq migrate up never announces the content it rewrote

<!-- sq:finding:F2:body -->
ADR-776 §5: "the sweep reports the files it touched the way `canonicalized` already does, in the
result and in the reflog delta, so the diff is stated rather than discovered." `sq repair` does
this. **`sq migrate up` does not** — and that is the only route the 0.11 population takes.

**Driven** on the frozen `v0_11` fixture at HEAD:

```
$ sq migrate up
squads 0.14.0 detected (managed files at 0.7.0). Run `sq sync` to refresh them.
  0.14.0 (schema v0.11->v0.14): Two new bundled item types, contract (PRD) and milestone (MILE): ...
migrated to schema v0.14; index rebuilt — run `sq sync` to refresh managed files
manual steps remain — read them with `sq migrate chlog v0.7.0..v0.14.0`
```

Reflog for that same run:

```
repair  {'items': 10, 'missing': 0, 'unreadable': 0, 'canonicalized': 0, 'stripped': 6}
migrate {'from_schema': '0.11', 'to_schema': '0.14', 'applied': 1}
```

Six item files had their content rewritten. The console says "index rebuilt". Nothing on stdout
says a byte of content moved.

**Cause.** `MaintenanceMixin.run_pending_migrations` calls `await self.repair()` and discards the
`RepairResult` (`_services/_maintenance.py`, the `if applied:` block). `_cli/_migrate.py::up` only
ever sees the `list[Migration]`, so it has nothing to print.

**Two aggravating facts.**

1. `sq repair` has **no `--json`**. I checked `--help`: the only options are `--renumber` and
   `--help`. So neither `stripped` nor the pre-existing `canonicalized` has a machine-readable
   surface anywhere except the reflog — a tooling consumer that wants to know whether a repair
   rewrote content has to parse `.reflog.jsonl`. That is not a regression this change introduced,
   but this change is what made it matter: the blast radius went from a rare ref re-encoding to
   654 files on this repository alone.
2. The indirect announcement — "manual steps remain — read them with `sq migrate chlog …`" — does
   exist, and the MANUAL section does describe the removal. So the adopter is *pointed at* the
   information rather than told. That would be defensible if the MANUAL were accurate; F1 is that
   it is not.

**Smallest correction:** have `run_pending_migrations` return, or the CLI re-read, the strip count
and print the same line `sq repair` prints. One console line on the path that reaches the only
population that has no other announcement.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-09-02T12:53:46Z] Elias Python:
  - Fixed. `run_pending_migrations` now returns a `MigrationRun` (`applied` + the rebuild's own `RepairResult`, `None` exactly when nothing applied) instead of discarding it, and `sq migrate up` prints the notice after "index rebuilt".
    
    The sentence has one constructor — `RepairResult.strip_notice()` — so `sq repair` and `sq migrate up` cannot drift into different wording, and neither can quietly lose it again.
    
    **Driven** on a real 0.12.1 → 0.14 upgrade:
    
    ```
    migrated to schema v0.14; index rebuilt — run `sq sync` to refresh managed files
    stripped retired regions from 4 item files — review the diff
    manual steps remain — read them with `sq migrate chlog v0.12.1..v0.14.0`
    ```
    
    Test `test_migrate_up_announces_the_content_it_rewrote` asserts against a real rewrite (the fixture's own bytes before/after), not the string alone, so it also reddens if a run announced a strip it did not perform. Falsified: dropping the print reddens it.
    
    **On `sq repair --json`, since you asked rather than assumed: yes, it should exist, and not in this fix.** The reflog being the only machine-readable surface for `stripped`/`canonicalized` is a real gap and your blast-radius argument is right. But adding `--json` is a new output contract — a documented shape, `--json` parity expectations against the other verbs, and adopter-facing docs — which is a decision and a ticket, not a line I slip into a review fix. Not tracked yet; it wants a bug or a follow-up task, and I have not created one.
- [2026-09-02T13:14:34Z] Catherine Manager:
  - Reopened: the fix covered sq migrate up, but the writer drove all four routes and two still say nothing. sq adopt performs the whole sweep and prints nothing, recording it only in the reflog — and that is the population docs/adoption.md addresses, so a first adopt over an existing folder of squads-native markdown rewrites it silently. sq renumber reaches the same sweep through _rebuild_index_from_disk and records nothing about it at all.
  - This widens the finding rather than duplicating it: the missing announcement is on two more commands, and renumber has no surface at all. The ruling this release was accepted on was announced-not-prevented; two of four doors do not announce.
- [2026-09-02T15:22:22Z] Elias Python:
  - Fixed, on the two routes that were still silent. `sq adopt` and `sq renumber` now print the same sentence `repair` and `migrate up` print, and `renumber` records the strip in its reflog line as well.
    
    No new wording: `strip_notice()` moved from a method on `RepairResult` to a module-level constructor in `_services/_results.py` that both result types delegate to, so there is still exactly one place the sentence exists. `AdoptResult` now carries the whole `RepairResult` of its import sweep (its `imported` count became a property of it, rather than a second stored number), and `RenumberResult` carries the `stripped` list its shared rebuild produced.
    
    Driven on all four routes before and after, each on its own staged corpus, console and reflog:
    
    - `sq repair` — before: announced; reflog `stripped:["ROLE-1","ROLE-2"]`. After: unchanged.
    - `sq migrate up` — before: announced ("stripped retired regions from 4 item files"); reflog `repair` line carries `stripped`. After: unchanged.
    - `sq adopt` — before: panel only ("imported: 8 existing item(s)"), nothing about the rewrite; reflog `repair` line already carried `stripped:["ROLE-1","ROLE-2"]`. After: the notice prints under the panel, reflog unchanged.
    - `sq renumber` — before: "renumbered 8 item(s); counter=108" and the remap list, nothing else; reflog `renumber` delta was `{from,onto,by,remap}` with no `stripped` key at all. After: the notice prints after the count line, and the delta carries `stripped:["ROLE-101","ROLE-102"]` — the post-shift ids, because the rebuild that strips runs on the already-renamed files.
    
    Test: `tests/integration/test_sweep_routes_announce_what_they_rewrote.py`, table-driven over all four doors rather than one standing in for the rest — that is what the first pass got wrong. Each case asserts a real strip (the retired regions are gone from the corpus afterwards, matched on the file bytes, not on the sweep's own idea of what is retired), the sentence on stdout, and a reflog record. Falsified: removing the adopt print reddens adopt, removing the renumber print reddens renumber, removing the reflog key reddens renumber alone.
    
    Two things I did not do, both deliberate, neither claimed as done:
    
    - `renumber` still discards the `canonicalized` list from its rebuild. That is pre-existing and outside this finding's ruling (the strip), so I left it rather than widen the scope; `repair` has no console line for it either, so console parity across the four routes is exact.
    - `docs/adoption.md` describes the population `adopt` serves and now says less than the command does. Adopter docs are the writer's artifact, not mine. @tech-writer for that.
    
    `sq repair --json` remains untracked, as noted when this was first fixed.
- [2026-09-02T15:34:20Z] Theo Writer:
  - Writer half done. The adopter text said only `sq repair` and `sq migrate up` announce the strip — true when written, false since all four routes gained the shared notice. Corrected in six places, each verified by driving the route rather than reading the constructor:
    
    - `docs/adoption.md` — "Not every route announces it" replaced with what the four now do; the clean-tree/`git diff` advice kept, re-argued from the notice being a count and the reflog a list of ids rather than from silence.
    - `docs/faq.md` — same sentence under "Does `sq repair` change my files?", same correction.
    - `CHANGELOG.md` (0.14.0, Changed) — the same stale sentence had been spliced into the release entry too.
    - The `0.11 → 0.14` `MANUAL` runbook — likewise; nothing else in that runner touched.
    - `docs/workflow.md` reflog op table — the `renumber` row now documents `delta.stripped`, which it had no record of before, and says the ids are post-shift.
    - `docs/internals.md` — the rescan paragraph now notes all four print the one notice from a single shared constructor.
    
    Driven on staged corpora, console and reflog: `repair` (`stripped:["TASK-2","TASK-3","TASK-4"]`), `renumber --from 2 --onto 100` (notice between the count line and the remap list; `renumber` delta `stripped:["TASK-101","TASK-102","TASK-103"]` — post-shift, as you said), `adopt` on an unindexed copy (notice under the panel; `repair` line carries the ids), `migrate up` on the `v0_11` fixture (notice after "index rebuilt"; 4 files).
    
    `renumber` discarding `canonicalized` is left undocumented — it never had a sentence, and I did not give it one.
    
    Gates: 4603 passed, 12 skipped, 0 failed; ruff, ruff format, pyright 0 errors, `sq check` clean.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — A declared type shadowing an authored skill slug deletes its body

<!-- sq:finding:F3:body -->
`_sweep_empties_body` keys on `is_system_skill(slug, spec)`, which is the right call and the one
that saves `releasing-squads` (verified: 10118 bytes, byte-identical across `1cf1d30..b37cdc9`,
while the other twelve skill files lost 1003 lines between them). Its docstring justifies reading
the **live** spec in one direction only:

> a project that renamed or dropped an item type changes which per-type skills are template-owned,
> and a literal list would mistake that project's own authored skill for a generated one and empty
> it.

The same liveness produces exactly that failure when a type is **added**. Nothing in the docstring,
the subtask, or ADR-776 §6 considers that direction.

**Driven end to end, supported commands only, no hand-editing:**

```
sq init --roles core
sq skill add sq-onboarding --desc "An authored runbook"
sq skill sq-onboarding body -m "AUTHORED RUNBOOK CONTENT that must survive."
# ... later, the adopter declares an item type named `onboarding`:
#   squads/.overrides/workflow.toml  ->  [lifecycles.onboarding] + [items.onboarding]
sq workflow lint      # -> workflow spec OK — no errors or warnings.   (exit 0)
sq check              # -> exit 0
sq repair             # -> "stripped retired regions from 1 item file — review the diff"
```

Result: `BYTE-IDENTICAL: False`, `AUTHORED CONTENT SURVIVES: False`. `sq skill sq-onboarding show`
now reports `kind: system (template-owned)` and renders generated per-type content in place of the
runbook. The authored text is gone, with no copy anywhere, announced only as "1 item file".

`sq check` reports nothing about the loss (only an unrelated pointer-drift warning).

**Why this is worth a finding rather than an accepted cost.** The `sq-` prefix is explicitly *not*
reserved — the test suite parametrises `sq-onboarding` as a legitimate authored slug precisely to
make that point. So the collision is a shape the product invites, and `sq skill add` accepts it
without a word. Before this change the collision was inert: `set_body` refused *further* writes to
the reclassified skill, but what was already stored stayed on disk and stayed readable. This change
turns an inert misclassification into a silent, unrecoverable deletion, and `repair` is a verb
adopters are told to run casually (see F7).

Likelihood is low; the loss is total and undoable. I am not deciding the remedy — options I can see
are refusing an `sq-`-prefixed slug at `sq skill add`, having `sq check` report a skill whose class
flipped while it still stores an authored body, or having the sweep skip a body that does not match
what the template would render. Any of them is a decision, not a dev's choice, per ADR-776 §3.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-09-02T12:53:26Z] Elias Python:
  - Fixed — but by containment, not by a better discriminator, and the finding is broader than stated.
    
    **The corpus cannot tell.** At the moment of the sweep nothing on a skill item records which writer produced its body. `is_system_skill` is the right classifier and stays exactly where it is (including in `set_body`'s refusal), but it is a function of *today's* vocabulary in **both** halves, and the body was written under an earlier one:
    
    - `custom_skill_slugs(spec)` moves with the project — your repro.
    - `bundled_skill_slugs()` moves with the **release** — which the review treats as spec-invariant, and it is not.
    
    **Driven, no override anywhere.** Released 0.12.1 build: `sq init`, `sq skill add sq-contract`, `sq skill sq-contract body -m "AUTHORED RUNBOOK CONTENT…"` — all accepted, `kind: custom (authored)`. Then `sq migrate up` on this build: body gone, console said only "index rebuilt", reflog `stripped` listed all 4 roles and all 11 skills. `contract` and `milestone` are new bundled playbook types in 0.14, so `sq-contract`/`sq-milestone` were authorable slugs on 0.13.1 and are template-owned now, for every squad at once. Comparing the stored text to what the template renders today does not separate the two either — the rendering is version-dependent, so genuine residue from an older release matches no better than authored prose.
    
    **What landed.** `_sweep_empties_body` is now `item.type == ROSTER_ROLE`. The role half is unchanged and is safe for a different reason than "derived": `set_body` and the importer's body event refuse on the **item type**, which does not grow or shrink with a spec or a release, so no supported path has ever stored authored prose there. The skill half is dropped — being derived is not the bar; proving nothing authored it is, and only the role half clears it.
    
    Cost, from your own measurement: 12 of the 654 files this repository stripped, i.e. ~2% of the sweep's reach and 100% of its unrecoverable risk. What stays on disk is inert — neither `show` path reads it (both render), the backend leaves it byte-untouched by design, `set_body` still refuses it — and reversible: drop the type declaration and the body is readable again (re-driven, survives).
    
    **Tests.** `test_a_system_skill_body_survives_the_sweep` and `test_declaring_an_item_type_does_not_delete_an_authored_skill_of_that_name` (your repro, supported commands, override written and spec reloaded). Falsified: restoring the skill half reddens both, and 5 of the 10 corpus params.
    
    **Two things for others.** @tech-writer the CHANGELOG and `MANUAL` claims that a template-owned skill's stored body is emptied are now false in the other direction — the F1 rewrite must drop them, not just add roles. @architect the reclassification itself is untouched: a shadowed slug still *renders* the generated definition over the authored one on `sq skill show`. Nothing is destroyed, but "should `sq skill add` refuse an `sq-` slug, or `sq check` report a class flip" is still your call.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Four of ten skill-body corpus params pass with the sweep disabled

<!-- sq:finding:F4:body -->
`tests/integration/test_migration_corpus.py::test_a_system_skill_body_is_emptied_and_never_deleted_by_the_migration`
is parametrised over all ten corpus fixtures. **Four of those ten cannot go red.**

**Driven.** I disabled the skill half of the sweep entirely (a pytest plugin on `PYTHONPATH`
replacing `_sweep_empties_body` with `item.type == ROSTER_ROLE`, so no skill body is ever emptied)
and ran the three affected files:

```
FAILED ...test_a_system_skill_body_is_emptied_and_keeps_its_markers
FAILED ...[0.5-v0_5]
FAILED ...[0.7-v0_7]
FAILED ...[0.8-v0_8]
FAILED ...[0.10-v0_10]
FAILED ...[0.11-v0_11]
6 failed, 64 passed
```

`v0_1`, `v0_2`, `v0_3`, `v0_4` **passed with the mechanism switched off**. Cause: those four
fixtures carry no `skill` item at all. The skills the test then asserts on are ones the migration
runners *create*, and this build creates them with an empty body. So the assertion
`assert not (_body_region(text) or "").strip()` is confirming that a file the runner just wrote
empty is empty. Nothing was stripped; nothing can regress. (Confirmed by inspection: skill body
bytes per fixture are `v0_1/2/3/4: none`, `v0_5/7/8/10/11: 79b + 70b`, `v0_14: 79b + 70b + 857b + 940b`.)

**The fix is one line, and its sibling already has it.** The role test right below it
(`test_a_role_keeps_its_record_and_loses_its_mirror_across_the_migration`) opens with an explicit
precondition:

```python
assert set(was.get("extra", {})) & _RETIRED_MIRROR_KEYS
```

so a fixture that never carried the mirror fails loudly instead of passing quietly. The skill test
asserts only `assert system, f"{corpus_name!r} carries no system skill to assert on"` — that the
*items* exist, never that any of them stored a body. Add the matching precondition (a snapshot of
the pre-migration body, asserted non-empty) and the four vacuous params will either become real or
declare themselves as fixtures with nothing to prove.

Not a product defect. It is a coverage claim that reads as ten proofs and is five, on the half of
the sweep where the destruction risk lives.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-09-02T12:54:10Z] Elias Python:
  - Fixed. The test now snapshots each system skill's pre-migration `sq:body` region and asserts against that snapshot; a fixture storing no skill body at all skips with a reason instead of passing quietly. Its subject flipped with F3 — the body must now come out **unchanged** rather than empty — but the vacuity was orthogonal to which way the assertion points, and the precondition is what fixes it either way.
    
    Confirmed with the mechanism switched back on: exactly 5 params redden (`v0_5`, `v0_7`, `v0_8`, `v0_10`, `v0_11`), and `v0_1`–`v0_4` skip. Ten parameters that read as ten proofs are now five proofs and four honest declarations.
    
    Suite count moves accordingly: 4 params leave `passed` for `skipped`, so 12 skipped rather than 8.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — The ADR gives a false reason for authored content being unreachable

<!-- sq:finding:F5:body -->
ADR-776's fourth 2026-09-01 amendment, §6 "Adopter safety", argues the sweep cannot reach authored
content:

> Marker regions are sq-managed, no verb writes an arbitrary marker, and `find_markers` is strict,
> so **prose naming a tag inside backticks is not matched**.

The bolded clause is false. Driven (tags written below without their HTML-comment wrapper, because
`reject_markers` refuses this very finding body otherwise — which is itself the point):

- `find_markers` on a string containing a backtick-wrapped, **well-formed** `sq:summary` tag returns
  `['sq:summary']`.
- `find_markers` on a backtick-wrapped `sq:*` tag returns `[]`.

`MARKER_RE` is `<!--\s*(sq:\w[\w:-]*)\s*-->`. Backticks sit outside the match and do nothing; what
saves the `sq:*` form is that `*` is not in `[\w:-]`. `_sections.find_markers`' own docstring makes
the same conflation ("documentation references ... written in prose are not mistaken for real
markers"). `reject_markers`' docstring, one module over, already gets it right — "an author who does
that reaches for backticks first, **which do not help**" — and its refusal message says so too.

**The conclusion still holds, by a different mechanism.** What actually keeps authored bodies safe
is `reject_markers`, which refuses *any* well-formed marker in any body, comment or title on every
sq write path (`_body_mutate`, and the importer's `_sim_body`). That is a stronger guarantee than
the one the ADR states — but it is not the one the ADR states, and the next person widening the
frozen list will reason from the recorded argument.

**What the exposure looks like when the guard is bypassed.** Driven on a hand-edited task file (the
shape a merge resolution or a foreign corpus can produce): a fenced code block illustrating the
retired region, with an authored sentence before it and a sentinel sentence after it. After
`sq repair` — announced only as "stripped retired regions from 1 item file" — the fence is empty,
its illustrated rows gone; the surrounding prose and the sentinel survive.

**I checked this repository is clean of it.** For every one of the 632 + 436 pre-strip files I
computed whether each retired region's open marker fell inside a `:body` or `:discussion` region.
**Zero.** So `b37cdc9` destroyed nothing. This finding is about the recorded reason, and about the
`adopt` population ADR-776 §1 names — a corpus stamped current by `adopt` never passed
`reject_markers`, and I could not construct one to drive (see the review's "could not test").

Correct the sentence in the amendment to cite `reject_markers`, and correct
`_sections.find_markers`' docstring to say what its character class actually excludes.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-09-02T12:53:46Z] Theo Writer:
  - Read and confirmed, and it is not mine to fix — the decision record is the architect's. Routing it rather than touching it.
    
    I re-drove the two probes independently, on a string built at runtime rather than typed into a body: `find_markers` on a backtick-wrapped, well-formed `summary` tag returns that tag; on the `*` form it returns nothing. So the amendment's stated mechanism ("prose naming a tag inside backticks is not matched") is false as written, exactly as reported — the backticks are outside `MARKER_RE` and do nothing, and the `*` is what fails the `[\w:-]` class. The conclusion holds through `reject_markers`, which is the guard that actually refuses a well-formed marker on every write path.
    
    @architect this wants your ruling on §6 of the fourth amendment, and on `_sections.find_markers`' docstring making the same conflation. Leaving the finding Open and unmarked.
    
    One thing I hit while verifying the neighbouring claim, worth folding into the same read since it is the same class of defect in the same commit — the justification given for *emptying* a body rather than removing it:
    
    > a removed region is what `sq role show`/`sq skill show` read as "no item for this slug"
    
    That is false too. Driven on a fresh squad: I deleted the whole `body` marker pair from a bundled role's file and from a template-owned skill's file, then ran both `show` commands. Both rendered their definition in full, and `sq check` reported no issues. Neither path branches on the region at all — `sq role <slug> show` keys on the item's existence (its own comment says so), `sq skill <slug> show` keys on `is_system_skill`, and the phrase "no item for this slug" appears nowhere in the codebase except in the two docstrings asserting it. It reads in `_strip_retired_regions` and `_sweep_empties_body`, and it had been copied into the release note, which is where I found it.
    
    Emptying is still the right behaviour; the recorded reason for it is not a fact. I have dropped the claim from both adopter texts rather than restating it — they now say only that the marker pair stays and the contents go, which is what I could verify. The two docstrings still carry it.
- [2026-09-02T13:13:52Z] Robert Architect:
  - **Ruling: the finding is correct, and the record — not the conclusion — was wrong. Marking Fixed.**
    
    I re-drove it before ruling, with a control, because a null result from a marker search is exactly
    the shape that proves nothing on its own. On strings built at runtime: a bare well-formed `summary`
    tag returns that tag; the *same tag wrapped in backticks* returns it too, identically; the `sq:*`
    form returns nothing whether backticked or bare. Backticks are not the discriminator in either
    direction — `MARKER_RE` never sees them. The `*` failing `[\w:-]` is the whole of it.
    
    So §6's clause "so prose naming a tag inside backticks is not matched" is false as written, and
    `reject_markers` is the guard that actually holds the bullet's conclusion — ten call sites, every
    prose input that lands in a marker region, refusing any well-formed tag before any write. That is a
    stronger guarantee than the one the amendment claimed, which is precisely why it was worth
    correcting rather than softening: the conclusion never needed the bad argument.
    
    **Amended ADR-776** with a fifth amendment note (2026-09-02) that quotes the false clause, states
    what was driven, gives the corrected bullet verbatim, and says why the wrong reason mattered even
    with the right conclusion — the next person widening the frozen region-tag list reasons from the
    recorded argument, and "a quoted tag is not matched" invites the belief that a corpus is safe
    because its authors quoted, when it is safe because a guard refused the tag at the door. Those two
    diverge exactly where the guard does not run, which is the `adopt` population the amendment exists
    to reason about. The rest of §6 is untouched.
    
    **Residue that needs code, which I am not authoring here.** Two docstring corrections the record
    cannot make for itself, both flagged in the amendment as sources a reader checks next:
    
    - `_sections.find_markers`' docstring attributes the exclusion to references "written in prose"
      rather than to the character class. The project's contributor conventions carry the same sentence.
      Narrowly true of the `sq:*` example, misleading about the reason.
    - @tech-writer's second point on this thread, which I confirmed and which is the same class in the
      same commit: "a removed region is what `sq role show`/`sq skill show` read as no item for this
      slug" survives in two docstrings — `_services/_maintenance.py:268` and `:1719` — after he
      correctly dropped it from the adopter texts. It appears in no decision record, so there is
      nothing for me to amend; it is a code edit. Emptying is still the right behaviour, and it needs a
      reason that is true.
    
    @reviewer both are outside my remit on this run; neither blocks the finding, whose stated defect
    was the record.
- [2026-09-02T13:35:14Z] Theo Writer:
  - Both stated reasons corrected in code, per the architect's ruling, and re-driven with a control before writing rather than taken from the ruling.
    
    **`_sections.find_markers`' docstring.** My own control, on strings built at runtime so no literal marker sits in the probe:
    
    ```
    bare well-formed tag         -> ['sq:summary']
    same tag inside backticks    -> ['sq:summary']
    same tag in a fenced block   -> ['sq:summary']
    bare sq:* form               -> []
    sq:* inside backticks        -> []
    ```
    
    Backticks and fences change nothing in either direction; `*` is the whole difference. The docstring now says position is irrelevant, names the two real mechanisms separately — `reject_markers` for why authored content cannot carry a live marker, the `*` for why that one documented form is safe to write in prose — and records the divergence the architect asked be carried: "a quoted tag is not matched" invites the belief that a corpus is safe because its authors quoted, when it is safe because a guard refused it at the door, and the two readings part company exactly where the guard does not run — an adopted corpus whose files never passed through a write path. It also points at `_retired_region_tags` by name, since that is the list the next reader will be widening.
    
    I verified the `reject_markers` half rather than restating it: ten call sites, in `_services/_items.py`, `_services/_base.py`, `_services/_subentities.py` (four), `_services/_collab.py` and `_services/_import.py` (three).
    
    **`CLAUDE.md`'s conventions line**, same correction, and confirmed hand-edited: the bullet sits at line 134 and the managed region opens at 243, so `sq sync` will not take it back. Only that bullet changed — the diff is one hunk at `@@ -134,2 +134,7 @@`, and `sq check` is clean.
    
    **The `_maintenance.py` pair**, from the earlier instruction, is also done: `_strip_retired_regions` and `_sweep_empties_body` no longer claim a removed region reads as "no item for this slug". The honest answer turned out to be that there is no load-bearing reason, and I said so rather than inventing one — driven on a scratch squad with the whole marker pair deleted from a role file, `show`, `check`, `sync`, `repair`, `regen`, `list`, `--json` and `search` all behave identically and nothing restores the pair. What the docstring now records instead is that the pair is the shape every item file carries, plus the one mechanical fact a future reader needs: `replace_section` raises `KeyError` on an absent region, so a writer that someday reaches a role's body would fault rather than refuse — none exists today, since `set_body` refuses a role first and the role addressing group has no `body` verb.
    
    One note on scope: `ServiceCore._create_core`'s inline comment makes the same emptied-not-removed choice and already justifies it honestly ("an absent one is a different fact about an item file"). It needed no correction, and I left it alone — `_services/_base.py` is in an active lane.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — The frozen list's own prose miscounts it and documents the wrong constant

<!-- sq:finding:F6:body -->
Three prose defects in the declaration of the frozen list — the set that decides what the sweep
deletes. All three landed in `1cf1d30`.

**1. The count is wrong, in the function that consumes it.**
`_services/_maintenance.py::_retired_role_extra_keys`:

> the candidates are `RETIRED_ROLE_EXTRA_KEYS` (**the eight definition keys**, declared beside the
> refusals that name where each value lives now) widened by `RoleDef.extra_keys`

Driven: `len(RETIRED_ROLE_EXTRA_KEYS)` is **9** —
`agreements, can_spawn, color, description, full_name, mission, responsibilities, skills, title`.
The ninth is `skills`, added by the same commit that wrote this sentence, and it is the one the dev
explicitly flagged for a reviewer's eye. A reader auditing the deletion set against the docstring
will count eight, find nine, and have to work out which is authoritative.

**2. The doc comment for `RETIRED_ROLE_EXTRA_KEYS` is attached to the wrong symbol.**
In `_models/_metadata.py` the `#:` block that describes the set — its provenance, the drift
argument, and the "keys deliberately absent" paragraph — runs straight into
`_RETIRED_ROLE_SKILLS_KEY`'s own `#:` comment with **no blank line between them**:

```
#: ``sq role set-default``.
#: The one retired key with no :class:`ExtraKey` member to name it by. ``extra.skills`` was a
```

`#:` attribution binds a contiguous comment block to the symbol that follows it, so all ~25 lines
now document the one-line `_RETIRED_ROLE_SKILLS_KEY: str = "skills"`, and `RETIRED_ROLE_EXTRA_KEYS`
— declared below, and the thing the block is about — carries **no doc comment at all**. One blank
line fixes it.

**3. "Four keys" names five.** Inside that same block:

> **Four keys** the mirror also wrote are deliberately absent, each because something still writes
> it: `slug` ...; `model` ...; `is_dev`/`tech` by `sq dev add`; and `is_default` by
> `sq role set-default`.

Five keys, four clauses. Minor on its own; on a list whose whole defence is "it is a **closed,
named** set", a reader checking the enumeration against the code finds a mismatch and has to decide
whether it is a typo or a missing name.

None of these changes behaviour — the derivation itself is right, and I falsified it: pinning
`is_dev=False` in `_retired_role_extra_keys` reddens
`test_a_role_keeps_exactly_the_extra_keys_a_writer_still_produces[developer]` on a stripped `model`,
and restoring it goes green. The subtraction against `RoleDef.stored_extra_keys` is the correct
shape and a developer's `model` is safe. This is about the description of the set, which is the
artefact the next person will read before adding a name to it.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-09-02T12:54:20Z] Elias Python:
  - Fixed, with one correction to the finding.
    
    **The count is nine** — verified against the code, not the prose: `agreements, can_spawn, color, description, full_name, mission, responsibilities, skills, title`. I removed the numeral from `_retired_role_extra_keys` rather than changing eight to nine: a count in a consuming docstring is a second declaration of a set's size that nothing keeps in step with it, which is how this defect arose. The sentence now names the set and says why it is not restated as a count.
    
    **"Four keys" names five** — right, and the five are `slug`, `model`, `is_dev`, `tech`, `is_default`. Corrected to "Five keys", with `is_dev` and `tech` spelled out separately so the enumeration is its own checksum. That count I kept: the names are in the same sentence, so it cannot drift unnoticed.
    
    **A blank line does not fix the attribution.** `#:` binds a block to the symbol that *follows* it. Inserting a blank line detaches the block from `_RETIRED_ROLE_SKILLS_KEY` but attaches it to nothing — `RETIRED_ROLE_EXTRA_KEYS` is declared past another symbol. I moved the block to sit directly above its own declaration instead, and left a line saying why it sits there.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — docs still describe sq repair as an index-only job

<!-- sq:finding:F7:body -->
`sq repair` is now a content rewriter — 654 files on this repository alone. Every adopter-facing
description of it in `docs/` still says it reconciles the index, and three of them recommend running
it casually, in situations where a content diff is the last thing the reader expects:

- `docs/adoption.md:151-153` — "Run `sq repair` immediately: `sq repair  # reconciles the index to
  whatever files exist on disk`", as recovery from a mid-import I/O failure. That is precisely a
  dirty tree, which is the one state the CHANGELOG and the MANUAL both warn against.
- `docs/adoption.md:173` — in the "Validate" block: "`sq repair  # rebuild the index from
  frontmatter if anything looks off`".
- `docs/faq.md:70` and `:97-102` — "On a `.squads.json` conflict, take either side and `sq repair`";
  and the ID-collision recipe running `sq repair --renumber` on a merged result.
- `docs/internals.md:118` — "`sq repair` rescans every `PREFIX-*.md` ..., rebuilds the index from
  their frontmatter, and sets `counter = max ID number`." No mention of any file write.
- `docs/workflow.md:461` — `sq repair` grouped with `sq check` as index/source-of-truth maintenance.

Nothing in `docs/` says repair can produce a content diff, or repeats the clean-working-tree advice.
An adopter who reads `docs/` and never reads the CHANGELOG — the documented path for someone
adopting squads rather than upgrading it — meets the diff with no warning at all.

Strictly this predates the sweep: the ref canonicalisation shipped earlier in 0.14 and already made
`repair` write files. But it wrote a handful of files in a rare state, and this makes it write the
whole corpus once. The docs' framing is now wrong by a large margin rather than a small one, and
`docs/adoption.md` is the file that tells a new adopter to run it on a dirty tree.

Scope note: this is adopter-facing documentation about the tool, so it stays free of item IDs and
repo process; it wants the tech-writer, not a dev.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-09-02T12:55:02Z] Theo Writer:
  - Fixed across the four files, plus two places in the same files the finding did not list but which carry the same false framing.
    
    **`docs/adoption.md`** — a new **What `sq repair` writes** section under Validate spells out what the rebuild removes, what a role keeps, and that a custom skill's body and every non-role frontmatter field are untouched. Three call sites now link it:
    
    - the mid-import I/O recovery step (line 151 in the finding) no longer reads as safe on a dirty tree: it says the content diff would land on top of the half-written import and the two cannot be separated afterwards, and to commit or stash first;
    - the Validate block gained the section beneath it;
    - **`sq adopt`'s own bullet**, which was not in the finding and needed it most. It described adopt's import as "same engine as `sq repair`" without saying that the engine now writes; I drove `sq adopt` over a corpus carrying the retired regions and it rewrote six item files. The neighbouring "it never clobbers authored content" is narrowed to a body you wrote through `sq`, with the exception named.
    
    **`docs/faq.md`** — a new **Does `sq repair` change my files?** entry, and the `repair`/`check`/`sync` comparison no longer calls repair an index rebuild alone (`check` is now the one of the three that writes nothing). The `.squads.json`-conflict answer and the post-merge `sq repair --renumber` recipe both say to commit the resolution before running it. The corrupt-index answer at the top says to run it on a clean tree.
    
    **`docs/internals.md`** — the `sq repair` bullet gains "The rescan also writes", naming the two families, the role body and the retired mirror keys, and recording that markdown is written before the index commit. The merge-conflict upshot says to commit the resolution first.
    
    **`docs/workflow.md`** — the reflog section no longer implies `repair` only reconciles an index, and the `repair` op row names `delta.stripped` / `delta.canonicalized` as where you read back what the rebuild rewrote, and that `sq adopt` and `sq migrate up` write that same op.
    
    Everything asserted is driven: the routes, the reflog fields (`stripped` carries item ids, not paths), the fresh-squad no-op (a `sq repair` on a squad created on this version leaves every `.md` byte-identical), and the second-run no-op.
    
    **Two instances of the same defect I did not touch**, because they are outside this finding and I would rather flag than widen the diff: `README.md:338` describes `sq repair` as "rebuild the index from frontmatter", `README.md:419-420` gives the merge recipe with no clean-tree advice, and `PYPI.md:62` says "`sq repair` reconstructs it from the files". Same claim, same release, two more adopter-facing files. @tech-lead worth a call on whether they ride this fix.
- [2026-09-02T13:12:22Z] Theo Writer:
  - **Correcting my comment above**, for the same reason as F1's: `98ca0638` landed while I was writing, and two claims in the doc text went false with it.
    
    - Every mention of a template-owned skill's body being emptied is **removed** from `docs/adoption.md`, `docs/faq.md` and `docs/internals.md`. All three now say no skill body is touched — authored or template-owned — and `internals.md` records why: the classification is a function of today's vocabulary while the stored body was written under an earlier one, so the two are indistinguishable on disk.
    - "Only `sq repair` announces it" is out of `docs/adoption.md` and `docs/faq.md`. I re-drove all four routes on the current build: `sq repair` and `sq migrate up` both print the strip notice and name the files in the reflog; `sq adopt` records them in the reflog only; `sq renumber` records nothing at all. All three docs that discuss the routes now state that split and name `git diff` as the fallback for the last two.
    
    `docs/workflow.md` needed no second pass — its two edits are about the reflog's `repair` op and its `delta` fields, both still accurate.
    
    The `README.md`/`PYPI.md` instances I flagged above are unchanged and still stand for a scope call.
- [2026-09-02T13:36:13Z] Theo Writer:
  - Widened to the three instances outside this finding, on the coordinator's scope call.
    
    Each verified against the code as it stands before writing, not carried from the earlier pass — I re-drove `sq repair` and `sq repair --renumber` from a clean export of `HEAD`'s `src` rather than the working tree, since three lanes are live in it. Both strip four item files on the `v0_11` corpus and both print `stripped retired regions from 4 item files — review the diff`.
    
    - **`README.md`** (the `sq repair [--renumber]` maintenance bullet) — now says it rebuilds the index **and rewrites item files** on the same pass, that it removes what squads computes on every read and canonicalises legacy ref encodings, that it wants a clean working tree, and that `sq adopt`, `sq renumber` and the rebuild ending `sq migrate up` reach the same sweep. Kept to the register of a command-reference list, with the detail behind a link to the FAQ entry rather than restated.
    - **`README.md`** (Git notes, the merge recipe) — gained the clean-tree advice as its own paragraph: commit the merge resolution first, because both `sq repair` and `sq repair --renumber` rewrite item files as well as the index and neither can separate its changes from yours.
    - **`PYPI.md`** — "delete it and `sq repair` reconstructs it from the files" was true but framed repair as purely reconstructive; it now says repair also rewrites the files themselves on that pass, and to run it on a clean tree. Left self-contained with no relative link, since that file renders off GitHub.
    
    Both new anchors resolve: `docs/faq.md#does-sq-repair-change-my-files` and `docs/adoption.md#what-sq-repair-writes` are real headings, checked by slugifying every heading in each file rather than by eye, and every inbound link in `README.md`, `docs/faq.md` and `docs/adoption.md` points at one of them.
    
    One instance I looked at and deliberately did **not** change: `README.md`'s "a fast index that is fully rebuildable from the files (`sq repair`)" in the source-of-truth section. That claim is about the index and it is true; it does not characterise repair as index-only.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T12:26:38Z] Paul Reviewer:
  - Reviewed at **b37cdc9d** on `release/0.14`. Findings on their own discussions: F1 high, F2/F3/F4 medium, F5/F6/F7 low.
    
    **Recommended verdict: ship, once F1 is fixed.** The mechanism is sound and I proved it rather than read it — my independent `sq repair` over the corpus at `1cf1d30` reproduces the committed 654-file diff exactly, three files apart (`.squads.json` plus the two task files carrying the manager's concurrent board writes). Second run is byte-identical; a never-carried squad writes no file at all (proven by mtime, not by byte-compare); `repair --renumber` matches plain `repair`; the discriminators are the correct ones and all five falsification drills redden the tests they should. `releasing-squads` survived at 10118 bytes. Nothing authored was lost in this repository — I checked every one of the 632 + 436 pre-strip files for a retired region sitting inside a `:body`/`:discussion` region and found none.
    
    F1 blocks because it is a text fix on the one thing ADR-776 §5 accepted in place of prevention: both announcements tell adopters "every item body, and every frontmatter field" survives, while every role item loses its body and nine `extra` keys. F2 and F3 are real but can follow the cut if that is the call.
    
    **What I could not test, and why.**
    - **A dev-shaped role in a real legacy corpus.** All ten frozen fixtures carry the same minimal `dev-agent` role (`extra: {slug, full_name}`) — no `is_dev`, no `model`. So the data-loss edge that actually matters (a developer's operator-set `model` surviving while a bundled role's is stripped) is proven only by the constructed unit test, never by a corpus. A fixture carrying a real developer role would close that.
    - **The `adopt` population.** ADR-776 §1 makes `adopt` over a folder with no `.squads.toml` the recurring reason the vehicle cannot key on the stamp — it is also the one population whose files never passed `reject_markers`. I could not build a credible foreign corpus for it, so F5's reachability there is inferred, not driven.
    - **Concurrency.** I did not test `sq repair` racing a live agent mutating the same corpus; the manager's own note on ST5 (running the strip with uncommitted board writes in the tree) is the shape that would matter.
    - **Byte-level golden of the generated surface.** I took the existing outcome test for that (`CLAUDE.md`/`AGENTS.md`/pointers identical) as read rather than re-driving it.
    
    Gates on the reviewed tree: `uv run --all-extras pytest` once to a file — **4499 passed, 8 skipped, 0 FAILED**. `sq check` clean. Nothing in `src/`, `tests/` or `docs/` was edited; the falsification drills ran as pytest plugins on `PYTHONPATH`, and every corpus experiment ran in scratch copies.
    
    @tech-writer F1 and F7 are yours — the CHANGELOG entry and the `MANUAL` section both claim the role half does not happen, and `docs/` still calls `sq repair` an index-only job.
    @architect F3 and F5 want your ruling rather than a fix: F3 is a deletion path the live-spec discriminator opens in the direction its own reasoning does not consider, and F5 is a sentence in ADR-776's fourth amendment whose stated mechanism is wrong even though its conclusion holds.
    @tech-lead F2, F4 and F6 are ordinary follow-up work.
- [2026-09-02T12:54:50Z] Elias Python:
  - F3, F2, F4, F6 fixed; details on each finding's own discussion. Nothing committed. F1, F5, F7 untouched.
    
    **F3 changed delivered behaviour, so it needs a decision to stand.** The sweep no longer empties any skill body — only role bodies and the retired marker regions. The reason is on F3: template-ownership moves with the **release** as well as with a project override, and I drove the release direction end to end on 0.12.1 → 0.14 with no override in sight, so no slug-membership test is safe. Being *derived* is not enough to delete something; the sweep also has to prove nothing authored it, and only the role half can.
    
    **Two knock-ons for people already mid-edit.**
    
    @tech-writer the CHANGELOG (`## [0.14.0]`, and the `### Migration` paragraph) and `_v0_11_to_v0_14.MANUAL` both now claim a template-owned skill's stored body is emptied. That is false as of this change — the F1 rewrite has to **remove** those clauses, not just add the role half. The role claims you are adding are correct and unaffected.
    
    @architect F3's *reclassification* is untouched and still yours: a shadowed slug renders the generated definition over the authored one on `sq skill show`. Nothing is destroyed now and the state is reversible, but whether `sq skill add` should refuse an `sq-` slug, or `sq check` should report a class flip, is still a decision. F5 is likewise untouched.
    
    **Gates**, measured in a clean worktree at HEAD `07f7217b` because this working tree is carrying another agent's in-flight docs/template/golden edits (they redden 5 tests in `tests/meta/test_override_manifest_and_stamp_freshness.py`, which are not mine):
    
    - baseline HEAD: 4539 passed, 8 skipped, 0 failed
    - with my changes: **4537 passed, 12 skipped in 80.08s**, exit 0, 0 FAILED
    
    The delta reconciles exactly: −4 passed / +4 skipped from F4's precondition (`v0_1`–`v0_4` have no stored skill body to prove anything with), +1 for the F3 shadowing regression test, +1 for the F2 announcement test.
    
    `pyright` 0 errors, `ruff check` clean, `ruff format --check` clean, `sq check` clean.
    
    Every fix falsified: restoring the skill half of the sweep reddens both new F3 tests and 5 of the 10 corpus params; removing the `migrate up` print reddens the F2 test.
- [2026-09-02T12:56:58Z] Theo Writer:
  - F1 and F7 fixed; F5 read, confirmed and routed to @architect unmarked. Detail on each finding's own discussion.
    
    **F1 (the blocker).** `CHANGELOG.md`'s 0.14.0 `### Changed` entry, its `### Migration` paragraph, and `_v0_11_to_v0_14.MANUAL` are rewritten. No other line of that runner is touched. The texts now state the role half — role bodies emptied, and the nine mirrored `extra` keys removed plus `model` on a non-developer role — and state what survives: `slug` and the default-role designation on every role, `model`/`is_dev`/`tech` on a developer one. The internal "two regions / all three" contradiction and the "every item body, and every frontmatter field" clause are gone from both.
    
    **Three things I found that the review did not name:**
    
    1. **`sq adopt` performs the whole sweep.** It calls `Service.repair()`. Driven on the `v0_11` corpus restamped to 0.14 so no runner applies: six item files rewritten, a `repair` reflog line naming them, nothing on the console. That is the population `docs/adoption.md` addresses and the one route no announcement covered — a first `sq adopt` over a folder of squads-native markdown rewrites it. `sq renumber` reaches it too, through `_rebuild_index_from_disk` where the writes happen, and records nothing at all. Both texts and all four docs now name every route and say only `sq repair` announces it. This widens F2 rather than duplicating it: the missing announcement is on three commands, not one.
    
    2. **The stated reason for emptying rather than removing a body is false.** "A removed region is what `sq role show`/`sq skill show` read as 'no item for this slug'" — driven: with the whole `body` marker pair deleted from a bundled role's file and a template-owned skill's file, both `show` commands render in full and `sq check` reports no issues. Neither path branches on the region. The phrase exists nowhere in the codebase but in the two docstrings asserting it, and it had been copied into the release note. Dropped from both adopter texts; the docstrings in `_strip_retired_regions` and `_sweep_empties_body` still carry it. Filed on F5's discussion as the same class.
    
    3. **An orphaned custom role loses its definition outright, with no reader left and no report.** A role item with no catalog entry, no `is_dev` shape and no `.overrides/roles/<slug>.toml` resolves through `RoleDef.from_extra_or_item`, and after the strip there is nothing left in `extra` to resolve from. Driven on the migrated `v0_11` fixture: `sq role dev-agent show` prints "the definition for dev-agent could not be resolved — run `sq check` to see why", and `sq check` then reports **no issues**, so the message names a remedy that says nothing. The mission text is gone from disk and no command renders it. `sq search` no longer matches it either. That shape is the fixture's, not a shape `sq role activate` can produce — but it is exactly what an adopted foreign corpus or a deleted role override leaves behind, and it sits next to F3 as a second direction the live-spec/catalog discriminator does not consider. I have not written it into the adopter texts: it wants a ruling, not a sentence.
    
    **F7.** Fixed in `docs/adoption.md`, `docs/faq.md`, `docs/internals.md`, `docs/workflow.md`, each with a linked section rather than a scattered warning, and including `adoption.md`'s `sq adopt` bullet and `faq.md`'s `repair`/`check`/`sync` comparison — neither in the finding, both carrying the same claim. The same claim also stands uncorrected in `README.md:338` and `:419-420` and `PYPI.md:62`; flagged there for a scope call, not touched.
    
    **Gates.** The tree is shared with an in-flight dev on the code findings, so a full-suite run here measures their working state, not mine: my first run reddened five `test_override_manifest_and_stamp_freshness` tests that pass on re-run, and `ruff` reported an F401 in `_services/_maintenance.py` I did not write. I re-ran the gates in an isolated worktree at `cbc7cbac` carrying only my six files: **4539 passed, 8 skipped, 0 failed**; `pyright` 0 errors; `ruff check` and `ruff format --check` clean. `sq check` clean. The doc-drift guards pass — no guard forced a change to `src/`. Nothing committed or pushed.
    
    @reviewer F1 and F7 are ready for your re-read. @architect F5 is yours, with the second false-reason above folded into its discussion.
- [2026-09-02T13:12:40Z] Theo Writer:
  - **Second pass, correcting my comment above.** `98ca0638` (skill half of the sweep removed, `sq migrate up` given the strip notice) landed while I was writing the first version, so both adopter texts were describing a build that had just stopped existing — the same defect as F1, one layer down. Both are rewritten against the code as it stands now, and every claim re-driven rather than adjusted. Corrections are on F1's and F7's own discussions; the two that matter here:
    
    - **No skill body is swept any more.** `_sweep_empties_body` is `item.type == ROSTER_ROLE` and nothing else. Driven on the `v0_11` fixture: `sq migrate up` rewrites **four** item files, not six, and both `SKILL` files are byte-identical. Every clause claiming a template-owned skill body is emptied is removed from the CHANGELOG entry, the `MANUAL` runbook and three of the four docs — removed, not softened.
    - **"Only `sq repair` announces it" was true when I wrote it and is not now.** Driven, all four routes on the current build: `sq repair` and `sq migrate up` both print the notice and name the ids in the reflog; `sq adopt` writes the reflog line and says nothing on the console; `sq renumber` records nothing at all. Every text now states that four-way split rather than a single announcer.
    
    The role half is unchanged and re-verified against the current code, and `sq adopt` remains the route no announcement covers — worth a look alongside F2 rather than inside it.
    
    **Gates, on a tree that is now mine alone** (the dev's work committed at `98ca0638`; only my six files are uncommitted): `uv run --all-extras pytest` once to a file — **4537 passed, 12 skipped, 0 failed**, zero `FAILED` lines. `ruff check .` and `ruff format --check .` clean. `sq check` clean. No doc-drift guard reddened and none forced a change to `src/` beyond the one `MANUAL` string.
    
    `pyright` reports **3 errors, all in files I did not touch** and all in the concurrent lane's in-flight work — `tests/tui/test_status_role_colour.py` (modified in the working tree, two `reportCallIssue`) and `tests/cli/test_an_empty_parent_value_is_refused_on_every_create_door.py` (untracked, one `reportMissingTypeArgument`). My six files are `CHANGELOG.md`, four docs and one string literal, none of which pyright reads as typed code. @python-dev flagging rather than fixing, since it is your lane.
    
    Nothing committed or pushed. @reviewer both texts are ready for a re-read against the current build.
- [2026-09-02T13:45:11Z] Theo Writer:
  - Third pass done: the three adopter-facing instances outside F7, and the four false-reason docstrings/conventions lines. Detail on F5's and F7's own discussions; the cross-cutting parts here.
    
    **What changed**, five files: `README.md` (the `sq repair` maintenance bullet, and the Git-notes merge recipe), `PYPI.md` (the rebuildable-index paragraph), `src/squads/_sections.py` (`find_markers`' docstring), `src/squads/_services/_maintenance.py` (`_strip_retired_regions` and `_sweep_empties_body`), and `CLAUDE.md`'s marker-regex convention line.
    
    **Every replacement re-driven, and one of them changed the answer.** The instruction offered "say it is a choice with no load-bearing justification" as an acceptable outcome for the emptied-not-removed reason, and that is what it turned out to be: with the whole `sq:body` marker pair deleted outright from a role file, `show`, `check`, `sync`, `repair`, `regen`, `list`, `--json` and `search` all behave identically, and nothing restores the pair. So the docstring now records the shape argument plus one checkable mechanical fact for whoever changes it next — `replace_section` raises `KeyError` on an absent region, so a future writer reaching a role's body would fault rather than refuse, and none exists today — rather than a behavioural reason that does not exist.
    
    For `find_markers` I ran the architect's control myself before writing, on strings built at runtime: a bare tag matches, the same tag in backticks matches, the same tag in a fenced block matches, and only the `sq:*` form is unmatched. I also counted the `reject_markers` call sites rather than repeating "ten": ten, across `_items`, `_base`, `_subentities` (four), `_collab` and `_import` (three).
    
    **Two process notes worth carrying.**
    
    1. **I nearly shipped a syntax error into `_sections.py`.** My first draft wrote the character class as `[\w:-]` inside a non-raw docstring — an invalid escape sequence, which `ruff` flags (W605) and `python -W error::SyntaxWarning` turns into a hard `SyntaxError`. Caught by running both against the single file before the suite. The wording avoids the backslash entirely now. Worth knowing for anyone quoting a regex into a docstring here.
    
    2. **The shared tree could not gate this work.** A full run on it came back **16 failed, 4572 passed**, and every one of the sixteen traces to a lane I am not in: thirteen to the override-loading refactor mid-landing (`ImportError: cannot import name 'describe_spec_error' from 'squads._specmerge'`, which kills every subprocess-launched `python -m squads`), two to the tree-walk lane's new `anchor` field against an unregenerated JSON golden, one to `_services/_validators.py`'s new module constants tripping the mutable-state allowlist. The same in-flight `_validators.py` also broke `sq` itself mid-session — a `sq … comment` refused with a validator-context assertion — so I ran `sq` from an exported copy of `HEAD`'s `src` on `PYTHONPATH` to write these comments, and drove the `sq repair` verifications the same way rather than through the working tree.
    
    **Gates, isolated** — a throwaway worktree at `4e126fc2` carrying only my five files: `uv run --all-extras pytest` once to a file, **4552 passed, 12 skipped, 0 failed**, zero `FAILED` lines. `pyright` **0 errors, 0 warnings**. `ruff check .` and `ruff format --check .` clean. `sq check` clean on the repo squad.
    
    **pyright is clean of my files** — confirmed twice: 0 errors on `_sections.py` and `_maintenance.py` individually in the shared tree, and 0 errors across the whole project in the isolated worktree. The errors visible in the shared tree belong to the live lanes.
    
    Nothing committed or pushed. The orphaned-role failure is untouched, as instructed.
    
    @reviewer the adopter surface is now consistent across `CHANGELOG.md`, the `MANUAL` runbook, four `docs/` pages, `README.md` and `PYPI.md`. @architect the two `_maintenance.py` docstrings and `find_markers` now carry your ruling; `_create_core`'s own comment already stated the honest reason and I left it alone, since `_services/_base.py` is in an active lane.
- [2026-09-02T15:26:26Z] Catherine Manager:
  - Approved. All seven findings Fixed. F1 and F7 were the release blockers — announcements that denied the role half of what the sweep does — and both were rewritten against the code as it stood at the time of writing, not against the ticket. F3 was the one that mattered most: authored skill bodies were destroyable on a plain upgrade because contract and milestone became bundled types in this release, and the remedy was to stop sweeping skill bodies at all rather than ship a cleverer discriminator.
  - F2 needed reopening after its first fix covered only sq migrate up. Driving all four routes found sq adopt silent on the console and sq renumber recording nothing anywhere — the ruling this release was accepted on was announced-not-prevented, and half the doors did not announce.
<!-- sq:discussion:end -->

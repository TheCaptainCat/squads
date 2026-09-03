---
id: REV-881
sequence_id: 881
type: review
title: Corpus strip in the repair sweep
status: ChangesRequested
author: reviewer
refs:
- TASK-849:addresses
- ADR-776
- TASK-853
subentities:
- local_id: F1
  title: Both adopter announcements deny the role half of the sweep
  status: Open
  severity: high
- local_id: F2
  title: sq migrate up never announces the content it rewrote
  status: Open
  severity: medium
- local_id: F3
  title: A declared type shadowing an authored skill slug deletes its body
  status: Open
  severity: medium
- local_id: F4
  title: Four of ten skill-body corpus params pass with the sweep disabled
  status: Open
  severity: medium
- local_id: F5
  title: The ADR gives a false reason for authored content being unreachable
  status: Open
  severity: low
- local_id: F6
  title: The frozen list's own prose miscounts it and documents the wrong constant
  status: Open
  severity: low
- local_id: F7
  title: docs still describe sq repair as an index-only job
  status: Open
  severity: low
created_at: '2026-09-02T12:23:23Z'
updated_at: '2026-09-02T12:26:54Z'
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
<!-- sq:discussion:end -->

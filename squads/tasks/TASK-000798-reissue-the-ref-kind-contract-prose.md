---
id: TASK-798
sequence_id: 798
type: task
title: Reissue the ref-kind contract prose
status: Done
parent: FEAT-790
author: tech-lead
assignee: tech-writer
priority: high
refs:
- ADR-775:implements
- TASK-797:depends-on
- TASK-799
description: Retire the closed-vocabulary policy from the stability doc and the generated
  cheatsheet, and reissue the replacement contract wording
subentities:
- local_id: ST1
  title: Retire the closed-vocabulary passage from docs/stability.md
  status: Done
  assignee: tech-writer
  story: US5
- local_id: ST2
  title: Retire the closed-vocabulary line from the cheatsheet template
  status: Done
  assignee: tech-writer
  story: US5
- local_id: ST3
  title: Regenerate the template manifest and managed artifacts
  status: Done
  assignee: tech-writer
  story: US5
- local_id: ST4
  title: Make the cheatsheet kinds table spec-driven
  status: Done
  assignee: tech-writer
  story: US5
- local_id: ST5
  title: Retire the closed-vocabulary claim from the README
  status: Done
  assignee: tech-writer
  story: US5
created_at: '2026-08-25T14:40:28Z'
updated_at: '2026-08-25T23:39:43Z'
---
<!-- sq:body -->
## Scope

ADR-775 §6 — FEAT-790 US5. Retire the closed-vocabulary extension policy from every carrier
that ships it, and reissue the replacement contract wording.

**Owner is the tech-writer, not the developer landing the engine change.** That is the
operator's explicit ruling, recorded on ADR-775: leaving the stability document promising a
closed list the engine no longer enforces is the worse of the two states, so the docs follow
the engine. This is contract wording, not a code comment.

## The three carriers, which retire together

- **`docs/stability.md:322-328`** — "The nine built-in kinds are frozen … A project-declared
  custom-kind extension is reserved for a future release."
- **`_rendering/templates/workflow_static.md.j2:88`** — "The vocabulary is closed — exactly
  nine kinds, no custom extensions in 1.0." This is a bundled template, and its rendered output
  is also the text of the `squads` skill that every agent reads.
- **`README.md:320`** — the cross-linking line enumerates the kinds by name and says "nine
  kinds". ADR-775 §6 names only the first two, so this one arrived unowned; it is folded in
  here rather than filed separately, because the three say the same retired thing and must stop
  saying it together.

**The README line is already false, before any of this lands.** `targets` ships bundled and is
accepted today — `sq task 21 ref add ADR-20 --kind targets` succeeds and stores
`refs: [ADR-20:targets]`. So the line enumerates an accepted-kind list missing a kind the tool
accepts, and asserts a closed count the engine no longer enforces. It is also the most
adopter-facing of the three: the PyPI page and the repo front page.

The literal count leaves every carrier. ADR-49's own amendment note already ruled that the
count was never the contract.

## The replacement, in the same load-bearing register (ADR-775 §6)

> Ref kinds are declared vocabulary. The bundled set is the default; a project may declare its
> own, and may rename or drop a built-in it does not use, subject to the same live-corpus
> refusal that protects a type or a status. A kind the merged spec does not declare is still
> rejected. Engine behaviour binds to a kind's declared semantic role, never to its name — so a
> renamed dependency kind keeps driving `sq blocked`, and a kind with no semantic is
> navigational.

The cheatsheet's kinds table stays **generated from the merged spec**, so a project's own kinds
appear in its own `sq workflow` output and in the skill text its agents read. Only the static
policy sentence is being replaced; the table is not hand-written.

## The template-manifest consequence, and what is already satisfied

Editing `workflow_static.md.j2` is a bundled-template edit, so it forces a template-manifest
regeneration. ADR-781 §6 states the ordering once for every template-touching change in this
release: **the version bump comes first, then the regeneration.**

**That ordering is already satisfied — `pyproject.toml` is at 0.14.0, which is not a shipped
release.** So:

- **Do not run `scripts/bump_version.py`.** Running it again would move the version off the one
  the whole release's regenerations are keyed to.
- Run `python scripts/gen_template_manifest.py`, which replaces the `0.14.0` entry wholesale.
- The managed-section golden and the generated-agent-text guards move with the template in the
  same change (ADR-781 §6).
- `sq sync` regenerates this repo's own `squads/agents/skills/` copy of the cheatsheet text.

**Sequencing against the manifest widening.** TASK-799 widens the generator and regenerates the
same `0.14.0` index entry. Both regenerations target one version key and the last one written
is what ships, so whichever of the two lands second must regenerate after the other's content
is in the tree. `docs/stability.md` is not package data and carries no such constraint.

## Acceptance

- No carrier states a closed, frozen or numerically-fixed ref-kind vocabulary; a grep for
  "nine" and for "closed" across `docs/stability.md`,
  `_rendering/templates/workflow_static.md.j2` and `README.md` returns nothing about ref kinds.
- `README.md` no longer hard-codes an enumeration of the kinds that a bundled addition can
  falsify, and what it does say about ref kinds is true of the shipped vocabulary including
  `targets`.
- The replacement wording carries all four claims: declared vocabulary; bundled set as default;
  rename/drop subject to the live-corpus refusal; an undeclared kind still rejected; semantic
  binding rather than name binding.
- The cheatsheet's kinds table still renders from the merged spec, and a project that declares
  its own kind sees it in `sq workflow` output and in its agents' skill text.
- `templates_manifest.json`'s `0.14.0` entry matches the tree; the manifest-freshness guard
  passes.
- `scripts/bump_version.py` was not run; `pyproject.toml` still reads 0.14.0.
- The generated-agent-text and managed-section golden guards pass; `sq sync` is a no-op
  afterwards.
- No sq item ID, phase/round/pass language or other build-process narration appears in the
  delivered prose. `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 798 add-subtask "<title>"`; track with `sq task 798 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | tech-writer | Retire the closed-vocabulary passage from docs/stability.md | US5 |
| ST2 | Done | tech-writer | Retire the closed-vocabulary line from the cheatsheet template | US5 |
| ST3 | Done | tech-writer | Regenerate the template manifest and managed artifacts | US5 |
| ST4 | Done | tech-writer | Make the cheatsheet kinds table spec-driven | US5 |
| ST5 | Done | tech-writer | Retire the closed-vocabulary claim from the README | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Retire the closed-vocabulary passage from docs/stability.md

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Theo Writer
**Implements:** US5 — Reissue the ref-kind contract prose (tech-writer)
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Replace the passage at `docs/stability.md:322-328` — "The nine built-in kinds are frozen … A
project-declared custom-kind extension is reserved for a future release."

The replacement carries four claims: ref kinds are declared vocabulary and the bundled set is
the default; a project may declare its own, and may rename or drop a built-in it does not use,
subject to the same live-corpus refusal that protects a type or a status; a kind the merged spec
does not declare is still rejected; engine behaviour binds to a kind's declared semantic role,
never to its name — so a renamed dependency kind keeps driving `sq blocked`, and a kind with no
semantic is navigational.

The literal count leaves the document; the count was never the contract.

`docs/stability.md` is not package data, so this file carries no manifest constraint of its own.

Done when the section states the new policy in the same load-bearing register as the old one,
with no residual promise of a closed or numerically-fixed vocabulary.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Retire the closed-vocabulary line from the cheatsheet template

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Theo Writer
**Implements:** US5 — Reissue the ref-kind contract prose (tech-writer)
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Replace the line at `_rendering/templates/workflow_static.md.j2` — "The vocabulary is closed —
exactly nine kinds, no custom extensions in 1.0" — with the same replacement policy, cut to
cheatsheet length.

This template's rendered output is also the text of the `squads` skill that every agent reads,
so the wording has to survive being read out of context by an agent deciding whether it may
declare a kind.

The sentence directly beneath the table — "Bare `ref add <id>` (no `--kind`) defaults to
`related`" — names the default kind by spelling. Under ADR-775 amendment A1 the bare form binds
to the declared `default` semantic, not to a name, so this sentence needs the same treatment as
the policy line: state that the bare form resolves to whichever kind declares `default`, and let
the name come from the spec.

The kinds **table** is a separate piece of work — it is hand-written today, and ST4 makes it
spec-driven. Keep the two edits in one pass on this file so it is opened once.

Done when the rendered cheatsheet and the generated skill text carry the new policy, and neither
the policy line nor the bare-ref sentence names a kind by a spelling the template hard-codes.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Regenerate the template manifest and managed artifacts

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Assignee:** Theo Writer
**Implements:** US5 — Reissue the ref-kind contract prose (tech-writer)
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Editing a bundled template forces a template-manifest regeneration, and the generator replaces
one version's entry **wholesale**, keyed on `[project].version`. The rule is: the version bump
comes first, then the regeneration.

**That ordering is already satisfied — `pyproject.toml` reads 0.14.0, which is not a shipped
release. Do not run `scripts/bump_version.py`.** Running it again would move the version off the
key every regeneration in this release is aimed at.

Steps:

- `python scripts/gen_template_manifest.py`, replacing the `0.14.0` entry.
- The managed-section golden and the generated-agent-text guards move with the template in the
  same change.
- `sq sync` to regenerate this repo's own copy of the cheatsheet under `squads/agents/skills/`.

Sequencing note: the manifest-widening task regenerates the same `0.14.0` entry. Both target one
version key and the last write is what ships, so whichever of the two lands second must
regenerate with both changes already in the tree.

Done when the freshness guard passes, `sq sync` is a no-op afterwards, and `pyproject.toml`
still reads 0.14.0.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Make the cheatsheet kinds table spec-driven

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Assignee:** Theo Writer
**Implements:** US5 — Reissue the ref-kind contract prose (tech-writer)
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
The cheatsheet's ref-kinds table is hand-written: ten literal `| ... |` rows in
`_rendering/templates/workflow_static.md.j2`, nine of them kind rows, with only two Jinja
substitutions inside them (the superseded status name and the dropped status name). It does not
list `targets`, and it cannot list an adopter-declared kind at all.

Drive the table from `spec.ref_kinds` instead, so every declared kind renders — bundled or
adopter-declared — with its declared `label` and `hint`, and its consumer column derived from
the declared semantic `role` rather than restated per row.

`targets` therefore appears, and that is correct rather than incidental. ADR-775 §6 states the
table stays generated from the merged spec precisely so a project's own kinds appear in its own
`sq workflow` output and in the skill text its agents read; a kind that is declared but hidden
would need a "hide from the cheatsheet" flag nothing declares. If the table is genuinely the
wrong place for a kind with no engine consumer, that is a vocabulary question for the architect,
not a row quietly omitted from a generated table.

**Move the row-count pin.** `tests/unit/test_workflow_cheatsheet_static_dynamic_split.py::test_the_ref_kind_cheatsheet_table_has_one_row_per_hand_written_kind`
currently asserts `len(table_rows) == 9` against a docstring explaining that the table is "still
a hand-written list (not yet spec-derived)". Once the table is spec-driven the pin becomes the
live vocabulary size and the test name stops describing what it checks — rename it and assert
against the declared set, including a case where an override adds a kind and gains a row.

The same test module asserts `"The nine built-in kinds are frozen" in docs/stability.md`, which
ST1 removes, so that module needs updating for this subtask and ST1 together — do them in one
pass rather than leaving the suite red between them.

Why this sits here rather than with the section that declared the vocabulary: editing this
template is a bundled-template edit and forces a manifest regeneration, which ST3 already owns
and which was not available to the task that declared `[ref_kinds]`.

Done when the rendered table lists every declared kind including `targets`, an override-added
kind gains a row with no template change, and no test pins the row count to a literal.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Retire the closed-vocabulary claim from the README

<!-- sq:subtask:ST5:head -->
**Status:** 🟢 Done
**Assignee:** Theo Writer
**Implements:** US5 — Reissue the ref-kind contract prose (tech-writer)
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
Retire the closed-nine-kinds claim from `README.md:320`, the third carrier and the most
adopter-facing one — the PyPI page and the repo front page.

The line reads, in the cross-linking section:

```
- `sq <type> <n> ref add TARGET [--kind related|blocks|depends-on|implements|fixes|addresses|
  supersedes|duplicates|scopes]` … — nine kinds. …
```

It states the count and enumerates the kinds by name.

**It is already false, independently of the rest of this work.** `targets` ships bundled and is
accepted today: `sq task 21 ref add ADR-20 --kind targets` succeeds and stores
`refs: [ADR-20:targets]`. So the line enumerates an accepted-kind list that is missing a kind
the tool accepts, and asserts a closed count the engine no longer enforces.

Replace it so it cannot go stale the same way: the README should not carry a hand-maintained
enumeration that any bundled addition falsifies. Say what `--kind` takes and point the reader at
the command that lists the live vocabulary (`sq workflow`), and keep whatever the line needs to
stay useful — the dependency-pair note and the supersession note are both still true and worth
keeping.

Two constraints on the replacement, both standing rules for this file:

- The README describes the tool for adopters. No sq item ID, no ADR reference, no repo or
  development-process content.
- No build-process narration — describe what the tool does, not that a policy changed.

`README.md` is not package data, so this carries no manifest constraint of its own.

Done when the README states nothing closed, frozen or numerically fixed about ref kinds, what it
does say is true of the shipped vocabulary including `targets`, and a grep for "nine" and
"closed" in it returns nothing about ref kinds.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T15:49:40Z] Olivia Lead:
  - Folded in the cheatsheet work that TASK-796 could not do. Verified before folding: the ref-kinds table in workflow_static.md.j2 is genuinely hand-written (nine literal pipe rows, only two Jinja substitutions inside them), it does not list targets, and tests/unit/test_workflow_cheatsheet_static_dynamic_split.py pins the row count to a literal 9 with a docstring saying the table is not yet spec-derived.
  - This task is the right home on three counts, not just proximity: it already opens workflow_static.md.j2 (ST2), it already owns the manifest regeneration that a bundled-template edit forces (ST3), and that same test module also asserts "The nine built-in kinds are frozen" in docs/stability.md - which ST1 removes. So the module is already this task to update, and doing the row-count pin anywhere else would leave the suite red between two tasks.
  - New ST4 covers making the table spec-driven and moving the pin off the literal. Also corrected ST2, which I had written on a false premise - it claimed the table was already generated from the merged spec. It is not, and ST2 now says so and points at ST4. ST2 also picked up a second hard-coded spelling I found while checking: the sentence under the table says bare ref add defaults to related, which ADR-775 amendment A1 makes a semantic rather than a name.
  - One judgment call flagged rather than settled: the dev excluded targets from the table deliberately, on the reading that it documents kinds an author picks from directly. ADR-775 section 6 says the table is generated from the merged spec so a project sees its own kinds - which admits no hidden entries. ST4 says targets appears, and that hiding a declared kind would need a flag nothing declares. @architect if that reading is wrong it is a vocabulary question, not a row to omit quietly.
- [2026-08-25T18:01:09Z] Olivia Lead:
  - Folded REV-808 F4 in: README.md:320 is a third carrier of the retired closed-nine-kinds policy. Verified the line myself - it says "nine kinds" and enumerates them by name, and it is already false today because targets ships bundled and ref add --kind targets is accepted. New ST5 covers it; the body now says three carriers, and the acceptance grep includes README.md.
  - ST5 asks for a replacement that cannot go stale the same way - no hand-maintained enumeration in the README, point the reader at sq workflow for the live vocabulary. It also carries the two standing rules for that file: no sq or ADR references in adopter-facing docs, and no build-process narration. README.md is not package data, so it adds no manifest constraint.
  - For the record and not a blocker: ADR-775 section 6 still names only two carriers. The operator ruled this into the task rather than the ADR, so the task now covers more ground than the section it implements. @architect flagging only in case you want the section list aligned - nothing here waits on it.
- [2026-08-25T22:24:35Z] Theo Writer:
  - Reissued the contract prose across all three carriers. docs/stability.md: the section is now "Ref-kind vocabulary (declared, bound by semantic)" and opens on the status-set-validation register — what is frozen is the validation behaviour and the semantic binding, not any kind name. It carries the four claims plus the per-capability floor: dependency (at most one per direction, zero legal), preload (exactly one), supersession (zero legal), default (exactly one, mandatory, stored bare so a rename relabels rather than re-points). No count, no enumeration, no promise of a closed set.
  - Cheatsheet template: the policy line is replaced with the same wording cut to one paragraph, and the kinds table is now generated from spec.ref_kinds. Meaning is the declared hint (falling back to label, so an adopter kind that declares only a label still reads); Consumer is derived from the declared role, with a fifth branch for kinds named by a per-type ref_rule. Every name below the table is resolved too - the dependency pair, the supersession kind, the superseded status and the default kind - so the bare-ref sentence no longer says "defaults to related" but names whichever kind declares the default semantic.
  - targets is in the table, per ST4 and the decision. I agree with the ruling rather than the earlier exclusion: the table is generated from the merged spec so a project sees its own kinds, and hiding a declared entry would need a flag nothing declares. The one cost is that its declared hint mentions a consumer that is a declared view, which now reads in adopter-facing text - a spec-wording question for whoever owns [ref_kinds], not something I changed here.
  - Dropped the Direction convention column. It was per-row prose the spec does not declare, and it was redundant: every hint already reads "A <kind> B", so one derived line under the table ("every edge is stored on the item you add it to") carries it for every kind including adopter-declared ones. The two facts the column alone held - the dependency pair being one edge, and the superseded record status - moved into that derived line.
  - README: the ref line no longer enumerates the kinds or states a count; --kind now points at sq workflow ref-kinds for the live set and names the dependency and supersession kinds by semantic. Also corrected two adjacent staleness spots: sq blocked now says "the dependency ref kinds (blocks / depends-on by default)", and the sq workflow subcommand list was missing four subcommands including ref-kinds.
  - Test module updated in the same pass so nothing is red between changes: the row-count pin is now len(spec.ref_kinds) with a per-kind row assertion, plus a new test that a declared extra kind gains a row with no template change, and one that a renamed default kind reads its own name with no bundled spelling left in the section. The stability-doc test asserts the new policy and the absence of the frozen-nine sentence. Module docstring records that "static" describes the narrative, not the table.
  - Regenerated the manifest without bump_version.py; pyproject still reads 0.14.0 and only the 0.14.0 index entry moved (verified by diffing every version key against HEAD) - one hash, workflow_static.md.j2. One blob inserted, zero swept. sq sync ran and is now a no-op; note it also picked up other 0.14 template work that had not been synced into this repo managed files (CLAUDE.md, the ten role files, the sq-<type> skills, .squads.toml version stamp) - that churn is not from my edit.
  - Gates: ruff check, ruff format --check and pyright all clean with --all-extras. tests/meta plus the golden and cheatsheet modules: 285 passed, then 246 passed on the re-run after the docs/workflow.md line. sq check clean. Goldens moved: workflow_cheatsheet, workflow_cheatsheet_raw, agents_md_section - all three carry the cheatsheet body. Full suite left to the main loop. @tech-lead
<!-- sq:discussion:end -->

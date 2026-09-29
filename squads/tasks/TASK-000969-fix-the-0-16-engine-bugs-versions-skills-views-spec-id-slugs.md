---
id: TASK-969
sequence_id: 969
type: task
title: 'Fix the 0.16 engine bugs: versions, skills, views, spec id, slugs'
status: Draft
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-937:fixes
- BUG-938:fixes
- BUG-957:fixes
- BUG-962:fixes
- BUG-965:fixes
- MILE-934:targets
description: Five independent engine fixes for MILE-934; the spec-identity and slug
  subtasks wait on architect rulings
subentities:
- local_id: ST1
  title: Order prereleases below their release in version_tuple
  status: Todo
  assignee: python-dev
- local_id: ST2
  title: Restore frontmatter on a stripped managed skill file
  status: Todo
  assignee: python-dev
- local_id: ST3
  title: Report view tags outside the body region
  status: Todo
  assignee: python-dev
- local_id: ST4
  title: Make the self-view spec identity track the merged spec
  status: Todo
  assignee: python-dev
- local_id: ST5
  title: Transliterate accented letters in slugify
  status: Todo
  assignee: python-dev
created_at: '2026-09-29T13:31:10Z'
updated_at: '2026-09-29T13:32:21Z'
---
<!-- sq:body -->
Five engine bugs targeted at 0.16, one dev pass. Each subtask is independent and touches a
different area, so they can land in any order. ST4 and ST5 wait on @architect rulings
(see below). Take ST1 to ST3 first.

## Subtasks

- **ST1, prerelease-aware `version_tuple` (BUG-937).** Delete the duplicate in
  `_cli/_common.py` and make `squads._util.version_tuple` order a prerelease below its
  release, so `sq migrate chlog` prints the window `sq migrate up` tells the operator to
  read.
- **ST2, recover a managed skill file with no frontmatter (BUG-938).** `sq sync` writes a
  missing managed skill file back with its frontmatter, and re-stamps one that already
  lost it. `sq check` names `sq sync` as the fix.
- **ST3, make out-of-region view tags visible (BUG-957).** Report only: `sq check` flags a
  `sq:view:*` tag outside `sq:body`, `view rm` stops saying "not present", and `view add`
  refuses rather than adding a duplicate. No writer moves tags.
- **ST4, spec identity that changes with the merged spec (BUG-962).** Blocked on an
  architect ruling about the contract. This **changes the `--json` shape** of `sq
  workflow view ... --json`'s `spec` block.
- **ST5, transliterate accented letters in `slugify` (BUG-965).** NFKD plus an explicit
  map. Slugs already stored in a squad never change. The dev-role path re-derives its
  slug from `extra.tech`, so it has to be pinned to the stored slug. Waiting on an
  architect ruling for existing identity keys.

## Acceptance (whole task)

- Each subtask's own acceptance holds (see the subtask bodies).
- **Falsified test per subtask:** break the fix on purpose, watch the new test go red,
  restore it. The handoff records what was broken and which test went red.
- **Table-driven coverage over input shapes**, not one test per branch: each subtask body
  names the shape families to cover. Add a pipeline-level invariant where one exists
  (for example: whatever window `migrate up` prints, `chlog` over that window is
  non-empty).
- Service-level test plus a CLI smoke test for each behaviour change.
- Gates clean: `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .`,
  `sq check`. Run `tests/meta` if you add a module-level constant (the mutable-state
  guard). CHANGELOG entries go through the writer. Name them in the handoff.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 969 add-subtask "<title>"`; track with `sq task 969 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Order prereleases below their release in version_tuple

<!-- sq:subtask:ST1:body -->
**Bug:** BUG-937. `version_tuple("0.14.0rc1")` comes out as `(0, 14, 1)`, which sorts
above `0.14.0`, so `sq migrate chlog v0.14.0rc1..v0.15.0` leaves out the 0.14.0 manual
steps that `migrate up` just told the operator to read. The duplicate in
`_cli/_common.py` is the one `_cli/_migrate.py` actually imports.

**Approach**

- Delete `_cli/_common.py::version_tuple`. Every caller (the `chlog` filter, the drift
  notice at `_cli/_common.py`) imports `squads._util.version_tuple`.
- Fix the comparator itself: split each segment into its numeric release part and an
  optional prerelease tag, and order `aN < bN < rcN < release` (with `.devN` below all of
  them if you handle it). Don't add a dependency. `packaging` is not declared in
  `pyproject.toml`, so relying on it transitively is not OK.
- The two selection sites in `_overrides/_manifest.py` (`min`/`sorted`) and the
  `_overrides/_service.py` floor compare pick up the fix automatically. Check their
  docstrings still say what the code does.

**Acceptance**

- Table-driven ordering test over shape families: clean `X.Y.Z` pairs; prerelease vs its
  own release (`0.14.0rc1 < 0.14.0`); prerelease vs the previous and next release;
  `a < b < rc`, and multi-digit numbers (`rc10 > rc9`); a leading `v`; a short `X.Y` vs
  `X.Y.0`; a segment with no digits (keeps today's fail-safe `0`). Assert both `<` and
  `sorted`/`min` results.
- End-to-end CLI test: a squad stamped `squads_version = "0.14.0rc1"` at an old schema,
  then `migrate up`. Parse the `chlog` window it prints and run it: the 0.14.0 manual
  steps come out. Plus the invariant: the window `up` prints is never empty when manual
  steps remain.
- Falsified: put the digit-concatenating body back and watch the ordering rows and the
  end-to-end test go red.
- `rg "def version_tuple" src` finds exactly one definition.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Restore frontmatter on a stripped managed skill file

<!-- sq:subtask:ST2:body -->
**Bug:** BUG-938. Delete a managed skill's item file (`SKILL-NNNNNN-<slug>.md`), run
`sq sync`, and it comes back with the body view tag but no frontmatter at all. Neither
`sync` nor `repair` ever re-stamps it. `sq check` flags it forever with "fix the file and
repair again", and no `sq` verb can do that fix.

**Approach**

- `sq sync` owns managed skill files. When it writes one that is missing, it writes the
  whole file, frontmatter included, the way a fresh `add_skill`/init does, and not just
  the body region. Find the path that writes body-only today and route it through the
  full-file writer.
- For a file that already lost its frontmatter (a `SKILL-` filename whose frontmatter has
  no `id`), `sq sync` re-stamps it. Take the id, sequence number and type from the
  filename, and slug, title and status from the index's carried-forward entry for that
  id, then rewrite the frontmatter with marker-safe edits (`_sections.py` /
  `_itemfile.py`). Keep the body as it is. This only runs for managed skills (items
  `sync` regenerates anyway). It is never a general "rebuild frontmatter from the index"
  path for authored items. That would turn invariant #1 upside down.
- Follow the markdown-before-index rule (invariant #8): the file is written before the
  index commit.
- `sq check`'s and `sq repair`'s message for this state names `sq sync` as the fix.

**Acceptance**

- Table-driven over shapes: a permanently-system skill (`squads`) and a per-item-type skill
  (`sq-task`), each with the file deleted, frontmatter stripped whole, frontmatter present
  but missing only `id`, and an empty file. After one `sq sync`, each file has valid YAML
  frontmatter matching its index entry, markers intact, and `sq check` clean.
- A non-managed item (for example a task) with its frontmatter stripped is **not**
  re-stamped. `sq check`/`repair` still report it.
- Round trip: delete, sync, repair, check comes back clean, and a second `sync` leaves the
  file byte-identical.
- Falsified: turn off the re-stamp and watch the table go red.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Report view tags outside the body region

<!-- sq:subtask:ST3:body -->
**Bug:** BUG-957. A `sq:view:<name>` tag outside an item's `sq:body` region doesn't
render, `sq check` stays silent about it, and `sq view rm` says "was not present, nothing
to do" (exit 0) while the tag is still on disk. `view add` then inserts a second copy, and
`sq check` flags that as a duplicate marker. Three routes reach this: a template override,
`sq adopt`, and hand edits.

**Scope ruling (tech lead): report only.** Writers stay region-scoped. Nothing moves a tag
automatically.

**Approach**

- `sq check`: a new rule in `_services/_validators.py` flags any `sq:view:*` tag found
  outside the region it renders from. It names the item, the view, and the remedy (move
  the tag inside `sq:body`). The same rule catches it in a project template override
  (`.overrides/.../items/*.md.j2`), so route 1 is caught at the source. Severity: warning.
- `sq view rm`: when the region-scoped removal finds nothing but a tag with that name
  exists elsewhere in the file, don't report "not present". Say where the tag is and that
  `view rm` only manages in-region tags. Exit non-zero, because the requested state was
  not reached.
- `sq view add`: when an out-of-region tag with that name exists, refuse with the same
  message instead of inserting a duplicate.
- Use `_sections.find_markers` over the whole file for detection. Don't widen
  `insert_unpaired_marker`/`remove_unpaired_marker`.

**Acceptance**

- Table-driven over tag position × surface: in `sq:body`; before the first region; after
  `sq:body:end`; inside another region (for example a sub-entity block); two copies, one
  in and one out. Surfaces: render count, `sq check` finding, `view rm` result and exit
  code, `view add` result. In-region rows keep today's behaviour exactly.
- Route coverage: one test each for the override-template, `sq adopt`, and hand-edited
  cases.
- Falsified: disable the new check rule and the `view rm` detection, and watch the
  out-of-region rows go red.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Make the self-view spec identity track the merged spec

<!-- sq:subtask:ST4:body -->
**Bug:** BUG-962. `_spec_identity_json` (`_cli/_workflow_cmd.py`) emits
`{schema_version, override}`, where `override` is only
`.overrides/workflow.toml`'s `.is_file()`. Two different override documents, or one
document before and after an edit, produce the same block. `playbook` and `role` sources
also read `.overrides/playbook.toml` and `.overrides/roles/*.toml`, which the block
doesn't reflect at all.

**Blocked on an @architect ruling.** This is a contract decision. Don't start until it is
on the record:

- what to carry: a digest of the merged spec result, or a hash over the override document
  set (workflow + playbook + roles);
- what a client may do with it: equality only, or some ordering;
- whether `override` stays a presence boolean (and gets renamed or reworded to what it
  really means), or the digest replaces it.

**JSON shape: this changes it.** Any of the three answers adds a key to, or changes a key
of, the `spec` block of `sq workflow view <name> <id> --json`. Checked: no VS Code client
code reads this block today (`clients/vscode/src` has no hit on the `spec` identity key or
`workflow view`), so there is nothing to break. If the ruling adds a key, the canary's
exact-key pattern (TASK-968 ST2) should cover this block when the client starts reading
it. Say so in the handoff to @typescript-dev.

**Approach (once ruled)**

- Compute the identity from the active spec threaded through `Service.spec`, not from
  file presence. If it's a digest, build it from a canonical serialisation (sorted keys,
  stable across runs and machines) so it is deterministic.
- Fix the docstring's "in force" claim so it matches what the field reports.

**Acceptance**

- Table-driven over override shapes: none; workflow override A; workflow override B (same
  keys, different values: the BUG-962 repro); A reformatted with the same merged result;
  a playbook-only override; a roles-only override; a present-but-rejected document. Pairs
  that differ in merged result get different identities. Pairs with the same merged
  result follow whatever the ruling says (equal under a merged digest, possibly different
  under a document hash).
- Deterministic: same squad, two runs, identical block.
- Falsified: put the `.is_file()` boolean back and watch the A-vs-B row go red.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-09-29T13:32:14Z] Olivia Lead:
  - @architect ruling needed before ST4 dispatch (BUG-962): merged-spec digest vs override-document hash, equality-only vs ordered, and whether override stays a boolean. Any answer changes the spec block of sq workflow view --json. No VS Code consumer today.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Transliterate accented letters in slugify

<!-- sq:subtask:ST5:body -->
**Bug:** BUG-965. `slugify` (`_util.py`) drops non-ASCII letters instead of
transliterating them: `Réduire` becomes `r-duire`, `Élodie` becomes `op-lodie`, and
`Ça marche` becomes `a-marche`.

**Approach (the `slugify` change itself)**

- Before the existing `[^a-z0-9]+` filter: NFKD-normalise, drop combining marks
  (`unicodedata.combining`), then apply an explicit map for letters NFKD doesn't split up
  (`ß→ss`, `æ→ae`, `ø→o`, `œ→oe`, `ł→l`, `đ→d`, plus their uppercase forms). The map is a
  module constant. Allowlist it in the `tests/meta` mutable-state guard.
- Non-Latin scripts still fall back to `untitled`. That's a known limit and out of scope.

**Existing slugs: they must not change or break a lookup**

This fix changes identity keys. What it does to slugs already stored in a squad (read, not
driven; verify each one with a test):

- **Item filename slugs** (`create`, `_rename`): parsed back from the filename on
  load/repair, never re-derived. A retitle renames the file in the same step. Safe as is.
- **Operator, skill, memory slugs**: stored (`item.slug` / `extra.slug` / the memory
  filename). Every lookup (`--as`, `--assignee`, `sq skill <slug>`, `sq memory <role> show
  <slug>`) matches the stored string exactly and never recomputes it. Existing slugs keep
  resolving. **The gap:** `add_operator`/`add_skill` catch a duplicate only by comparing
  the *newly derived* slug. So re-adding "Élodie Martin" after the fix creates `op-elodie`
  next to the existing `op-lodie` instead of refusing.
- **Dev-role slugs: the dangerous one.** `dev_base_from_item` calls `dev_role(extra.tech)`,
  which re-derives `slug = slugify(tech) + "-dev"` on every resolve (sync, `role show`,
  check). A dev role whose tech label has an accent would resolve to a *new* slug after the
  fix, while its item, pointer files and `@mentions` keep the old one. On top of that,
  `resolve_dev_role` builds the override-TOML path from `tech.strip().lower()`, not
  `slugify`. Those two derivations already disagree for any non-trivial label.

**Required regardless of the ruling:** no stored slug changes silently, and every existing
lookup keeps resolving. Dev-role resolution keeps the item's stored slug, never a
re-derived one.

**Waiting on an @architect ruling:**

1. Is the stored slug authoritative over its derivation everywhere (so the dev-role path
   pins to `item.slug`)? MILE-934 is also retiring the `-dev` pseudo-role in favour of a
   declared capability, so this should line up with that ADR and not guess ahead of it.
2. Do existing mangled slugs stay as they are forever (no migration), or does a migration
   or an opt-in re-slug verb rename them? The default here is no migration.
3. Should duplicate detection in `add_operator`/`add_skill` also match the legacy
   derivation (or the stored full name), so a re-add can't fork one identity into two?

**Acceptance**

- Table-driven `slugify` test over shape families: plain ASCII (unchanged, byte-for-byte:
  a regression guard for every existing slug); precomposed accents; decomposed (NFD)
  input; `ß/æ/ø/œ/ł/đ` in both cases; an accent at a string boundary (`Ça`); mixed
  punctuation and accents; the `max_len` cut landing next to a multi-char expansion (`ß`);
  non-Latin (falls back to `untitled`); empty or whitespace only.
- Per identity consumer (operator, dev role, skill, memory): build a squad with an
  accented slug stored in the old form, apply the fix, and assert that the lookup, `sq
  sync` and `sq check` still resolve the stored slug and that no file or pointer is
  renamed.
- Falsified: take out the NFKD step and watch the accent rows go red. Make dev-role
  resolution re-derive the slug again and watch the stored-slug row go red.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-09-29T13:32:13Z] Olivia Lead:
  - @architect ruling needed before ST5 dispatch (BUG-965). dev_base_from_item re-derives the dev-role slug from extra.tech on every resolve, so fixing slugify would silently move an accented-tech dev role to a new slug. Three calls: (1) is the stored slug authoritative everywhere (pin dev-role resolution to item.slug), aligned with the MILE-934 dev-pseudo-role ADR; (2) existing mangled slugs stay forever (no migration) or get a re-slug path; (3) should add_operator/add_skill duplicate detection also match the legacy derivation. Default in the body: stored slugs never change, no migration.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T13:32:21Z] Olivia Lead:
  - Authored from BUG-937/938/957/962/965. Left in Draft. ST1-ST3 are ready to build; ST4 and ST5 wait on @architect rulings (see their subtask comments). Ruled ST3 report-only (no writer relocates tags).
<!-- sq:discussion:end -->

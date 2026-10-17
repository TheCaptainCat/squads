---
id: TASK-969
sequence_id: 969
type: task
title: 'Fix the 0.16 engine bugs: versions, skills, views, spec id, slugs'
status: Done
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
- BUG-978:fixes
description: Five independent engine fixes for MILE-934; the spec-identity and slug
  subtasks wait on architect rulings
subentities:
- local_id: ST1
  title: Order prereleases below their release in version_tuple
  status: Done
  assignee: python-dev
- local_id: ST2
  title: Restore frontmatter on a stripped managed skill file
  status: Done
  assignee: python-dev
- local_id: ST3
  title: Report view tags outside the body region
  status: Done
  assignee: python-dev
- local_id: ST4
  title: Make the self-view spec identity track the merged spec
  status: Done
  assignee: python-dev
- local_id: ST5
  title: Transliterate accented letters in slugify
  status: Done
  assignee: python-dev
- local_id: ST6
  title: Report two files carrying the same id
  status: Done
  assignee: python-dev
created_at: '2026-09-29T13:31:10Z'
updated_at: '2026-10-09T18:18:40Z'
---
<!-- sq:body -->
Six engine bugs targeted at 0.16, one dev pass. Each subtask is independent and touches a
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
- **ST6, report two files carrying one id (BUG-978).** `check` errors and `repair` exits 1
  naming every file. Plain repair refuses to pick a winner. `--renumber` renumbers a
  different-slug copy without rewriting refs (it lists them) and refuses a same-slug copy. `list`/`show`
  read the index and `show` warns. Writes to that id refuse. The ST2 restamp uses the same
  detector (REV-975 F3).

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
- [2026-09-29T13:32:14Z] `tech-lead` Olivia Lead:
  - @architect ruling needed before ST4 dispatch (BUG-962): merged-spec digest vs override-document hash, equality-only vs ordered, and whether override stays a boolean. Any answer changes the spec block of sq workflow view --json. No VS Code consumer today.
- [2026-09-29T13:44:18Z] `architect` Robert Architect:
  - Ruled in ADR-970 (Proposed, for op-pierre). Carry a digest of the merged workflow spec (sha256 over the model dump, key order kept), not a hash of override files: a file hash misses every upgrade that changes the bundled spec and is constant with no override. Equality only, opaque. override stays as a display flag with its meaning restated; the block becomes {schema_version, override, digest}. Playbook and roles are out: they do not resolve a self payload. Body rewritten to build from. @tech-lead ready to dispatch once you are satisfied; status left as is.
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
- [2026-09-29T13:32:13Z] `tech-lead` Olivia Lead:
  - @architect ruling needed before ST5 dispatch (BUG-965). dev_base_from_item re-derives the dev-role slug from extra.tech on every resolve, so fixing slugify would silently move an accented-tech dev role to a new slug. Three calls: (1) is the stored slug authoritative everywhere (pin dev-role resolution to item.slug), aligned with the MILE-934 dev-pseudo-role ADR; (2) existing mangled slugs stay forever (no migration) or get a re-slug path; (3) should add_operator/add_skill duplicate detection also match the legacy derivation. Default in the body: stored slugs never change, no migration.
- [2026-09-29T13:44:27Z] `architect` Robert Architect:
  - Ruled in ADR-971 (Proposed, for op-pierre). (1) The stored slug is authoritative everywhere; derivation only proposes one at creation. dev_base_from_item takes the slug from the item, and resolve_dev_role builds its override path from the derived slug, not tech.lower(). Read: without this, sync would rewrite extra.slug and the pointer name via to_extra() for an accented tech. (2) Existing slugs stay forever: no migration, no re-slug verb. (3) Duplicate detection in add_operator (no explicit --slug), add_skill and add_dev also matches a frozen private copy of the pre-fix rule. Compatible with the -dev retirement: no new -dev suffix reader. Body rewritten. @tech-lead ready to dispatch; status left as is.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Report two files carrying the same id

<!-- sq:subtask:ST6:body -->
**Bug:** BUG-978. When two item files carry the same `id`, nothing reports it. `sq check`
says "no issues", `sq repair` exits 0 with both files kept, and `list`/`show` show
whichever copy the scan reached last. REV-975 F3 depends on this: the managed-skill
restamp (ST2) can create exactly this state from a renamed file.

**Approach**

- **One detector, shared.** While scanning the corpus, group the item files by their
  frontmatter `id`, normalised through the same parser `from_frontmatter` uses, so a
  padded and an unpadded spelling of one id count as one. Any group with more than one
  file is a duplicate. `check`, `repair`, and the ST2 restamp all use this detector. None
  of them reimplements it.
- **`sq check`**: an error for each duplicate id, naming the id and every file that carries
  it (paths relative to the squad). Exit code follows the existing error level.
- **`sq repair`: report and refuse to pick a winner.** For a duplicated id, repair doesn't
  take either file's frontmatter. It keeps the previous index entry for that id if there
  is one (the same carry-forward it uses for an unreadable file), leaves the id out if
  there isn't, names every file, and exits 1. Every other item rebuilds as normal.
  *Why:* frontmatter is the source of truth (invariant #1), and here there are two
  truths. Every tie-break on offer (scan order, mtime, the file that sits in the right
  type folder, the file whose name matches the slug) can pick the stale copy and quietly
  drop the edits in the other one. That's the silent identity loss the bug is about. Only
  a human can tell which copy is meant. The remedy says to merge the content you want
  into one file, delete the other by hand, then run `sq repair`. Byte-identical copies
  get the same refusal: one rule, and keeping the extra copy costs nothing.
- **`repair --renumber` (op-pierre's ruling).** What happens depends on the slugs in the
  duplicate group. A file's slug is its frontmatter `slug`, or the filename slug if the
  frontmatter has none.
  - **All slugs different** (the parallel-tree merge collision): keep one file and mint a
    fresh number for each of the others, the same way the number-collision path does
    (renamed file and a rewritten frontmatter `id`, nothing else in the file). **Which file
    is kept:** sort the group by squad-relative POSIX path, byte order. The first one keeps
    the id. The rest get fresh numbers in that same order, so the same corpus always gives
    the same result.
  - **References are not rewritten.** Every existing reference to the old id is ambiguous
    (it could mean either copy), so nothing touches it: not refs, not `parent`, not
    sub-entity fields, not prose. `--renumber` lists them instead, one block per
    renumbered file:

    ```
    TASK-21: two files, different slugs
      kept      tasks/TASK-000021-alpha.md
      renumbered tasks/TASK-000021-other.md -> TASK-42 (tasks/TASK-000042-other.md)
      references to TASK-21 left unchanged; check each by hand:
        tasks/TASK-000030-beta.md   refs       TASK-21:implements
        bugs/BUG-000031-gamma.md    parent     TASK-21
        tasks/TASK-000030-beta.md   body:12    "see TASK-21 for the ..."
        tasks/TASK-000030-beta.md   comment:40 "@python-dev TASK-21 is ..."
    ```

    One line per reference: file, where it sits (`refs`, `parent`, a sub-entity field,
    or `body`/`comment` with its line number), and the reference text. Scan every item
    file, including the two copies themselves. If there are no references, print
    "no references". Exit 1 when any reference is listed, because a board that still
    needs a hand check is not a clean result. Exit 0 when there are none.
  - **Any two slugs the same** (a stray file copy, including a group of three where only
    two match): refuse the whole group. Report it the way plain `repair` does, rename
    nothing, and exit 1. Distinct ids that share a number keep today's `--renumber`
    behaviour.
- **`list`/`show` while a duplicate exists.** Both keep reading from the index, so `list`
  shows one row: the carried-forward entry, or no row if there was none. `show` renders
  the indexed file and prints a warning to stderr naming the other files and pointing at
  `sq check`. The item stays readable, and the `--json` output is unchanged.
- **Writes refuse.** `update`, `body`, `comment`, sub-entity edits, retitle, retype and
  every other write to a duplicated id refuse with the same message, because a write would
  land on one copy chosen by scan order. The check has to be cheap: glob for that
  sequence number's files across the type folders, and don't rescan the whole corpus.
- **Closes REV-975 F3 with ST2.** The restamp calls the detector before it writes, and
  skips and reports a file whose id another file already carries. Mark F3 Fixed and
  point it at this subtask.

**Acceptance**

- Table-driven over the bug's shapes, each run through `check`, `repair`, `repair
  --renumber`, `list -a`, `show`, and one write:
  1. work item, same id, same slug (a `-copy` file);
  2. skill, same id;
  3. same id, different slug and title (the copy that shadows the original);
  4. same id, file in a different type folder (`bugs/TASK-...`);
  5. REV-975 F3: a managed skill renamed away from its slug with frontmatter intact, then
     `sync`;
  6. REV-975 F3: the same rename with frontmatter stripped, then `sync`;
  7. three files for one id;
  8. a padded and an unpadded spelling of one id.
  Every row: `check` errors and names every file; `repair` exits 1, names every file, and
  keeps both files byte-identical; `--renumber` refuses on same-slug rows (1, 2, 4, 5, 8) and, on different-slug rows (3, 7 when all slugs differ), keeps the first path, renumbers the rest, rewrites no reference, and prints the listing; `list`
  shows at most one row; `show` warns; the write refuses. Control rows: a clean squad,
  and distinct ids sharing a number, both behave exactly as today.
- `--renumber` rows: the kept file is the same across repeated runs and a reversed scan order; a different-slug group with zero references (exit 0) and with references in each position (refs, parent, sub-entity field, body, comment; exit 1, every one listed, none changed); a three-file group mixing same and different slugs (refused).
- Also cover: with no previous index (`.squads.json` deleted), repair leaves the id out
  and still exits 1.
- Falsified: turn off the detector (group but never report), watch rows 1 to 8 go red,
  restore it.
- Service-level tests plus a CLI smoke test for `check`, `repair` and `show`.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-09-29T14:33:06Z] `tech-lead` Olivia Lead:
  - Added per op-pierre (via manager). Ruled: repair reports and refuses to pick a winner (carries the previous entry, exits 1), because any tie-break can silently drop edits. Also closes REV-975 F3 with ST2.
- [2026-09-29T14:36:42Z] `op-pierre` Pierre Chat:
  - repair --renumber on a same-id, different-slug duplicate (the merge case): keep one, mint a fresh number for the other, do NOT rewrite the ambiguous references; list every ref to that id for a manual check. Same-slug copies (a stray file copy) refuse.
- [2026-09-29T15:39:39Z] `op-pierre` Pierre Chat:
  - repair --renumber refuses when the duplicate files are byte-identical apart from the filename (a copy, not a merge collision).
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T13:32:21Z] `tech-lead` Olivia Lead:
  - Authored from BUG-937/938/957/962/965. Left in Draft. ST1-ST3 are ready to build; ST4 and ST5 wait on @architect rulings (see their subtask comments). Ruled ST3 report-only (no writer relocates tags).
- [2026-09-29T13:47:49Z] `manager` Catherine Manager:
  - Dispatched ST1-ST3 to @python-dev. ST4/ST5 were waiting on @architect rulings, now ADR-970/ADR-971 (Proposed).
  - Restated: a git stash plus reset at 13:44Z had reverted this item's statuses and the original dispatch comment.
- [2026-09-29T13:55:15Z] `manager` Catherine Manager:
  - ADR-970 and ADR-971 accepted by op-pierre (no slug-rename command). ST4/ST5 dispatched to @python-dev. Full suite green on ST1-ST3: 6342 passed, pyright 0 errors.
- [2026-09-29T13:56:00Z] `python-dev` Elias Python:
  - ST1-ST3 implemented, each with a falsified table-driven test. version_tuple is prerelease-aware in _util and the CLI duplicate is gone. sync re-stamps a managed skill file that lost its id from the index entry. sq check warns on out-of-region view tags, and view add/disable refuse them (view rm is retired, so disable is the verb that misreported). CHANGELOG entries needed for all three, via the writer.
- [2026-09-29T14:03:33Z] `python-dev` Elias Python:
  - ST4 and ST5 implemented per ADR-970 and ADR-971, each with a falsified table-driven test. The self-view spec block is now {schema_version, override, digest}. slugify transliterates accented Latin letters, dev_base_from_item takes the slug from the item, resolve_dev_role reads its override under the stored-form slug, and duplicate checks in add_operator/add_skill/add_dev also match a frozen copy of the earlier rule. One existing operator test pinned the old accent-dropping slug and was updated. CHANGELOG entries (both) and a docs/stability.md refresh for the digest key are needed via the writer; the exact-key canary should cover the self block when the client starts reading it.
- [2026-09-29T14:24:14Z] `manager` Catherine Manager:
  - REV-975 ChangesRequested: F1-F2 on ST1, F3-F5+F7 on ST2, F6 on ST3, F8-F9 on ST5. Back to @python-dev.
- [2026-09-29T14:30:26Z] `op-pierre` Pierre Chat:
  - BUG-978 goes into this task as a subtask, fixed in the same pass as the REV-975 restamp work.
- [2026-09-29T14:36:30Z] `python-dev` Elias Python:
  - All nine REV-975 findings fixed, each with a falsified table-driven test. version_tuple orders by PEP 440 with the release numbers as their own tuple. The managed skill restamp now builds frontmatter from the file name and the skill catalog, runs before and after the sync writes, rebuilds the index when it lacks the restored file, refuses to create a second file with the same id, and rebuilds unreadable YAML. repair, adopt and migrate print the single sync remedy for such a file. The duplicate view tag message names a working remedy. legacy_slugify is a self-contained frozen copy; the transliteration map covers thorn, eth, h and t stroke, dotless i, and the length cut never splits an expansion. One existing sync test asserted that a merge-conflicted managed skill file aborts sync; it now asserts sync rebuilds it. Fast gates clean; tests/cli, tests/integration, tests/service, tests/unit and tests/meta pass.
- [2026-09-29T14:57:48Z] `manager` Catherine Manager:
  - Checkpoint 48cf1444 (suite 6412 passed). REV-975 F10-F13 (restamp) reopen ST2; ST6 (BUG-978) dispatched with them to @python-dev in one pass.
- [2026-09-29T15:17:49Z] `python-dev` Elias Python:
  - REV-975 F10-F13 and ST6 done, each with a falsified table-driven test. The restamp carries the index's timestamps, refuses on a duplicate id or slug, rebuilds only a conflict wholly inside the frontmatter, and check names the remedy that works. One shared detector (services/_duplicate_ids.py) serves check, repair and the restamp. check errors and names every file; repair refuses to pick a winner and exits 1; repair --renumber renumbers only groups whose slugs all differ (first path by byte order keeps the id), rewrites no reference and lists every one; show warns; writes refuse. A file's slug is extra.slug, else frontmatter slug, else the filename slug, so a work item copied to a differently named file counts as a different slug and is renumbered, while a skill copy or a copy in another type folder is refused. Two scan-wrapping test helpers gained a carriers argument. CHANGELOG via the writer.
- [2026-09-29T15:41:36Z] `python-dev` Elias Python:
  - ST6 addition: repair --renumber also refuses a duplicate group whose files are byte-identical (a copy, not a collision); a whitespace-only difference counts as different, since a byte comparison cannot tell an edit from noise and renumbering keeps both files. Rows added; falsified (1 red).
- [2026-09-29T15:58:40Z] `manager` Catherine Manager:
  - REV-975 round 3: F11 reopened, F14-F22 new (F14 high). ST2/ST6 back to @python-dev as one consolidation pass: one identity definition shared by detector, write guard and restamp.
- [2026-09-29T16:23:22Z] `python-dev` Elias Python:
  - REV-975 round 3 (F11, F14-F22) done as one consolidation: file identity (id and slug) is defined once in _duplicate_ids.py and used by the detector, the write guard, the restamp and the renumber scan.
    
    Index parses and file reads, measured with the same probe on 48cf1444 and now (clean squad after an initial sync):
    - sync clean: 7 parses, 7 max reads of one file (baseline 7 / 7, now 7 / 7)
    - check clean: 1 parse, each file read once (baseline 1 / 1, now 1 / 1)
    - check with three stripped skills: 2 parses, 1 file read twice (baseline 2 / 1, now 2 / 1; it was 3 parses and 13 re-read files before this pass)
    - sync with three stripped skills: 8 parses at 48cf1444, 9 now (one extra parse, only when a file needs restamping)
    
    Writes: every write verb (comment, body, retitle, status, link/unlink, add/rm ref, sub-entity, remove, remove --force, retype, rename-status, set-default) checks before it touches a file; retype, rename-status and set-default refuse while any id is duplicated. The table proves a refused write leaves the squad tree byte-identical by hash.
    Renumber: keeps the file the index points at, refuses a group with a file outside its type folder, lists references after all renames. CHANGELOG via the writer.
- [2026-09-29T16:35:52Z] `manager` Catherine Manager:
  - REV-975 round 4: F11, F14-F22 Verified; F23 (write-guard cost, ~2.3x on show/comment), F24, F25 back to @python-dev.
- [2026-09-29T16:52:03Z] `python-dev` Elias Python:
  - REV-975 round 4 (F23-F25) done.
    
    Timings, median of 5 runs each, on a copy of this repo's 1029-file squad (separate interpreter per run):
    - task 969 show: c5331f42 0.79s, now 0.78s (round 3 build: 1.8s)
    - task 969 show --json: c5331f42 0.74s, now 0.80s (that path runs no guard; run-to-run noise)
    - task 969 comment: c5331f42 0.84s, now 0.86s (round 3 build: 1.9s)
    
    Guard rule: only files whose name carries the item's number, or no number at all, are read, then confirmed by frontmatter id. A copy with a well-formed name for a different number (for example TASK-000099-alpha.md carrying id TASK-22) is no longer seen by show or by writes; check and repair still find it (tested). Bulk-rewrite verbs (retype, status rename, set-default) still read every file, since they may touch any of them. A test bounds the files one write reads and shows it does not grow with the corpus.
    
    Scan state (skill texts, skill items, skill folder, id carriers) now lives in a ScanContext created by check, repair or the restamp and passed down; nothing is kept on the service. The misplaced comment in set_default_role is back on default_kind.
- [2026-09-29T17:05:11Z] `tech-writer` Theo Writer:
  - CHANGELOG 0.16.0 section added (new, with compare link): Added self-view spec digest; Changed repair --renumber on one id in several files; Fixed duplicate-id reporting, slug transliteration, dev add override filename, sync skill frontmatter restore, out-of-region view tags, migrate chlog prerelease bounds. Canary fixes left out (no earlier section lists test-harness changes).
  - Docs: stability.md (self spec block + digest rules), faq.md (ID collisions rewritten for same-id vs shared-number, sync bullet), internals.md (renumber + check), workflow.md (out-of-region tags, migration skip note), migration.md (prerelease chlog bounds), roles.md (slug derivation, stored slugs never change), README.md (renumber link).
  - Already wrong before this: workflow.md said check accepts an out-of-region tag and view add duplicates it; faq/internals said repair --renumber rewrites every reference for a same-id collision. Claims checked against the diff and a scratch squad. @manager for review; nothing committed.
- [2026-10-09T18:15:26Z] `tech-writer` Theo Writer:
  - Docs fix for the hygiene gate failure on release/0.16 (not a change to the 0.16 engine work).
    
    The gate test_source_and_docs_have_no_stray_ticket_references_anywhere_in_their_text reported docs/faq.md lines 138, 141 and 144 (token TASK-2). These were concrete example IDs (TASK-21, BUG-21) in the ID collisions section, added by commit 7cd45323.
    
    Changed, docs/faq.md only:
    - L138: `TASK-21` and `BUG-21` became `TASK-<n>` and `BUG-<n>`, with the text saying they carry the same number but are two different IDs.
    - L141: "both branches created `TASK-21`" became "both branches created `TASK-<n>`, so one ID is carried by two files".
    - L144: "A reference to `TASK-21`" became "A reference to `TASK-<n>`".
    The rest of the section is unchanged, and the same-number versus same-ID distinction still reads clearly.
    
    Checked the rest of 7cd45323 (CHANGELOG.md, README.md, docs/*.md): the lines it added contain no concrete item IDs under the gate pattern. Only the three faq.md lines matched.
    
    Test run: tests/meta/test_source_and_new_test_tree_have_no_stray_ticket_references.py, 14 passed. The gate's test file and allowlist are untouched. Full suite not run.
    
    No status change. No git state changed.
- [2026-10-09T18:18:38Z] `manager` Catherine Manager:
  - Closing under the operator's standing delegation for reviewed, verified, non-visual work: all six subtasks Done, REV-975 Approved, the six bugs Verified by QA. Gates on the tree with the faq example-ID fix: pyright, ruff check and ruff format clean; full suite 6505 passed, 13 skipped.
<!-- sq:discussion:end -->

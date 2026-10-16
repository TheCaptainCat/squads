---
id: REV-1063
sequence_id: 1063
type: review
title: Flat frontmatter and the 0.16 flattening step
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-1059:addresses
- FEAT-1016:addresses
- MILE-934:targets
description: 'Review of TASK-1059 ST1-ST8: flat frontmatter, the 0.16 flattening contribution
  and the chosen-name fix.'
subentities:
- local_id: F1
  title: A CRLF role file is corrupted, other CRLF items stay nested
  status: Fixed
  severity: high
- local_id: F2
  title: An unquoted date attribute makes its item unwritable
  status: Fixed
  severity: high
- local_id: F3
  title: Config-sourced role names are marked chosen and frozen
  status: Fixed
  severity: medium
- local_id: F4
  title: A refused run leaves an index 0.15.0 misreads
  status: Fixed
  severity: medium
- local_id: F5
  title: Hand-added path and prefix keys are dropped on write
  status: Fixed
  severity: medium
- local_id: F6
  title: A declared role attribute named like a retired key is swept
  status: Fixed
  severity: medium
- local_id: F7
  title: An unchosen developer keeps a removed per-slug name
  status: Fixed
  severity: low
- local_id: F8
  title: The flattening guesses on core-key and nested extra shapes
  status: Fixed
  severity: low
- local_id: F9
  title: A differing skill description is dropped unlisted
  status: Fixed
  severity: low
- local_id: F10
  title: Pin table spells attribute keys as literals
  status: Fixed
  severity: low
created_at: '2026-10-16T15:11:18Z'
updated_at: '2026-10-16T16:14:43Z'
---
<!-- sq:body -->
## Scope

TASK-1059 ST1 to ST8 at commit 62871850: the flat frontmatter of ADR-1007, the `name_chosen` rule that fixes BUG-1049, and the `flat-frontmatter` contribution of the 0.15 to 0.16 step. ST9 and ST10 are not in scope.

## Method

- Read the step, the compatibility reader, the index-load shim, the item model and writer, the skew guard, the resolver seams, the validator wiring and the meta guard.
- Built 0.15 squads with the released `~/.local/bin/sq` 0.15.0 and migrated them with the dev build, each in its own git-initialised folder under the session scratchpad. The squads held a renamed role, a retired role, a pool developer, a named developer, a role named through `roles.toml`, one named through a per-slug file, a project-defined role, an operator without `full_name`, an operator whose title differs from its full name, unknown keys inside and outside `extra`, an unquoted date, and CRLF files.
- Ran the refusal path with the whole tree hashed before and after, then drove the released tool on the squad the refused run left behind.
- On a squad built by the dev tree: the write invariant (hand-added keys, a declared attribute, a retired key name), the name precedence across bundled, `roles.toml`, per-slug and chosen names for a bundled role and a developer, `attribute_valid` against an unrelated write, and the `extra_fields` refusal at migration.

## What holds (driven)

- The step plans everything before it writes. A refusal joins the failures of both contributions, writes no item file and keeps the stamp. Only the index changes, through the pre-runner rebuild (see F4).
- Operators: the full name moves into `title` and the file is listed. The importer shape gets its slug from the file name. Headers resolve by full name or slug, as the ADR-979 A6 note says.
- Unknown keys inside `extra` (a mapping value, a list) are lifted unchanged, and hand-added top-level keys survive an unrelated write, except `path` and `prefix` (F5) and values YAML parses as a date (F2).
- Name precedence for a role created by the dev tree: an unchosen bundled role follows `roles.toml` and then its per-slug file, and goes back to the catalog name when the override is removed. A chosen role and a chosen developer keep their names under every layer. Each rename moves `updated_at` and is recorded in the reflog. `init --name` stores true and `--default-names` stores false.
- `attribute_valid` cannot block an unrelated write: `gate()` passes no `raw_text`, so the validator, which requires it, does not run there. An item with an invalid stored `tags` was retitled with exit 0, and `sq check` reports the value at error level.
- An `extra_fields` override stops `sq migrate up` before anything is written, with the replacement named.
- The two skill descriptions dropped in this repository were byte-identical to the top-level ones.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1063 add-finding "…" --severity medium`; track with `sq review 1063 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A CRLF role file is corrupted, other CRLF items stay nested

<!-- sq:finding:F1:body -->
**Driven.** The flattening reads each file as bytes and decodes it without newline translation, then calls `read_frontmatter` and `replace_frontmatter`, whose block pattern is `^---\n(.*?)\n---\n?`. A file with CRLF line endings does not match, so the planner sees an empty mapping.

- **A CRLF role file is corrupted.** The planner still adds `name_chosen` to the empty mapping, and the writer's `replace_frontmatter` finds no block, so it prepends a second one. The file then opens with `---` / `name_chosen: false` / `---` and the real frontmatter follows as body text. Run on a 0.15 squad built by the released tool, with `ROLE-000019-devops.md` (chosen name `Hank Chosen`) converted to CRLF: the run stamps the squad 0.16, then its trailing repair reports `file has no id in frontmatter` and exits 1. Every later `sq` command reports the role as invalid item data. `sq role list` shows `devops` as the catalog's `Hugo Ops`, so the chosen name is gone. No reverse migration exists.
- **Any other CRLF item is skipped without a word.** A CRLF guide with `extra: {tags: [a, b], tech: python}` is not flattened, not reported and not counted. After the run, `show --json` carries `extra` as an attribute and `tags`/`tech` as unset, `sq check` is clean, and the next write keeps the nested block. This is the way a nested `extra` survives into normal operation.

**Failure scenario.** A Windows adopter checks out with `core.autocrlf=true`, so the working tree is CRLF. `sq migrate up` corrupts every role file and leaves every other item nested, and a squad stamped 0.16 cannot be migrated again.

**Fix direction.** Normalise line endings when parsing, or refuse a CRLF frontmatter block in the pre-flight. The frontmatter writer needs a terminator-preserving path, the same as the header writer's. Add CRLF rows to the step's table for a role, an operator, a skill and a plain item.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T15:38:14Z] Elias Python:
  - Fixed. Falsification: CRLF round-trip table (LF/CRLF x role, developer, operator, skill, guide); reverting the LF-only regex turns 6 tests red.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — An unquoted date attribute makes its item unwritable

<!-- sq:finding:F2:body -->
**Driven.** YAML's `safe_load` reads an unquoted `2026-12-01` as a `date`, an unquoted timestamp as a `datetime`, and `{1: a}` with an int key. The index stores attributes through pydantic `mode="json"`, so it holds the strings `"2026-12-01"` and `{"1": "a"}`. `frontmatter_skew` compares the disk side, which is still a `date`, with the index side, which is a `str`. They never agree, so every write to the item is refused:

    error: MILE-15: on-disk frontmatter has diverged from the index (target_date) — run `sq repair` before mutating MILE-15 again

`sq repair` rebuilds the same index, so the refusal comes back after it. `sq check` warns about drift on every run. Steps run on a dev-built squad: `--set target_date=2026-12-01` writes `'2026-12-01'` quoted, which works. Then `target_date: 2026-12-02` written by hand, then `sq repair`, then `sq milestone 15 comment`: refused. A hand-added `due: 2026-10-20` on a task fails the same way.

**Scope.** The `extra` block on 0.15 had the same defect (an unquoted `extra.deadline` shows drift under the released tool). This change widens it to every top-level key, at the moment it starts keeping hand-added keys. An unquoted date is the natural spelling of the `date` kind it introduces, and the 0.16 step copies an unquoted `extra` value across unchanged (`deadline` stays a `date`).

**Failure scenario.** An adopter writes `target_date: 2026-12-01` by hand on a milestone. The milestone can no longer be written. The remedy the error gives does nothing, and the cause, quoting the value, is named nowhere.

**Fix direction.** Make the skew comparison and the index agree on one value shape, for example by normalising attribute values to their JSON form on both sides of the comparison. The write-invariant table needs a date row, a datetime row and a non-string-key row.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T15:38:16Z] Elias Python:
  - Fixed. Falsification: YAML-typed scalars (date, timestamp, non-string key) rows; identity _json_form turns 45 tests red.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Config-sourced role names are marked chosen and frozen

<!-- sq:finding:F3:body -->
**Driven.** `name_was_chosen` compares a bundled role's stored name with the bundled catalog name only, and a developer's with pool names only. A 0.15 name that came from configuration is therefore marked `name_chosen: true` and frozen:

- `qa` renamed by `.overrides/roles/qa.toml` (`full_name = "Quinn Perslug"`, applied by a 0.15 `sq sync`) is marked chosen.
- `product-owner` activated while `roles.toml` set `full_name = "Pam Toml"` is marked chosen.

After the run, changing the per-slug file to `Quinn Two` (and `roles.toml` to `Pam Two`) and running `sq sync` renames neither of them, and `sq check` stays clean. On 0.15 the per-slug edit renamed `qa` (BUG-1049 records this as driven). A project-defined role was renamed in the same run (`Dana Data` to `Dana Two`), so the two cases now behave differently. The operator's ruling is that configuration supplies the default name of a role never named. No operator chose these names with `--name`.

The step's MANUAL covers only the opposite direction (keeping a name for a role marked never named). Nothing tells an adopter that a role whose name came from their override has stopped following that override.

**Failure scenario.** An adopter renames every agent through per-slug files on 0.15 and migrates. The next time they edit one of those files, nothing changes and nothing reports why.

**Fix direction.** Decide against the name configuration resolves at migration time (bundled catalog, then `roles.toml`, then the per-slug file; for a developer, the pool draw and then the per-slug file). Only a name that matches none of them is chosen. Add per-slug and `roles.toml` rows to the step's `name_chosen` table.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T15:38:18Z] Elias Python:
  - Fixed. Falsification: name is unchosen when it equals any configuration layer name (bundled, roles.toml, per-slug, pool); old bundled-only rule turns 5 tests red.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — A refused run leaves an index 0.15.0 misreads

<!-- sq:finding:F4:body -->
**Driven.** `sq migrate up` rebuilds the index from the files before the first runner. That rebuild now writes items in the new shape (`attributes`, `slug_in_file`, no `extra`) while the stamp stays at 0.15. When the step refuses, it says to change the roster with a release that reads schema v0.15. The released 0.15.0 tool then reads an index whose role and operator entries carry no `extra`:

- `sq role python-dev show` reports `(unassigned — run sq dev add --tech python)`.
- `sq check` reports every author as unregistered and every item as drifted.
- `sq sync` regenerates managed files from that index. `.claude/agents/python-dev.md` loses `model: sonnet` and `color`, and its prose becomes "the Elias Python on this project". The `CLAUDE.md` roster lists `Ann` instead of `Ann Smith` and gives the developers' names as their titles.

A 0.15 `sq repair` then a `sq sync` restore it, and the item files are untouched. The index has always been rebuildable, but this shape mismatch at a 0.15 stamp is new with this change, and the refusal text does not say to run a repair first.

**Failure scenario.** An adopter's run is refused for a duplicate name. They follow the printed advice, switch to 0.15.0 and run `sq sync`, and commit agent pointers and a `CLAUDE.md` that lost their model, colour and names.

**Fix direction.** Either the pre-runner rebuild stays in the old shape until the step commits, or a refusal restores the index it found. Failing both, the refusal should tell the user to run `sq repair` with 0.15.0 before anything else.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T15:38:20Z] Elias Python:
  - Fixed. Falsification: refused first step restores the index as 0.15 read it, later step says rebuild with earlier release; no restore turns 1 test red.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Hand-added path and prefix keys are dropped on write

<!-- sq:finding:F5:body -->
**Driven.** `_frontmatter_payload` leaves `NON_FRONTMATTER_KEYS` (`path`, `prefix`) out of `attributes`, and `to_frontmatter_dict` never writes them. A hand-added `path: docs/spec.md` or `prefix: X` on a task survives `sq repair`. Then `sq task 15 comment` rewrites the file without both keys. `sq check` reports no issue at either point, because both sides of the skew comparison drop them.

ADR-1007 refuses `path` and `prefix` as declared attribute names, but decision 7 says a hand-added (never declared) key is kept on every write, and the US4 table has a "never declared" column. Neither name has a row in it. An unknown `badges:` key survives (it is kept in the file and left out of the row), so these two are the only names whose removal goes unreported.

**Failure scenario.** An adopter adds `path: docs/runbook.md` to a guide, which is a natural key for a guide. The next comment on that guide erases the key without a message.

**Fix direction.** Keep these keys through load and write the way the `--json`-only names are kept: stored, carried, left out of the model field. Add `path` and `prefix` rows to the write-invariant table.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T15:38:23Z] Elias Python:
  - Fixed. Falsification: path and prefix are both kept as unknown attributes, left out of --json rows; re-excluding them turns 30 tests red.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — A declared role attribute named like a retired key is swept

<!-- sq:finding:F6:body -->
**Driven.** The loader accepts `[items.role.attributes] color = { kind = "str" }`, and `sq workflow types --json` lists it as settable. The `sq sync` and `sq repair` sweep removes `RETIRED_ROLE_KEYS | RoleDef.attribute_keys()` minus the stored set from every role's top-level attributes. With `color: red` set on `ROLE-1`, `sq repair` prints "stripped retired regions from 1 item file" and the key is gone. The same applies to `mission`, `responsibilities`, `agreements`, `can_spawn`, `full_name` and `skills`.

Before this change those names were nested under `extra`, apart from adopter keys. Now they share the namespace an adopter declares attributes in, so the closed, named sweep can remove a declared attribute that no command targeted.

**Failure scenario.** An adopter declares `skills` (a list of skills an agent is trained on) or `color` on roles and fills it in. The next `sq sync` erases it from every role file.

**Fix direction.** Refuse these names as role attributes in the loader, with the reason, or have the sweep skip a name the resolved spec declares on `role`. Add a row for it to the refusal table and the write-invariant table.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T15:38:25Z] Elias Python:
  - Fixed. Falsification: retired-key sweep spares keys the spec declares on role; ignoring declarations turns 7 tests red.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — An unchosen developer keeps a removed per-slug name

<!-- sq:finding:F7:body -->
**Driven.** `sq dev add --tech python` gives `Elias Python`, with `name_chosen: false`. Setting `.overrides/roles/python-dev.toml` `full_name = "Per python-dev"` and running `sq sync` renames it, as intended. Deleting that file and syncing again leaves `Per python-dev`. A bundled role under the same steps (`qa` to `Per qa` and back) returns to `Mara Tester`.

`dev_base_from_item` uses the stored title as the base, and the sync writes the per-slug name into that title, so once a per-slug name is applied the pool draw is lost. The acceptance says the pool draw is never re-rolled. It is not re-rolled, but it is overwritten, and an unchosen developer ends up keeping a configured name after its configuration is gone.

**Failure scenario.** An adopter tries a per-slug name for a developer, deletes the file, and the trial name stays, although `name_chosen` is false.

**Fix direction.** Store the pool draw apart from the resolved name, or recompute it from the role's stored sequence, so removing the per-slug file restores it. Add a removal column to the precedence table.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T15:38:27Z] Elias Python:
  - Fixed. Falsification: pool_name role attribute (pinned) restores unchosen developer names; ignoring it turns 1 test red.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — The flattening guesses on core-key and nested extra shapes

<!-- sq:finding:F8:body -->
**Driven** with `flatten_frontmatter` called directly. The pre-flight refuses only a non-mapping `extra`, a collision with a different top-level value, and a roster `extra.slug` that differs from the file name. These shapes go through without a problem being raised:

- `extra: {extra: {a: 1}}` lifts to a top-level `extra`. The output still carries `extra`, so a second pass changes the file again: the step is not idempotent for this shape.
- `extra: {assignee: qa, parent: FEAT-9}` with no top-level value is lifted into the core `assignee` and `parent`. A key that was inert under `extra` becomes the item's assignee and parent.
- On a non-roster item, `extra.slug: other` with file slug `t` becomes the top-level `slug: other`, with no problem raised, so the item's slug no longer matches its file name.
- A skill's `extra.path` is lifted to `path` after the stray top-level `path` is removed. The next load drops it (see the finding on `path`/`prefix`), and a second pass changes the file again.

None of these is a shape the released tool writes, but the step is meant to refuse what it cannot place rather than guess.

**Failure scenario.** A hand-edited 0.15 file with `extra.assignee` migrates into an item assigned to someone, with no report.

**Fix direction.** Add a pre-flight problem for an `extra` key that is a core key, `extra`, `path` or `prefix`, and for a non-roster `extra.slug` that differs from the file name. Add the rows to the step's table.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-16T15:38:29Z] Elias Python:
  - Fixed. Falsification: flattening refuses core-key/extra/path/prefix in extra and non-roster slug mismatch; check off turns 7 tests red.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — A differing skill description is dropped unlisted

<!-- sq:finding:F9:body -->
**Read and driven.** The 0.15 Claude Code backend read `extra.description or description or title`, so when the two descriptions differed, the agent host showed `extra.description`. The step drops `extra.description` whenever the top-level `description` is non-empty. The report gives only a count. Unlike an operator retitle, it does not list the files.

In this repository both skills that carry `extra.description` hold it byte-identical to the top-level value (checked on `SKILL-000508` and `SKILL-000974`), so the two dropped here were redundant. For an adopter whose copies differ, the selection text the host used changes after the run, and no line names the file.

**Failure scenario.** An adopter edited a skill's host text under `extra:`. After the run, the pointer carries the other text and nothing points them to the file.

**Fix direction.** When the dropped value differs from the kept one, list the file under the count, as for operator retitles. The MANUAL should state the rule.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-16T15:38:31Z] Elias Python:
  - Fixed. Falsification: report lists files where a dropped skill description differed; flag off turns 2 tests red.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Pin table spells attribute keys as literals

<!-- sq:finding:F10:body -->
**Read.**

- `PINNED_ROSTER_ATTRIBUTES` in `_workflow/_models.py` spells `"is_default"`, `"is_dev"`, `"model"`, `"name_chosen"`, `"tech"`, `"allowed_tools"` and `"when_to_use"` as literals, not `AttributeKey` constants. The guard in `tests/meta/test_attribute_reads_name_a_constant.py` matches only an `.attributes` receiver or `.attribute(...)`, so it cannot see this table, or a read through an alias (`a = item.attributes; a["tech"]`). The guard does fail on the shapes it lists, as the developer's falsification showed. If the pin table and `AttributeKey` drift apart, the loader pins a key that no reader uses.
- `AttributeKey` still carries `TITLE` and `DESCRIPTION`, which are core keys, and `FULL_NAME`, `MISSION`, `RESPONSIBILITIES`, `COLOR`, `CAN_SPAWN` and `AGREEMENTS`, which no item stores any more. This contradicts the module docstring, which says an attribute is any key that is not a core key.
- A test comment narrates history: "no stored title to compare any more" in `tests/integration/test_role_override_reaches_managed_files_before_a_healing_sync.py`.

**Failure scenario.** A later rename of `AttributeKey.MODEL` updates every reader, but the pin table goes on requiring the old name.

**Fix direction.** Key the pin table by `AttributeKey`. Move the catalog and retired names out of `AttributeKey`, or into a separate class. Rewrite the comment in the present tense.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-16T15:38:34Z] Elias Python:
  - Fixed. Falsification: pin table keyed by AttributeKey, catalog/retired names moved out, comment rewritten; no behavioural mutation (pyright/ruff enforce key names).
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T15:13:31Z] Paul Reviewer:
  - Reviewed TASK-1059 ST1-ST8 (commit 62871850). Verdict: ChangesRequested, with 2 high, 4 medium and 4 low findings, each driven on scratch squads.
  - High: F1, a CRLF role file is corrupted by the 0.16 step and other CRLF items keep a nested extra; F2, an unquoted YAML date in any attribute makes its item unwritable, and sq repair does not clear it.
  - Medium: F3, names that came from configuration are marked chosen; F4, after a refused run, 0.15.0 misreads the rebuilt index; F5, path and prefix keys are dropped on write; F6, the sweep removes a declared role attribute named like a retired key.
  - @python-dev please take F1 to F10. @manager F3 changes how existing roles are marked, so it may need the operator's call on the rule.
- [2026-10-16T15:15:20Z] Pierre Chat:
  - 2026-10-16, F3: at migration, a role's name counts as unchosen when it equals the name the configuration layers resolve at that moment (bundled catalog, then roles.toml, then the per-slug file); any other name was chosen by hand.
- [2026-10-16T15:38:36Z] Elias Python:
  - F1-F10 fixed in the working tree, uncommitted. Gates clean (pyright, ruff, sq check, targeted suites). @reviewer @manager ready for re-review.
- [2026-10-16T15:44:04Z] Paul Reviewer:
  - - 2026-10-16 re-review of the uncommitted fixes on top of 62871850. I re-ran every original reproduction against the dev tree, on fresh copies of the 0.15.0-built squads:
      - F1: the CRLF role file keeps one frontmatter block and its CRLF endings, with `name_chosen: true`. The CRLF guide is flattened (`tags` and `tech` lifted). The run exits 0.
      - F2: unquoted date, timestamp and int-key values no longer block a write after `sq repair`, and `sq check` is clean.
      - F3: per-slug and `roles.toml` names migrate as never named, and later edits to those files rename the role. The BUG-1049 repro migrated from 0.15.0 shows `Rita Catalog` after `sq sync`.
      - F4: a refused run leaves the whole tree byte-identical, and a 0.15.0 `sq sync` afterwards changes nothing.
      - F5: hand-added `path` and `prefix` keys survive a comment.
      - F6: a declared `color` survives `sq repair` and `sq sync`, and an undeclared `mission` is still swept.
      - F7: a pool developer returns to `Elias Python` when its per-slug file is removed.
      - F8 and F9: the edge shapes are now refused, and a differing skill description is listed.
      - F10: the pin table uses `AttributeKey`, and the test comment is gone.
      - Targeted `-n0` pytest run of the step, the write invariant, the meta guard, the retired-key sweep and the developer base: 309 passed. I did not run the full suite; the coordinator's run covers it.
    - (a) F3, the "any layer" reading is the better one. The literal reading (the name the layers resolve at migration) would mark a stored bundled name as chosen whenever `roles.toml` names the role differently. Every squad migrated with a `roles.toml` would then keep BUG-1049 permanently. Under "any layer", a name that matches a layer was configuration's name, and configuration supplies the default name of a role never named. The one case marked wrong is an operator who chose, by hand, a name equal to some layer's name. That name is still shown until the configuration changes, and the literal reading cannot tell this case apart either. So it is safe. @op-pierre, this reads your ruling as "equal to a name any layer gives the role"; please confirm.
    - (b) F7, `pool_name` is needed, not derivable. The draw is `pool[seq % len(pool)]`, with `seq` the number of developers at the time the role was added. After developers are removed, or the pool is overridden, that sequence cannot be recovered. Once a per-slug name is applied, the stored title no longer holds the draw either. It duplicates `title` only while the developer is unrenamed. One residue: a developer already renamed by a per-slug file before the migration gets no `pool_name`, so removing that file keeps the per-slug name. The draw is unrecoverable in that case, so this is acceptable.
    - Observation, not blocking: since F2, an unrelated write stores a YAML-native value in its JSON form. An unquoted `2026-10-20` becomes `'2026-10-20'`, and `{1: a}` becomes `{'1': a}`. For a date the value is equal, but an int key changes type. @architect, ADR-1007 decision 5 says a value is carried "verbatim", so it may want a dated note.
    - No finding of medium severity or worse is left. REV-1063 moves to InReview, and I recommend approval. @manager
- [2026-10-16T15:44:39Z] Catherine Manager:
  - Approved on the reviewer's recommendation: F1–F10 Fixed and re-verified against the original repros; full suite 10,977 passed, 0 failed.
- [2026-10-16T16:14:43Z] Pierre Chat:
  - 2026-10-16: confirmed the built F3 reading: at migration a role's name is unchosen when it equals the name of any configuration layer (catalog, roles.toml, per-slug file, developer pool).
<!-- sq:discussion:end -->

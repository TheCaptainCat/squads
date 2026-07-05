---
id: FEAT-283
sequence_id: 283
type: feature
title: Unpadded display IDs, decoupled from filename padding
status: Done
parent: EPIC-12
author: product-owner
refs:
- ADR-282:implements
- FEAT-27
subentities:
- local_id: US1
  title: IDs read unpadded on every human-facing surface (frontmatter, refs, prose,
    CLI, tables)
  status: Todo
- local_id: US2
  title: Files stay padded and lexicographically sorted on disk while the id is unpadded
  status: Todo
- local_id: US3
  title: 'An existing squad migrates cleanly: structural id/refs + bounded prose rewrite,
    code fences untouched'
  status: Todo
- local_id: US4
  title: 'CLI lookup stays width-tolerant: FEAT-283 and FEAT-000283 both resolve'
  status: Todo
- local_id: US5
  title: Managed artifacts and goldens regenerate to unpadded; managed-section diff
    verified clean
  status: Todo
created_at: '2026-07-02T09:36:33Z'
updated_at: '2026-07-04T23:23:53Z'
---
<!-- sq:body -->
## Problem

Every item ID is rendered with a hard-coded 6-digit zero pad (`FEAT-000283`, `TASK-000030`). That
width exists for **one** reason that matters: on-disk filenames sort lexicographically. Everywhere a
human reads an ID — frontmatter `id:`, refs, ID mentions in body prose, CLI output, tables — the
padding is pure noise. `FEAT-283` is the JIRA-style form people say and type; `FEAT-000283` is the
form the tool insists on echoing back. This decouples the two: display goes unpadded, the filename
width stays. Authoritative design: **ADR-282** (Proposed). Sibling of **FEAT-27**, which owns
the stored padding + `repad` migration this feature reinterprets.

## Scope — exactly two changes (no config knob)

1. **Every human-facing surface renders unpadded.** Frontmatter `id:`, refs, prose ID mentions, CLI
   output, and tables all read `FEAT-283`. Display padding becomes a fixed **0**: `Item.id_padding`
   is a constant `0` (not a stored or configurable field), and `_propagate_padding` stamps `0`
   squad-wide so `Item.id` → `format_item_id(prefix, seq, 0)` → `FEAT-283`.
2. **The existing index-stored `SquadsDB.padding` is reinterpreted as the *filename width only*.**
   It is consumed exclusively at the filename-building seam, never for display. **No new config
   surface, no second stored field, no `.squads.toml` change.** It stays a derived/cached value in
   `.squads.json` exactly as today: `sq repair` re-derives it from disk (`max(stored, max observed
   filename width)`); `sq migrate repad` widens it on counter overflow. Invariant #1 holds — the
   width is fully reconstructable from the `.md` files, so nothing irreproducible is stored.

## The filename-seam crux (the one load-bearing divergence)

Under the new model `item.id` is `FEAT-283` but the file must stay `FEAT-000283-slug.md`. Today the
filename is built by concatenating the computed `item.id` — the crux site is
`src/squads/_services/_items.py:137` (`_rename`):

```python
new_rel = self.paths.squad_relative(item.type, f"{item.id}-{new_slug}.md", spec=self.spec)
```

Every site that **locates or creates a file** by concatenating `item.id + slug` must instead format
the **padded** name explicitly from the sequence number:
`format_item_id(item.prefix, item.sequence_id, db.padding)` — the index-stored `padding` as the
filename width. Audit all such path-builders (rename/create, `item_file` resolution, any
retype/renumber path). This is a footgun for anyone assuming "filename stem == id": it needs a
**comment at each such call site** and an **invariant test** (assert the file exists at the padded
name while the frontmatter carries the unpadded id).

`format_item_id` already takes the width as a parameter (`_models/_item.py:26`), so this is not a new
formatting path — it is the *same* formatter called with two widths: `0` for display, stored
`padding` for filenames.

## CLI input stays lenient for free

Lookups already resolve via `ref_id_matches` (`_item.py:62`, matches on `(prefix, int sequence_id)`)
and the sequence-keyed index, so `sq show FEAT-283` and `sq show FEAT-000283` both resolve regardless
of stored width. **No input-parsing change** — only *output* narrows to unpadded. Keep a test that
both widths resolve.

## Migration — structural + prose, gated on a schema bump

`SCHEMA_VERSION` is `"0.5"` today; bump it (compare via `schema_tuple`) and add a `Migration` record
+ `_vN_to_vM.py` runner to `_migrations/_registry.py`. The root callback already hard-stops on a
schema mismatch until `sq migrate up` runs. The runner:

1. **Structural (deterministic):** rewrite each frontmatter `id:` and every ref to the unpadded form,
   driven by `sequence_id`.
2. **Prose (bounded):** rewrite padded ID mentions in body prose to unpadded — same class of edit as
   the renumber path's `rewrite_ids` (`_itemfile.py:45`, `\bOLD\b → NEW`). **Bound it to the exact
   old-form strings the migration already knows** (iterate the index's `{padded → unpadded}` map per
   item); never a blind "collapse any run of zeros" pattern, which could maul unrelated text. **Skip
   fenced code blocks / inline code** where an ID may be a literal example, matching how
   `retype`/renumber scope their mention rewrites.
3. **Filenames untouched** — already width-6, stay width-6. No renames → no git-rename churn, no path
   rewrite beyond `repair`.
4. `.squads.json` rebuilt by the trailing `repair`, re-deriving both widths from disk.

The `manual` runbook should note the prose rewrite is best-effort and worth an eyeball on
mention-heavy bodies.

## Golden churn (mechanical but broad)

Managed artifacts embed example / real item IDs: the `sq-<type>` skills, the `squads`/`greeting`
skills, the CLAUDE.md / AGENTS.md managed sections, and `sq workflow`. Roster/roadmap prose cites
real IDs (`FEAT-000027`, `EPIC-000012`). All of these shift to unpadded → **regenerate every golden
fixture** and run the **managed-section diff check** the way we do on item-type changes (see the
"verify .claude artifacts on item-type changes" discipline). Expect a sizeable but purely mechanical
golden diff in the implementing PR.

## Acceptance criteria

- `Item.id` renders unpadded (`FEAT-283`) in frontmatter `id:`, refs, and every CLI surface
  (show/list/tree/tables/JSON); `id_padding` is a fixed constant `0`, not stored or configurable.
- On disk, files remain padded (`FEAT-000283-slug.md`) and stay lexicographically sorted; the
  index-stored `padding` is understood as filename width and is consumed **only** at path-builder
  seams via `format_item_id(prefix, sequence_id, db.padding)`.
- An invariant test asserts: file exists at the padded name **while** its frontmatter `id:` is
  unpadded — for create *and* rename/retype paths. Each such call site carries a clarifying comment.
- `sq show`/lookup resolves both `FEAT-283` and `FEAT-000283` (input tolerance unchanged; a test
  pins both).
- No `.squads.toml` change; no new stored field. `sq repair` re-derives the filename width from disk;
  `sq migrate repad` still widens it; the capacity/overflow check keys off the same stored padding.
- Schema bumped from `0.5`; `sq migrate up` runs the structural (id/refs) + prose (bounded,
  code-fence-skipping) rewrite; filenames untouched; trailing `repair` rebuilds `.squads.json`.
  A migration test covers a mixed fixture (padded frontmatter/refs/prose + a code fence that must be
  left alone) and asserts it lands unpadded and idempotent.
- Golden fixtures regenerated; managed-section diff verified clean; `sq check` green;
  `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean.

## Out of scope / non-goals

- No user-configurable display width — display is fixed unpadded, full stop.
- No filename renames (widths unchanged); no `repad` retarget.
- No change to identity, the global counter, or ref resolution — `sequence_id` stays the identity.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 283 add-story "As a <role>, I want … so that …"`; track with `sq feature 283 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | IDs read unpadded on every human-facing surface (frontmatter, refs, prose, CLI, tables) |
| US2 | Todo |  | Files stay padded and lexicographically sorted on disk while the id is unpadded |
| US3 | Todo |  | An existing squad migrates cleanly: structural id/refs + bounded prose rewrite, code fences untouched |
| US4 | Todo |  | CLI lookup stays width-tolerant: FEAT-283 and FEAT-283 both resolve |
| US5 | Todo |  | Managed artifacts and goldens regenerate to unpadded; managed-section diff verified clean |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — IDs read unpadded on every human-facing surface (frontmatter, refs, prose, CLI, tables)

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a developer reading squads output, I want every human-facing surface to show IDs unpadded (e.g. `FEAT-283`) so that I see the short form people actually type and say, instead of the padded on-disk artifact.

**Acceptance criteria**

- Frontmatter `id:` renders unpadded for every item type.
- Every ref (`refs:` entries and computed backrefs) renders unpadded wherever displayed.
- ID mentions in body prose render unpadded.
- CLI output renders unpadded: `show`, `list`, `tree`, tables, and JSON output.
- `Item.id_padding` is a fixed constant `0` — not a stored field and not configurable via `.squads.toml` or any flag.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Files stay padded and lexicographically sorted on disk while the id is unpadded

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a maintainer of the on-disk squad folder, I want files to keep their padded, lexicographically-sortable filenames while the id itself displays unpadded, so that directory listings stay sorted and nothing forces a mass rename.

**Acceptance criteria**

- On disk, item files keep the padded name (e.g. `FEAT-000283-slug.md`) and continue to sort lexicographically by sequence number.
- The index-stored padding value is reinterpreted as filename width only — never consumed for display.
- Every path-builder that locates or creates a file by combining prefix, sequence number, and slug (create, rename, retype, renumber) formats the padded name explicitly via the sequence-number formatter with the stored width, rather than concatenating the (now-unpadded) displayed id.
- Each such call site carries a comment flagging that the filename stem is not the same as the displayed id.
- An invariant test asserts, for both the create path and the rename/retype path, that the file exists at the padded name while its frontmatter `id:` is unpadded.
- No new `.squads.toml` field is introduced; `sq repair` still re-derives the filename width from disk and `sq migrate repad` still widens it on counter overflow.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — An existing squad migrates cleanly: structural id/refs + bounded prose rewrite, code fences untouched

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As an operator upgrading an existing squad, I want a single migration run to flip stored ids, refs, and body-prose mentions to the unpadded form without touching filenames or mangling unrelated text, so that my squad works correctly the moment the schema bumps.

**Acceptance criteria**

- The schema version is bumped past its current value; a new migration record and runner are registered in the migration registry; the root CLI hard-stops on the mismatch until the migration runs.
- The runner rewrites every item's frontmatter `id:` and every ref to unpadded, driven by each item's stored sequence number.
- The runner rewrites padded ID mentions in body prose to unpadded, but only for the exact old-form strings the migration already knows from its own padded-to-unpadded map — never a blind zero-collapsing pattern that could touch unrelated text.
- Fenced code blocks and inline code are skipped by the prose rewrite, matching how the existing retype/renumber mention rewrites scope themselves.
- Filenames are left untouched — no renames, no git-rename churn.
- The migration's trailing repair step rebuilds the index, re-deriving both the display constant and the filename width from disk.
- A migration test covers a mixed fixture (padded frontmatter, padded refs, padded prose mentions, and a code fence containing a padded id) and asserts the result is fully unpadded outside the fence, and that a second run is a no-op (idempotent).
- The manual runbook entry flags the prose rewrite as best-effort and worth an eyeball on mention-heavy bodies.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — CLI lookup stays width-tolerant: FEAT-283 and FEAT-283 both resolve

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As someone typing an id at the CLI, I want lookup to accept either the padded or the unpadded form so that I never have to remember which width the tool expects.

**Acceptance criteria**

- Lookup resolves an id typed in either the short unpadded form (e.g. `FEAT-283`) or the fully padded form (e.g. `FEAT-000283`), for every item type and command that accepts an id.
- Resolution continues to key off prefix and sequence number via the existing matcher and the sequence-keyed index — no change to input parsing.
- Only output narrows to unpadded; input tolerance for either width is unchanged.
- A test pins that both widths resolve to the same item.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Managed artifacts and goldens regenerate to unpadded; managed-section diff verified clean

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
As the team maintaining squads' own bundled content, I want every managed skill, managed CLAUDE.md/AGENTS.md section, and golden fixture that embeds an id to regenerate in unpadded form, so that shipped artifacts and this project's own working tree don't lag the new display rule.

**Acceptance criteria**

- All per-type managed skills, the core workflow skills, and the workflow cheatsheet output regenerate with unpadded example ids.
- Managed CLAUDE.md/AGENTS.md sections regenerate unpadded, and the managed-section diff check comes back clean.
- Roster and roadmap prose citing real ids is updated to the unpadded form.
- All golden fixtures affected by the id format are regenerated and reviewed as one mechanical diff.
- `sq check` is green and the strict typing/lint/format gates are clean.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-04T23:00:41Z] Mara Tester:
  - QA sign-off — acceptance verified end-to-end by behavior in throwaway squads (never touched this live repo).
  - US1 (unpadded everywhere) — PASS. In a fresh squad: 'sq create feature' printed 'created FEAT-9 -> .../FEAT-000009-....md' (unpadded in the message, padded on disk in the same breath). Frontmatter id: FEAT-9; parent: FEAT-9 on a child task; refs: - BUG-11:fixes after 'sq task 10 ref add BUG-11'. 'sq task 10 show --full', 'sq bug 11 show --full', 'sq list', 'sq tree FEAT-9', and 'sq task 10 show --json' all render every id/parent/ref unpadded (confirmed the JSON payload's id/parent/refs fields too).
  - US2 (padded filenames, unpadded id) — PASS. 'sq task 10 update --title ...' renamed the file to a new padded stem (TASK-000010-implement-paginated-widget-list-endpoint.md) while frontmatter stayed id: TASK-10. 'sq task 10 retype bug' relocated it to bugs/BUG-000010-....md (padded, 6-digit) with frontmatter id: BUG-10, parent: FEAT-9, refs: - BUG-11:fixes all unpadded. Directory listing (BUG-000010 before BUG-000011) confirms lexicographic sort intact.
  - US3 (migration) — PASS, most load-bearing check. Copied tests/fixtures/corpus/v0_5 into a throwaway squad, hand-added a prose mention ('See TASK-000003 ... BUG-000004'), a fenced code block ('sq task show TASK-000003'), and an inline code span ('TASK-000003') to a body. Pre-migration: any normal command ('sq list') hard-stopped with 'this squad is at schema v0.5; squads 0.6.0 expects v0.7. Run sq migrate up...'. Ran 'sq migrate up': frontmatter id/parent/refs (FEAT-2, TASK-3, BUG-4, ADR-5, REV-6) all unpadded; the prose sentence became 'See TASK-3 ... BUG-4 ...'; the fenced code block and the inline code span both stayed byte-identical as TASK-000003; all 8 filenames unchanged (still 6-digit padded). 'sq check' came back clean, 'sq show TASK-3' and 'sq show TASK-000003' both resolved post-migration. Ran 'sq migrate up' a second time: 'already at schema v0.7; nothing to migrate' and md5sums of every item file were unchanged (idempotent). 'sq migrate chlog v0.5.0..v0.7.0' surfaces the expected manual note flagging the prose rewrite as best-effort.
  - US4 (lookup tolerance) — PASS. Both 'sq show BUG-000011' and 'sq show BUG-11' return the identical item; '--parent FEAT-000009' on create resolved and stored unpadded (parent: FEAT-9); 'sq bug 13 ref add BUG-000011' resolved and stored 'refs: - BUG-11:duplicates'.
  - US5 (managed artifacts unpadded) — PASS. Read-only checks on this dogfood repo: no 6-digit padded FEAT-0.../TASK-0.../ADR-0.../BUG-0.../EPIC-0.../REV-0... pattern remains under squads/agents/skills/ or CLAUDE.md; SKILL-000200-squads.md and 'sq workflow' output use unpadded examples (FEAT-2, TASK-3-style). A freshly 'sq init --backend claude_code' throwaway squad's generated SKILL-000017-squads.md likewise has zero padded examples and only unpadded ones.
  - Everything above was exercised in /tmp scratch squads via 'uv run --project /home/pchat/projects/squads sq ...'; the dogfood repo itself was only read (show/grep), never written. Recommending FEAT-283 move toward Done once TASK-291's review lands (task is currently InReview).
- [2026-07-04T23:23:53Z] Catherine Manager:
  - Deferral note for the FEAT-13 stability contract: this feature changes a documented public surface — item IDs now DISPLAY unpadded (FEAT-283, TASK-30) everywhere (frontmatter id:, refs, prose, CLI, --json) while on-disk filenames stay zero-padded. The FEAT-13 contract doc, which froze the ID-format surface, now lags reality and must be refreshed before 1.0 to state: display/canonical form is unpadded (JIRA-style), filename width is a separate index-derived value, and input remains width-tolerant (FEAT-283 and FEAT-000283 both resolve). Authoritative design: ADR-282 (Accepted).
<!-- sq:discussion:end -->

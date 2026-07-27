---
id: TASK-664
sequence_id: 664
type: task
title: Atomic markdown writes and markdown-ahead ordering in the write path
status: InReview
author: tech-lead
refs:
- ADR-663:implements
- BUG-656:fixes
- BUG-668:fixes
- BUG-670:fixes
description: One atomic temp+fsync+replace primitive for every squad-data .md write,
  and the markdown-ahead ordering rule enforced at every mutation core.
subentities:
- local_id: ST1
  title: Atomic replace primitive for squad-data writes
  status: Todo
- local_id: ST2
  title: Route every squad-data write through the primitive
  status: Todo
- local_id: ST3
  title: Board notices and memory entries onto the primitive
  status: Todo
- local_id: ST4
  title: Ordering audit across mutation cores; fix the violating sites
  status: Todo
- local_id: ST5
  title: Repair-convergence tests and the changelog line
  status: Todo
- local_id: ST6
  title: Route the sync filesystem calls on the mutation path through _aio
  status: Todo
created_at: '2026-07-27T14:22:46Z'
updated_at: '2026-07-27T15:42:42Z'
---
<!-- sq:body -->
Implements the write side of ADR-663: §1 (skew direction — markdown ahead or equal, index
never ahead) and §2 (per-file atomicity on the markdown side). Read ADR-663 in full first;
where a bug body disagrees with it the ADR wins — BUG-656's own "rename the `.md` into place
only after the index commit" option is rejected there as the *lossy* direction.

## Problem

Two halves of one seam.

**Not atomic.** Every squad-data write goes through `_aio.write_text` → `Path.write_text`, which
truncates in place: no temp file, no rename, no fsync anywhere on the markdown side. A process
killed inside that call leaves a truncated or empty file on disk — it destroys the source of
truth, and `sq repair` cannot heal it, because repair rebuilds *from* the markdown.

Worse than unhealable: **repair silently drops the item.** With the cut inside the frontmatter
block, the file has no parseable `id`, so repair sees "no markdown file found", reports a warn,
and rebuilds the index without that item. Afterwards `sq <type> <n> show` answers "no item with
number N", `sq list -a` no longer lists it, and the corrupted file stays on disk as a permanent
orphan no `sq` command can recover. That is silent data loss, and it is the sharpest thing this
task prevents.

The same partial state is visible to a concurrent reader with no crash at all — the check scan
reading a half-written file takes one of two shapes, depending on where the cut lands:

- **inside the frontmatter block**, before its closing `---`: no closer is found, the
  frontmatter parses as empty, and the file is reported `file has no 'id' in frontmatter` (an
  error-level, single-source issue).
- **inside the body**, after the frontmatter closed intact: the item still has a valid `id`, but
  any sq marker straddling the cut is left half-written and reported as an unclosed marker (also
  error-level and single-source).

A bare `yaml.YAMLError` escaping the frontmatter split is **not** one of the shapes: the
frontmatter dict is fully serialized in memory before any byte reaches disk, and the split
requires a literal closing `---` line, so a truncated write can only stop before that line
exists (first shape) or land at/after it, where the whole dict is already present and parses.
Do not go looking for it.

**Order stated once.** The rule "markdown write inside the transaction body, index
`os.replace` last" is written down in a local comment at exactly one call site
(`remove_work_item`) out of ~a dozen mutation cores, and one site contradicts it:
`remove_item(purge=True)` in `_services/_items.py` drops the index entry inside the
transaction and unlinks the `.md` *after* it closes. Process death in that window leaves the
index without the entry and the file on disk — the direction in which `sq repair` re-indexes
the file and resurrects a removed item.

## Failure model

In model: process death — SIGKILL/SIGTERM, harness timeout, background-stop, OOM kill,
container stop, and (same event class) any exception escaping a transaction body. Writes the
kernel already accepted survive, so program order is enough to order durability events.

Out of model: host crash and power loss. `sq repair` stays the recovery path there, and no
promise is made about which side is ahead.

## The rule this task makes true everywhere

Within a transaction, every write to squad data on the markdown side — create, frontmatter
update, marker-section edit, rename/move, unlink — happens inside the transaction body, before
it returns. The index `os.replace` is the transaction's last write to squad data. Nothing that
mutates an item `.md` may run after the commit.

Exempt, and to stay exempt:

- **Regenerable artifacts** — backend pointer files, the managed regions in
  `CLAUDE.md`/`AGENTS.md`, `.claude/` output, the squad `.gitignore`, override stamps. They hold
  no state, `sq sync` reproduces them, and they may be written after the commit (as `update`'s
  pointer regen already does). They also stay on the plain write — routing them through the
  atomic primitive is churn for no invariant.
- **The reflog** — append-only observability, deliberately appended after `os.replace` under a
  never-raise contract. Do not move it.

`.squads.toml` is **not** exempt: it is squad data and goes through the atomic primitive. `sq
sync` only re-stamps its version field; nothing reconstructs the active backends, the default
role, the schema version the CLI gates every invocation on, or the squad-dir pointer that path
resolution walks up to find. Truncating it does not cost a `sq sync` — it makes the squad
unresolvable. It *is* outside §1's ordering rule, though: nothing in the index mirrors it, so
there is no skew to direct.

## Constraints

- One primitive, not two shapes: temp file in the **same directory** as the target, write,
  flush, fsync, `os.replace`, all in a single thread hop with no `await` between the fsync and
  the rename.
- Do **not** touch `src/squads/_index/_store.py`. Its `_atomic_write` already has the right
  shape and is being changed concurrently elsewhere; folding it onto the shared primitive is a
  separate step.
- Do **not** defer renames to the end of a transaction and do **not** reorder any markdown
  write against the index commit. If a bulk import measures a real regression from the fsync,
  the only sanctioned relief is skipping the fsync on the markdown side.
- A transaction writing N markdown files is still not atomic across those N files, and that is
  fine: each is durable before the index commits, so the skew stays one-sided for N exactly as
  for one. Do not introduce a journal or a two-phase commit — both are rejected in the ADR.
- Sync filesystem calls on the async mutation path (`Path.exists` / `Path.rename` /
  `Path.unlink` called directly in `_services/_items.py`) go through the `_aio` helpers the
  rest of the layer uses.
- Migration runners (`src/squads/_migrations/`) are frozen, point-in-time code that is never
  re-migrated. Leave them on their existing writes.
- Keep the temp-name shape collision-safe (pid + thread id, as the index writer does) so
  concurrent writers never share a temp path. `*.tmp` is already gitignored in a squad dir.
- Full gate before handoff: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .`, and the suite. `--all-extras` is required or
  pyright reports hundreds of false import errors under `_tui/`.

## Acceptance

The strongest one first, because it is the loss this task exists to stop:

- **An interrupted write can no longer cost an item.** A kill anywhere inside a squad-data write
  leaves the file complete-or-previous, so `sq repair` never again drops the item from the index:
  it stays reachable by `show`, stays in `sq list -a`, and no corrupted orphan file is left
  behind. Prove it against the same interruption pattern that produces the loss today (a
  fractional-prefix write followed by process death), not only against a clean unit test.

Then:

- No squad-data write in `src/squads/` reaches `Path.write_text` / `_aio.write_text` any more —
  item files, board notices, memory entries, `.squads.toml`. The item-file layer exposes only the
  atomic primitive, so a future mutation site cannot bypass it by accident.
- `remove_item(purge=True)` unlinks inside the transaction body.
- Every mutation core is enumerated and checked against the ordering rule, with the
  regenerable-artifact exemptions named where they occur.
- No reader can observe a partially written file: neither the "no `id` in frontmatter" shape nor
  the half-written-marker shape is reachable from an in-flight write.
- Interrupting any mutation leaves markdown ahead of (or equal to) the index, never behind, and
  `sq repair` converges on the file's state.
- `uv run sq check` clean; the suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 664 add-subtask "<title>"`; track with `sq task 664 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Atomic replace primitive for squad-data writes |  |
| ST2 | Todo |  | Route every squad-data write through the primitive |  |
| ST3 | Todo |  | Board notices and memory entries onto the primitive |  |
| ST4 | Todo |  | Ordering audit across mutation cores; fix the violating sites |  |
| ST5 | Todo |  | Repair-convergence tests and the changelog line |  |
| ST6 | Todo |  | Route the sync filesystem calls on the mutation path through _aio |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Atomic replace primitive for squad-data writes

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add one async atomic-write helper for squad-data text. `_aio.py` is the only place awaitables
touch the filesystem below the CLI edge, so it is the natural home; a small dedicated module is
acceptable if `_aio` is to stay a thin wrapper set.

Shape, matching what the index writer already does: build a temp path in the **same directory**
as the target (a cross-directory rename is not atomic), open it for writing, write the text,
`flush()`, `os.fsync(fh.fileno())`, then `os.replace` onto the target — all inside one sync
closure handed to `_aio.to_thread`, so no coroutine can interleave between the durability
barrier and the rename. The temp name carries pid + thread id so concurrent writers never
collide on it.

Do not make the primitive implicitly create parent directories: today's `write_new` does its own
`mkdir` and that split should stay, so the primitive has exactly one job.

The docstring states the contract plainly: after it returns, the target holds either the
complete new bytes or the complete previous bytes — never a prefix of either.

Acceptance:
- Writing over an existing file yields exactly the new content.
- No temp file survives a successful write.
- When the write raises partway (patch the writer to fail after the temp write, before the
  replace), the target still holds its previous bytes exactly.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Route every squad-data write through the primitive

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Convert every write of an item `.md` onto the atomic primitive:

- `_itemfile.py` — `write_new`, `update_frontmatter`, `rewrite_ids`.
- `_services/_base.py` — the shared section-edit core.
- `_services/_subentities.py` — the block-file writer and the sub-entity remove path.
- `_services/_rename.py` — the frontmatter/comment writers and the rollback restore.
- `_services/_retype.py` — the type-change writer, the container ensure, the retype comment.
- `_services/_maintenance.py` — the renumber apply path's frontmatter resync, and the
  skill-seeding convention-named file write.

`.squads.toml` comes with them — it is squad data, not a regenerable artifact. Its writers are
the config writes in `_services/_service.py` (init and adopt) and the two stamp helpers in
`_services/_maintenance.py` (`_stamp_version`, `_stamp_schema`). It is outside the ordering rule
(nothing in the index mirrors it), so this is purely about atomicity: a truncated `.squads.toml`
does not cost a `sq sync`, it makes the squad unresolvable — path resolution walks up to find it,
and the CLI gates every invocation on the `schema_version` inside it.

Leave the regenerable-artifact writers alone, on the plain write: both backends, the
managed-region writer, the squad `.gitignore`, the override stamps. Leave the migration runners
under `_migrations/` alone too — frozen, never re-migrated code.

Prefer routing the service call sites *through the item-file layer* rather than importing the
primitive into each service module, so "the item-file layer exposes only the atomic primitive"
is structurally true rather than a convention someone has to remember. Several services build
the whole new file text themselves and then write it; that is exactly the shape the item-file
layer should expose as one function.

Acceptance:
- No `_aio.write_text` call remains on any path that resolves to an item `.md` or to
  `.squads.toml`.
- A truncated `.squads.toml` is no longer reachable from an interrupted write; the squad still
  resolves and the schema gate still reads a complete file.
- Every converted command's existing tests still pass unchanged.
- A test asserts the item-file layer's writers go through the primitive, so a new mutation site
  cannot silently reintroduce a truncating write.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Board notices and memory entries onto the primitive

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
ADR-663 §2 names item `.md` files, board notices, and memory entries as squad **data**.
`_board/_store.py` and `_memory/_store.py` both write their `.md` files with the plain helper;
move both onto the atomic primitive.

Neither store touches `.squads.json`, so there is no ordering question here — only atomicity. A
killed process must not leave a truncated notice or memory entry: both are hand-authored content
with no regeneration path, so a truncated one is lost content, not a `sq sync` away.

Acceptance:
- Posting a board notice and adding a memory entry both go through the primitive.
- The existing board and memory tests stay green.
- One test per store: when the write raises partway, the file is complete-or-untouched.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Ordering audit across mutation cores; fix the violating sites

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Walk every `store.transaction()` site and every mutation core reached from one (~26 sites across
`_services/`, plus the two in the migration runners), and check each against the ordering rule.
For each site, classify every write it performs: squad data (must complete inside the body) or
regenerable artifact (may follow the commit). Where a site is already correct, leave the code
alone — this is an audit, not a refactor pass.

Known work:

- `remove_item(purge=True)` in `_services/_items.py`: move the unlink inside the transaction
  body. It currently drops the index entry inside the transaction and unlinks after it closes,
  which is the lossy direction — a crash there leaves the index without the entry and the file on
  disk, so `sq repair` re-indexes the file and resurrects a removed item.
- The two skill-seeding paths in `_services/_maintenance.py` unlink the legacy slug-named body
  file *after* the transaction commits. Decide this one explicitly: that file is a pre-stamp body
  `sq sync` reproduces and the check scan skips slug-named skill files, so it is arguably an exempt
  regenerable artifact — but the item's own convention-named file is already written inside the
  transaction, so moving the unlink inside costs nothing. Move it unless that breaks the
  idempotent-skip logic; if it cannot move, record the exemption and its reason at the call site.
- Confirm `IndexStore.load()` already raises the counter in memory when it trails the max sequence
  on disk, so a lost counter bump cannot reissue a sequence number even before `repair` runs. It
  does today — cover it with a test rather than a change.

Whether those unlinks are issued synchronously is a separate concern, handled by the sibling
subtask on the `_aio` helpers.

`remove_item`'s default of de-indexing while leaving the `.md` on disk is deliberately out of
scope: it produces an on-disk-but-not-indexed file by design, and whether that should change is a
separate question.

Acceptance:
- Every enumerated site either satisfies the rule or is a named exemption with a reason.
- The audit's conclusion is recorded as a comment on this ticket — not as a file in the tree.
- `uv run sq check` clean.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Repair-convergence tests and the changelog line

<!-- sq:subtask:ST5:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
The crash window is reachable without killing a process: raise from inside a transaction body
*after* the markdown write, then assert the index is unchanged, the file is ahead, and `repair`
converges on the file's state. Cover each direction of change:

- **create** — file exists, not indexed → repair indexes it, and the counter high-water mark
  keeps the sequence number from being reissued.
- **update** — file has the new value, index the old → repair adopts the file's value.
- **remove** — file gone, index still has the entry → repair drops the orphan and reports it
  missing.
- **retype / rename** — file at the new path and id, index at the old → repair re-indexes from
  the new path.

Also cover the truncation guarantee end to end, and make the sharpest case the headline test: a
write interrupted partway leaves the file complete-or-previous, so the item survives. Today, a cut
inside the frontmatter block costs the item outright — repair finds no parseable `id`, reports "no
markdown file found", and rebuilds the index without it, after which `show` answers "no item with
number N", `sq list -a` omits it, and the corrupted file remains as an unrecoverable orphan. Pin
that it cannot happen: interrupt the write, run `repair`, and assert the item is still indexed,
still resolvable by `show`, and still listed.

Cover the second shape too — a cut inside the body, after the frontmatter closed intact, which
today leaves a half-written sq marker and an unclosed-marker error. Do **not** write a test for a
`yaml.YAMLError` escaping the frontmatter split: it is structurally unreachable from a single
truncated write, since the frontmatter dict is fully serialized before any byte is written.

A faithful interruption test writes a fractional prefix of the intended text and then kills the
process, rather than asserting against a hand-built "what the outcome would look like" file — the
mutation has to go through the real code path for the test to mean anything.

Name tests by the behaviour they pin, never by a ticket id — repo rule, and `tests/meta`
enforces it. If a new module-level constant is introduced anywhere in this task, run
`tests/meta` too: a module-level dict or list trips its mutable-state guard and needs an
allowlist entry rather than a restructure.

Add the adopter-facing CHANGELOG line under the unreleased section: an interrupted mutation now
always leaves the repairable skew — markdown ahead of the index — instead of, in the worst case,
a truncated item file. Adopter-facing wording only: no ticket ids, no repo-process detail.

Acceptance:
- The four repair-convergence tests exist and pass.
- Full suite green under `uv run --all-extras`; run it once, redirect to a file, and read the
  file rather than re-running to reslice output.
- CHANGELOG updated in the unreleased section.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Route the sync filesystem calls on the mutation path through _aio

<!-- sq:subtask:ST6:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST6:head:end -->

<!-- sq:subtask:ST6:body -->
Three filesystem calls on the async mutation path in `_services/_items.py` are made synchronously,
bypassing the `_aio` helpers the rest of the layer uses — they block the event loop and sit outside
the one seam that is supposed to own filesystem access below the CLI edge:

- `_rename`'s `old_path.exists()` and `old_path.rename(new_path)`;
- `remove_item(purge=True)`'s `Path.unlink(missing_ok=True)`;
- `remove_work_item`'s `Path.unlink(missing_ok=True)`.

Route all of them through `_aio.path_exists` / `_aio.path_rename` / `_aio.path_unlink`. `_rename`
is currently a sync method, so making it await means its callers (`_update_model`, and the
type-change path that shares the slug/path logic) change shape — keep the pure model half pure and
put the filesystem half where the other awaited writes already live, rather than making the whole
model layer async.

Mechanical, but separable from the ordering audit: the audit decides *when* a write happens, this
decides *how* it is issued. The unlink placement itself belongs to the audit; do not move it here.

Acceptance:
- No direct `Path.exists` / `Path.rename` / `Path.unlink` call remains on the async mutation path
  in `_services/`.
- The pure, no-I/O halves of the status and metadata cores stay pure and stay sync.
- Existing rename / remove / purge tests pass unchanged.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T14:27:06Z] Olivia Lead:
  - Open question for @architect before ST2 lands: the body lists `.squads.toml` with the regenerable artifacts, but ADR-663 §2 never classifies it. `sq sync` only re-stamps its version field — active backends and spec-override settings are adopter state that nothing reconstructs. If Robert agrees, move `.squads.toml` onto the atomic primitive and out of the exempt list; `.gitignore` and the override stamps stay exempt either way.
- [2026-07-27T14:46:36Z] Olivia Lead:
  - Open question above is resolved — @architect ruled against the exemption and ADR-663 §2 now names `.squads.toml` as squad data. Body and ST2 updated: it goes through the atomic primitive (writers: `_services/_service.py` init/adopt config writes, `_stamp_version`/`_stamp_schema` in `_services/_maintenance.py`), and stays outside §1's ordering rule since nothing in the index mirrors it. `.gitignore` and the override stamps remain exempt.
  - Acceptance strengthened off BUG-668: the headline criterion is now that an interrupted write cannot cost an item — today a cut inside the frontmatter block makes `sq repair` drop it from the index (unreachable by `show`, absent from `sq list -a`, corrupted orphan left on disk). Also corrected: the bare `yaml.YAMLError` the ADR posited is structurally unreachable; the two real shapes are the missing-`id` error and a half-written marker.
- [2026-07-27T14:52:28Z] Catherine Manager:
  - Dispatched to Elias Python. Scope: the atomic write primitive + routing every squad-data writer onto it, including .squads.toml per ADR-663 §2. Running solo in the main tree; TASK-666 follows.
- [2026-07-27T15:40:27Z] Catherine Manager:
  - Audit note: two migration runners (_v0_4_to_v0_5.py ~246, _v0_8_to_v0_10.py ~186) share the fixed skill-seeding shape — db.add inside the transaction, legacy-slug unlink after it closes. Left unfixed: runner modules are frozen and never re-migrated, and sq migrate up ends in repair + stamp, which reconciles the surviving state. Recorded so the exception is deliberate and findable, not an oversight.
<!-- sq:discussion:end -->

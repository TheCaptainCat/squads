---
id: REV-671
sequence_id: 671
type: review
title: Atomic write primitive and write-path ordering rule
status: ChangesRequested
author: reviewer
refs:
- TASK-664
- TASK-665
- TASK-666
subentities:
- local_id: F1
  title: Stamped skill item files still written non-atomically by sync
  status: Verified
  severity: high
- local_id: F2
  title: Interruption tests pass with the primitive sabotaged
  status: Verified
  severity: medium
- local_id: F3
  title: Whole-file rewrites of partly hand-authored files stay non-atomic
  status: Verified
  severity: medium
- local_id: F4
  title: Markdown-ahead skew is reverted by the next mutation
  status: Open
  severity: medium
- local_id: F5
  title: Migration-runner exemption's recorded reason covers only ordering
  status: Verified
  severity: low
- local_id: F6
  title: Post-commit role-file writes in link-role carry no exemption note
  status: Verified
  severity: low
- local_id: F7
  title: Temp files leak on the error path; config temp escapes gitignore
  status: Verified
  severity: low
- local_id: F8
  title: Dry-run filesystem fix landed without a regression test
  status: Verified
  severity: low
- local_id: F9
  title: No changelog entry for the durability change
  status: Open
  severity: low
- local_id: F10
  title: Confirm round drops a durable drift when the index path is stale
  status: Open
  severity: high
- local_id: F11
  title: Interruption tests hook os.fsync, which the ADR may remove
  status: Open
  severity: low
- local_id: F12
  title: Root gitignore pattern never reaches an existing squad
  status: Open
  severity: low
- local_id: F13
  title: Nested different-store transaction silently drops the outer log
  status: Open
  severity: low
created_at: '2026-07-27T16:00:06Z'
updated_at: '2026-07-27T20:57:11Z'
---
<!-- sq:body -->
Independent review of the atomic write primitive and the write-path ordering rule as committed in
`68a44ed..fc9be74` (three commits; the middle one is a board record only). Read as committed via
`git show`, not from the working tree.

## What was verified, and how

- The primitive (`src/squads/_aio.py::atomic_write_text`) read against its stated contract, with its
  failure modes reasoned through: temp naming under concurrency, the error path, and parent-directory
  durability.
- Write coverage grepped across `src/squads/` independently of the ticket's claim — every
  `write_text` / `open(…, "w")` / `write_bytes` / `shutil` call site — then confirmed dynamically by
  wrapping both `_aio` writers and recording every path a single `sq sync` writes.
- All 25 live-code `store.transaction()` sites (plus the two in migration runners) enumerated, and
  the code that runs after each block's exit extracted mechanically, to look for post-commit
  squad-data writes rather than trusting the audit's conclusion.
- The added tests re-run against a deliberately sabotaged primitive (temp+fsync+replace replaced by a
  bare truncate-in-place) to see which ones actually fail.
- Gates re-run on the committed tree in a scratch worktree: `pyright`, `ruff check`, `ruff format`
  all clean; targeted regression runs over the import / retype / remove / sub-entity / board /
  memory / rename suites green.

## The primitive delivers atomicity

The write, flush, fsync and replace all live in one sync closure handed to a single `to_thread`, so
the "no `await` between fsync and replace" claim is literally true. The pid+thread-id temp name
cannot collide: two writers of the same target either land on different worker threads (different
idents) or on the same thread, where the pool serialises them. Skipping the parent-directory fsync is
correct rather than an oversight — it only matters for host crash and power loss, which the decision
puts out of model, and even there the data is fsynced before the rename, so the worst surviving state
is the previous complete content. The one real hole is on the error path (temp-leak finding).

## Coverage has one genuine gap

Within `_services/` the claim holds exactly: only the two `.gitignore` writes remain on the plain
helper, and both are correctly exempt. Outside it, the Claude Code backend still writes stamped
skill item files — real indexed items, not `.claude/` output — through the truncating helper on
every sync. That is this work's own loss shape, still reachable.

## Ordering is enforced, with one silent site

Both fixed sites are correct. The mechanical sweep of what runs after each transaction found only
backend pointer regen, `.claude/` artifact removal, and `repair` — all exempt — plus
`_resync_role_skills`, which writes a role item's `.md` after the commit. Its skew direction is safe,
so it satisfies the rule's substance, but it carries no note saying so.

## The tests prove less than they claim

The repair-convergence set is the strongest work here: it faults the index commit, so the skew and
repair's convergence are real observations, and the purge case pins the ordering fix directly. The
two interruption tests, including the headline one, both stay green when the primitive is sabotaged
into a truncate-in-place write, so nothing pins atomicity for item `.md` files — the artifact this
work exists to protect — while board notices, memory entries and `.squads.toml` all have that proof.

## The deliberate exceptions are the right calls

The migration runners, `repad`/`renumber` and `_refresh_role_skills_extra` are all correctly left
alone. Only the recorded justification for the migration runners is wrong in its atomicity half.

## What I could not check

- No real `fork` + `SIGKILL` interruption was run: QA already did that on the pre-fix code, and this
  review's fault injection is equivalent for the shapes at issue. A post-fix kill test would be the
  one thing that closes the atomicity question end to end.
- Concurrency was reasoned about, not exercised: no test (and no check here) runs two processes
  writing the same target at once.
- The full suite was not run — that belongs to the operator; targeted suites over the touched paths
  were run instead.

---

# Second pass — the fixes, plus the read side and the transaction context

Re-reviewed at `bb39384`, covering `ebaf966` (the five fixes), `d6cd884` (the cross-source confirm
round) and `13888b8` (the task-local transaction context). Method was the same as the first pass and
deliberately adversarial: every claimed fix was re-broken in a scratch worktree to see whether the
tests that are supposed to hold it actually fail.

## Sabotage results

| what was broken | tests that went red |
|---|---|
| primitive → bare truncate-in-place | 4 (both interruption tests) |
| primitive → in-place write that still flushes and fsyncs | 4 |
| primitive → fsync dropped, temp+replace kept (atomicity intact) | 4 — see the finding on the hook |
| pre-fix impure rename restored in `_rename` | 1, on the right assertion |
| section-edit routed back to the plain writer | 1 |
| confirm round returns nothing | 8, including the CLI exit-3 case |
| stale name in the `index_reconciled` filter | 2 race tests |
| pre-change shared-attribute transaction context | 3, one showing 1 of 8 reflog lines surviving |

Everything the first pass asked for is delivered and provably held by a test. The atomic write path
is in good shape.

## The read side

The confirm round's design is sound and its "pays nothing when clean" contract is real (one index
load, no re-reads). Durable inconsistencies survive concurrent activity on *other* items — I wrote
three adversarial race tests to check that specifically, and all three report correctly.

It has one hole, and it is the one this design was always going to risk: a candidate is re-observed
through the index's stored path, so when that path is stale the file is not found and the claim is
dropped. An interrupted title-changing update produces exactly that state, and for a board in it
`sq check` prints "no issues" and exits 0 where the previous commit reported the drift.

## The transaction context

Correct, and it fixes more than the record claimed — the misattribution it prevents is reachable
today with two concurrent transactions on one store, not merely latent. The nested different-store
degradation is unreachable in live code (every `IndexStore` construction site checked) and is pinned
by a test; the only thing I would change is the wording that calls it a faithful translation of the
attribute it replaces.

## What I could not check

- The full suite and `sq check` remain the operator's; targeted `tests/service`, `tests/unit` and
  `tests/cli` runs are green on the committed tree, as are pyright, ruff check and ruff format.
- Still no real `fork`+`SIGKILL` test post-fix. The fault injection now lands inside the live
  primitive, which is most of the distance, but a genuine kill remains the only end-to-end proof.
- Concurrency across *processes* (two `sq` invocations racing) is still reasoned about rather than
  exercised; the new race tests are all single-process.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 671 add-finding "…" --severity medium`; track with `sq review 671 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Verified |  | Stamped skill item files still written non-atomically by sync |
| F2 | 🟡 medium | Verified |  | Interruption tests pass with the primitive sabotaged |
| F3 | 🟡 medium | Verified |  | Whole-file rewrites of partly hand-authored files stay non-atomic |
| F4 | 🟡 medium | Open |  | Markdown-ahead skew is reverted by the next mutation |
| F5 | 🟢 low | Verified |  | Migration-runner exemption's recorded reason covers only ordering |
| F6 | 🟢 low | Verified |  | Post-commit role-file writes in link-role carry no exemption note |
| F7 | 🟢 low | Verified |  | Temp files leak on the error path; config temp escapes gitignore |
| F8 | 🟢 low | Verified |  | Dry-run filesystem fix landed without a regression test |
| F9 | 🟢 low | Open |  | No changelog entry for the durability change |
| F10 | 🟠 high | Open |  | Confirm round drops a durable drift when the index path is stale |
| F11 | 🟢 low | Open |  | Interruption tests hook os.fsync, which the ADR may remove |
| F12 | 🟢 low | Open |  | Root gitignore pattern never reaches an existing squad |
| F13 | 🟢 low | Open |  | Nested different-store transaction silently drops the outer log |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Stamped skill item files still written non-atomically by sync

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
`src/squads/_backends/_claude_code/_backend.py::_write_managed_skill` writes the skill body with
`_aio.write_text` in all four of its branches. On the normal sync path the body path is resolved from
`item.path`, i.e. `<squad>/agents/skills/SKILL-<NNNNNN>-<slug>.md` — a real indexed item file
carrying sq frontmatter. That is squad data by the decision's own enumeration ("item `.md` files"),
and it is none of the exemptions: the exemption covers `.claude/` output, backend *pointer* files and
managed regions, while project convention keeps `.claude/` as pointers and the real definition under
`squads/`. `_aio.py`'s new module docstring lists the legal users of the plain writer as "backend
pointer files, managed-region files, the squad `.gitignore`, override stamps" — this call site is none
of them, so the code contradicts the contract the same commit wrote.

**Measured.** Wrapping both `_aio` writers over one `sq sync` on a fresh squad: 8 role item files
written through the atomic primitive, 10 skill item files through the truncating one. Same class of
artifact, opposite treatment — the role body regen goes through the item-file layer, the skill body
regen does not.

**Consequence, reproduced end to end.** Truncate a stamped skill file inside its frontmatter, then:
`sq repair` drops it ("indexed but no markdown file found"); `sq skill 18 show` answers "no item with
number 18"; the corrupt file stays on disk; `sq sync` writes a *new* legacy slug-named body beside it;
and `seed_bundled_skills` skips re-stamping because its convention-named glob matches the corrupt
file. Two rounds of `repair` + `sync` do not converge — `sq check` exits 3 permanently on "file has no
`id` in frontmatter", and the `.claude` pointer degrades to the pre-stamp slug path. Recovering it
needs a manual file deletion. That is exactly the silent, unrecoverable loss this work exists to
close, still reachable on ten files per sync.

**Shape of the fix.** Route the three body-writing branches (and the pre-stamp first write) onto
`_aio.atomic_write_text`; the backend already imports `_aio`, so no layering rule is touched. The
`.claude/` pointer write in the same method correctly stays on the plain writer.

Worth noting for whoever picks this up: the *content* of a skill body is regenerable, which is
probably why it read as exempt. The frontmatter is not — the id, sequence_id, created_at and session
fields exist nowhere else, and losing them is what makes the state above unrecoverable.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-27T20:53:37Z] Paul Reviewer:
  - Verified against ebaf966. All four write branches in _write_managed_skill now use atomic_write_text; re-ran my write spy over a fresh init+sync and every one of the 10 SKILL item files is atomic (was 10 plain / 8 atomic before), leaving only .claude/ pointers and settings.json on the plain writer.
  - Independently checked the _agents_md conclusion rather than taking it: spied a full init+sync with backend=agents_md — its only plain writes are the .agents_md/roles/*.md staging files, which carry no frontmatter id and no index entry. The conclusion holds.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Interruption tests pass with the primitive sabotaged

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
Replacing the primitive's body with a bare `path.write_text(text, encoding="utf-8")` — no temp file,
no fsync, no replace — keeps both interruption tests green:

- `tests/integration/test_interrupted_write_never_costs_the_item.py` (all three parametrisations)
- `tests/cli/test_interrupted_update_recovers_through_the_cli.py`

Nine other tests do fail under the same sabotage (the primitive's own unit tests, board, memory,
`.squads.toml`), so the suite is not blind to it — it is blind for item `.md` files specifically, the
artifact this work exists to protect.

**Why the headline test cannot fail.** It monkeypatches `squads._aio.atomic_write_text` with a stub
that writes a fractional prefix to its *own* temp path and raises. "The real target is untouched" is
then guaranteed by the stub's construction, not observed from the code under test. What it does pin is
routing — that `set_status` reaches `atomic_write_text` at all — which is worth keeping, but it is not
the atomicity proof the acceptance criterion asks for. The three `frac` values exercise the same
stub-only path three times.

**Why the CLI test cannot fail.** It patches `pathlib.Path.replace` globally, which the index commit
also uses, so the non-zero exit it asserts is produced by the *index* write failing, independently of
the markdown write. The command sets `--desc`, but the post-conditions assert the *title* string
("CLI smoke target") is still shown — a value the update never touched — and never assert `"Renamed"`
is absent. `show` renders from the index, not from the file. Every assertion holds whether or not the
markdown write was atomic; the inline comment claiming "the interrupted description update never
landed" is not what the assertion checks.

**One assertion that can never fail.** In the headline test:

    for stray in path.parent.glob("*.tmp"):
        assert stray.name != path.name

A `*.tmp` name can never equal a `.md` name, so the loop is a no-op — including for the `.crash.tmp`
file the stub deliberately leaves behind.

**Cheap way to make them real.** Inject the fault *inside* the live primitive (patch the temp handle's
`write`, or `os.fsync`, to emit a prefix and then raise) and assert the target's bytes directly; and
assert the item file's own frontmatter for the field that was updated, rather than `show`'s
index-backed output.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-27T20:53:52Z] Paul Reviewer:
  - Verified against ebaf966, by re-running the sabotage myself rather than taking the report. Three variants: (A) bare truncate-in-place — 4 tests red; (B) in-place write that still flushes and fsyncs, i.e. non-atomic but durable — 4 tests red, which is the sharper case and the one that matters. Both now fail on the right assertion: the CLI test reads the item file's own frontmatter and catches description='Renamed' having landed.
  - The vacuous *.tmp assertion is gone, replaced by an assertion that the primitive's new error-path cleanup actually removed the temp sibling — it now tests something.
  - One residual coupling filed separately as F13: the fault hook is os.fsync, which ADR-663 §2 explicitly sanctions removing.
- [2026-07-27T20:56:17Z] Paul Reviewer:
  - Correction to my note above: the fsync-hook follow-up is F11, not F13.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Whole-file rewrites of partly hand-authored files stay non-atomic

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Two exempt writers rewrite a *whole file* whose contents are only partly generated, so the exemption's
premise ("losing it costs a re-sync") does not hold for the part that is hand-authored.

**`_backends/_managed_region.py::inject`** — rewrites the entire `CLAUDE.md` / `AGENTS.md` with
`_aio.write_text` on every sync. The decision exempts "the managed regions in CLAUDE.md/AGENTS.md",
but the write is not region-scoped: it truncates and rewrites the whole file, and in a real adopter
project most of that file is hand-written project instructions that `sq sync` cannot reproduce. A kill
inside that write costs the adopter's own content, not a re-sync. (This repo's own `CLAUDE.md` is a
good measure of the exposure.)

**`_overrides/_stamp.py::stamp_template_file` / `stamp_toml_file`** — read-modify-write in place (sync
`Path.write_text`) of an override template or role TOML the adopter authored by hand, to refresh a
provenance comment. Again the exemption was reasoned about the *stamp*; the write is whole-file.

Neither is an ordering question: nothing in the index mirrors either artifact, so there is no skew to
direct — this is purely the atomicity half.

I am not calling this a routing miss by this change: both sit inside the exemption list as written, so
the change followed its instructions. The finding is that the exemption's reasoning does not survive
contact with these two call sites, and the fix is one call swap each (plus making the overrides pair
async, or leaving them sync and using the same temp+replace shape inline).
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-27T20:53:58Z] Paul Reviewer:
  - Verified against ebaf966. managed_region.inject routes all four branches through atomic_write_text — confirmed live: CLAUDE.md and AGENTS.md now appear in the atomic set of a full init+sync. The override stamp writers use the new _aio.atomic_replace_sync; factoring the sync core out rather than cloning the temp+fsync+replace shape is the right call, and the same core now backs both the sync and async wrappers.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Markdown-ahead skew is reverted by the next mutation

<!-- sq:finding:F4:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
The decision's §1 promises the surviving skew is "healed losslessly and by construction" because
repair derives the index from the markdown. True — provided repair runs before anything else touches
that item. Any ordinary mutation in between silently reverts the markdown to the index's stale copy,
because every mutation core rewrites the *whole* frontmatter from an index-sourced `Item`
(`update_frontmatter(path, item)` where `item` came from `store.load()`).

**Reproduced.** Crash the index commit during `update --desc` on a fresh squad: the file carries the
new description, the index carries the old (empty) one — the sanctioned markdown-ahead skew. Then run
one perfectly ordinary `set_status`. Afterwards the `description` key is gone from the file
altogether: the committed mutation is lost, in the direction §1 forbids. Nothing warns, and the
mutation that destroyed it succeeded normally.

So the guarantee is real for the *interrupted* mutation (the file is never truncated, and the item is
never dropped — that part of the work holds) but the *repair* half of the promise is conditional in a
way nothing states or enforces.

Mitigation that does exist: `sq check` reports the drift at warn level, and this repo runs it before
every handoff — so it is loud, if someone looks in the window between the two mutations. An adopter
who does not run `check` habitually gets no signal.

This is not a defect in the routing work; the ordering rule is what was asked for and it holds. It is
recorded as the gap between what the decision promises and what the code delivers, for the architect
to settle: either a mutation core re-reads the file's frontmatter before rewriting it (and reports the
divergence), or §1 gains the qualifier "provided repair runs before the next mutation on that item".
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-07-27T20:19:54Z] Catherine Manager:
  - Left Open deliberately: not fixed in 0.12.2. The architect ruled it a gap in the stated guarantee rather than the chosen direction, narrowed ADR-663 §1 to a three-way bound, and sanctioned detection-not-merging as the remedy — cut as TASK-672 for 0.13, since a guard that refuses a mutation is user-visible behaviour and does not belong in a patch. Closing this as Fixed would misrepresent what ships.
- [2026-07-27T20:26:15Z] Pierre Chat:
  - Not deferring: the guard ships in 0.12.2 (TASK-672).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Migration-runner exemption's recorded reason covers only ordering

<!-- sq:finding:F5:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
The recorded audit note leaves `_migrations/_v0_4_to_v0_5.py` and `_v0_8_to_v0_10.py` unfixed with the
justification that "`sq migrate up` ends in repair + stamp, which reconciles the surviving state".

I agree with the exemption. I do not agree with that reason, and it is the reason a future reader will
inherit.

- **Ordering half — the reason is right.** Both runners commit the index and then unlink the legacy
  slug-named file. A crash in that window leaves the convention-named file indexed and a stray
  slug-named body on disk; the check scan skips slug-named skill files and repair cannot index a file
  with no frontmatter, so nothing resurrects and nothing is lost. Fine as-is.
- **Atomicity half — the reason is wrong.** Those runners write item `.md` files with the plain
  writer, and repair cannot rebuild a file whose bytes were truncated; that is the entire premise of
  the defect this work closes. A migration is also the widest window in the product, since it rewrites
  every item file in one pass.

What actually makes the exemption safe is different and worth recording in its place: migrations are
one-shot and operator-driven, and `docs/migration.md`'s own quick-start puts
`git switch -c chore/upgrade-squads` immediately before `sq migrate up` as a "clean rollback point", so
a truncated file is recoverable from version control rather than from repair.

No code change requested — frozen runners should stay frozen. Only the recorded justification should
stop telling a future reader that repair covers a truncation.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-07-27T16:10:31Z] Catherine Manager:
  - ADR-663 §2 amended: migration runners are not exempt in principle — new migration code uses the primitive; the shipped runners stay frozen because a migration is one-shot, operator-driven and preceded by the runbook's version-control rollback point. The 'repair reconciles it' reason was mine and was wrong for atomicity.
- [2026-07-27T20:54:09Z] Paul Reviewer:
  - Verified: ADR-663 §2 now carries the corrected reasoning — migration runners are not exempt in principle, the shipped ones stay frozen because a migration is one-shot, operator-driven and preceded by the runbook's version-control rollback point, and it says in as many words that this is not because repair reconciles a truncation. That is the record I asked for.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Post-commit role-file writes in link-role carry no exemption note

<!-- sq:finding:F6:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
`link_role` / `unlink_role` (and `sync`'s roster sweep) call `_resync_role_skills` *after* their
transaction commits, and it writes the role item's `.md` twice: `_refresh_role_skills_extra` rewrites
the frontmatter (`extra.skills`) and `_regen_role_body` rewrites the body's `## Skills` region. §1's
letter is explicit — "nothing that mutates an item `.md` may run after the commit" — and this is the
only site in live code that does.

I agree it is safe, and the reasoning should be on the record rather than inferred:

- The committing transaction mutated the *skill* item's refs, not the role's `extra.skills`, so the
  index never mirrored the values being written. A crash before the write leaves both sources holding
  the same stale derived value; a crash after leaves the markdown ahead. Neither direction is
  index-ahead, so §1's substance ("compliance is the skew direction, not the syntax") is satisfied.
- Both written values are re-derived from the ref graph by `sq sync`, so the worst case is a stale
  cache, not lost content.

What is missing is the note. The decision's audit obligation asks that every enumerated site either
satisfy the rule or be a named exemption with a reason; the two seeding unlinks — which were harmless
either way — got several lines of comment, while the one site genuinely outside the rule's letter got
none. A future auditor of this seam will find the undocumented one and have to re-derive the argument.

Either one sentence at the call site, or a third exemption category in the decision ("re-derivable
regions of an item `.md` the committing transaction did not mirror").
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-07-27T16:10:32Z] Catherine Manager:
  - ADR-663 §1 gains a third exemption bullet naming this as the permitted skew, with both conditions pinned: a derived value the committing transaction did not mirror into the index, and reproducible by sq sync.
- [2026-07-27T20:54:15Z] Paul Reviewer:
  - Verified: ADR-663 §1 now names a third exemption — re-derivable regions of an item .md the committing transaction did not mirror into the index — with both conditions pinned (derived value the transaction did not mirror, and reproducible by sq sync). It is framed as the permitted skew rather than the absence of one, which is the distinction I wanted. No code change was needed and none was made.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Temp files leak on the error path; config temp escapes gitignore

<!-- sq:finding:F7:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
Two small holes in the primitive's temp-file story.

**No cleanup when the write itself fails.** If `write`, `flush`, `fsync` or `replace` raises, the temp
file survives and nothing ever removes it; the unit test asserts that leftover as intended behaviour.
Under process death nothing *can* clean up, agreed — but an exception escaping the write is explicitly
in-model per the crash model ("any exception escaping a transaction body" is the same event class), and
there `tmp.unlink(missing_ok=True)` before re-raising costs one syscall. As it stands each failed write
leaves a permanent `*.tmp` sibling and nothing sweeps them.

**The "it's gitignored" argument stops at the squad dir.** `sq init` writes `*.tmp` into
`<squad-dir>/.gitignore`, but `.squads.toml` lives at the *project root*, so an interrupted config
write leaves `.squads.toml.<pid>.<tid>.tmp` at the root — untracked and unignored. Verified on a fresh
init: the only `.gitignore` sq writes is `squads/.gitignore`.

Mirroring `IndexStore._atomic_write`'s shape (which leaks the same way) was the right call for keeping
one primitive rather than two — this is a note that the shared shape has the hole, not a request to
make the two diverge. Fixing it in both places keeps them identical.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-07-27T20:54:30Z] Paul Reviewer:
  - Verified for both halves as specified. Cleanup: atomic_replace_sync and both IndexStore writers now unlink the temp sibling on the way out under except BaseException, and the unit test that previously asserted the leak now asserts its absence — that test change is correct, not convenient: it was pinning the behaviour this finding asked to change, and it still fails if the cleanup is removed.
  - Gitignore: verified live. Into a project with an existing root .gitignore, init appends only the pattern and leaves node_modules/ and *.log untouched; a second run is a no-op. Appending rather than rewriting is the right mechanism and applies F3's own lesson.
  - The fix's reach is narrower than the hole — filed separately as F14 rather than reopening this one.
- [2026-07-27T20:56:19Z] Paul Reviewer:
  - Correction to my note above: the gitignore-reach follow-up is F12, not F14.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Dry-run filesystem fix landed without a regression test

<!-- sq:finding:F8:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
The `(item, delta, rename)` split — the pure half no longer touching the filesystem, the physical move
performed only by `_update_core` — is the whole fix for the dry-run-mutates-disk defect, and nothing
pins it.

- `tests/service/test_bulk_import_engine.py`'s dry-run cases assert plan/issue shapes only; none
  asserts the item file is still at its original path after a dry run carrying a title change.
- The apply-path assertion (`feat.title == "Feature renamed"`) reads the index, so it would pass just
  as happily if the physical move never happened at all.

Two assertions close it: after `import_events(…, dry_run=True)` with a title-bearing update, the
original filename still exists on disk; after the real apply, the new filename exists and the old one
does not. A high-severity defect with a verified repro deserves that much, or the next refactor of the
pure/impure split silently reopens it.

Same gap, smaller: the second commit's routing changes (sub-entity block writes, rename/retype comment
appends, the shared section-edit core, the role-body regen) have no equivalent of the board/memory gate
test — nothing fails if a future edit at one of those sites reaches for `_aio.write_text` directly.
One service-level test per family, patching `_aio.write_text` to raise if reached, would cover them.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-07-27T20:54:35Z] Paul Reviewer:
  - Verified by sabotage, not by reading: re-introducing the pre-fix impure rename inside _rename turns test_a_dry_run_title_change_never_renames_the_file_on_disk red on exactly the right assertion (the original filename no longer exists). The apply-side companion test asserts the physical move, closing the half that the index-reading assertion could never have caught.
  - The routing gate file also has teeth — routing _section_edit_core back to _aio.write_text turns test_commenting_never_reaches_the_plain_write red.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — No changelog entry for the durability change

<!-- sq:finding:F9:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
The decision's consequences and this work's own final subtask both call for an adopter-facing line: an
interrupted mutation now always leaves the repairable skew — markdown ahead of the index — instead of,
in the worst case, a truncated item file.

`CHANGELOG.md` is unchanged across all three commits. Its top section is the already-released `0.12.1`,
so there is no unreleased section to hold the line either — it needs opening as part of adding it.

Adopter wording only, per the docs rule: no ticket ids, no repo-process detail, no mention of the
internal primitive.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Confirm round drops a durable drift when the index path is stale

<!-- sq:finding:F10:head -->
**Status:** 🔴 Open
**Severity:** 🟠 High
<!-- sq:finding:F10:head:end -->

<!-- sq:finding:F10:body -->
The confirm round re-reads a drift candidate's file at `item_file(self.paths, fresh_item)` — the
path the **index** holds — and silently `continue`s on `FileNotFoundError`. When the index's stored
`path` for that item is stale, the file is not there, the candidate is dropped, and a real, durable
drift is never reported.

A stale index `path` is not an exotic state. It is exactly what an interrupted **title-changing**
update leaves: `_update_core` renames the file, writes the new frontmatter, and only then commits the
index, so a crash in that window leaves the file at the new path with the new values and the index
holding the old path *and* the old status. Both conditions for the miss hold at once.

**Reproduced through the real code path** (fault the index commit during
`update(title=…, status=…)`):

    INDEX : Ready   tasks/TASK-000002-original-title.md
    ONDISK: TASK-000002-renamed-mid-crash.md   (status: InProgress)
    sq check -> (no issues at all)

And end to end through the CLI on a scratch squad in the same state: `✓ no issues`, **exit 0**.

**It is a regression, not a pre-existing gap.** The same scenario against `ebaf966` (the commit
immediately before this one) reports `warn TASK-2: status drift between frontmatter and index`. The
scan pass finds the file by walking the type folders — reality — while the confirm pass looks it up
through the index, which is the side already known to be behind.

**Why this one matters more than its class usually would.** The architect's F4 ruling accepts shipping
the silent-clobber gap on the strength of exactly this signal: "the drift message tells the reader to
repair before mutating that item again". A gate that answers "no issues" for a board in that state
removes the only warning the user gets before the next mutation destroys the interrupted update's
fields. It also breaks the gate's own stated contract in the other direction from the one this work
was worried about: `check` may decline to claim quiescence, but a durable inconsistency has to survive
the confirm round.

**Fix shape.** In the drift loop, re-observe the file wherever the sequence number actually lives, not
only where the index thinks it does: try the fresh index's path, and on `FileNotFoundError` fall back
to the path the scan recorded for that sequence (`on_disk[seq][1]`) before giving up. Only skip when
neither exists — that is the genuine "gone since the scan" case the `continue` was written for. The
ADR's instruction to use the freshly loaded index's path was aimed at an in-flight retype
manufacturing a false claim; it does not anticipate the index's path field itself being the stale
side, which an interrupted rename guarantees.

Worth a regression test in the same file as the other durable-inconsistency cases: durable drift on an
item whose index path is stale must still be reported.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Interruption tests hook os.fsync, which the ADR may remove

<!-- sq:finding:F11:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F11:head:end -->

<!-- sq:finding:F11:body -->
Both interruption tests now fault the live primitive by monkeypatching `os.fsync`. That is a real
improvement over the stub — I verified it catches a bare truncate-in-place *and* an in-place write
that still flushes and fsyncs. The residual problem is the choice of hook.

ADR-663 §2 names removing the markdown-side fsync as the **sanctioned relief** if bulk import ever
measures a real regression: "the sanctioned relief is to skip the fsync on the markdown side — not to
defer the renames … and not to reorder against the index commit". So the tests are pinned to a call
the design explicitly reserves the right to delete.

Verified: dropping only the fsync from `atomic_replace_sync`, leaving temp+replace (and therefore
atomicity) fully intact, turns all four interruption tests red. Whoever takes that sanctioned relief
will get four failing durability tests describing a data-loss scenario that has not occurred, and the
natural reading of that failure is "the relief broke atomicity" when it did not.

Not urgent and not a correctness problem today. A hook that survives the sanctioned change: patch
`pathlib.Path.replace` but raise only when the target is this item's path, letting the index's own
replace through. That faults the step the design cannot remove — the rename is the atomicity — and it
sidesteps the reason `Path.replace` was abandoned in the first place (the index commit tripping the
same global patch).
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Root gitignore pattern never reaches an existing squad

<!-- sq:finding:F12:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F12:head:end -->

<!-- sq:finding:F12:body -->
`_ensure_root_tmp_ignored` is called from `init` and `adopt` only. Neither runs again on a squad that
already exists, so every squad initialised before this release keeps the hole the finding described:
an interrupted `.squads.toml` write leaves `.squads.toml.<pid>.<tid>.tmp` at the project root,
untracked and unignored, where a `git add -A` sweeps it into a commit.

This repository is itself an example — its root `.gitignore` contains neither `*.tmp` nor the new
pattern, and nothing in the upgrade path will add it.

`sq sync` is the natural home: it is the idempotent "bring this squad up to date with the installed
version" command, the helper is already a no-op when the pattern (or a covering `*.tmp`) is present,
and it is what an upgrading adopter runs anyway. Calling it from `sync` in addition to `init`/`adopt`
is a one-line change and needs no migration.

Low severity — the artefact only appears after a failed config write, and committing it is untidy
rather than harmful. Filed separately rather than reopening the original finding, whose two asks were
both delivered as written.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Nested different-store transaction silently drops the outer log

<!-- sq:finding:F13:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F13:head:end -->

<!-- sq:finding:F13:body -->
The store-scoped guard is right, and the concurrency fix it delivers is real: I restored the
pre-change shared-attribute design in a scratch worktree and the new concurrency test fails hard —
**1 of 8** reflog lines survives, the other seven misattributed into another task's buffer. The
defect the decision called "currently unreachable" is reachable the moment two transactions on one
store share an event loop, which is what a long-lived process (TUI, editor extension, server) does.
Worth recording, because it makes this change more than hygiene.

The one thing I would not leave as written is the claim that instance identity is "the faithful
translation of the per-instance attribute being replaced". For the nested case it is not a
translation, it is a behaviour change:

- **Before:** store A opens a transaction; store B's transaction is nested inside; `A._log()` reads
  `A._current_ctx`, which is still A's own context, and buffers correctly.
- **After:** one ambient slot per task, so B's binding shadows A's; `A._log()` sees a foreign owner
  and returns `None`. A's entries are **silently discarded** for the duration of the inner
  transaction — not misattributed, but not written either.

The unit test pins that discard as intended (`assert _transaction_ctx_for(outer_store) is None`),
which is the right way to record a known divergence but does mean the divergence is now load-bearing.

Unreachable today — I checked every `IndexStore(...)` construction site: the two migration runners
build their own store outside any other transaction, `init`/`adopt` build one standalone, and
`Service` holds exactly one. Nothing nests across stores. So no fix is needed for 0.12.2.

Two cheap ways to close it whenever the transaction API is next touched (the decision already names
that as the promotion trigger): bind a per-store mapping rather than a single slot
(`ContextVar[dict[IndexStore, _TransactionCtx]]`, entry added and removed by token), or keep the
single slot and drop the "faithful translation" wording so the next reader knows the nested case
loses log lines rather than assuming parity with the old attribute.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T16:02:48Z] Paul Reviewer:
  - Reviewed 68a44ed..fc9be74 as committed (git show, not the working tree — another dev is mid-edit in _index/_store.py). Method and per-question verdicts are in the body; nine findings filed, one high.
  - F1 is the only one I would hold the work on: sq sync still writes the 10 stamped skill item files through the truncating _aio.write_text (measured by wrapping both writers over one sync), and I reproduced the full unrecoverable end state — repair drops the item, sync writes a new legacy body beside the corrupt one, seeding skips it, sq check exits 3 permanently. The backend already imports _aio, so it is a three-line fix.
  - F2 is the second one worth acting on before this is called proven: I sabotaged the primitive into a bare truncate-in-place and both interruption tests (including the headline data-loss test) stayed green — the board/memory/.squads.toml tests caught it, the item-file ones did not. Details and the cheap faithful variant are in the finding.
  - The ordering work itself checks out: I enumerated all 25 live-code transaction sites and extracted what runs after each block's exit; only backend pointer regen, .claude artifact removal, repair and _resync_role_skills follow a commit, and the first three are exempt. Both fixed sites are correct and the purge case has a real test.
  - Gates re-run on the committed tree in a scratch worktree: pyright, ruff check and ruff format clean; targeted import/retype/remove/sub-entity/board/memory/rename suites green. I did not run the full suite or sq check — the operator owns both.
  - Board note, no finding filed: all six subtasks (ST1-ST6) are still Todo while the parent sits InReview.
  - @tech-lead @python-dev F1 and F2 are the actionable pair; F3/F4 are model-level and need @architect's call rather than a patch here.
- [2026-07-27T20:19:40Z] Catherine Manager:
  - F1/F2/F3/F7/F8 fixed in the tree; awaiting full-suite verification and re-review. F2's acceptance was met by demonstration: sabotaging the primitive to a bare truncate turns both interruption tests red (4 failed), restoring turns them green. Signed off the dev's scope call to touch _services/_service.py for F7's gitignore half — it was the only way to close it. F4/F5/F6 ruled by the architect; F9 goes to the tech writer at the end of the round.
- [2026-07-27T20:57:11Z] Paul Reviewer:
  - Second pass at bb39384 (ebaf966 + d6cd884 + 13888b8). All five fixes verified by re-breaking them, not by reading: F1, F2, F3, F5, F6, F7, F8 → Verified. Details and the sabotage table are in each finding and the appended body section.
  - One new high finding, F10, and it is a shipping blocker for 0.12.2 as it stands: sq check's confirm round re-reads a drift candidate at the path the INDEX holds and silently skips on FileNotFoundError, so when that path is stale the durable drift is never reported. An interrupted title-changing update leaves exactly that state (rename, then frontmatter write, then the index commit that never lands). Reproduced through the real code path and end to end — the CLI prints '✓ no issues' and exits 0; ebaf966, one commit earlier, reports the drift. Fix is a fallback to the scan's own path for that sequence before giving up.
  - F10 matters beyond its own scope because @architect's F4 ruling accepts the silent-clobber risk on the strength of this exact signal — 'the drift message tells the reader to repair before mutating that item again'. With F10 open there is no message.
  - Three low findings, none blocking: F11 (the interruption tests hook os.fsync, which ADR-663 §2 explicitly reserves the right to remove — taking that sanctioned relief turns all four red for a reason unrelated to atomicity), F12 (the root gitignore pattern only reaches new squads; sync is the idempotent home), F13 (the nested different-store context degradation is a behaviour change, not a faithful translation, of the attribute it replaced — unreachable today, so wording or a per-store mapping, not a fix now).
  - Otherwise the read side is sound: the confirm round pays nothing on a clean board, and durable inconsistencies survive concurrent activity on other items — I wrote three adversarial race tests to check that specifically. The transaction context is right and fixes more than was claimed: restoring the old shared attribute leaves 1 of 8 reflog lines surviving, so that misattribution was reachable, not latent.
  - On pace: this round is not being rushed in the sense of skipped work — the fixes are thorough and the new tests have teeth. But F10 is a regression that landed in the same commit as its own test suite and neither the suite nor the gate caught it, which is the second time in this ticket that a green suite has stood in for a proof. Fix F10, add the regression test, and I would call 0.12.2 shippable.
  - @python-dev F10 is the one to act on. @tech-lead F11/F12 are cheap; F13 is a judgement call for @architect on wording versus mechanism.
<!-- sq:discussion:end -->

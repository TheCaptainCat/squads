---
id: REV-671
sequence_id: 671
type: review
title: Atomic write primitive and write-path ordering rule
status: ChangesRequested
author: reviewer
refs:
- TASK-664
subentities:
- local_id: F1
  title: Stamped skill item files still written non-atomically by sync
  status: Fixed
  severity: high
- local_id: F2
  title: Interruption tests pass with the primitive sabotaged
  status: Fixed
  severity: medium
- local_id: F3
  title: Whole-file rewrites of partly hand-authored files stay non-atomic
  status: Fixed
  severity: medium
- local_id: F4
  title: Markdown-ahead skew is reverted by the next mutation
  status: Open
  severity: medium
- local_id: F5
  title: Migration-runner exemption's recorded reason covers only ordering
  status: Fixed
  severity: low
- local_id: F6
  title: Post-commit role-file writes in link-role carry no exemption note
  status: Fixed
  severity: low
- local_id: F7
  title: Temp files leak on the error path; config temp escapes gitignore
  status: Fixed
  severity: low
- local_id: F8
  title: Dry-run filesystem fix landed without a regression test
  status: Fixed
  severity: low
- local_id: F9
  title: No changelog entry for the durability change
  status: Open
  severity: low
created_at: '2026-07-27T16:00:06Z'
updated_at: '2026-07-27T20:26:15Z'
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
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 671 add-finding "…" --severity medium`; track with `sq review 671 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | Stamped skill item files still written non-atomically by sync |
| F2 | 🟡 medium | Fixed |  | Interruption tests pass with the primitive sabotaged |
| F3 | 🟡 medium | Fixed |  | Whole-file rewrites of partly hand-authored files stay non-atomic |
| F4 | 🟡 medium | Open |  | Markdown-ahead skew is reverted by the next mutation |
| F5 | 🟢 low | Fixed |  | Migration-runner exemption's recorded reason covers only ordering |
| F6 | 🟢 low | Fixed |  | Post-commit role-file writes in link-role carry no exemption note |
| F7 | 🟢 low | Fixed |  | Temp files leak on the error path; config temp escapes gitignore |
| F8 | 🟢 low | Fixed |  | Dry-run filesystem fix landed without a regression test |
| F9 | 🟢 low | Open |  | No changelog entry for the durability change |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Stamped skill item files still written non-atomically by sync

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
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
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Interruption tests pass with the primitive sabotaged

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
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
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Whole-file rewrites of partly hand-authored files stay non-atomic

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
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
**Status:** 🟡 Fixed
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
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Post-commit role-file writes in link-role carry no exemption note

<!-- sq:finding:F6:head -->
**Status:** 🟡 Fixed
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
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Temp files leak on the error path; config temp escapes gitignore

<!-- sq:finding:F7:head -->
**Status:** 🟡 Fixed
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
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Dry-run filesystem fix landed without a regression test

<!-- sq:finding:F8:head -->
**Status:** 🟡 Fixed
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
<!-- sq:discussion:end -->

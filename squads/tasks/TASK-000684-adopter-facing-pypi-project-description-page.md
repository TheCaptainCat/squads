---
id: TASK-684
sequence_id: 684
type: task
title: Adopter-facing PyPI project description page
status: Done
author: tech-writer
created_at: '2026-07-28T14:48:35Z'
updated_at: '2026-07-29T08:37:45Z'
---
<!-- sq:body -->
The root README carries the GitHub repo, contributors, and — via `readme = "README.md"` — the PyPI project description. This splits the last audience onto its own page, the way the VS Code client already has a dedicated Marketplace overview.

## What was written

`PYPI.md` at the repository root, 144 lines (the Marketplace overview is 206). Ordered for a reader at a terminal: what squads is, install, `sq init`, then the problem it solves, the model, a worked CLI example, backends, a short pointer to the read-only clients, docs links, and a pre-1.0 maturity note with the licence.

## Shape and rationale

- **Install and first squad come before the argument.** A PyPI reader wants to know what a package is and how to start, in that order; the persuasion can follow.
- **The worked example is the centrepiece** — a full piece of work from proposal to closed, sixteen commands, each one executed against a real squad rather than checked against `--help`. It keeps the line where a review cannot move straight from Requested to Approved, because on a CLI page that is the clearest available proof that transitions are validated rather than free text.
- **The clients are three sentences, not a section.** `sq ui` (named with its `tui` extra) and the VS Code extension, both read-only, no feature list.
- **Every link is absolute.** PyPI renders no repo-relative links, so each doc pointer is a full `https://github.com/...` URL. No HTML, no badges, no images.
- **Maturity stated plainly:** pre-1.0, surfaces still moving, schema changes possible, `sq migrate up` as the carry-forward, and the stability contract linked for what 1.0 will promise. No claims about adoption or ecosystem.

## Left out relative to the Marketplace overview

The three sidebar views, the dossier anatomy, the auto-refresh section, the search and view controls, the read-only-boundary section, and the whole VS Code install and discovery flow. Reference material is left to the repository, which is one click away.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 684 add-subtask "<title>"`; track with `sq task 684 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-28T14:50:26Z] Theo Writer:
  - Wrote PYPI.md at the repository root (144 lines, untracked — not committed). Reused the squads half of the Marketplace overview as source material but reordered it for the audience: install and 'sq init' come before the argument, since a PyPI reader wants what-it-is then how-to-start, fast.
  - Every link is absolute (nine github.com/TheCaptainCat/squads URLs plus the Marketplace item URL) — checked mechanically, no repo-relative paths, no HTML, no badges or images. The commands in the page were run rather than assumed: the sixteen-line example against a throwaway squad in an earlier pass, and sq workflow / sq docs / sq mine / sq blocked / show --full --comments re-checked for exit 0 here.
  - Cut relative to the Marketplace overview: the three sidebar views, the dossier anatomy, auto-refresh, search and view controls, the read-only-boundary section, and the whole VS Code install and discovery flow. The clients are three sentences with the tui extra named and both flagged read-only.
  - @op-pierre filename: PYPI.md at the root, for symmetry with clients/vscode/MARKETPLACE.md — each file named for where it is published, sitting next to the thing it describes. It has to be inside the sdist for 'readme' to resolve, which the root guarantees. One consequence worth a nod: the root then holds README.md and PYPI.md side by side, and a browser may wonder which is canonical — the answer is README.md, and if that ever grates the alternative is packaging/PYPI.md.
  - @devops the packaging change this needs is 'readme = "PYPI.md"' in pyproject.toml — not made here, and the file is deliberately left uncommitted for review first.
- [2026-07-28T15:26:19Z] Catherine Manager:
  - 0.12.3 resume point. Branch release/0.12.3, 9 commits, unpushed. Done: VSIX LICENSE fix, extension Marketplace metadata, MARKETPLACE.md rewrite+expansion+trim, README corrections, PYPI.md + pyproject readme wiring + runbook drift note, TASK-681 (global refresh + fold preservation, dev-host verified by op-pierre). Open: doc fixes from REV-685/REV-686 were in flight with the tech writer when the session ended — check the working tree for uncommitted MARKETPLACE.md/PYPI.md/README.md/clients-vscode-README changes before redoing them. Then: changelog for 0.12.3, bump_version.py 0.12.3, uv build, push, PR into main, watch CI (the matrix caught Windows-only failures last release). Deferred to a later release: REV-685 F1 (contributor onboarding section; CONTRIBUTING.md omits clients/, the extension, npm) and F2 (root README ordering).
- [2026-07-28T15:28:08Z] Catherine Manager:
  - Correction to the resume point: the tech writer was stopped during verification, before touching any doc file — MARKETPLACE.md, PYPI.md, README.md and clients/vscode/README.md are all at their committed state. The doc fixes from REV-685/686 are unstarted, not half-done.
- [2026-07-29T07:34:03Z] Theo Writer:
  - Review-fix pass across the four docs (nothing committed). Fixed: the worked example on MARKETPLACE.md and PYPI.md, the ref-kind list and the sq blocked bullet in README.md, the directional clause on PYPI.md, and the extension README's opening paragraph.
  - Example root cause: my verification run included 'sq dev add --tech python' as its first command and the published block did not. That one omission produced both failures at once — python-dev did not exist, and without the dev role the counter sat at 18 so the first feature was FEAT-19 rather than the FEAT-20 my run produced. The lesson is mechanical: paste the block that ships, then run that, rather than running a sequence and transcribing it.
  - Durability fix: literal IDs replaced by typed placeholders (FEAT-<n>, TASK-<n>, REV-<n>) after confirming full-ID addressing is legal and type-validated. The example can no longer go stale when init's role/skill count changes or a reader picks --roles core. Verified end to end twice from a clean init, the second time using the page's exact text.
  - One out-of-list correction on MARKETPLACE.md: the auto-refresh caveat said 'each view's refresh button', which the unified-refresh work made imprecise — the button in each view's title bar now runs one global Refresh All, so the clause names it.
  - Findings closed: REV-686 F1, F3; REV-685 F3, F4, F5, F6, F7, F8. Left Open: REV-686 F2 (Marketplace pre-1.0 disclosure — outside both the fix and defer lists, so untouched), REV-686 F4 (informational), REV-685 F9 (half-done), F1 and F2 (deferred).
- [2026-07-29T07:38:55Z] Theo Writer:
  - Follow-up pass, three edits, nothing committed.
  - MARKETPLACE.md: added the pre-1.0/schema disclosure (REV-686 F2, now Fixed) as a fourth bullet in 'What it doesn't do' — before Getting started, in the same plain register as the section's other limits, with sq migrate up and the stability contract in the same bullet so the limitation arrives with its remedy. Every link on the page remains absolute.
  - clients/vscode/README.md: dev-host launch corrected. --disable-extensions dropped from the default command because it disables Remote-WSL — the host then runs on Windows over the UNC share where a Linux sq in .venv/bin cannot execute, producing a discovery error instead of the extension. WSL exception stated explicitly, flag kept as an option elsewhere.
  - README.md: one clause on the existing link row naming clients/vscode/README.md as where the VS Code client is worked on — REV-685 F9's cheap half, no restructuring, so the ordering question stays closed. F9 stays Open for the PYPI.md half.
- [2026-07-29T08:37:45Z] Theo Writer:
  - Closed REV-685's last three findings (F1, F2, F9) in README.md and CONTRIBUTING.md; the review is now fully Fixed. Nothing committed.
  - README.md restructured, no deletions: pitch / Install / Quickstart / Working with agents / Browsing the squad / Concepts / Documentation / Contributing / Command reference / Shell completion / Backends / Git notes. Shell completion moved from third section to appendix; 'Working with agents' moved from line 265 up to just after Quickstart; a real Contributing section added; the sibling-page question answered in Documentation.
  - Split chosen: README routes (two toolchains, both gate blocks, --all-extras, where architecture lives, the conventions that bounce a PR), CONTRIBUTING.md holds the depth (full conventions, how-to-add recipes, release runbook) and gained what it was missing — the VS Code client's npm gate, the tests/meta guard tests, --all-extras with its symptom, and a two-toolchain opening.
  - Stale material found by the reorganisation: the Quickstart failed as written ('sq create feature' without the required --author) and used a literal task number; both fixed and verified end to end from a clean init. CONTRIBUTING.md's 'how to add an item type' pointed at the deleted _models/_enums module and at a PLAYBOOK constant that is now bundled TOML; both rewritten. Flagged but out of scope: the bundled TOMLs cite golden-lock test paths that have moved, and the repo-root docs plus tests/CONVENTIONS.md sit outside both hygiene gates' scan roots.
  - Note for whoever commits: the working tree also carries BUG-679/BUG-680 status transitions and a verification comment authored by the manager, not by me — my changes are README.md and CONTRIBUTING.md only.
<!-- sq:discussion:end -->

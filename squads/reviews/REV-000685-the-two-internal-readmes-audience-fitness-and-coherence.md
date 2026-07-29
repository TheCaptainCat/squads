---
id: REV-685
sequence_id: 685
type: review
title: 'The two internal READMEs: audience fitness and coherence'
status: Approved
author: reviewer
description: Root README and the VS Code extension README reviewed for audience fitness,
  contradiction, duplication and staleness; the two published listings deliberately
  out of scope.
subentities:
- local_id: F1
  title: Root README has no contributor onboarding
  status: Fixed
  severity: high
- local_id: F2
  title: Ordering serves neither arrival
  status: Fixed
  severity: medium
- local_id: F3
  title: Extension README serves neither of its audiences
  status: Fixed
  severity: medium
- local_id: F4
  title: Extension README describes two views; there are three
  status: Fixed
  severity: medium
- local_id: F5
  title: Ref-kind list is five of nine valid kinds
  status: Fixed
  severity: medium
- local_id: F6
  title: Extension README omits search and display labels
  status: Fixed
  severity: medium
- local_id: F7
  title: Review-finding id leaked into the extension README
  status: Fixed
  severity: low
- local_id: F8
  title: Dropped 'meta' terminology still in the extension README
  status: Fixed
  severity: low
- local_id: F9
  title: Neither README acknowledges its sibling documents
  status: Fixed
  severity: low
created_at: '2026-07-28T15:03:55Z'
updated_at: '2026-07-29T08:39:06Z'
---
<!-- sq:body -->
Independent review of the two internal READMEs — `README.md` (repo root, what GitHub shows) and
`clients/vscode/README.md` (the presentation of that subdirectory) — judged against their stated
purpose: **each is both an advert and contributor onboarding**, for the same page, serving two
different arrivals. The two published listings (`PYPI.md`, `clients/vscode/MARKETPLACE.md`) are
reviewed separately and were deliberately not read as sources here.

## Method

Every checkable claim was verified against the code, the bundled spec, or `package.json` — never
against the other document. Specifically: the bundled workflow spec for every lifecycle row and every
type prefix (`bundled_spec()`, `prefix_for`), `VALID_REF_KINDS` for the ref-kind list, the `docs/`
directory listing for all thirteen documentation links, `clients/vscode/package.json` for the
contributed views, commands and npm scripts, `pyproject.toml` for the Python floor and the `clients/`
exclusion, and `CONTRIBUTING.md` for what contributor material exists elsewhere.

Ada is mid-implementation in `clients/vscode/` on the unified-refresh work, so `package.json` already
contains a `squads.refreshAll` command absent from both READMEs. That is in-flight work, not a
documentation defect, and is excluded from the findings.

## The criterion

Two audiences, one page, so the test is not *which* job each file does but whether it does **both**,
in an order that serves whoever arrived:

- an **advert** reader has to learn what squads is and why they'd want it, before being asked to
  install anything;
- a **contributor** reader has to get from interested to able-to-work — setup, gates, architecture,
  conventions.

Duplication with the published listings is expected under this framing and is not treated as a
defect. Contradiction is, and so is a fact stated in four places with no owner.

## What holds up

The root README's factual content is in good shape, and the earlier ten-defect pass evidently held.
Verified correct: "ten types ship by default" across the three named categories; all six rows of the
status-workflow table, including the bug lifecycle that was previously wrong; all ten built-in
prefixes; the sub-entity lifecycles; all thirteen `docs/` links resolving to real files; the Python
≥ 3.14 floor; and the sq-owned-files warning now correctly saying nobody hand-edits them.

The extension README's verifiable specifics also hold: `npm run check`, `npm run test:canary` and
`npm run test:e2e` all exist as described, and the claim that nothing under `clients/` is read by the
Python gate matches `pyproject.toml`'s `exclude = ["clients"]` and vulture's `src/squads`-only paths.

The advert half of the root README is also genuinely good where it exists — the opening sixteen lines
say what the product is, for whom, and what makes it different, without hedging.

So this is not a repeat of the accuracy sweep. What the dual-purpose criterion exposes is different
and more structural.

## Assessment against the criterion

**The root README does the advert job unevenly and the contributor job barely at all.** Of 354 lines,
the contributor audience gets a three-line parenthetical about `uv sync` and a link to
`CONTRIBUTING.md` buried mid-sentence at line 194. There is no gate command, no architecture pointer,
no statement of the conventions a contributor would violate first. Half the file's stated purpose is
served by a link.

The advert half is undermined by ordering rather than content. The most persuasive material in the
repo — the roster, greeting impersonation, and how a team of agents actually divides work — sits at
line 265, below a 65-line command reference. And thirty lines of shell-completion instructions sit
above the Quickstart, addressed to a reader who has already installed and committed.

**The extension README fails both audiences, and it is the weak point of the set.** Its bulk is a
single 36-line paragraph of implementation detail with source paths threaded through it — too
internal to advertise the extension, and not an architecture map either, because it is prose rather
than structure. Its onboarding content is six lines of npm commands, with nothing on how the pieces
fit, how to run the dev host, or what the layering rules are. Someone arriving to work on the
extension has effectively nothing, and the file looks occupied enough that this went unnoticed.

**The split between the four documents is invisible from both READMEs.** Neither acknowledges that a
PyPI page or a Marketplace listing exists, and the extension README never says what it is or what
`MARKETPLACE.md` is for. The structure exists in the team's head, not on the page.

## On the tech writer's three recommendations

**A one-line pointer to the PyPI page — agree, and widen it.** Under the dual-purpose framing this is
not cosmetic: a reader who cannot tell which document owns which audience cannot tell whether they
are in the right place. Both READMEs should name their siblings. Recorded as its own finding.

**"Move contributor material forward" — the premise is gone, so reject the framing and keep the
intent.** That recommendation assumed the README had become contributor-owned. It hasn't; it owns two
audiences, so the question is ordering between them, not promotion of one. Promoting contributor
material would push the advert down and fail the more common arrival.

The order I would actually put them in: pitch → what it looks like in use (Quickstart) → concepts →
where to go next (docs + the sibling listings) → contributing, as a real section rather than a link →
command reference → reference appendices (shell completion, backends, git notes). That fixes both
audiences at once, because the advert reader stops reading before the reference and the contributor
reader now has a section to stop at. The single largest ordering defect is shell completion above
Quickstart; the second is "Working with agents" below the command reference.

**Against pruning the command reference — agree, with a condition.** It is the only complete command
inventory outside `--help`, it is browsable in a way `--help` and `sq docs` are not, and pruning it
would push a reader to per-command discovery, which is worse. But its value depends entirely on being
true, and it is currently not: the ref-kind list is five of nine actual kinds. Keep it, and treat
anything in it that the tool can print as owing a verification pass against the tool rather than
against a previous edit of the README.

## Which facts are safe to repeat

Duplication across arrival paths is fine for stable prose — what squads is, why it exists, the
concept vocabulary. It is not fine for anything the tool itself can print, because those drift
silently and there is no gate on them: the install command, the Python floor, the status-lifecycle
table, the ref kinds, and the command reference. Those are already stated in up to four places with
no owner. The durable fix is not deduplication but attribution — say where the authoritative version
comes from (`sq workflow`, `sq --help`, `sq docs`) so a reader who hits a contradiction knows which
side to trust, and a future editor knows what to re-verify against.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 685 add-finding "…" --severity medium`; track with `sq review 685 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | Root README has no contributor onboarding |
| F2 | 🟡 medium | Fixed |  | Ordering serves neither arrival |
| F3 | 🟡 medium | Fixed |  | Extension README serves neither of its audiences |
| F4 | 🟡 medium | Fixed |  | Extension README describes two views; there are three |
| F5 | 🟡 medium | Fixed |  | Ref-kind list is five of nine valid kinds |
| F6 | 🟡 medium | Fixed |  | Extension README omits search and display labels |
| F7 | 🟢 low | Fixed |  | Review-finding id leaked into the extension README |
| F8 | 🟢 low | Fixed |  | Dropped 'meta' terminology still in the extension README |
| F9 | 🟢 low | Fixed |  | Neither README acknowledges its sibling documents |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Root README has no contributor onboarding

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Contributor onboarding is one of the root README's two stated jobs, and the file does almost none of
it.

What a contributor arriving on the GitHub page actually gets, across 354 lines:

- a three-line block quote at lines 48–50 noting that `uv sync` creates the venv and the CLI is then
  `uv run sq …` — framed as a caveat for reading the *usage* examples, not as setup;
- a link to `CONTRIBUTING.md` at line 194, mid-sentence, in a run-on line that also carries
  `CONTRIBUTORS.md` and `CHANGELOG.md`.

That is the whole of it. There is no test command, no lint or type-check command, no statement that
the gate is `pyright` + `ruff` + `pytest` and must be run with `--all-extras`, no pointer to the
architecture (`docs/internals.md` is listed among ten doc links with no signal that it is the one a
contributor wants), and no statement of the conventions someone would breach first — the
module-privacy rule, the marker regions, or the rule that sq-managed files are never hand-edited.

The `docs/` list does not help here either: it is ordered and worded for adopters ("a 15-minute,
end-to-end first squad", "migrating an existing project"), so a contributor scanning it has no cue
which entries are for them.

This is not an argument for turning the README into `CONTRIBUTING.md`. It is that half the file's
stated purpose is currently discharged by a hyperlink, and a reader who came to contribute has to
guess both that the link is for them and that it is the only thing that is.

Worth noting alongside: `CONTRIBUTING.md` itself contains no mention of `clients/`, the VS Code
extension, or `npm` — verified by grep. So the single place the README delegates this entire audience
to does not cover a substantial part of the repo, which is the same gap the extension README's own
thin onboarding leaves open from the other side.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Ordering serves neither arrival

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
The root README's content is largely right; its order serves neither arrival.

**Shell completion is the third section**, at lines 52–81 — thirty lines of per-shell installation
detail, above the Quickstart. It is addressed to a reader who has already installed the tool, decided
to keep it, and wants to tune their shell. Every reader who has not yet decided must scroll past it,
and it sits between "how to install" and "what it looks like to use", which is exactly where the
advert's momentum should be.

**The most persuasive material in the repo is at line 265**, in "Working with agents": the roster of
named agents, greeting impersonation ("say *Hi Robert* and Claude becomes Robert Architect"), and how
the division of labour actually works. That is the thing that makes squads different from a task
tracker, and it sits below a 65-line command reference, at three-quarters depth. A reader evaluating
the product has almost certainly stopped by then.

The net effect is an advert whose strongest argument is filed under reference material, and a
reference section positioned as though it were the pitch.

Suggested order, which serves both audiences without promoting either — pitch → Quickstart → concepts
→ where to go next (docs, and the sibling listings) → contributing as a real section → command
reference → reference appendices (shell completion, backends, git notes). The advert reader stops
before the reference; the contributor reader has a section to stop at; nothing is deleted.

Two specific moves carry most of the benefit: shell completion down to an appendix, and "Working with
agents" up above the command reference.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Extension README serves neither of its audiences

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
`clients/vscode/README.md` is 88 lines, and it serves neither of its two audiences.

**As an advert it is unreadable.** Lines 13–48 are a *single 36-line paragraph* — verified: one blank
line in that whole span. It threads implementation detail and source paths through continuous prose:
`src/treeDataProvider.ts`, `src/itemPreviewManager.ts`, `src/domain/previewMessages.ts`,
`src/domain/graphDiagrams.ts`, `media/mermaid.min.js`, `scripts/copy-mermaid.js`,
`src/domain/markdown.ts`, `src/domain/previewDocument.ts`, `src/commands.ts`,
`src/metaTreeDataProvider.ts`, `src/discovery.ts`, `src/sqAdapter.ts`, `src/squadWatcher.ts`. Someone
browsing the subdirectory to find out what the extension does cannot skim it, and the detail is
addressed to somebody who already knows the codebase.

**As onboarding it is six lines** — `npm install`, `npm run check`, `npm test`, plus the two extra
test lanes. Those are correct and useful. What is absent: how the pieces fit (the layering that keeps
`domain/` vscode-free and unit-testable is one of the extension's real design rules and appears only
as an aside), how to launch the dev host for a visual check, what the CSP and no-CDN constraints
oblige a contributor to preserve, and why TypeScript is pinned. A contributor has to reverse-engineer
the architecture from the same paragraph an advert reader is bouncing off.

**And it is the paragraph's form that causes the staleness filed separately.** A 36-line prose block
with no headings has no section to update when a feature ships, so features get appended or not at
all — which is why a whole activity-bar view and the search QuickPick are missing from it. Any fix
that preserves the single-paragraph shape will go stale again the same way.

The reframing that resolves it: `MARKETPLACE.md` now owns the extension's user-facing feature
description, so this file does not need to carry one at all. Replacing the paragraph with a short
"what this is" opener plus an architecture-and-conventions map would serve the browser *and* the
contributor, and would be structurally resistant to going stale.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Extension README describes two views; there are three

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
The two documents disagree about how many activity-bar views the extension has, and the extension's
own README is the one that is wrong.

`clients/vscode/package.json` contributes **three** views, verified:

    squadsTree     "Work Items"
    squadsMeta     "Roster"
    squadsRecords  "Records"

The root README describes them correctly — "work items, records, and roster as activity-bar trees"
(line 101–104).

`clients/vscode/README.md` describes two. It introduces the Work Items tree, then "A second,
independent activity-bar view — **Roster**", and closes with "**Both views** auto-refresh when
`.squads.json` changes on disk". The Records view is absent entirely: no mention of the view, of
`recordsTreeDataProvider.ts`, or of what it contains.

This is the clearest instance of the contradiction the review was asked to look for, and note the
direction: the document *closest* to the code is the stale one, while the repo-root README a level up
is accurate. A reader who trusts proximity gets the wrong answer.

Two consequences beyond the count. "Both views" makes the auto-refresh claim wrong as written for a
three-view extension. And a contributor working on refresh behaviour — which is live work right now —
would take "both" as the complete set.

Verified via `package.json`'s `views` block, not by comparing the two documents.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Ref-kind list is five of nine valid kinds

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
The root README's command reference lists five of the nine valid ref kinds, and the omission is the
kind that makes a correct command look invalid.

Line 243:

    sq <type> <n> ref add TARGET [--kind related|blocks|implements|fixes|addresses]

`VALID_REF_KINDS` actually contains nine, verified from `squads._models._item`:

    addresses  blocks  depends-on  duplicates  fixes  implements  related  scopes  supersedes

Missing: `depends-on`, `duplicates`, `scopes`, `supersedes`.

`depends-on` and `supersedes` are the consequential two. `supersedes` is the mechanism the ADR
lifecycle depends on — `sq check` warns when a Superseded record has no incoming `supersedes` edge,
so a reader following only the README cannot produce a clean board for a superseded decision.
`depends-on` is how sequencing between items is recorded; a reader would reasonably conclude from
this line that it is not supported and reach for `blocks`, which means something different.

This is the same defect class as the ten already fixed in this file — a reference line that drifted
behind the code — and it is why the command reference is worth keeping only if it is verified against
the tool. The authoritative list is in the code, and the per-command `--help` shows it; the README
should either match or say where the current list comes from.

Verified against `VALID_REF_KINDS`, not against another document.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Extension README omits search and display labels

<!-- sq:finding:F6:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
The extension README's feature description stopped being updated two releases ago.

Absent entirely — **full-text search**. `clients/vscode/src/searchQuickPick.ts` exists, the
`squads.search` command is contributed with an `ctrl+alt+s` / `cmd+alt+s` keybinding, and the 0.12.0
changelog announces it: "VS Code: full-text search. A new search QuickPick searches item bodies and
discussions, narrowed by a single type or status, with a result opening straight into the preview."
The README contains no occurrence of the word "search" at all — verified by case-insensitive grep.

Absent — **per-type display labels**, shipped in 0.12.1, whose changelog entry names this client
specifically: the Records and Work (group-by-type) trees showing "Decisions" / "Tasks" rather than the
raw type names, and the Roster tree resolving its labels from the spec.

Also absent, and filed separately because it is a contradiction rather than an omission: the Records
view.

Two things make this more than a housekeeping gap. Search is a headline user-facing capability, so its
absence hurts the advert audience directly — someone browsing the subdirectory to see whether the
extension can find things concludes that it cannot. And the pattern of what is missing (the two most
recent releases, in a file whose feature description is one continuous paragraph) points at the cause
rather than the instances: there is no section for a shipped feature to be added to, so it isn't.

Verified against `package.json`'s contributed commands and keybindings, the presence of
`searchQuickPick.ts`, and the CHANGELOG entries for 0.12.0 and 0.12.1.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Review-finding id leaked into the extension README

<!-- sq:finding:F7:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
An internal review-finding reference leaked into a published-on-GitHub document.

`clients/vscode/README.md` line 47:

    Both views auto-refresh when `.squads.json` changes on disk (F17, via `src/squadWatcher.ts`).

"F17" is a review finding's local id. It means nothing to any reader of this file — an advert reader,
a contributor, or anyone browsing the repo — and it is not resolvable from the document, since
finding ids are scoped to a review item nobody reading GitHub can see. It is also ambiguous on its
face: `treeDataProvider.ts`'s own comments use "F19", "F21" and "F1" the same way, so the convention
is established in code comments, where it is at least reachable by someone with the board.

This is the residue the project's own rules are aimed at: delivered text describes the thing, not the
process that produced it, and ticket or finding ids do not appear in shipped artefacts. It survived
because it is four characters inside a 36-line paragraph.

The claim it decorates is separately wrong ("Both views" — see the three-view finding), so the
sentence needs editing anyway; the reference should go with it rather than be carried across.

Low severity: it misleads nobody about behaviour. Worth fixing because it is exactly the kind of thing
that becomes convention if it stays.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Dropped 'meta' terminology still in the extension README

<!-- sq:finding:F8:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
The extension README uses the terminology the project decided to drop.

Line 35–37: "A second, independent activity-bar view — **Roster** (`squadsMeta`,
`src/metaTreeDataProvider.ts`) — lists the **meta**/reserved items (roles, skills, operators) the work
tree deliberately excludes".

The project's standing decision is that "meta" is not the word: the category is **roster**, and the
term was purged from code, comments and docs (`is_meta` → `category`, `item_is_meta` →
`item_is_roster`, `META_*` → `ROSTER_*`). The root README follows it — its Concepts section names the
three categories as work / records / **roster**, with no occurrence of "meta".

So this is both a terminology regression and a small coherence break between the two documents: the
same set of three item types is "roster" in one file and "the meta/reserved items" in the other, which
reads to a newcomer as two different concepts.

The identifiers `squadsMeta` and `metaTreeDataProvider.ts` are real and pre-date the decision, so
*naming* them is legitimate — the defect is the prose word "meta" used as the category's name, not the
mention of the symbols. A fix should keep the symbol references and change the description around
them.

Low severity: nothing is factually wrong about behaviour. Recorded because the sentence is being
edited anyway for the view-count error, so the cost of fixing it is zero.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Neither README acknowledges its sibling documents

<!-- sq:finding:F9:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
Four documents now describe this product across two audiences, and neither README acknowledges the
other three exist.

The root README never mentions that a PyPI project description exists, or that the extension has a
Marketplace listing as a document. It does tell a reader to install the extension "from the VS Code
Marketplace (search *Squads*)", which is a store reference, not a signpost to a sibling document.
`clients/vscode/README.md` never says what it is, nor that `MARKETPLACE.md` is the published
description of the same extension — so a contributor editing feature prose there has no way to know
that the user-facing version lives next door and is the one shipped.

Under the dual-purpose framing, duplication across arrival paths is expected — the same pitch reaching
a reader from PyPI and from GitHub is intentional. What is not free is that a reader cannot tell which
document owns which audience, and an editor cannot tell which copy is authoritative. Both problems are
solved by naming siblings, not by deduplicating.

**The related and more durable half: which facts are safe to repeat.** Stable prose — what squads is,
why it exists, the concept vocabulary — can live in all four with no risk. What cannot are the facts
the tool itself can print, because they drift silently and nothing gates them:

- the install command and the Python floor;
- the status-lifecycle table (`sq workflow` prints the *active* spec, which may not be the bundled
  one at all);
- the ref-kind list (already wrong in the root README — filed separately);
- the command reference.

Each of those is now stated in up to four places. The fix is attribution rather than deletion: say
where the authoritative version comes from — `sq workflow`, `sq --help`, `sq docs` — so a reader
hitting a contradiction knows which side to trust, and the next editor knows what to re-verify
against. The root README already does this well in one place, noting that `sq workflow` "prints the
lifecycles of whatever spec your project is actually running"; that sentence is the model for the
rest.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-28T15:08:49Z] Olivia Lead:
  - Reviewed README.md and clients/vscode/README.md against the dual-purpose criterion (advert + contributor onboarding on the same page). Nine findings, one high. Every checkable claim verified against the code, the bundled spec or package.json — never against the other document; method and the verified-clean list are in the body.
  - Verdict: the root README's facts hold (the earlier ten-defect pass stuck) but it discharges half its purpose — contributor onboarding — with a single mid-sentence link, and its ordering buries the strongest advert material below a 65-line command reference while putting 30 lines of shell completion above the Quickstart. The extension README is the weak point: a 36-line single-paragraph feature inventory that is too internal to advertise and too shallow to onboard, and whose form is why a whole activity-bar view and the search QuickPick went missing from it.
  - Two cross-document notes: the root README correctly names three activity-bar trees while the extension README describes two (the doc closer to the code is the stale one), and the read/write boundary is consistent in both — 'Read-only, like sq ui' and 'Current state: read-only browse … a later increment' — so no drift there. Weighed the tech writer's three recommendations in the body: agree on the sibling-document pointer, reject the 'move contributor material forward' framing now the page owns two audiences (ordering, not promotion) with a concrete order proposed, agree on keeping the command reference but only on condition it gets verified against the tool — its ref-kind list is five of nine.
  - @tech-writer for the fixes; @manager F1/F3 are the pair worth acting on, and F3's fix subsumes F4/F6/F7/F8 if the paragraph is replaced rather than patched. Note for the record: content from the parallel listings review bled into my working files mid-pass and landed once in F1's body; caught, F1 rewritten from my own reading, and I confirmed no other finding was affected. The published listings stayed out of scope.
- [2026-07-29T07:33:43Z] Theo Writer:
  - F3 fixed by replacement, not patching, so F4/F6/F7/F8 close with it. The 36-line paragraph is gone; the file now opens with two short paragraphs (what the client is, and a pointer to MARKETPLACE.md as the owner of the user-facing feature description) and then becomes a contributor map: a Layers section splitting the host layer (a module/responsibility table, all three tree providers named) from the vscode-free domain layer grouped by concern, then seven numbered conventions — domain purity, pure CLI consumption, read-only, spec-driven vocabulary, strict CSP and no CDN, no squad-item ids, and the TypeScript pin.
  - Added what F3 listed as missing onboarding: a 'Running it in a dev host' block (compile first, --extensionDevelopmentPath, --disable-extensions, and the WSL caveat that the Linux binary misleads a visual check). The existing three test-layer sections are unchanged and were already correct.
  - F7 note worth keeping: the leaked id was 'F17' in the extension README, not the root README, and the local hygiene gate's pattern only matches full ids (ADR|FEAT|TASK|REV|BUG|EPIC-<digit>, US<digit>, ST<digit>) — a bare finding id like F17 is invisible to it. That is why a gate written to prevent exactly this defect did not catch it. Widening the pattern is a code change and out of scope here; flagging it for whoever owns that test.
  - F5 fixed in the root README: all nine kinds listed, plus a clause that blocks and depends-on are two spellings of one dependency edge (both feed sq blocked) and that supersedes is what sq check looks for on a superseded record. Verified against VALID_REF_KINDS. Adjacent to it, the sq blocked bullet said 'via the blocks ref kind' and now names both kinds — the service consumes them identically.
  - F9 half-done: the extension README now names MARKETPLACE.md as the sibling that owns feature copy. The root README still does not name PYPI.md or the extension README; left for the deferred ordering work. F1 and F2 untouched, as deferred.
- [2026-07-29T07:38:54Z] Theo Writer:
  - F9's cheap half taken, within the existing structure: the root README's link row now reads '… changes: CHANGELOG.md · working on the VS Code client: clients/vscode/README.md'. One clause, no reordering, and it points a contributor at the client's own map rather than just at the published listing. The root README still does not name PYPI.md — that one is inward-facing trivia for a repo browser, and naming it invites the 'which of these is canonical' question the ordering work should answer properly. F9 left Open for that reason.
  - Also corrected the dev-host instructions I added: --disable-extensions is no longer the default command. It disables Remote-WSL, so the host runs on Windows over the UNC share and a Linux sq in .venv/bin cannot execute — a discovery error rather than a working extension. The block now launches without the flag, with the WSL exception stated and the flag offered for other environments.
- [2026-07-29T08:37:26Z] Theo Writer:
  - F1, F2 and F9 fixed; all nine findings on this review are now closed.
  - F2 — new order: pitch / Install / Quickstart / Working with agents / Browsing the squad / Concepts / Documentation / Contributing / Command reference / Shell completion / Backends / Git notes. Two departures from the proposed order, both deliberate: Install stays above Quickstart (a quickstart that opens with sq init before the reader has the tool is the wrong first instruction), and 'Working with agents' goes directly after Quickstart rather than after Concepts — once a reader has seen the commands, the question is what the team does with them, not what the data model is. Shell completion, backends and git notes are last, in that order. Nothing was deleted and the command reference is intact.
  - F1 — split: README routes, CONTRIBUTING.md is the manual. The README's new Contributing section states that the repo holds two separately gated toolchains, gives both gate blocks (Python with --all-extras on every command, npm from clients/vscode/), says both must be green and sq check clean, points at internals.md and the client's own README for architecture, and lists the five conventions most likely to bounce a change. CONTRIBUTING.md gained the client's gate as a subsection, a tests/meta guard-tests subsection, the --all-extras warning with its symptom, and a two-toolchains framing in its opening. Deliberately not duplicated: the full convention list, the how-to-add-things recipes and the release runbook stay in CONTRIBUTING alone.
  - F9 — answered in the Documentation section: this README is the repo's front page, PYPI.md is the package's front page on PyPI, MARKETPLACE.md the extension's on the Marketplace. Same paragraph carries CONTRIBUTORS.md and CHANGELOG.md, so the old run-on link row is gone.
- [2026-07-29T08:37:27Z] Theo Writer:
  - Found while restructuring — the README's Quickstart was broken, and had been through every previous pass on this file. 'sq create feature "User authentication" --desc "Login & sessions"' fails with 'Missing option --author'; --author is required. It also used a literal 'sq task 11 …' that corresponds to nothing a reader would have. Both fixed and the block run end to end from a clean init: feature and task now pass --author, addressing uses the FEAT-<n> / TASK-<n> placeholder convention the listings adopted, and a following line explains the substitution and why every item has an author. The Team workflow snippets got the same treatment (--author on create, TASK-<n> addressing, --story US1 rather than the invalid 'USn').
  - Two stale instructions in CONTRIBUTING.md's 'How to add things', both pointing at things that no longer exist: 'add to ItemType (_models/_enums)' — that module is gone, types are declared in squads/_bundled/workflow.toml — and 'a PLAYBOOK entry in _interactions', which is now a [types.<name>] entry in squads/_bundled/playbook.toml. Both rewritten, with the note that the TOMLs are golden-locked and that a *project* adds types through .overrides/workflow.toml with no code change.
  - Two gaps flagged, not fixed, both outside this review's files. (1) The bundled TOMLs' own header comments point at 'tests/test_workflow_spec.py' and 'tests/test_playbook.py'; the golden-lock tests are now tests/unit/test_workflow_spec_artifact.py and tests/unit/test_playbook_spec_artifact.py. (2) tests/CONVENTIONS.md — which CONTRIBUTING.md now links, and should — opens with a status line citing two item ids and build-phase language; it sits outside both hygiene gates' scan roots, as do README.md, CONTRIBUTING.md and PYPI.md at the repo root. That is the same blind spot that let a bare finding id survive in the extension README.
<!-- sq:discussion:end -->

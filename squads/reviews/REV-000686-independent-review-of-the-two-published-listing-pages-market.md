---
id: REV-686
sequence_id: 686
type: review
title: Independent review of the two published-listing pages (MARKETPLACE.md, PYPI.md)
status: InReview
author: product-owner
subentities:
- local_id: F1
  title: 'Worked example fails as written: python-dev role does not exist after sq
    init --roles all'
  status: Fixed
  severity: high
- local_id: F2
  title: Marketplace page omits the pre-1.0/schema-instability disclosure PyPI states
  status: Open
  severity: medium
- local_id: F3
  title: PyPI page states its present-tense limits without the directional pairing
    the Marketplace page already has
  status: Fixed
  severity: medium
- local_id: F4
  title: Manifest positioning, audience split, and all checkable factual claims verified
    clean
  status: Open
  severity: low
created_at: '2026-07-28T15:06:17Z'
updated_at: '2026-07-29T07:33:41Z'
---
<!-- sq:body -->
Independent read of `clients/vscode/MARKETPLACE.md` (VS Code Marketplace listing) and `PYPI.md`
(PyPI project description), requested directly by Pierre because I set the manifest metadata
(TASK-683) but did not write or review either page's prose. Scope is assessment against audience
fit, cross-page coherence, and claim accuracy (verified against code/CLI, not trusted from the
prose) — not copy-editing. The two repo READMEs are the tech lead's review, out of scope here
except for one cross-cutting note.

Method: read both pages end to end, diffed the shared "problem it solves"/"the model" sections,
ran the worked example against a real `sq init --roles all` squad in scratch, and grepped the
VS Code extension source (`clients/vscode/src/`) and CLI (`src/squads/_cli/`) for every checkable
claim — command contributions, settings keys, discovery order, network calls, bundled deps,
`.squads.toml` detection, `sq docs`/`sq ui`/`sq dev` behaviour.

Findings below. Overall verdict and the single highest-value fix are recorded as a comment,
per Nina's brief to the coordinator.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 686 add-finding "…" --severity medium`; track with `sq review 686 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | Worked example fails as written: python-dev role does not exist after sq init --roles all |
| F2 | 🟡 medium | Open |  | Marketplace page omits the pre-1.0/schema-instability disclosure PyPI states |
| F3 | 🟡 medium | Fixed |  | PyPI page states its present-tense limits without the directional pairing the Marketplace page already has |
| F4 | 🟢 low | Open |  | Manifest positioning, audience split, and all checkable factual claims verified clean |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Worked example fails as written: python-dev role does not exist after sq init --roles all

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Both pages carry the identical "What using it looks like" worked example, and it does not run as
written against the "Getting started"/"Start a squad" steps that precede it on the same page.

Reproduced live: `sq init --roles all` (the exact command both pages tell the reader to run)
creates only the 8 fixed roles (`architect, devops, manager, product-owner, qa, reviewer,
tech-lead, tech-writer`) — no `python-dev`. The very next block in both pages runs
`sq feature 20 add-story "..." --assignee python-dev`, which fails with `error: unknown slug
'python-dev'; valid slugs: architect, devops, manager, product-owner, qa, reviewer, tech-lead,
tech-writer`. A stack-developer role only exists after a separate, unmentioned
`sq dev add --tech python`.

This is exactly the class of defect the brief warned about: a doc that reads perfectly well but
is verifiably wrong the moment someone runs it. It's not a divergence between the two pages —
it's the same bug on both, inherited from a shared source block — so it damages trust on both the
Marketplace and PyPI reader's first fifteen seconds of hands-on-keyboard trust in the project.

Fix is small and identical in both files: add a `sq dev add --tech python` line before the
`add-story --assignee python-dev` step (or switch the assignee to an existing role for the
example, e.g. `tech-lead`).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Marketplace page omits the pre-1.0/schema-instability disclosure PyPI states

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
`PYPI.md` has an explicit "Where it is" section: squads is pre-1.0, surfaces are still settling,
a release can change the on-disk schema, `sq migrate up` carries a squad forward, and a stability
contract spells out what holds after 1.0. `MARKETPLACE.md` never says any of this — I grepped the
whole 206 lines for "pre-1.0", "stability", "schema", "migrat" and got nothing.

The two pages describe the same product core (same "problem it solves" and "the model" sections,
near-verbatim). The Marketplace reader is deciding whether to point a VS Code extension at their
project's `squads/` folder — they are exactly as exposed to "this format is still moving" as the
PyPI reader, arguably more so: I checked the extension source and it has no schema-version
awareness of its own (no `schema_version` check anywhere in `clients/vscode/src/`) and no stated
minimum/compatible `sq` CLI version in the Requirements section. It just shells out to whatever
`sq` it finds and renders the output — so a mismatch between an old squad tree's schema and a
newer extension (or vice versa) has no documented story on the Marketplace page at all, where
PyPI at least points at `sq migrate up` and the stability contract.

This isn't an over-claim, it's a coherence gap under review-criterion 4: the same honesty
Pierre asked for on the PyPI page is simply missing from the Marketplace page. A one- or
two-line pointer — "squads is pre-1.0 and its on-disk format can change between releases;
`sq migrate up` keeps it current" plus a link to the stability contract — would close it without
bloating the page.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — PyPI page states its present-tense limits without the directional pairing the Marketplace page already has

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Per the coordinator's mid-review steer sharpening criterion 4: honesty about the present is the
floor, not the whole test — a page that states a limitation and stops can under-sell a young,
moving project as under-selling is dishonest in the other direction (reads as parked, not early).

MARKETPLACE.md already gets this right in one place: "You cannot create, edit, transition,
assign or comment from here. [...] Editing from the editor is a planned direction, not a shipped
feature." That's the correct shape — present tense stays exact ("cannot", not "not yet"), the
direction is named without a date or version ("a planned direction", not "coming in 0.13"), and
it sits right next to the limitation it qualifies, so a reader doesn't mistake "read-only" for
"read-only forever."

PYPI.md has no equivalent. Its two places that state the present-tense limit flatly, with no
directional pairing at all:
- "Two read-only clients exist for browsing a squad: `sq ui` [...] and a VS Code extension
  [...] Neither writes anything — every mutation goes through `sq`."
- The "Where it is" section (pre-1.0, schema can change, `sq migrate up`, stability contract)
  is entirely about surviving change, not moving toward anything — it's the "maturity" framing
  the coordinator flagged, with no complementary "and this is where it's headed."

I'm not recommending PyPI name specific unshipped features or release lines (0.13/0.14 are
internal roadmap, not a public commitment, and naming them would tip into the vapour risk the
coordinator warned against) — one clause in the same register as the Marketplace line is enough,
e.g. "read-only today" near the clients sentence, or a closing line on "Where it is" noting that
write access from a client is the direction this is heading, without a date. Right now the
asymmetry is real: the Marketplace page tells its reader this is early-and-moving, the PyPI page
only tells its reader this is early.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Manifest positioning, audience split, and all checkable factual claims verified clean

<!-- sq:finding:F4:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Recording the parts that verified clean rather than only the defects, per the brief's request not
to manufacture findings — these hold up:

- **Manifest alignment (criterion 5).** `clients/vscode/package.json`'s `description` is exactly
  the string decided in TASK-683 ("Browse your AI-agent team's work items, roster, and workflow in
  VS Code — read-only companion for squads-managed projects"), and both pages' prose is
  recognisably the same product with the same emphasis: read-only companion, work
  items/roster/workflow, VS Code. No drift between what I decided at the manifest layer and what
  the tech writer wrote at the prose layer.
- **Audience split (criteria 1 and 3) is the right call.** The Marketplace page's extra ~90
  lines earn their place for a VS Code reader (three sidebar views, the dossier panel, live
  refresh, search, view controls, `sqPath`/`command` troubleshooting) and PyPI's reader has no use
  for any of it — a terminal user deciding on a CLI doesn't need to know about a codicon-remap
  setting. Conversely PyPI keeps things the listing rightly drops for space (the tui `sq ui`
  client, the doc index, `sq migrate`) that a VS Code-only reader doesn't need either.
- **Every checkable factual claim on both pages verified true against the code/CLI**: the
  `squads.search` command and its "Search…" palette title, all `sq init --roles all` / `sq docs`
  / `sq ui` / `sq dev add` behaviour, the venv → uv → poetry → PATH discovery order in
  `discovery.ts`, `.squads.toml` walk-up detection, zero network calls anywhere in
  `clients/vscode/src/`, mermaid bundled as a real `dependencies` entry (not a CDN load), no
  write-capable commands contributed by the extension, and every doc link in PyPI's
  "Documentation" section resolving to a real file under `docs/`. Nothing else was stale or
  invented.
- **The shared "problem it solves"/"the model" sections are substantively identical** (diffed
  line by line) — wording varies but no fact or emphasis conflicts between the two, which is
  exactly what criterion 2 asked for.

Cross-cutting note for the tech lead's README review (not chased further here, out of my scope):
`README.md` links to the Marketplace listing for the extension and to `docs/adoption.md`, so it's
worth a quick check that neither README's description of the extension's read/write boundary has
drifted from the "read-only, planned direction for editing" framing settled here.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-28T15:08:16Z] Nina Product:
  - Verdict: not quite ship-as-is. Fix F1 (worked example fails as written — 2-line fix, same block on both pages) before this goes live; F2/F3 are worth a fast follow but wouldn't block a release on their own.
  - Highest-value single change: add 'sq dev add --tech python' before the add-story step in the shared worked example (F1) — it's the one thing a reader will actually type, and it's currently broken on both pages.
  - Direction steer addressed: MARKETPLACE's 'planned direction, not a shipped feature' line for editing is the right shape and stays as-is (F3 notes it as the model). PYPI's pre-1.0 framing states the present cleanly but has no equivalent forward clause — F3 recommends one clause, no specifics, no version numbers.
  - @tech-lead cross-cutting note in F4: worth a quick check that README.md's description of the extension's read/write boundary still matches 'read-only, planned direction for editing' while you're in there.
- [2026-07-29T07:33:41Z] Theo Writer:
  - F1 fixed on both pages, and the root cause was worse than a missing line: my verification run had 17 commands and the published block had 16 — I ran 'sq dev add --tech python' first to make python-dev real, then omitted it when writing the block. That single omission caused both symptoms, because dev add also consumes a counter slot: without it the roles/skills leave the counter at 18 and the first feature is FEAT-19, with it the feature is FEAT-20. The page showed the numbers from my run and the commands from a run that never happened.
  - Fix goes further than adding the line back: literal IDs are now gone. The block uses typed placeholders (FEAT-<n>, TASK-<n>, REV-<n>) with a lead-in saying sq create prints the ID to substitute. Full-ID addressing is a legal, type-checked form ('sq feature FEAT-20 add-story' works; 'sq task FEAT-20 show' is rejected), so the page shows real syntax and cannot drift when init's role/skill count changes or when a reader uses --roles core instead of all.
  - Verified twice from a clean 'sq init --roles all': once with substituted numbers, once with the page's exact full-ID form. All 17 commands succeed, including 'sq inbox reviewer' listing the task at the moment the example calls it.
  - F3 fixed: 'Neither writes anything today … Editing from a client is a planned direction, not a shipped feature' beside the clients sentence, and 'pre-1.0 and under active development' in the maturity section. Present tense stays exact, no dates, no version numbers.
  - F2 (Marketplace missing the pre-1.0/schema disclosure) is NOT fixed — it fell between the coordinator's fix list and defer list, so I left the published page alone rather than adding unrequested copy to it. @op-pierre @manager it is a two-line addition when someone wants it. F4 left Open as an informational record.
<!-- sq:discussion:end -->

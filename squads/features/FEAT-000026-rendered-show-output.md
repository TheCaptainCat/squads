---
id: FEAT-000026
sequence_id: 26
type: feature
title: Rendered show output
status: Done
parent: EPIC-000038
author: product-owner
priority: high
refs:
- FEAT-000019:depends-on
- BUG-000025:depends-on
description: sq show renders body and discussion as styled markdown on a TTY (headings,
  bullets, code), with --raw opt-out, NO_COLOR respected, and plain output when piped
subentities:
- local_id: US1
  title: As an operator reading the backlog in my terminal, I want show to render
    the markdown, so that sq tree + sq show covers browsing and reading without external
    viewers
  status: Done
- local_id: US2
  title: As an agent or script consuming show output, I want piped/--raw/NO_COLOR
    output plain and stable, so that rendering never breaks my parsing
  status: Done
- local_id: US3
  title: As a user with an ID or number in hand, I want a root sq show command that
    displays any item regardless of type, so that I can read anything in one step
    without naming its type
  status: Done
- local_id: US4
  title: As a reader of a feature, task or review, I want show to include the sub-entity
    summary table and the discussion, so that one command gives me the whole item,
    not just its body
  status: Done
- local_id: US5
  title: As a reader wanting the whole story, I want --full to render each sub-entity
    and its comments in tidy panes along with the main discussion, so that one command
    reads as the item's dossier
  status: Done
- local_id: US6
  title: As an agent briefing on an item, I want the squads skill and the sq-<type>
    skills to teach reading with --full --comments as the standard briefing move,
    so that decisions captured in discussion comments are never missed
  status: Done
created_at: '2026-06-10T14:57:23Z'
updated_at: '2026-06-12T09:43:53Z'
---
<!-- sq:body -->
## Problem

`sq <type> <n> show` is the team's reading surface, but it's both **plain and incomplete**: it
prints the metadata panel and the raw body — `##` and `**` verbatim, no color beyond the panel —
and then stops. The sub-entity summary table (user stories, subtasks, findings) and the discussion
never appear at all (verified 2026-06-11): reading a whole item takes `show` plus `stories` plus
opening the file. Operators fall back to external viewers (VSCode preview, glow), which lose the
live sq state and the tree context. Reading is also one step harder than it should be: you must
name the type to show an item, even though the ID (or the globally-unique number) already
identifies it.

Beyond the rendering gap, there is a guidance gap: agents briefing on an item tend to run plain
`show`, which omits the discussion entirely. Decisions recorded only in discussion comments are
then silently missed — FEAT-000026's own flag semantics (decided in op-pierre's 2026-06-11
comments) are a concrete instance of this failure. The onboarding texts (the `squads` skill, the
per-type `sq-<type>` skills) must teach reading with `--full --comments` as the standard briefing
move.

## Value

`sq tree` already navigates the hierarchy; a complete, rendered `show` finishes the loop — one
tool to browse *and* read, from a quick brief to the item's full dossier, chosen by two composable
flags. A root `sq show <id|number>` makes the loop frictionless: copy anything from the tree, show
it, no type required. The renderer is already in the dependency tree (rich powers the panels), so
this is wiring, not a new stack.

Once `--full` and `--comments` exist, the skills that teach `show` must be updated to recommend
them — closing both the rendering gap and the guidance gap in one feature.

## Scope

- **Two composable axes** (decided with op-pierre, 2026-06-11): **`--full` widens the scope**
  (item alone → item + its sub-entities); **`--comments` adds the discussion facet to whatever is
  in scope**. The matrix:

  | flags | output |
  |---|---|
  | *(none)* | panel + rendered body + compact sub-entity summary table |
  | `--comments` | … + the item's discussion (main comments only — subs aren't in scope) |
  | `--full` | … + one pane per sub-entity (badge line + rendered body, no comments) |
  | `--full --comments` | … + sub-entity panes each embedding their own comments, then the main discussion |

- **Pretty panes**: comments and sub-entities render as rich Panels — a comment pane titled with
  author + timestamp, a sub-entity pane titled with its local id + title + badges; rendered
  markdown inside. Easy to read at a glance, never a wall of text.
- `--raw` to opt out (exact file text, today's behaviour); **auto-plain when piped** and full
  respect for `NO_COLOR` — panes degrade to plain delimited text; `--json` always carries the
  complete item (sub-entities, discussions) regardless of flags — flags are presentation-only,
  the machine surface stays FEAT-000015's domain.
- A root **`sq show <id|number>`** displaying any work item regardless of type — same output and
  flags as `sq <type> <n> show`, resolution per FEAT-000019's shared resolver (bare numbers are
  unambiguous thanks to the global counter, and with no type named there is no mismatch to
  police).
- Sensible width handling (don't hard-wrap inside code blocks).
- Out of scope: themes/configurable palettes — rich's defaults first; a `.squads.toml` knob only
  if someone actually asks.
- **Agent-facing onboarding guidance** (US6): once `--full` and `--comments` are implemented, the
  generated `squads` skill and every per-type `sq-<type>` skill must update their reading guidance
  to recommend `show --full --comments` as the default briefing move. The **Enter** / "before you
  act" section of each per-type skill is the primary target. Any other generated text that teaches
  `sq <type> <n> show` (workflow docs, role onboarding) must follow. The requirement is
  replayable: an agent following only the generated skills must automatically read the full
  dossier, including decisions captured only in discussion comments.

## Acceptance

- The four-cell matrix above behaves exactly as specified; the axes stay composable if scope ever
  grows further (the rule is "comments follow scope", not a hard-coded flag pairing).
- On a TTY it's styled markdown and panels; piped/`--raw`/`NO_COLOR` output is plain and
  byte-stable.
- `sq show FEAT-000013` and `sq show 13` work for every work-item type; unknown ids error cleanly.
- `--json` includes the full item (sub-entities, discussions) independent of flags, and is stable.
- BUG-000025's redundant `Body` label is gone (folded in or fixed first — linked).
- Existing CLI tests pass unmodified except those asserting raw body output, which switch to
  `--raw` or piped mode.
- The generated `squads` skill and all per-type `sq-<type>` skills teach reading with
  `--full --comments` as the standard briefing move; an agent following only the skills reads the
  full dossier without needing out-of-band knowledge of the flags (US6).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 26 add-story "As a <role>, I want … so that …"`; track with `sq feature 26 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | As an operator reading the backlog in my terminal, I want show to render the markdown, so that sq tree + sq show covers browsing and reading without external viewers |
| US2 | Done |  | As an agent or script consuming show output, I want piped/--raw/NO_COLOR output plain and stable, so that rendering never breaks my parsing |
| US3 | Done |  | As a user with an ID or number in hand, I want a root sq show command that displays any item regardless of type, so that I can read anything in one step without naming its type |
| US4 | Done |  | As a reader of a feature, task or review, I want show to include the sub-entity summary table and the discussion, so that one command gives me the whole item, not just its body |
| US5 | Done |  | As a reader wanting the whole story, I want --full to render each sub-entity and its comments in tidy panes along with the main discussion, so that one command reads as the item's dossier |
| US6 | Done |  | As an agent briefing on an item, I want the squads skill and the sq-<type> skills to teach reading with --full --comments as the standard briefing move, so that decisions captured in discussion comments are never missed |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator reading the backlog in my terminal, I want show to render the markdown, so that sq tree + sq show covers browsing and reading without external viewers

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** headings, bold, bullets and code blocks display styled on a TTY for body, sub-entity prose and discussion; no redundant viewer-injected labels.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an agent or script consuming show output, I want piped/--raw/NO_COLOR output plain and stable, so that rendering never breaks my parsing

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** when piped, with --raw, or with NO_COLOR set, output is unstyled and byte-stable; --json byte-identical to pre-change.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a user with an ID or number in hand, I want a root sq show command that displays any item regardless of type, so that I can read anything in one step without naming its type

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** `sq show FEAT-000013` and `sq show 13` both work for every work-item type, with the same rendered output as `sq <type> <n> show`; unknown id/number errors cleanly. Resolution follows FEAT-000019's shared-resolver rules (bare numbers are unambiguous via the global counter; no type to mismatch since none is named).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As a reader of a feature, task or review, I want show to include the sub-entity summary table and the discussion, so that one command gives me the whole item, not just its body

<!-- sq:story:US4:head -->
**Status:** 🟢 Done
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
**Acceptance:** default `show` = panel + rendered body + compact summary table; `--comments` alone adds the item's main discussion only (one pretty pane per comment, author + timestamp as title) — sub-entity comments stay out because subs aren't in scope. Today show stops at the body (verified 2026-06-11).
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As a reader wanting the whole story, I want --full to render each sub-entity and its comments in tidy panes along with the main discussion, so that one command reads as the item's dossier

<!-- sq:story:US5:head -->
**Status:** 🟢 Done
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
**Acceptance:** `--full` alone adds one pane per sub-entity (local id + title + badges as pane title, rendered body, no comments); `--full --comments` embeds each sub-entity's comments in its pane and closes with the main discussion. Rule: comments follow scope. Panes degrade to plain text when piped/NO_COLOR; --json unaffected by flags.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — As an agent briefing on an item, I want the squads skill and the sq-<type> skills to teach reading with --full --comments as the standard briefing move, so that decisions captured in discussion comments are never missed

<!-- sq:story:US6:head -->
**Status:** 🟢 Done
<!-- sq:story:US6:head:end -->

<!-- sq:story:US6:body -->
**Acceptance criteria:**

- The generated `squads` skill's reading guidance explicitly recommends `sq <type> <n> show --full --comments` (or equivalent flags) when briefing on an item, not just plain `show`.

- Every per-type `sq-<type>` skill's **Enter** section (the 'before you act' checklist) includes reading the item with `--full --comments` so discussion is never silently skipped.

- Any other generated text that teaches `sq <type> <n> show` (e.g. workflow docs, role onboarding) likewise surfaces the flags.

- Replayable: an agent that follows only the generated skills will automatically read the full dossier — including decisions captured exclusively in discussion comments — without needing to know about the flags from other context.

- The guidance is present in the generated output of `sq sync` / `sq backend sync`, not just in handwritten notes.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T07:34:02Z] Pierre Chat:
  - show must display the sub-entity summary table (stories/subtasks/findings) and not stop at the body — requested while reviewing the backlog.
- [2026-06-11T08:51:17Z] Pierre Chat:
  - Spec refinement: tiered show — default stays lean (panel + body + summary table); --comments adds the discussion in per-comment panes; --full is the dossier (each sub-entity pane with its own comments, plus main discussion). Panes must be pretty and easy to read.
- [2026-06-11T08:54:53Z] Pierre Chat:
  - Correction: --full does NOT imply --comments. The flags are orthogonal — --full adds only the sub-entity prose panes; --comments adds all comments (main + sub-entity, wherever they belong); combined they make the dossier.
- [2026-06-11T08:56:44Z] Pierre Chat:
  - Final flag semantics: --full widens scope (item → item + sub-entities); --comments adds the discussion facet to whatever is in scope. Hence: --comments = main comments only; --full = sub prose only; together = subs with their comments + main comments. Comments follow scope.
- [2026-06-12T08:54:13Z] Pierre Chat:
  - Real incident, happened right now: I asked an agent to brief on this feature and it read only the body — completely missing the flag semantics I'd recorded in the discussion comments on 2026-06-11. The agent had no idea --full and --comments were orthogonal because that decision lived only in the comments it never read.
  - Once these flags exist, the docs need to teach reading with --full --comments as the normal briefing move, not an optional extra. Every sq-<type> skill's Enter section should say: run show --full --comments. An agent that follows only the skills should automatically get the full dossier. This is not a nice-to-have — it is what closes the incident class.
- [2026-06-12T08:54:27Z] Nina Product:
  - @tech-lead — FEAT-000026 is greenlit for immediate implementation (priority: high, status: Ready). Six user stories are defined (US1–US6); US6 is the new one added today: once --full and --comments are implemented, update the generated squads skill and every sq-<type> skill's Enter section to teach reading with --full --comments as the standard briefing move.
  - Read this feature with --full --comments once the flags exist to verify US6 (and to model the behaviour the feature itself mandates). The flag semantics — orthogonal axes, comments follow scope — are in the 2026-06-11 discussion comments. Pierre has greenlit starting immediately.
- [2026-06-12T09:00:06Z] Olivia Lead:
  - @python-dev FEAT-000026 broken down into three Ready tasks (all high, assigned to you). Build in order — they share the render path.
  - TASK-000058 (US1/US2/US3/US4): render core — body as styled markdown on a TTY, the --comments facet (main discussion as per-comment panes), --raw opt-out, auto-plain when piped / NO_COLOR (byte-stable), --json untouched, plus the root 'sq show <id|number>' for any type. Default scope only. Add the inverse-of-format_comment splitter in _discussion.py. Anchors: _cli/_common.py print_item, _cli/_items.py _cmd_show, _cli/_main.py (model on tree/blocked), _sections.get_section + markers.DISCUSSION.
  - TASK-000059 (US5): the dossier — --full adds one pane per sub-entity (local id + title + badges as title, rendered body, NO comments); --full --comments embeds each sub's own comments then closes with the main discussion. Rule: comments follow scope. Extend 058's render entry point, do not fork it. SubentityDetail from _services/_subentities.py already gives per-sub body+discussion.
  - TASK-000060 (US6): docs sweep, gated behind 058+059. The Enter checklists are DATA-DRIVEN — edit the enter tuples in _interactions.py, not the generated .md. Then squads_skill.md.j2 + item_skill.md.j2 footer + workflow.md.j2. Must show up in 'sq sync' output, not just notes.
  - Deps FEAT-000019 (resolver) and BUG-000025 (Body label) are both Done — no blockers. Honour the four-cell matrix and 'comments follow scope' exactly; the semantics live in the 2026-06-11 discussion comments on this feature — read them with the very flags you're building. Don't hand-edit .md under squads/.
- [2026-06-12T09:15:37Z] Elias Python:
  - TASK-000058 complete. Render core is live — all gates green (319 passed, pyright + ruff clean).
  - What was built: (1) split_discussion() in _discussion.py — inverse of format_comment, parses the discussion region into Comment(timestamp, author, body) objects; handles multi-line messages, continuation lines, fenced code blocks with internal blank lines. (2) read_discussion() on Service (in _services/_items.py) — reads the sq:discussion region, symmetric to read_body(). (3) print_item() in _cli/_common.py refactored into _build_item_panel_rows / _print_item_content / _print_discussion helpers; accepts raw=bool and comments=bool kwargs. (4) _is_styled() — detects TTY + color; body goes through rich.markdown.Markdown when styled, plain markup=False when not. (5) _print_subentity_summary() — sub-entity summary table always shown in default output, driven from item.subentities (no re-parse). (6) --raw and --comments flags wired onto sq TYPE N show in _cli/_items.py. (7) Root sq show command in _cli/_main.py (name='show') using resolve_item_id_any — full ID or bare number, same flags.
  - For TASK-000059 (dossier / --full): the render entry point is print_item() in _cli/_common.py. The --full flag should call _print_full_panes(svc, it, styled=styled, comments=comments) from _print_item_content, which you add alongside the existing helpers. SubentityDetail from svc.get_story/subtask/finding gives per-sub body+discussion. The comment-follows-scope rule: if comments is True and full is True, render each sub's discussion inside its pane; main discussion renders last. The _render_comments_styled/_plain helpers are reusable. _SUBENTITY_KIND maps item type to sub kind. Do NOT change _cmd_show signature — just add the full: bool kwarg to print_item and thread it through.
- [2026-06-12T09:22:42Z] Elias Python:
  - TASK-000058 and TASK-000059 are both Done. The rendered show layer is fully implemented.
  - TASK-000058 delivered: styled Markdown body on a TTY, plain-text degradation when piped/NO_COLOR/--raw, a sub-entity summary table always included in default output, and --comments rendering the main discussion as per-comment panes (styled Panels or plain delimited blocks). Root sq show resolves any item by full ID or bare number.
  - TASK-000059 delivered (this task): --full adds one pane per sub-entity after the summary table. Each pane title carries the local id, the title, and status/severity/assignee/story badges (all escaped through e() before going into Rich markup context). Body content goes through Markdown() on a TTY. --full --comments embeds each sub-entity's own comments inside its pane (as nested Panels / plain delimiter blocks) and then renders the main discussion last, so the ordering rule 'comments follow scope' is honored. Items with no sub-entities degrade to exit-0 with no extra output. --json is unaffected by both flags.
  - New helpers in _common.py: _subentity_pane_title(), _status_badge_for_pane(), _print_full_panes(). The _print_item_content() signature gained full: bool=False; print_item() gained full: bool=False. Both sq <type> <n> show and root sq show accept --full.
  - TASK-000060 (docs sweep) is next. The docs task should cover: updating the squads skill and all sq-<type> skills to recommend 'show --full --comments' as the standard briefing move; updating the Enter/before-you-act section of each per-type skill; updating the workflow cheatsheet if it references show. The four-cell matrix from the feature acceptance criteria is the authoritative spec to teach. No onboarding text has been updated yet — that is entirely within TASK-000060's scope.
- [2026-06-12T09:27:35Z] Elias Python:
  - FEAT-000026 fully implemented. All six user stories Done. Handing to @reviewer for code review.
  - TASK-000058 (US1/US2/US3/US4 — render core): styled Markdown body on a TTY, sub-entity summary table always included in default output, --comments renders the main discussion as per-comment panes (styled Panels on TTY, plain delimiter blocks when piped/NO_COLOR/--raw), --raw opt-out, auto-plain when piped, root 'sq show ID|number' resolves any item type.
  - TASK-000059 (US5 — dossier): --full adds one pane per sub-entity after the summary table (id+title+badges as title, rendered body). --full --comments embeds each sub-entity's own comments inside its pane then renders main discussion last. Rule 'comments follow scope' honored. --json unaffected.
  - TASK-000060 (US6 — docs sweep): item_skill.md.j2 injects a universal first Enter bullet in every role section of every sq-type skill: 'Read the full item dossier: sq type n show --full --comments'. squads_skill.md.j2 updated at three locations (Golden rules, Anchor-to-an-item, Common commands). workflow.md.j2 and claude_section.md.j2 likewise updated. sq sync regenerated all files. Two new tests in test_skills.py assert the guidance is present in the squads skill and all per-type skills.
  - Gates: 333 tests passed, 1 skipped; pyright 0 errors; ruff clean.
- [2026-06-12T09:33:46Z] Paul Reviewer:
  - Code review done (REV-000061): ChangesRequested. The implementation is strong — styled rendering quality is excellent, the four-cell flag matrix is exact, split_discussion is a faithful inverse of format_comment, --json is flag-independent, root sq show works, and the US6 docs sweep regenerates cleanly (sq sync idempotent). All gates green: 333 passed, pyright + ruff clean.
  - One behavioural blocker (F1, medium): in the PLAIN path (piped / NO_COLOR / --raw), sub-entity pane titles leak Rich-escape backslashes for bracket-bearing titles — e.g. a subtask titled with [red]x[/red] renders as backslash-red in the delimiter line instead of the literal brackets. Styled output is correct; this violates the byte-stable-plain acceptance criterion. Two low nits also logged (badge/column duplication; missing plain-path bracket-fidelity test).
  - Not blocking the verdict but noted: under NO_COLOR on a TTY the metadata panel + summary table keep bold ANSI (color is stripped, bold attribute survives — standard Rich NO_COLOR semantics; the panel is pre-existing). The piped path is fully color-free, so scripting fidelity holds.
  - @python-dev see REV-000061 for repro and fix guidance on F1.
- [2026-06-12T09:43:25Z] Paul Reviewer:
  - Code review REV-000061 is APPROVED. The re-review confirmed all three findings fixed (F1 plain-output escaping leak, F2 badge/column duplication, F3 plain-path bracket-fidelity test gap), gates green (336 passed, 1 skipped; pyright + ruff clean), four-cell flag matrix correct, --json flag-independent.
  - @tech-lead FEAT-000026 implementation passes review. Ready to mark Done / proceed to merge per the team workflow.
- [2026-06-12T09:43:53Z] Catherine Manager:
  - Closing the loop: TASK-000058/059/060 Done, REV-000061 Approved after one fix round (plain-output escaping), all six stories Done. Feature complete; uncommitted in the working tree pending op-pierre's commit call.
<!-- sq:discussion:end -->

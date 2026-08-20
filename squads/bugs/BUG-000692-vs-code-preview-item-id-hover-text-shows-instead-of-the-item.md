---
id: BUG-692
sequence_id: 692
type: bug
title: 'VS Code preview: item-id hover text shows "#" instead of the item'
status: Verified
author: op-pierre
description: Only role mentions carry a title; every item-id anchor falls back to
  its href
created_at: '2026-07-29T13:24:21Z'
updated_at: '2026-08-20T18:40:27Z'
---
<!-- sq:body -->
In the VS Code extension's item preview, hovering any item-id reference in the rendered
prose shows `#` instead of useful text about the item. Role mentions (`@manager`,
`@tech-lead`) are the only tokens that hover correctly.

## Observed

Open any item's preview panel. Its body/discussion links every item id it mentions
(`TASK-688`, `FEAT-321`, …) as a navigable anchor. Hovering one shows the tooltip `#`.
Hovering an `@<slug>` role mention in the same prose shows the role's name, slug and mission.

## Cause

`domain/markdown.ts` builds two anchor shapes and only one carries a `title` attribute:

- `@<slug>` mentions render as `<a class="sq-item-link" href="#" data-item-id="…"
  title="…">`, the title coming from `domain/roleDirectory.ts`'s `hoverTextFor`.
- Plain item-id tokens and markdown-link-syntax references render the same anchor **without**
  a `title`.

An anchor with no `title` falls back to displaying its href, and every one of these anchors
uses `href="#"` (navigation is intercepted from `data-item-id`, so the href is only a
placeholder). Hence the literal `#` on every item reference, and hover text working for
roles alone.

## Why the fix is more than an attribute

A useful tooltip needs the referenced item's title — `TASK-688 — VS Code: narrow the roster
view by status` — and the preview never fetches titles for the ids it links. It renders from
a fixed set of parallel `sq` calls — dossier, tree, graph, `show --json`, the roster list, the
type catalog and the sub-entity-kind catalog — none of which covers arbitrary ids mentioned in
prose.

The roster path is the precedent to copy: one batched `sq list -t role --json` per render,
turned into a slug→mention map. An id→title directory built from a single batched list call
keeps the cost at one extra call per render. Resolving each link with its own `sq show`
would make render cost scale with how many ids the prose happens to mention, which is the
shape to avoid.

## Acceptance criteria

- Hovering an item-id reference in a preview shows text identifying that item (at minimum
  its id and title), not `#`.
- Hover text works for the markdown-link form as well as bare item-id tokens.
- Role mentions keep the hover text they already have.
- Per-render `sq` call count stays independent of how many item references the prose
  contains.
- An id that cannot be resolved (unknown, or a failed fetch) degrades quietly: the link
  still navigates, with no tooltip and no broken preview — the same graceful degrade an
  unresolvable role mention already gets.
- A reference to the item already open in the panel keeps rendering as plain text, as it
  does today.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T13:24:26Z] Pierre Chat:
  - Scheduled for 0.13.
- [2026-07-29T14:29:07Z] Pierre Chat:
  - Correction: this lands in 0.14, not 0.13 — 0.13 keeps its planned scope.
- [2026-07-29T14:31:14Z] Catherine Manager:
  - Record correction: the 0.13 -> 0.14 note above was mine in error. The operator's call stands — this bug is 0.13; the 0.14 move applies to the two commissioned decisions, not here.
- [2026-08-15T13:11:45Z] Ada Typescript:
  - Fixed. domain/itemDirectory.ts (new) maps id -> "ID — Title" from one batched sq list --json --all, itemPreviewManager threads it alongside the role directory, and domain/markdown.ts stamps title="…" on an item anchor through one shared helper used by BOTH anchor shapes — the bare id token found in prose and the markdown link whose url is an id — so the two cannot drift into one hovering and the other not.
  - Every acceptance criterion is pinned by a test: an unresolved id keeps its link and gets no title attribute at all (never a fabricated one), no directory at all degrades the same way, a self-reference still renders as plain text, role mentions keep their own hover text, and the title is HTML-escaped. Per-render sq call count is fixed at eight and independent of how many ids the prose cites — two list fetches on purpose, the roster one keeping the default view (an archived role is not a mention target) and the id directory passing --all because prose overwhelmingly cites settled work.
  - Driven against real payloads, not fixtures: this repo TASK-737 dossier rendered through the production builders yields 6 item anchors, 6 titled, none untitled, with an apostrophe in one title correctly escaped. Falsified four ways — dropping the title (11 red), titling only the prose shape (1 red, the link case), removing the escaping (1 red), keeping blank-titled rows (1 red) — each reddening exactly the intended test and green on restore.
  - Body corrected for one stale detail, per the routing brief: it described the preview as rendering from five parallel sq calls. That inventory had already moved to seven before this bug was picked up. The rest of the report read true and is unchanged, and nothing about status was written into it.
  - Worth an operator look, since I do not run a dev host: the markup change is verified (anchors now carry the right title text) but how VS Code paints a tooltip is host behaviour I cannot exercise. @op-pierre hovering an id in a preview should now read e.g. "REV-736 — Bundled-assumption sweep across src and clients". Gates: typecheck, lint, format all clean; 606 unit tests in 32 files; 19 canary tests against live sq. Not committed.
- [2026-08-15T13:13:13Z] Catherine Manager:
  - One thing stays owed to op-pierre before this moves to Verified: the typescript-dev could not confirm that the no-title fallback painted literally "#", because that is host rendering behaviour and she correctly declined to launch a dev host. The fix does not depend on it -- an anchor carrying real text has nothing to fall back to -- but the visual confirmation is the operators, and it is the same dev-host check TASK-730 needed. Parking at Fixed rather than moving it myself.
- [2026-08-15T19:55:26Z] Catherine Manager:
  - Left at Fixed deliberately, not Verified. The fix is verified where it can be: markdown.test.ts passes 78/78 covering both anchor shapes, and the developer drove this repo TASK-737 dossier through the production builders getting 6 item anchors, 6 titled, 0 untitled. What remains unverified is the original symptom -- that the no-title fallback paints literally "#" -- which is host rendering behaviour and needs the dev host. That is op-pierre check, alongside TASK-730.
- [2026-08-20T18:40:26Z] Pierre Chat:
  - Checked in the dev host. The hover shows the item id and title. Good.
<!-- sq:discussion:end -->

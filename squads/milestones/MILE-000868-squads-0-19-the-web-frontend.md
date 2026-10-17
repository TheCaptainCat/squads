---
id: MILE-868
sequence_id: 868
type: milestone
title: squads 0.19 - the web frontend
status: Draft
author: product-owner
refs:
- EPIC-29
- MILE-1051:depends-on
created_at: '2026-09-02T08:03:39Z'
updated_at: '2026-10-16T13:39:47Z'
---
<!-- sq:body -->
A squad readable in a browser: the squad's state stops being visible only to whoever is sitting at the terminal. This milestone holds the work that brings the browser surface to a first usable state. The linked epic carries the outcome and the framing. The surface is built on the local API and daemon of the daemon milestone, which it depends on.

**Belongs here**

- The browser frontend: pages rendered server-side from Jinja templates, so they are indexable and readable without scripting, with Vue 3 adding the interactivity.
- The browse surface itself: tree, item, refs, discussion.
- Whatever the frontend needs from the shared addressing layer to present those views.

**Does not belong here**

- The local API, the CLI's remote and local modes, and the daemon logic. They live in the daemon milestone, and this milestone consumes them.
- Write paths from the browser. Mutation reachable from a shared URL raises actor, auth and concurrency questions this milestone does not answer; it takes its own decision first, and that decision is not part of the target. (Writes through the local daemon for the CLI are a separate matter and belong to the daemon milestone.)
- The other browse clients. The terminal UI and the editor extension have their own homes; only work whose reason for existing is the web surface aims here.
- Engine or vocabulary changes the web view merely consumes.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T08:04:47Z] Nina Product:
  - Linked to the sq web epic with a plain related ref, not membership: the roll-up inverts incoming targets refs only, so the shell stays empty while the epic's outcome and framing stay one hop away instead of being restated here and drifting.
- [2026-10-16T11:22:52Z] Pierre Chat:
  - 2026-10-16: split this milestone. A new milestone, squads 0.17, is the daemon release: the API (serves and listens on localhost, no authentication), the CLI's remote and local modes, and the daemon logic. This milestone keeps only the browser frontend and builds on 0.17. Transport (HTTP port vs Unix socket) is undecided and goes to an ADR.
- [2026-10-16T11:51:38Z] Pierre Chat:
  - 2026-10-16: this milestone becomes squads 0.18 (the web frontend), after 0.17 (MILE-1051, the daemon).
- [2026-10-16T13:39:35Z] Pierre Chat:
  - 2026-10-16: renumbered to 0.19; the backends release takes 0.18 because supported backends take priority over the web frontend.
<!-- sq:discussion:end -->

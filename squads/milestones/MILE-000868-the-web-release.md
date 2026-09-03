---
id: MILE-868
sequence_id: 868
type: milestone
title: The web release
status: Draft
author: product-owner
refs:
- EPIC-29
created_at: '2026-09-02T08:03:39Z'
updated_at: '2026-09-02T08:04:47Z'
---
<!-- sq:body -->
A squad readable in a browser: `sq` serves a local web view, and the squad's
state stops being visible only to whoever is sitting at the terminal. This
milestone holds the work that brings that surface to a first usable state. The
linked epic carries the outcome and the framing.

**Belongs here**

- The server command and its skeleton, shipped as an optional extra so the core
  install stays lean.
- The browse surface itself — tree, item, refs, discussion.
- Movement in the read API and the shared addressing layer, insofar as serving
  those views requires it.

**Does not belong here**

- Write paths. Mutation reachable from a shared URL raises actor, auth and
  concurrency questions this milestone does not answer; it takes its own decision
  first, and that decision is not part of the target.
- The other browse clients. The terminal UI and the editor extension have their
  own homes; only work whose reason for existing is the web surface aims here.
- Engine or vocabulary changes the web view merely consumes.

This milestone deliberately carries no version number. It is defined by the
surface it delivers, not by a slot in the release sequence.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T08:04:47Z] Nina Product:
  - Linked to the sq web epic with a plain related ref, not membership: the roll-up inverts incoming targets refs only, so the shell stays empty while the epic's outcome and framing stay one hop away instead of being restated here and drifting.
<!-- sq:discussion:end -->

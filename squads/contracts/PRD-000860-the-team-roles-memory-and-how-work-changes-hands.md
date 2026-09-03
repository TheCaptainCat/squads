---
id: PRD-860
sequence_id: 860
type: contract
title: 'The team: roles, memory, and how work changes hands'
status: Draft
author: product-owner
refs:
- PRD-862
- PRD-859
- PRD-861
description: 'The team as a product: roles, operators, compiled skills, per-role memory,
  the board, and the handoff protocol.'
created_at: '2026-09-01T13:02:19Z'
updated_at: '2026-09-01T13:09:42Z'
---
<!-- sq:body -->
## What the product does

A squad is a named team. Every role in it is a real, addressable thing with a definition, a
place in the workflow, its own knowledge, and its own queue — not a label on a ticket. The
product's job is to make a team of agents behave like a team: everyone knows who they are, what
they are meant to touch, what they have learned, what is waiting for them, and how to hand
something on so the next one can pick it up cold.

### Roles

A squad starts with a catalog of defined roles — a coordinator, an architect, a tech lead, a
reviewer, a QA engineer, a DevOps engineer, a product owner and a technical writer — each with a
full name, a title, a mission, responsibilities and working agreements. Activating a role makes
it a tracked entity in the corpus with its own identity, so it can author, be assigned, be
mentioned, and be listed alongside the work.

A project is not held to that catalog. Any bundled role can be renamed, re-missioned or moved to
a different model a field at a time, and an entirely new role can be defined from a scaffold and
activated into the roster. Two listings stay distinct on purpose: the catalog a squad could draw
from, and the roster it actually has live.

Developer roles are created on demand rather than enumerated in advance: a squad asks for a
developer in a technology and gets one, named, with the right guidance attached. That is what
lets the same product serve a Python project and a TypeScript project without either carrying
the other's roles.

A role's capability boundary is part of its definition. Whether a role may orchestrate other
agents is declared on the role, and it is that declaration — not an instruction in prose — that
the generated agent-tool configuration carries as a hard constraint.

### Operators

The humans on a project are registered too, and are first-class in the same way: they can author
items, author comments, and be assigned work, including manual steps no agent can perform. They
are deliberately not roles — nothing spawns them — and they are addressed by their own kind of
slug so that "a person did this" and "an agent did this" never blur in the record. An operator
who leaves is archived rather than erased, so their authorship stays intact.

### Skills

A skill is a document a role reads before acting. Some are general — how to work in a squad at
all, how to open a session with a human, how to keep a notebook. The rest are per item type, and
they are compiled: for each kind of work, the product assembles the type's lifecycle, its
commands, and a section per role saying what that role should check before acting, what to do,
what to hand off, and what to watch for. Change which roles touch a type, or what one of them is
told, and the document is rebuilt.

Because they are compiled rather than hand-maintained, a role's skill list is derived: a role
that gains a stake in a type gains that type's document automatically, in its own definition and
in whatever the host agent tool is configured with. A skill whose type stops existing is
withdrawn and reported until it is closed out.

### Memory

Each role has its own committed notebook: short facts it has learned, each with a one-line
summary, a slug, and as much body as it needs. A role lists its index at the start of a run,
searches it, opens what is relevant, adds to it when it learns something, and deletes what has
gone stale. The notebook is stored in the squad folder like everything else, so it is reviewable,
diffable and versioned with the project — this is not hidden state.

Memory is per role and durable. The bulletin board is the other half: notices posted to the whole
team, optionally with an expiry, visible until they are taken down or lapse. One is what a role
knows; the other is what everyone needs to be told right now.

### How work changes hands

Handoff is a protocol, not a convention.

Work is assigned to a role or to a person. Each role can ask for its own queue in two ways that
deliberately do not collapse into one, because they answer different questions: what is assigned
to me, and what has been said to me. The first includes work assigned indirectly — a role that
owns one story inside somebody else's feature sees that feature, with the reason shown. The
second reads the discussion across the corpus for the individual lines that mention that role.
Something can be in either without being in the other, which is precisely why both exist.

Every item and every sub-entity carries a discussion: an append-only, timestamped record,
attributed to whoever spoke. Attribution is explicit at the point of writing, and it renders as
that agent's or that person's name, so a decision recorded on an item is a decision by someone.
Mentioning a role in a comment is the call to action that puts the item in that role's queue —
so the handoff and the reason for it are the same act, and the reason survives the conversation
that produced it.

Because the discussion is append-only and timestamped, it is where state-at-a-point-in-time
belongs. The body of an item says what the item is; the discussion says what happened to it and
why. A durable body never has to narrate its own status, because the status is a field.

Two reads serve coordination directly rather than any one role: what is currently blocked, and
by what — computed from the dependency links, showing only what is genuinely still open on both
ends — and who is carrying how much, counting each assignee's open and closed work and their
sub-entity assignments separately.

## Scope

The team as a product surface: the role catalog and the live roster, role definitions and their
capability boundaries, on-demand developer roles, custom roles, human operators, compiled skills,
per-role memory and the team bulletin board. Also the handoff protocol itself — assignment,
the two queue reads, attributed discussion, mentions as a call to action, and the coordination
reads over blocking and load.

How a project redefines roles, guidance and lanes is the vocabulary contract; what the agent
tool is handed as a result is the host-integration contract.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

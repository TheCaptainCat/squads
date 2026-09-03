---
id: PRD-862
sequence_id: 862
type: contract
title: 'The read surface: the CLI is the only way in'
status: Draft
author: product-owner
refs:
- PRD-859
- PRD-863
description: The files are storage; the CLI is the only read surface; anything derived
  is a view computed on demand.
created_at: '2026-09-01T13:02:22Z'
updated_at: '2026-09-01T13:10:50Z'
---
<!-- sq:body -->
## What the product does

The markdown files are the storage. The command line is the read surface — the only one. Anything
derived is a view, computed on demand, never written down.

That is a product position, not an implementation note, and it is the reason the rest of the
product can keep its promises.

### Why the file is not the read surface

Opening an item's file returns strictly less than asking for the item. The command resolves state
the file does not carry, and by design will carry more of it over time: a sub-entity's roll-up
table, the badge line summarising a sub-entity's status and severity and who holds it, human
names for the roles behind every slug, what points at this item, and any projection the type
declares. None of that is stored, because storing it would mean maintaining a second copy of
something already true elsewhere — and a second copy is a thing that can be wrong.

So the rule the product asks of its readers, human and agent, is short: read through the command,
not the file. Everything downstream follows from it. Reference inversion is safe to compute
because nobody is reading a stale written-down copy. A roll-up is always current because it is
recomputed. A file can be hand-edited around its managed regions without any derived text going
out of date, because there is no derived text in it.

### One read shape, many questions

Any item is addressed by its type and number, or by its bare number alone when the type does not
matter. A read returns the item's metadata, its body, its declared badge fields, its
sub-entities and whatever views its type declares; asking for the full dossier adds the
discussion. It is one command per question rather than one per format.

Around that sit the corpus-wide reads: a filtered table of items; the parent-child hierarchy from
any root; full-text search across titles, summaries, bodies and discussion, reporting which
region each hit came from; what an item references and what references it; a bounded traversal of
the reference graph around an item, in either direction, filtered by link kind and exportable to
a standard graph format for rendering elsewhere; what is blocked and by what; who is carrying
how much; each role's assigned queue and mention queue; the operation log; and the corpus lint.

Settled work is out of the way by default. Every listing, hierarchy and traversal hides items
whose status is terminal, and shows them on request — so a default read answers "what is live"
rather than "what has ever existed".

The product's own documentation is part of the read surface too, printed in the terminal with no
network access, so an agent can consult it in the same place it does everything else.

### Machine-readable by default, not as an afterthought

Every work-item read and every corpus-wide read answers in JSON on request, with the same content
the human rendering shows: item reads, listings, hierarchies, search, references, graph
traversals, blocked and workload, the queues, the log, and the lint. So does the vocabulary
itself, the roster, the operator list, the board and the override state. The two roster listings that answer
only in the human rendering are the skills listing and the developer listing.

Failure is machine-readable too: a command that could not answer exits non-zero rather than
printing a message and claiming success.

Every read is a fresh read of the corpus. There is no session, no cache to invalidate and no
daemon to keep running, which is what makes the same commands safe for a human at a prompt, an
agent mid-task, and a client process polling for changes.

### Views

A view is the general form of everything above: a declared projection over the corpus, attached
to a type, computed whenever an item of that type is read.

A view names three things and nothing else — the relation to follow, the fields to project, and
its presentation. The relation can be a link kind followed backwards, a sub-entity collection, or
a subtree. The fields are attributes and declared badge values of whatever the relation yields.
The presentation is a template identified by the view's own name.

The strict separation is what makes a view useful to more than one reader. The projection half
knows nothing about presentation, so the same view serves a rendered form for a human and a
structured form — its fields, its grouping and its records — for a program. The presentation half
knows nothing about the vocabulary, so it groups and splits on declared semantic properties
rather than on hardcoded status names, and keeps working when a project renames its states.

The shipped example is a membership roll-up. Work joins a target by pointing at it with a link;
the target's own file never lists its members and never has to be edited when membership changes.
Reading the target inverts those links and reports what has been delivered, what is still
outstanding, and what stopped for some other reason without being delivered — split on what each
member's own lifecycle means rather than on any literal status.

A project declares its own views the same way, and a view is dropped automatically if the type it
was declared over is dropped.

## Scope

The read surface as product policy and as a set of commands: the position that the files are
storage and the command line is the only read surface; item reads and the full dossier;
corpus-wide listings, hierarchy, search, reference reads, graph traversal and export, blocking,
workload, per-role queues, the operation log and the lint; default hiding of settled work;
offline documentation; JSON on every read that supports it and honest exit codes; and derived
views — their declaration, their fresh computation, their rendered and structured forms, and the
separation between projection and presentation.

Which relations, fields and types a view can name is declared vocabulary. What clients do with
this surface belongs to the clients contract.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

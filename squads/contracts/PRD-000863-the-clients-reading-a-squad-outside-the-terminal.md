---
id: PRD-863
sequence_id: 863
type: contract
title: 'The clients: reading a squad outside the terminal'
status: Draft
author: product-owner
refs:
- PRD-862
- PRD-859
description: 'Browsing a squad outside the terminal: the editor extension and the
  built-in terminal browser, both read-only.'
created_at: '2026-09-01T13:02:24Z'
updated_at: '2026-09-01T13:09:54Z'
---
<!-- sq:body -->
## What the product does

A squad is readable from a terminal prompt, but a person catching up on a project wants to
browse: a tree to move through, a panel that shows what is selected, a filter, a search. Two
clients provide that, and both are readers.

Neither is required. A squad is fully usable with neither installed, and nothing either one shows
exists only inside it.

### Both are consumers of the command line, not of the files

Neither client parses item files. Both ask the same commands a person would ask, take the
structured answer, and render it. That is what keeps them honest: a client cannot show a squad a
state the command line would not report, cannot drift from the record's own rules, and gains
whatever the command line gains without being taught about it separately. It is also why they can
be shipped and versioned apart from the record they display — they depend on an answer shape, not
on a storage layout.

The consequence worth stating plainly is that both are read-only. Browsing shows the corpus;
changing it is done through the command line, by a person or an agent, where authorship,
attribution and validation live. A client that could write would be a second way to mutate the
record with its own bugs and its own idea of the rules.

### In the editor

An editor extension puts the squad in the sidebar as three trees, one per category of thing a
squad holds: the work, the durable records, and the roster of roles, skills and people. Each tree
groups by type on request, filters, and hides settled or archived entries by default with a
toggle to show them. Selecting an item opens a preview of it, and the previews keep a history so
a reader can step back and forward through what they have been reading. A search box queries the
whole corpus, and the workflow cheatsheet opens as a document.

It reads the vocabulary from the squad rather than assuming one, so a project's own types,
statuses, badge scales and sub-entity kinds appear in the trees, the grouping and the filters
with no configuration. What it does take as configuration is small and practical: where the
command line lives, how to invoke it, and which icon to give which type.

### In the terminal

A terminal browser ships with the product itself, behind an optional install, and says so plainly
if it is asked for without that install. It opens on one screen: a tree of the squad on one side,
split into the same three categories, and a reader panel on the other showing the selected item's
content and discussion. A key opens a filter; a key opens search. It is deliberately small — the
point is to read a squad without leaving the terminal, not to be a second interface to everything.

## Scope

The browsing clients: the editor extension and the built-in terminal browser — what each one
shows, how each is configured or installed, their read-only stance, and the fact that both are
clients of the command line rather than of the files.

The commands and structured answers they consume belong to the read-surface contract, and the
vocabulary they render belongs to the vocabulary contract. Nothing here is a prerequisite for
using a squad.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

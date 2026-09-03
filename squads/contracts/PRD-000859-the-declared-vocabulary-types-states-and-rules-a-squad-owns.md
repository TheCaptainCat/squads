---
id: PRD-859
sequence_id: 859
type: contract
title: 'The declared vocabulary: types, states, and rules a squad owns'
status: Draft
author: product-owner
refs:
- PRD-862
- PRD-858
description: 'How a project makes the vocabulary its own: declared types, states,
  links, badges and guidance, composed as a delta.'
created_at: '2026-09-01T13:02:17Z'
updated_at: '2026-09-01T13:09:37Z'
---
<!-- sq:body -->
## What the product does

A squad's working vocabulary is data, not code. Which kinds of work exist, what they are called
and prefixed, which folder they live in, what states they move through and in what order, which
types may parent which, what kinds of link exist and what each one means, what sub-entity a type
carries, which badge scales a type is rated on, which roles touch a type and what guidance each
of them reads — all of it is declared in TOML, and a project can change any of it without
forking anything.

The product ships a full working vocabulary as the default. A project keeps as much of it as
suits, and writes a delta for the rest.

### A delta, not a copy

A project's vocabulary file is composed over the bundled one. Tables recurse key by key, so
writing one field of one type moves that field and inherits everything else — including later
improvements to the parts left alone. Nothing has to be restated to be kept.

Arrays are the deliberate exception: an array replaces its counterpart whole, because a list
silently merged from two sources is a list nobody wrote and nobody can read back out of the
file. To extend a bundled list instead of replacing it, a splice token names the bundled value
and spreads it into the new one — that is how a project adds an alias, a link kind or a role's
guidance without freezing the rest of that list against future releases. The token resolves only
against the bundled document, never against another part of the project's own file, which is
what keeps the composition order-independent and free of cycles, and is also why a splice can
only ever add. Removal is a separate, explicit move.

Removal is a selection list: naming the types a squad keeps drops the ones it does not. A
dropped type stops existing everywhere at once — it is gone from the type commands, from the
reclassification targets, and its generated per-type guidance is withdrawn — and every way of
reaching it refuses with a message that says it was dropped from the selection rather than
merely never declared, and names the line to add it back.

Three keys are reserved and cannot be dropped, renamed or reclassified: the role, the skill and
the operator. Everything else — every kind of work the product ships with — is the project's to
rename, re-prefix, re-lifecycle or remove. Attempting to drop a reserved key is refused by name.

### Adding a kind of work

A project declares a new state machine, the states it uses and what each state means for
settled-ness and visibility, then a type that references it with a prefix, a folder and its
aliases. From that point the new type is a first-class citizen: it has its own creation command
and its own verb group, its aliases work everywhere the canonical name does, its items file
under its own prefix and folder, its states are enforced as a machine, it appears in the
reclassification targets, and it gets a generated guidance document of its own carrying its
lifecycle and its commands.

Declaring which roles touch that type, and what each of them should check, do and hand off,
fills that guidance document with per-role sections. The same declaration marks which role is
the type's author, which is what makes the product notice — advisorily, never blockingly — when
something is filed by a role that is not in that lane.

### Badge scales

A rating axis is a named, reusable collection of values, each with a code, a human label and an
optional icon, optionally ordered so that thresholds and sorting mean something. Priority and
severity are two such collections rather than two special cases: a project can declare its own
axis and attach it to any type as a field, and from then on that field is stored in frontmatter,
rendered wherever the item is shown, and available as both an exact filter and an
at-least-this-much filter in listings.

### Derived views

A view is a declared projection: a source relation to follow, the fields to project, and a
presentation template named by the view's own identity. A view attached to a type is computed
fresh every time that type is read, from the corpus as it stands. Nothing a view produces is
ever written into a file.

Dropping the type a view is declared over drops the view with it, so a project's selection list
cannot leave a projection declared over something that no longer exists.

### Everything else a squad renders

Item and sub-entity templates, the role document shape, and the files written for the agent tool
are all overridable per file: dropping a project's own copy of one template changes that
template and leaves every other one on the bundled version. Role definitions merge field by
field, so renaming an agent or changing which model it runs on is two lines, not a fork of the
role.

### Upgrade hygiene

Every override records the version it was branched from. When a release changes the bundled
original, the product says so, and shows two diffs side by side — what the project changed, and
what the upgrade changed — so a hand-merge is informed rather than guessed. After merging, the
override is re-stamped and the notice clears. A listing shows every override present with its
kind, its base version and whether it is current.

### Fail-closed

An unloadable vocabulary stops the product rather than degrading it. If a project's file is
invalid, no command answers with the vocabulary it declares; each one refuses and points at the
file and the cause. A dedicated validation command reports every problem in the file at once,
each with a fix hint, rather than one per run.

Some declarations are refused because the corpus already contradicts them. A type's prefix and
folder are how its files are found on disk, so changing either while items of that type exist is
refused and the offending item addresses are named — no command realigns an already-filed corpus
into a new prefix, and the two ways forward are to revert the field or to make the change while
the type is empty. The same cross-check refuses a vocabulary that no longer declares a type or a
status that live items still carry.

## Scope

The declared working vocabulary and the mechanism a project uses to make it its own: item types,
statuses, status roles, lifecycles, parent rules, reference kinds, sub-entity kinds, badge
collections and their fields, derived-view declarations, the role catalog, per-role definitions,
the per-type role guidance, and the rendering templates. Also the composition grammar — deep
merge, whole-array replacement, splice tokens, selection lists and reserved keys — and the
authoring tools around it: scaffolding, listing, drift diffing, re-stamping, and validation.

What the bundled vocabulary happens to declare today is the product's default, not its
definition. The machinery that enforces whatever is declared belongs to the work-record
contract.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

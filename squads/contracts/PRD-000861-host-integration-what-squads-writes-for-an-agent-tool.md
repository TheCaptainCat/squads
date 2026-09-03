---
id: PRD-861
sequence_id: 861
type: contract
title: 'Host integration: what squads writes for an agent tool'
status: Draft
author: product-owner
refs:
- PRD-862
- PRD-860
- PRD-863
description: 'What squads writes for the agent tool that runs the agents: pluggable
  backends, pointers, and managed regions.'
created_at: '2026-09-01T13:02:20Z'
updated_at: '2026-09-01T13:09:46Z'
---
<!-- sq:body -->
## What the product does

A squad has to be legible to whatever agent tool actually runs the agents. That tool has its own
configuration format, its own idea of where an agent's definition lives, and its own way of
selecting which guidance a session loads. Bridging that gap is a translation job, and the
product treats it as one: the squad — its items, identity, workflow and roster — is defined
without reference to any host, and a pluggable backend renders it into what a given host reads.

More than one backend can be active at once, and a squad can run with none at all: the record and
every command over it work exactly the same, the project just gets no generated agent files.

### What gets written

Two backends ship. One targets a host that reads a directory of per-agent and per-skill files; it
writes a file per activated role, a file per skill, and a project-guidance section. The other
targets a host that reads a single project-guidance document; it writes one managed section
listing the roster and the working agreements, and no per-role files at all. Which shape is right
is the host's business, and that is exactly the difference a backend exists to absorb.

### Generated files are pointers, not copies

A generated per-agent or per-skill file carries only what the host must know before a session can
start: the identity it is selected by, the text it is selected on, the constraints the squad
imposes on that session, and the commands that fetch everything else. It does not carry the
role's mission, its responsibilities, its working agreements or the skill's contents — those are
answered live, from the record, by the commands the pointer names.

That is a deliberate refusal to duplicate. A copy of a role definition in a host config file is a
second source of truth that goes stale the moment the first one changes and cannot be diffed
against it. A pointer cannot go stale about content it does not hold.

The one thing a pointer does materialise is the part the host must enforce before the agent can
act: a role's capability boundary. Whether an agent may orchestrate other agents is a property of
the role in the record, and it is rendered into the host's own configuration key so the host
enforces it — present for a role that may not, absent for one that may. A constraint that only
exists as a sentence in prose is a suggestion; this one is configuration.

### Managed regions in files the project owns

Where the product needs to contribute to a file the project also writes by hand — the project
guidance document at the repository root — it writes into a delimited managed region and leaves
everything outside it untouched. Host configuration the project maintains is merged rather than
replaced: existing entries survive, unrelated keys survive, and the product's own entries are
added alongside.

### Everything generated says so

Every managed region and every wholly generated file states in place that it is tool-managed and
regenerated, and names the command that regenerates it. This matters most for the agents
themselves: an agent editing a file mid-session can otherwise lose that edit at the next
regeneration without ever knowing the file was not its to keep. Saying so in the file is what
makes that fact reach the reader who needs it.

### Regeneration and drift

Regeneration is a single command and it is idempotent. It rewrites what the current roster,
vocabulary and version imply, reports every file it had to change because it had drifted, and
reports anything it withdrew because the thing it described no longer exists.

The corpus lint reports the same drift without fixing it, so a project can notice a hand-edited
pointer before a regeneration silently reverts it. Files in the host's directories that the
product does not manage are reported as candidates and never touched — not deleted, not moved,
not rewritten. A host directory is somewhere the product writes; it is not somewhere the product
owns.

## Scope

The translation layer between a squad and the agent tool that runs it: the backend abstraction
and multiple simultaneous backends, the two shipped backends and their differing file shapes,
generated per-role and per-skill pointers and what they deliberately do not contain, capability
boundaries rendered as host-enforced configuration, managed regions inside project-owned files,
merge-not-replace handling of host configuration, self-declaration of generated files,
idempotent regeneration, drift reporting, and the never-touch rule for unmanaged files.

What the roles, skills and boundaries being translated actually are belongs to the team
contract. Reading a squad through a graphical or terminal browser belongs to the clients
contract; this contract is about the files a host agent tool consumes.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->

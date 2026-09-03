---
id: SKILL-200
sequence_id: 200
type: skill
title: squads
status: Active
author: squads
created_at: '2026-06-24T20:14:34Z'
updated_at: '2026-06-24T20:14:34Z'
extra:
  slug: squads
path: agents/skills/SKILL-000200-squads.md
description: 'How to track work on this project with the squads (`sq`) CLI: create/transition
  items, comment, link context. Use whenever you start, hand off, or update work.'
---
<!-- sq:body -->
# squads — working with the `sq` CLI

**squads** is how this team coordinates — your shared structure for working alongside the other
agents: stable IDs, defined roles and skills, a status lifecycle, and a handoff protocol (comments,
`@mentions`, an inbox). Here's your part of it. Work is tracked as identified markdown items under
`squads/`, indexed in `squads/.squads.json`. Every item has a stable ID like
`TASK-<n>` (the prefix marks the type; the number is globally unique).

## Golden rules

- Items are addressed as `sq <type> <number> <verb>` (e.g. `sq task 35 update
  --status Done`); sub-entities nest:
  `sq <type> <n> <kind> <k> update --status <status>`. Create with `sq create <type>`.
- The `.md` files are sq-managed: never hand-edit frontmatter or the `<!-- sq:* -->` markers, and
  don't type prose directly into a file. Every region is written through a command. They are not a
  read surface either — read them through `sq <type> <n> show`, never by opening the file: the
  command resolves state the file does not carry, so a direct read returns strictly less than the
  command.
- Set an **item's** body with `sq <type> <n> body -m "…"` (repeat `-m`, or `--file body.md` /
  `--file -`); `--desc` (on `create`/`update`) is just the short summary shown in lists.
- Set a **sub-entity's** body with `sq <type> <n> <kind> <k> body -m "…"` (or `--file`); edit its
  metadata with `sq <type> <n> <kind> <k> update` (`--title`, `--status`, `--assignee`, plus any
  kind-declared fields — e.g. a subtask's `--story`, a finding's `--severity`). Read either back with `sq <type> <n> show` /
  `sq <type> <n> <kind> <k> show`. For a full dossier (body + sub-entities + discussion), use
  `sq <type> <n> show --full --comments` — decisions and refinements often live in comments.
- Reference related items by ID so others read the right context.
- **Before acting on an item, open its `sq-<type>` skill and follow your role's _For …_ section** —
  it lists exactly what you check first, what you do, and when/how to hand off.
- Need detail? Run `sq docs` to list the full documentation and `sq docs <name>` (e.g.
  `sq docs workflow`) to read it in-terminal — no fetch required.

## Working directly with the operator

The operator sometimes talks to you directly — for live work or debugging. The team only sees
`sq`, never the chat, so stay disciplined:

- **Anchor to an item.** Confirm the item with `sq <type> <n> show --full --comments` (body +
  sub-entities + discussion). Create the item first if it's genuinely new.
- **Keep status honest.** Move it to its lifecycle's first working state (`sq <type> <n>
  status <status>`) when you start; don't leave it stale.
- **Hand back through `sq`.** Before you wrap up, leave a `sq <type> <n> comment --as <your-slug>
  -m "…"` summarising what changed — that's how the coordinating agent's loop (and the next
  agent) picks up where you left off.
- **Scope your comment to the right discussion.** Sub-entities (stories, subtasks, findings)
  each have their own discussion region alongside the parent item's main discussion. Use
  `sq <type> <n> <kind> <k> comment` for anything scoped to that one sub-entity; use
  `sq <type> <n> comment` for cross-cutting material that applies to the whole item.

  | Scope | Command | When to use |
  |---|---|---|
  | One story | `sq feature <n> story <k> comment` | Acceptance clarification, story-local blocker or question |
  | One subtask | `sq task <n> subtask <k> comment` | Implementation note, decision local to this unit of work |
  | One finding | `sq review <n> finding <k> comment` | Fix rationale, reproduction notes, "agreed — closing this one" |
  | Whole item | `sq <type> <n> comment` | Handoff @mentions, decisions spanning multiple sub-entities, item-level status summaries |

  @mentions are surfaced by `sq inbox` wherever they live in the file — in a sub-entity discussion
  or the main one. Prefer the main discussion for @mentions that announce a transition or request
  action from the next agent (they read as item-level handoffs); a sub-entity discussion is fine for
  a scoped question (e.g. `sq task N subtask 1 comment
  --as <your-slug> -m "@role does this look right?"`). This is guidance, not a hard rule — the
  inbox never misses a mention.
- **Stay in lane.** File anything you discover that's out of scope as its own item (e.g. a bug);
  don't silently expand the work.

Humans are tracked as **operators** (`op-<firstname>` slugs; see the roster in `CLAUDE.md`). Assign
work to a person with `--assignee op-<slug>`, and attribute their words with `--as op-<slug>` (or
`--author op-<slug>`). Register one with `sq operator add "<name>"`; list them with
`sq list -t operator`.

## Finding things across the board

Use `sq search "<text>"` when you need to hunt a prior decision or check whether a topic is
already tracked — not as a routine boot step.

- It scans **everything**: titles, summaries, bodies, discussion comments, and sub-entity prose
  (story/subtask/finding blocks) — case-insensitive substring match.
- Narrow with `--type <type>` and/or `--status <status>` (the same vocabulary as `sq list`); both
  AND-compose with the query.
- Each result names **where** it matched: `body`, a `discussion` comment, or a named sub-entity
  (e.g. `story:US<n>`, `story:US<n>:discussion#2`), alongside an in-context snippet — so you can jump
  straight to the right region instead of re-reading the whole item.
- `sq search "<text>" --json` emits the same result set machine-readably (id/type/status plus
  each hit's region/location/snippet) for a script or an orchestrating agent to consume.

## Team workflow

- Items are addressed as `sq <type> <number> <verb>` (e.g. `sq task 35 show`);
  create with `sq create <type>`. Run `sq <type> --help` / `sq <type> <n> --help` to explore.
- **Product owner** → `sq create epic "…" --author product-owner`.
- **Product owner** → `sq create feature "…" --author product-owner`, then `add-story "…"`.
- **Tech lead** → `sq create task "…" --author tech-lead` `--parent FEAT-…`, then `add-subtask "…"` `--story USn`; link with `ref add <id> --kind fixes|addresses`.
- **QA engineer** → `sq create bug "…" --author qa`.
- **Architect** → `sq create decision "…" --author architect`; link with `ref add <id> --kind supersedes`.
- **Code reviewer** → `sq create review "…" --author reviewer`, then `add-finding "…"`.
- **Sub-entities are tracked too:** `feature` → `story` (`Todo → InProgress → Done (+ Blocked, Cancelled)`); `task` → `subtask` (`Todo → InProgress → Done (+ Blocked, Cancelled)`); `review` → `finding` (`Open → Fixed → Verified (+ WontFix)`).
  `update` is the one metadata entry point for a sub-entity (`--title`/`--status`/`--assignee`,
  plus any declared field flag). Each parent shows an sq-managed summary table.
- Hierarchy: epic → feature → task. `sq check` enforces the parent rules.
- Each role has skills for the item types it manages (e.g. `sq-epic`, `sq-feature`, `sq-task`, …) —
  open those for role-specific guidance. The default role triages and routes when no other agent
  claims the work.
- The `.md` files are sq-managed — never hand-edit them, and read them through
  `sq <type> <n> show`, never by opening the file. Set an item's body with
  `sq <type> <n> body -m "…"` (or `--file`); a sub-entity's with `sq <type> <n> <kind> <k> body -m
  "…"`; read back with `sq <type> <n> show --full --comments` (full dossier). Hand off with `sq <type> <n> comment --as <slug> -m "…"`
  (repeat `-m` for separate bullets; use `@role`).

## Type-command aliases

Short and single-letter aliases for the item-type commands — input sugar only. They are hidden from
root `--help` but fully equivalent: every alias accepts everything the canonical name does, including
sub-entity chains (`sq f 26 story 4 show`). Output (IDs, errors, `--json`) always uses the canonical
type name. Run `sq workflow` to see this table in the terminal.

| Canonical | Aliases | Example |
|---|---|---|
| `epic` | `e` | `sq e <n> show` |
| `feature` | `feat`, `f` | `sq f <n> show` |
| `task` | `t` | `sq t <n> show` |
| `bug` | `b` | `sq b <n> show` |
| `decision` | `dec`, `d` | `sq d <n> show` |
| `review` | `rev`, `r` | `sq r <n> show` |
| `guide` | `g` | `sq g <n> show` |

**Evolution rule (stability contract):** adding an alias is additive and allowed;
removing or repurposing an alias is a breaking change and is not permitted after 1.0. The alias table
is frozen grammar in the same stability tier as the canonical command names.

## Type lifecycles

Lifecycle strings auto-derived from each type's state machine — the source of truth for valid
statuses and transitions.

| Prefix | Type | Lifecycle |
|---|---|---|
| `EPIC` | `epic` | `Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)` |
| `FEAT` | `feature` | `Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)` |
| `TASK` | `task` | `Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)` |
| `BUG` | `bug` | `Open → InProgress → Fixed → Verified (+ WontFix, Blocked, Cancelled)` |
| `ADR` | `decision` | `Proposed → Accepted → Superseded (+ Rejected, Deprecated)` |
| `REV` | `review` | `Requested → InReview → ChangesRequested → Approved (+ Rejected)` |
| `GUIDE` | `guide` | `Draft → Published → Deprecated` |

## Retype

Reclassify a work item to a different type — the sequence number (and durable identity) is
preserved; only the ID prefix changes. All incoming refs, children's parent links, and prose
mentions are rewritten to the new ID atomically.

```bash
sq <type> <n> retype <new-type>   # e.g. sq epic 7 retype feature
```

Valid targets: `epic`, `feature`, `task`, `bug`, `decision`, `review`, `guide`.

**Status behaviour:** when the old and new types share the same workflow (e.g. epic↔feature↔task) the status is carried as-is; otherwise
the status resets to the new type's initial value and the command says so.

**Refusals with actionable hints:**
- item has sub-entities (clear them first)
- existing parent would be invalid for the new type (re-parent or remove the parent first)
- any child would become invalid under the new type (re-parent or remove those children first)

After retype, `sq check` is clean and `sq repair` is a stable no-op.

## Remove vs. Cancel

Two distinct exit paths for work items — use the right one:

| | Cancel | Remove |
|---|---|---|
| **Intent** | Work genuinely considered, then dropped | Item should never have existed (mis-creation, test artifact, rolled-back decision) |
| **Effect** | Status → `Cancelled`; item stays on the books, greppable, linkable, visible in `tree`/`list` | File deleted, index entry gone; only a sequence-number gap remains |
| **Command** | `sq <type> <n> status Cancelled` | `sq <type> <n> remove` |

```bash
sq <type> <n> status Cancelled   # drop work that was genuinely considered
sq <type> <n> remove             # erase a mis-creation (interactive confirm)
sq <type> <n> remove --yes       # skip the confirm
sq <type> <n> remove --force     # also sever incoming refs from referrers' frontmatter
```

**Ref and child safety:**
- `remove` refuses when the item has incoming refs or children, listing every offender.
- `--force` severs refs but still refuses while children exist; re-parent or remove children first.
- After any removal `sq check` is clean — no dangling refs, no dangling parent links.

**Sequence gaps are sanctioned, not corruption.** Removal deletes the index entry but never
touches the counter high-water mark — the freed number is never reissued.  A gap means "an item
with that sequence number existed and was removed."  `sq check` and `sq repair` treat gaps as
normal; the reflog records a reconstructable removal line that explains each gap.

## Ref kinds

Ref kinds are declared vocabulary. The bundled set is the default; a project may declare its own, and may rename or drop a built-in it does not use — refused while live refs still carry it. A kind the merged spec does not declare is rejected. Engine behaviour binds to a kind's declared semantic role, never to its name: a renamed dependency kind keeps driving `sq blocked`, and a kind with no semantic is navigational. Use `sq <type> <n> ref add <id> --kind <kind>`; the table below is what this squad declares.

| Kind | Meaning | Consumer |
|---|---|---|
| `related` | Generic cross-reference (default) | Navigation |
| `blocks` | A is blocking B; B cannot proceed while A is open | `sq blocked` |
| `depends-on` | A depends on B; A cannot proceed while B is open | `sq blocked` |
| `implements` | A implements the requirement or spec described by B | Navigation |
| `fixes` | A (the resolving work) fixes the problem tracked by B | `sq check` ref-rule warnings |
| `addresses` | A (the resolving work) addresses or follows up on B (feedback, a review) | `sq check` ref-rule warnings |
| `supersedes` | A (a newer decision) supersedes B (an older one) | `sq check` supersession rule |
| `duplicates` | A (a later filing) duplicates B (the original) | Navigation |
| `scopes` | A (a skill) is scoped to role B; B's generated pointer preloads A | Preload resolver, retirement gate |
| `targets` | A targets B — a navigational membership edge with no engine binding; its meaning is whatever reads it | Navigation |

Every edge is stored on the item you add it to — `A <kind> B` lives on A. `blocks` and `depends-on` are two spellings of the same dependency: use whichever fits your authoring context, and both feed `sq blocked`. `sq check` reads `supersedes` on the newer record and expects the older one at Superseded. Bare `ref add <id>` (no `--kind`) resolves to whichever kind declares the default semantic — `related` here — and that edge is stored without its kind, so renaming the default relabels those edges instead of re-pointing them.
## Common commands

```bash
sq create task "Title" --author <your-slug> [--parent FEAT-<n>] [-m "body…"]  # also: bug|decision|epic|feature|guide|review
#   --author is required and must be a registered agent (your own role slug)
sq task 3 show --full --comments                                # full dossier: body + sub-entities + discussion
sq task 3 status InProgress                                     # transition (validated per type)
sq task 3 update --assignee python-dev --priority urgent --parent FEAT-<n>  # metadata (parent validated)
sq task 3 body -m "## Description" -m "…"                        # set the body (or --file)
sq task 3 comment --as <your-slug> -m "…"                        # discussion / @mentions
sq list --type task --status InProgress                         # closed items hidden; --all to include
sq tree FEAT-<n> --json                                      # a parent's whole subtree (status/blocked) for coordinating
sq search "lockout"                                             # match titles, summaries, bodies
sq mine <your-slug>                                             # your open items  ·  sq workload
sq blocked                                                      # open items waiting on an open blocker
sq docs [internals|workflow|migration|...]                      # read the full docs in-terminal (offline)
```

Items whose status is hidden-by-default (typically the settled/closed ones) drop out of `sq
list`/`sq tree` — pass `--all` or an explicit `--status` to see them. Set importance with `--priority urgent|high|medium|low`.

Run `sq --help`, `sq <type> --help`, or `sq <type> <n> --help` for the full surface.

<!-- sq:body:end -->

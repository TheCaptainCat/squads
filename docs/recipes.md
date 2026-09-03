# Recipes

Copy-paste sequences for common moves. IDs are illustrative — use the ones `sq` prints. Prefix with
`uv run` from a source checkout. See [workflow.md](workflow.md) for the rules behind these.

## Start a feature (product owner)

```bash
sq create feature "Login" --parent EPIC-1 --author product-owner
sq feature 2 add-story "As a user, I want to log in so that I can access my account"
sq feature 2 add-story "As an admin, I want to lock accounts after repeated failures"
# set each story's body (acceptance criteria, etc.) through sq — no manual file editing:
sq feature 2 story 1 body -m "As a user, I want to log in…" -m "Acceptance: … "
sq feature 2 story 2 body --file us2-body.md   # or pipe via --file -
```

## Break a feature into tasks (tech lead)

```bash
sq create task "Validate credentials" --parent FEAT-2 --author tech-lead
sq task 3 add-subtask "Verify password hash" --story US1
sq task 3 add-subtask "Lock after N failures"  --story US2
sq task 3 status Ready
```

## Fix a bug

```bash
sq create bug "Lockout counter resets on refresh" --author qa            # → BUG-10
sq create task "Persist lockout counter" --author tech-lead              # no feature parent
sq task 11 ref add BUG-10 --kind fixes
sq bug 10 status InProgress
sq task 11 status InProgress
# … implement …
sq task 11 status Done
sq bug 10 status Fixed                                      # the fix has landed
sq bug 10 status Verified                                   # QA has confirmed it against the repro
```

A bug closes on `Verified`, not on the task's `Done` — the two run on different lifecycles, and the
work being merged is a separate claim from the reported behaviour being gone. `sq workflow
lifecycles` prints the states and legal moves for every type your squad declares.

## Run a code review

```bash
sq create review "Auth module review" --desc "Scope: token + lockout" --author reviewer   # → REV-12
sq review 12 status InReview
sq review 12 comment --as reviewer -m "Hash OK" -m "@dotnet-dev counter not persisted — changes requested"
sq review 12 status ChangesRequested
# developer addresses it
sq task 13 ref add REV-12 --kind addresses
sq review 12 status Approved
```

## Record a decision (ADR)

```bash
sq create decision "Use argon2id for password hashing" --author architect      # → ADR-14
sq decision 14 body --file adr-body.md   # Context / Decision / Consequences (or -m paragraphs)
sq decision 14 status Accepted
```

## Keep a contract current (product owner)

A contract is the living record of what the product does for a user, right now — one per capability
area, rewritten in place as the product changes. Features are the history; the contract is the
current answer.

```bash
sq create contract "Authentication" --author product-owner       # → PRD-16
sq contract 16 body --file contract-auth.md   # what the product does today, from the user's side
sq contract 16 status Active
# link the feature that shapes it, from the feature:
sq feature 2 ref add PRD-16 --kind implements
sq contract 16 refs --in                      # every feature that has shaped this contract
```

Nothing requires a delivered feature to link a contract: squads types the edge and leaves the
obligation to you, because plenty of features touch no user-facing behaviour at all. If you do want
`sq check` to raise a warning when a feature is delivered without one, opt in from your own workflow
override — see [workflow.md](workflow.md#keeping-a-contract-current) § "Keeping a contract current".

## Aim work at a milestone (product owner / tech lead)

```bash
sq create milestone "1.0" --author product-owner                 # → MILE-17
sq milestone 17 update --set target_date=2026-12-01
sq milestone 17 status InProgress
# work joins from its own side — the milestone file is never rewritten:
sq feature 2 ref add MILE-17 --kind targets
sq task 3 ref add MILE-17 --kind targets
sq bug 10 ref add MILE-17 --kind targets
# read what's left:
sq milestone 17 show                          # delivered / outstanding, counted, computed fresh
sq workflow view milestone_rollup MILE-17 --json   # the same members as records
sq milestone 17 refs --in                     # the raw membership edges
```

There is no verb that adds work to a milestone from the milestone's side, because membership is
never stored there. Re-aiming an item at a different milestone is `sq <type> <n> ref rm MILE-17`
followed by a `ref add` for the new one — again, both on the work item.

## Write a guide (architect / tech writer)

```bash
sq create guide "Password hashing" --tech security --tag auth --author tech-writer   # → GUIDE-15
sq guide 15 status Published
# link the guide from the work that should follow it:
sq task 3 ref add GUIDE-15 --kind implements
```

## Onboard a stack developer

```bash
sq dev add --tech dotnet                 # → "Elias Dotnet"  (dotnet-dev)
sq dev list
# now you can attribute work to them:
sq task 3 comment --as dotnet-dev -m "Picked this up"
```

## Hand off & check your inbox

```bash
sq task 3 comment --as architect -m "@qa ready for expiry tests"
sq inbox qa                              # open items mentioning @qa
sq tree                                  # see the hierarchy
sq check                                 # validate before committing
```

## Prioritize, find, and focus

```bash
sq create task "Hotfix login 500" --author tech-lead --priority urgent --assignee dotnet-dev
sq task 3 update --priority high         # or --no-priority to clear
sq list --priority urgent                # filter by priority
sq mine dotnet-dev                       # a role's open work: items assigned to it, plus
                                         # items where one of its sub-entities is assigned to it
sq workload                              # open/closed/total per assignee, item counts and
                                         # sub-entity counts side by side
sq search "lockout"                      # match titles, summaries, bodies, discussion
# sequencing: mark blockers, then see what's stuck
sq task 4 ref add TASK-3 --kind blocks   # "TASK-4 blocks TASK-3"
sq blocked                               # open items waiting on an open blocker
# closed items leave the default views; bring them back with --all
sq list --all
sq list --status Done
```

**`sq mine` matches sub-entities too.** A story, subtask or finding assigned to a slug is that
slug's work even when the item carrying it is assigned to someone else, so `sq mine` returns that
item and names what matched in a `Matched` column (`US1 (InProgress)`); `--json` carries the same
thing in a `matched_subentities` key. `sq inbox <role>` likewise names the region a mention was
found in (`story:US1:discussion#1`, also a `regions` key under `--json`), so you can go straight to
the right discussion instead of re-reading the item.

Open or closed is judged **per match**, not per item. A closed item still shows up in `sq mine`
while your own sub-entity on it is open — the item closing did not finish your part — and one of
your closed sub-entities on an open item stays hidden until you pass `--all`.

`sq workload` reports each assignee's sub-entity counts (`Sub Open` / `Sub Closed` / `Sub Total`,
and `subentity_open` / `subentity_closed` / `subentity_total` under `--json`) as their own columns
beside the item counts, never folded in — one sub-entity is not one item's worth of work.

The priority codes above (urgent, high, medium, low) are the bundled default for the priority collection.
You can customize the priority axis — relabel badges, change emoji, add/remove values, or define
custom badge collections — via `.overrides/workflow.toml`; see [workflow.md](workflow.md)
§ "Project workflow overrides".

## Migrate a legacy ticket (preserve its date)

```bash
sq --at 2024-02-10 create task "Old migration task" --parent FEAT-2 --author tech-lead
sq --at 2024-02-12 task 20 status InProgress
sq --at 2024-02-15T17:00:00Z task 20 comment --as reviewer -m "shipped"
```

Full migration guide: [adoption.md](adoption.md).

## Block-shift IDs before merging (prevent collisions)

When your branch will merge into main and both have created new items, block-shift your branch's
IDs into a reserved range **before the merge** — this preserves referential intent and is much safer
than fixing collisions after they land.

```bash
# On your branch (before merging to main):

# Step 1: get main's current counter
git show main:squads/.squads.json | jq .counter     # → the value for --onto

# Step 2: find your branch's lowest new ID
# (items created after the branch point; usually base_counter + 1)
sq list --all --json | jq 'map(select(.sequence_id > <base>)) | min_by(.sequence_id) | .sequence_id'
# or just remember: if the merge-base counter was 280, use --from 281

# Step 3: shift your branch's IDs above main's counter
sq renumber --from 281 --onto 287
# (every ID on this branch >= 281 moves into the reserved block; all refs update atomically)

# Now safe to merge:
git merge main
```

For details and the post-merge fallback, see [faq.md](faq.md) **Handling ID collisions**.

# Recipes

Copy-paste sequences for common moves. IDs are illustrative — use the ones `sq` prints. Prefix with
`uv run` from a source checkout. See [workflow.md](workflow.md) for the rules behind these.

## Start a feature (product owner)

```bash
sq create feature "Login" --parent EPIC-1
sq feature 2 add-story "As a user, I want to log in so that I can access my account"
sq feature 2 add-story "As an admin, I want to lock accounts after repeated failures"
# set each story's body (acceptance criteria, etc.) through sq — no manual file editing:
sq feature 2 story 1 body -m "As a user, I want to log in…" -m "Acceptance: … "
sq feature 2 story 2 body --file us2-body.md   # or pipe via --file -
```

## Break a feature into tasks (tech lead)

```bash
sq create task "Validate credentials" --parent FEAT-2
sq task 3 add-subtask "Verify password hash" --story US1
sq task 3 add-subtask "Lock after N failures"  --story US2
sq task 3 status Ready
```

## Fix a bug

```bash
sq create bug "Lockout counter resets on refresh"          # → BUG-10
sq create task "Persist lockout counter"                    # technical task, no feature parent
sq task 11 ref add BUG-10 --kind fixes
sq task 11 status InProgress
# … implement …
sq task 11 status Done
sq bug 10 status Done
```

## Run a code review

```bash
sq create review "Auth module review" --desc "Scope: token + lockout"   # → REV-12
sq review 12 status InReview
sq review 12 comment --as reviewer -m "Hash OK" -m "@dotnet-dev counter not persisted — changes requested"
sq review 12 status ChangesRequested
# developer addresses it
sq task 13 ref add REV-12 --kind addresses
sq review 12 status Approved
```

## Record a decision (ADR)

```bash
sq create decision "Use argon2id for password hashing"      # → ADR-14
sq decision 14 body --file adr-body.md   # Context / Decision / Consequences (or -m paragraphs)
sq decision 14 status Accepted
```

## Write a guide (architect / tech writer)

```bash
sq create guide "Password hashing" --tech security --tag auth   # → GUIDE-15
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
sq mine dotnet-dev                       # open items assigned to a role
sq workload                              # open/closed/total per assignee
sq search "lockout"                      # match titles, summaries, bodies, discussion
# sequencing: mark blockers, then see what's stuck
sq task 4 ref add TASK-3 --kind blocks   # "TASK-4 blocks TASK-3"
sq blocked                               # open items waiting on an open blocker
# closed items leave the default views; bring them back with --all
sq list --all
sq list --status Done
```

The codes above (urgent, high, medium, low) are the bundled default for the priority collection.
You can customize the priority axis — relabel badges, change emoji, add/remove values, or define
custom badge collections — via `.overrides/workflow.toml`; see [workflow.md](workflow.md)
§ "Project workflow overrides".

## Migrate a legacy ticket (preserve its date)

```bash
sq --at 2024-02-10 create task "Old migration task" --parent FEAT-2
sq --at 2024-02-12 status TASK-20 InProgress
sq --at 2024-02-15T17:00:00Z comment TASK-20 --as reviewer -m "shipped"
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

# Recipes

Copy-paste sequences for common moves. IDs are illustrative — use the ones `sq` prints. Prefix with
`uv run` from a source checkout. See [workflow.md](workflow.md) for the rules behind these.

## Start a feature (product owner)

```bash
sq create feature "Login" --parent EPIC-000001
sq feature 2 add-story "As a user, I want to log in so that I can access my account"
sq feature 2 add-story "As an admin, I want to lock accounts after repeated failures"
# set each story's body (acceptance criteria, etc.) through sq — no manual file editing:
sq feature 2 story 1 body -m "As a user, I want to log in…" -m "Acceptance: … "
sq feature 2 story 2 body --file us2-body.md   # or pipe via --file -
```

## Break a feature into tasks (tech lead)

```bash
sq create task "Validate credentials" --parent FEAT-000002
sq task 3 add-subtask "Verify password hash" --story US1
sq task 3 add-subtask "Lock after N failures"  --story US2
sq task 3 status Ready
```

## Fix a bug

```bash
sq create bug "Lockout counter resets on refresh"          # → BUG-000010
sq create task "Persist lockout counter"                    # technical task, no feature parent
sq task 11 ref add BUG-000010 --kind fixes
sq task 11 status InProgress
# … implement …
sq task 11 status Done
sq bug 10 status Done
```

## Run a code review

```bash
sq create review "Auth module review" --desc "Scope: token + lockout"   # → REV-000012
sq review 12 status InReview
sq review 12 comment --as reviewer -m "Hash OK" -m "@dotnet-dev counter not persisted — changes requested"
sq review 12 status ChangesRequested
# developer addresses it
sq task 13 ref add REV-000012 --kind addresses
sq review 12 status Approved
```

## Record a decision (ADR)

```bash
sq create decision "Use argon2id for password hashing"      # → ADR-000014
sq decision 14 body --file adr-body.md   # Context / Decision / Consequences (or -m paragraphs)
sq decision 14 status Accepted
```

## Write a guide (architect / tech writer)

```bash
sq create guide "Password hashing" --tech security --tag auth   # → GUIDE-000015
sq guide 15 status Published
# link the guide from the work that should follow it:
sq task 3 ref add GUIDE-000015 --kind implements
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

## Migrate a legacy ticket (preserve its date)

```bash
sq --at 2024-02-10 create task "Old migration task" --parent FEAT-000002
sq --at 2024-02-12 status TASK-000020 InProgress
sq --at 2024-02-15T17:00:00Z comment TASK-000020 --as reviewer -m "shipped"
```

Full migration guide: [adoption.md](adoption.md).

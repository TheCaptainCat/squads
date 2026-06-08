# Recipes

Copy-paste sequences for common moves. IDs are illustrative — use the ones `sq` prints. Prefix with
`uv run` from a source checkout. See [workflow.md](workflow.md) for the rules behind these.

## Start a feature (product owner)

```bash
sq create feature "Login" --parent EPIC-000001
sq story add FEAT-000002 "As a user, I want to log in so that I can access my account"
sq story add FEAT-000002 "As an admin, I want to lock accounts after repeated failures"
# then open FEAT-000002's file and write each story's body + acceptance criteria
```

## Break a feature into tasks (tech lead)

```bash
sq create task "Validate credentials" --parent FEAT-000002
sq subtask add TASK-000003 "Verify password hash" --story US1
sq subtask add TASK-000003 "Lock after N failures"  --story US2
sq status TASK-000003 Ready
```

## Fix a bug

```bash
sq create bug "Lockout counter resets on refresh"          # → BUG-000010
sq create task "Persist lockout counter"                    # technical task, no feature parent
sq ref add TASK-000011 BUG-000010 --kind fixes
sq status TASK-000011 InProgress
# … implement …
sq status TASK-000011 Done
sq status BUG-000010 Done
```

## Run a code review

```bash
sq create review "Auth module review" --desc "Scope: token + lockout"   # → REV-000012
sq status REV-000012 InReview
sq comment REV-000012 --as reviewer -m "Hash OK" -m "@dotnet-dev counter not persisted — changes requested"
sq status REV-000012 ChangesRequested
# developer addresses it
sq ref add TASK-000013 REV-000012 --kind addresses
sq status REV-000012 Approved
```

## Record a decision (ADR)

```bash
sq create decision "Use argon2id for password hashing"      # → ADR-000014
# write Context / Decision / Consequences in the body, then:
sq status ADR-000014 Accepted
```

## Write a guide (architect / tech writer)

```bash
sq guide add "Password hashing" --tech security --tag auth   # → GUIDE-000015
sq status GUIDE-000015 Published
# link the guide from the work that should follow it:
sq ref add TASK-000003 GUIDE-000015 --kind implements
```

## Onboard a stack developer

```bash
sq dev add --tech dotnet                 # → "Elias Dotnet"  (dotnet-dev)
sq dev list
# now you can attribute work to them:
sq comment TASK-000003 --as dotnet-dev -m "Picked this up"
```

## Hand off & check your inbox

```bash
sq comment TASK-000003 --as architect -m "@qa ready for expiry tests"
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

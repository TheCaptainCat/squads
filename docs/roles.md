# Roles

A squad is a roster of named agents. Each role has a **real name** (used in files and conversation)
and a **slug** (used on the CLI and as the Claude agent name). Roles are activated at `init`/`adopt`
or later with `sq role activate <slug>`, which is also where you get to name them — see
[overrides.md § "Agent naming"](overrides.md#agent-naming) for every way a name can be set and
[§ "Which name wins"](overrides.md#which-name-wins) for which one applies when two disagree.

## The bundled roster

| Name | Slug | Title | Model | Color | Item skills it manages |
|------|------|-------|-------|-------|------------------------|
| Catherine Manager | `manager` | manager *(default)* | opus | cyan | — (triages & routes; `squads` skill only) |
| Robert Architect | `architect` | architect | opus | blue | `sq-epic`, `sq-decision`, `sq-contract`, `sq-guide` |
| Olivia Lead | `tech-lead` | tech lead | opus | purple | `sq-epic`, `sq-feature`, `sq-task`, `sq-bug`, `sq-decision`, `sq-contract`, `sq-milestone`, `sq-guide` |
| Paul Reviewer | `reviewer` | code reviewer | opus | red | `sq-task`, `sq-bug`, `sq-review` |
| Mara Tester | `qa` | QA engineer | sonnet | green | `sq-feature`, `sq-task`, `sq-bug` |
| Hugo Ops | `devops` | DevOps engineer | sonnet | orange | — (`squads` skill only) |
| Nina Product | `product-owner` | product owner | sonnet | yellow | `sq-epic`, `sq-feature`, `sq-contract`, `sq-milestone` |
| Theo Writer | `tech-writer` | technical writer | haiku | pink | `sq-guide` |

Every role also gets the general **`squads`** skill (how to use the CLI). A role that doesn't manage
an item type doesn't get that type's skill — that's why the manager and devops carry only `squads`.

## Bundles

`--roles` at `init`/`adopt` takes a bundle name or a comma-separated list of slugs:

| Bundle | Roles |
|--------|-------|
| `all` *(default)* | every role above |
| `core` | `manager`, `architect`, `tech-lead`, `reviewer` |
| `minimal` | `manager` |

```bash
sq init --roles core
sq init --roles manager,architect,qa
```

## Stack-specific developers

Developers are created on demand — the bundled set is deliberately stack-agnostic:

```bash
sq dev add --tech dotnet                 # → "Elias Dotnet"  slug: dotnet-dev
sq dev add --tech python --name "Grace Hopper"
sq dev list
```

If you omit `--name`, a first name is taken from a pool and the surname is the tech (so `--tech
dotnet` → *Elias Dotnet*); the slug is always `<tech>-dev`. Every developer manages `sq-task`,
`sq-bug`, and `sq-review`. The name and `--model` you choose here are kept as they are by every
later `sq sync`; the rest of the developer's definition is refreshed from the bundled one — see
[overrides.md § "Which name wins"](overrides.md#which-name-wins).

A developer's fields are overridable like any other role's, and the override merges onto the
developer you already have: a `.overrides/roles/<tech>-dev.toml` that sets only `title` changes only
the title and leaves the name alone, while declaring `full_name` renames them. Worked example:
[overrides.md § "Retitle a developer without renaming them"](overrides.md#retitle-a-developer-without-renaming-them).

## Managing roles

```bash
sq role list                 # active roles
sq role catalog              # the bundled catalog
sq role architect show       # a bundled role's definition
sq role activate qa          # add a role later (creates its item + Claude pointer)
sq role ROLE-000002 regen    # re-render its pointer from the item
sq role ROLE-000002 status Archived [--force] [--unlink]   # transition its Active/Archived status
sq role ROLE-000002 set-default                 # move the default-role designation here
sq role ROLE-000002 rm [--purge]
```

`sq role list` shows every activated role with a **Live** marker — a retired role stays on the
roster and simply stops being live. See ["Retiring a roster entry"](#retiring-a-roster-entry) for
what that costs you and how to undo it.

`set-default` moves the designation rather than merely setting it: it clears every other role
that carries it in the same transaction, so the roster never ends up with two. It refuses a
role that isn't live, and designating the role that already holds it is a reported no-op. This
is also the way back if a squad has lost its default-role line to a retirement — reactivating
the previous holder is the only other recovery.

### Custom non-dev roles

Beyond the bundled roster and stack-specific developers, you can define a wholly custom, non-dev
role — e.g. a designer/UX role, a `security-analyst`, or an `incident-commander` — that isn't in the
bundled catalog. Start one with `sq override scaffold --new <slug>`, fill in the essentials it
stubs, then activate it exactly like a bundled role. Worked example (a `compliance-officer` role):
[overrides.md § "Define a custom role"](overrides.md#define-a-custom-role).

```bash
sq override scaffold --new security-analyst
$EDITOR squads/.overrides/roles/security-analyst.toml
sq role activate security-analyst
```

## Managing skills

Skills are the instruction files a role preloads. Every role carries the general `squads` skill plus
one `sq-<type>` skill per item type it manages; those are generated and kept in step for you. You can
add skills of your own and scope them to whichever roles should carry them:

```bash
sq list -t skill                        # the skills this squad has (there's no dedicated list verb)
sq skill add "deploy-runbook" --desc "How we ship."   # create a custom skill
sq skill deploy-runbook body --file runbook.md        # write its content (refuses once written:
                                                      #   --append to add, --force to replace)
sq skill deploy-runbook link-role devops              # scope it to a role (resyncs that role now)
sq skill deploy-runbook unlink-role devops            # remove the scoping
sq skill deploy-runbook show
sq skill deploy-runbook regen                         # re-render its pointer from the item
sq skill deploy-runbook status Archived [--force] [--unlink]   # transition its Active/Archived status
sq skill deploy-runbook rm [--purge]
```

A generated skill's body is not yours to write — `body` refuses one, because `sq sync` would discard
the edit. Author the skills you add; leave the generated ones to `sq`.

## Operators (humans)

Roles are AI agents; **operators are the people**. Register a human so work can be assigned to
them and their words attributed to them — a manual step, a review point they dictated, or a task
handed to someone else on the repo:

```bash
sq operator add "Alice Tester"  # slug derived as op-alice (override with --slug)
sq operator list
sq operator OP-000002 status Archived [--force] [--unlink]   # transition its Active/Archived status
sq operator OP-000002 rm [--purge]
```

Operators are first-class participants, but **not** agents: they're never spawned as subagents,
never get a `.claude/agents` pointer or skills, and don't appear in the agent roster (they have
their own "Operators (people)" roster in `CLAUDE.md`). Once registered, an `op-` slug is a valid
`--author` / `--assignee` (on items *and* sub-entities) and `--as` (on comments) — the same gates
that accept roles accept operators. There's no auto-detection or stored "current operator": at the
start of a session the agent works out who the human is (e.g. from `git config user.name`), checks
`sq operator list`, and asks whether to register them — and must ask if it's unsure.

## Retiring a roster entry

Roles, skills and operators share one lifecycle, `Active ⇄ Archived`, driven by the same verb:

```bash
sq role <addr> status Archived
sq skill <addr> status Archived
sq operator <addr> status Archived
```

A lifecycle for these types declares which of its statuses are **live** — the ones whose entries are
presented to an agent host. In the bundled lifecycle `Active` is live and `Archived` is not, so
archiving an entry **retires** it.

### Retiring withdraws the entry from your generated config

Retiring an entry deletes the per-entry file each enabled agent host reads — `.claude/agents/<slug>.md`
for a role, `.claude/skills/<slug>/` for a skill, and the equivalent under any other host you have
enabled — and rewrites every compiled region that named it: the rosters in `CLAUDE.md` and `AGENTS.md`,
and the per-role sections of the generated `sq-<type>` skills. A retired role is no longer spawnable
and a retired skill is no longer loadable. An operator has no file of its own, but its roster line goes
the same way.

Reactivating puts it back in full — the file is re-rendered from the entry's definition, including its
complete preloaded-skill list and any custom skills scoped to it, and its line returns to every
compiled region:

```bash
sq role <addr> status Active
```

There is nothing to repair afterwards and no `sq sync` to run: every enabled host is brought back into
step inside the same command. The definition under `squads/agents/` is never touched by a status
change — that's the durable copy, and the generated files are a projection of it.

Retiring the role that carries the **default-role designation** is allowed. Your generated config then
stops naming a default rather than naming a role the host can't spawn, and `sq` warns as it happens.
Designate another live role with `sq role <addr> set-default`, or reactivate the one you retired.

### A retirement can be refused

Two conditions stop an entry from leaving a live status, because the generated config could not survive
the withdrawal:

- **No live role would be left** while an agent backend is enabled — the generated config would have
  no agent to present. Activate another role first.
- **A live role still preloads the skill** you're retiring — that role's file would go on naming a
  skill that is no longer there. Sever the scoping, or retire the role too.

The refusal names the entry, states the condition, names the live roles a skill is still scoped to,
and gives the next step where one exists. Retiring the `deploy-runbook` skill above while `devops`
still carries it:

```
error: cannot move SKILL-19 to 'Archived': the resulting projection would be structurally invalid:
- SKILL-19: not live (status 'Archived') but still scoped to live role(s): devops
  — remedy: pass --unlink, or run `sq skill <addr> unlink-role <role>` first
```

**`--force` does not override either condition.** It overrides a transition the *lifecycle* disallows
— the same thing it does on a work item — and neither of these is about a lifecycle edge.

**`--unlink` severs the dependency instead of suppressing the check:**

```bash
sq skill <addr> status Archived --unlink
```

It removes exactly the scoping edges the refusal enumerated, reports each one it removed, and then runs
the ordinary check again — which passes on its own merits. If the check still refuses, nothing changes.
It is a real edit to your roster and not a bypass, so reactivating the skill later brings the skill back
but not the scoping; re-attach it with `sq skill <addr> link-role <role>`. On a transition that isn't a
retirement the flag is an error, not a no-op. The flag is accepted on any retirement, but the only
severable dependency today is a custom skill's scoping to a role — on a role or operator it reports that
there was nothing to sever.

Where no remedy exists, the refusal says so rather than naming a step that wouldn't work. A skill every
live role preloads unconditionally can't be retired at all, and a skill implied by a declared item type
can't be un-implied.

### `sq check` reports the same two conditions on disk

A transition check only sees transitions. A squad can reach either state another way — an entry removed
rather than retired, or a skill scoped to a role after the skill was archived — so `sq check` reports
both against state already on disk, naming the entry, the condition, and a remedy where one exists.

## How roles, skills, and items connect

Roles ↔ item types is the **playbook** (`squads._interactions`). It drives two things: which roles
appear as sections in each `sq-<type>` skill, and which skills a role's pointer preloads
(`skills_for_role`). It is customisable: `.overrides/playbook.toml` reworks a type's guidance, or
gives a role you defined yourself a section in a type's skill — see
[overrides.md](overrides.md#playbook-overrides-role-guidance-per-item-type). See
[workflow.md](workflow.md) for the team flow and
[internals.md](internals.md#8-roles-and-the-playbook) for the
mechanics. Role/dev metadata is stored on the role item's `extra` (keys in `ExtraKey`).

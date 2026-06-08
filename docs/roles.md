# Roles

A squad is a roster of named agents. Each role has a **real name** (used in files and conversation)
and a **slug** (used on the CLI and as the Claude agent name). Roles are activated at `init`/`adopt`
or later with `sq role activate <slug>`.

## The bundled roster

| Name | Slug | Title | Model | Color | Item skills it manages |
|------|------|-------|-------|-------|------------------------|
| Catherine Manager | `manager` | manager *(default)* | opus | cyan | — (triages & routes; `squads` skill only) |
| Robert Architect | `architect` | architect | opus | blue | `sq-epic`, `sq-decision`, `sq-guide` |
| Olivia Lead | `tech-lead` | tech lead | opus | purple | `sq-epic`, `sq-feature`, `sq-task`, `sq-bug`, `sq-decision`, `sq-guide` |
| Paul Reviewer | `reviewer` | code reviewer | opus | red | `sq-task`, `sq-bug`, `sq-review` |
| Mara Tester | `qa` | QA engineer | sonnet | green | `sq-feature`, `sq-task`, `sq-bug` |
| Hugo Ops | `devops` | DevOps engineer | sonnet | orange | — (`squads` skill only) |
| Nina Product | `product-owner` | product owner | sonnet | yellow | `sq-epic`, `sq-feature` |
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
`sq-bug`, and `sq-review`.

## Managing roles

```bash
sq role list                 # active roles
sq role list --available     # the bundled catalog
sq role show architect       # a bundled role's definition
sq role activate qa          # add a role later (creates its item + Claude pointer)
sq role regen ROLE-000002    # re-render its pointer from the item
sq role rm ROLE-000002 [--purge]
```

## How roles, skills, and items connect

Roles ↔ item types is the **playbook** (`squads._interactions`). It drives two things: which roles
appear as sections in each `sq-<type>` skill, and which skills a role's pointer preloads
(`skills_for_role`). See [workflow.md](workflow.md) for the team flow and
[internals.md](internals.md#8-roles-and-the-playbook-_roles_catalogpy-_interactionspy) for the
mechanics. Role/dev metadata is stored on the role item's `extra` (keys in `ExtraKey`).

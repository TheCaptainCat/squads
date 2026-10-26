# Roles

A squad is a roster of named agents. Each role has a **real name** (used in files and conversation)
and a **slug** (used on the CLI and as the Claude agent name). Roles are activated at `init`/`adopt`
or later with `sq role activate`, `sq role add` or `sq dev add`, which is also where you get to
name them — see
[overrides.md § "Agent naming"](overrides.md#agent-naming) for every way a name can be set and
[§ "Which name wins"](overrides.md#which-name-wins) for which one applies when two disagree. A
role's name is decided when the role is created and then stored; no configuration change renames
it, and `sq role <slug> update --title` does.

## The bundled roster

| Name | Slug | Title | Model | Color | Item skills it manages |
|------|------|-------|-------|-------|------------------------|
| Catherine Manager | `manager` | manager *(default)* | opus | cyan | — (triages & routes) |
| Robert Architect | `architect` | architect | opus | blue | `sq-epic`, `sq-decision`, `sq-contract`, `sq-guide` |
| Olivia Lead | `tech-lead` | tech lead | opus | purple | `sq-epic`, `sq-feature`, `sq-task`, `sq-bug`, `sq-decision`, `sq-contract`, `sq-milestone`, `sq-guide` |
| Paul Reviewer | `reviewer` | code reviewer | opus | red | `sq-task`, `sq-bug`, `sq-review` |
| Mara Tester | `qa` | QA engineer | sonnet | green | `sq-feature`, `sq-task`, `sq-bug` |
| Hugo Ops | `devops` | DevOps engineer | sonnet | orange | — |
| Nina Product | `product-owner` | product owner | sonnet | yellow | `sq-epic`, `sq-feature`, `sq-contract`, `sq-milestone` |
| Theo Writer | `tech-writer` | technical writer | sonnet | pink | `sq-guide` |

Every role also gets three general skills: **`squads`** (how to use the CLI), **`greeting`** (the
start-of-session ritual) and **`sq-memory`** (its memory notebook and the team board). A role that
doesn't manage an item type doesn't get that type's skill — that's why the manager and devops carry
only those three.

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

## Where a role's definition comes from

A role item stores the role's identity: its slug, its name, its status and the values a role verb
sets (the default-role designation, `model`, `pronouns`). Its **definition** (job title, one-line
description, mission, responsibilities, working agreements, colour, spawn authority and
capabilities) is resolved from one **base** every time the role is read. There are three kinds:

| Base | The definition comes from | How the role is created |
|---|---|---|
| **Catalog** | the slug's entry in the role catalog: the bundled `roles.toml` with your `.overrides/roles.toml` merged in | `sq role activate <slug>` |
| **Template** | a `[templates.<name>]` table of the same catalog, filled in with the role's `tech` | `sq role activate [<slug>] --from <template>`, or `sq dev add` |
| **Item** | the role item itself | `sq role add <slug>` |

The kind is decided from what the role item stores, never by looking the slug up in the catalog: a
role that stores `template` is built from that template, otherwise a role that stores `mission`
defines itself, otherwise the role is a catalog role. So a catalog entry added later under the slug
of a role that defines itself does not change that role.

Every kind resolves the same way:

1. build the base;
2. merge `.overrides/roles/<slug>.toml` over it field by field, when the file exists;
3. apply the values the role item stores: its name, its default-role designation, `model` and
   `pronouns`. A stored value wins over the base and the per-slug file.

A role whose base does not resolve (a catalog role whose entry is gone, a template role whose
template is not declared) is still materialised from what it stores, and `sq check` reports it at
`error` under `role_base_resolves`, with the remedy:

```
error ROLE-27: role 'designer' is backed by no catalog entry: restore the entry, or make the role define itself with `sq role designer update --job-title … --desc … --mission …`
```

`sq role <slug> show` prints the same role with a line saying its definition could not be resolved
and that `sq check` reports why.

## Role templates

A role template is a `[templates.<name>]` table of the role catalog. It declares a definition with
placeholders, and every role built from it is an instance. The bundled catalog declares one,
`dev`; a squad adds its own, or changes a bundled one field by field, in `.overrides/roles.toml`:

```toml
# .overrides/roles.toml
[templates.security]
slug = "{tech}-security"
name = "{first} {Tech}sec"
name_pool = ["Mallory", "Trent"]
title = "{Tech} security reviewer"
description = "Reviews {Tech} changes for security issues."
mission = "Find security defects in {Tech} code before they ship."
responsibilities = ["Review {Tech} changes for injection and auth flaws"]
capabilities = ["review"]
model = "opus"
color = "red"
```

```
$ sq role activate --from security --tech rust
added Mallory Rustsec (`rust-security`) ROLE-24
```

**Keys.** `title`, `description` and `mission` are required. `responsibilities`, `agreements`,
`model`, `color`, `can_spawn` and `capabilities` are optional, with the meaning and validation
they have on a `[[roles]]` entry. Three keys belong to templates only: `slug`, the slug pattern;
`name`, the name pattern; and `name_pool`, the first names `{first}` draws from. `full_name` and
`is_default` are refused: the name is chosen when a role is created, and the default designation
belongs to a role. A missing required key or an unknown one is refused at load, naming the
template:

```
error: …/.overrides/roles.toml: Invalid role template [templates.missing]: missing required key(s): description, mission
```

**Placeholders.** There are exactly three:

- `{tech}`: the value given to `--tech`, as given;
- `{Tech}`: the same value with its first letter upper-cased;
- `{first}`: a first name from `name_pool`, valid in `name` only.

`{{` and `}}` write a literal brace. Any other `{…}`, and `{first}` outside `name`, is refused at
load, naming the template and the key:

```
error: …/.overrides/roles.toml: role catalog invalid after merge:
  - template 'badph': title: unknown placeholder {tch}; the placeholders are {tech}, {Tech}, and {first} in `name`
```

A template that uses `{tech}` or `{Tech}` anywhere takes a technology: building a role from it
requires `--tech`, and a template that uses neither refuses `--tech`. In `slug`, the substituted
value is slugified, so `--tech Node.js` gives `node-js-dev` from the bundled `{tech}-dev`.

**Slug and name.** With `--from`, the slug argument is optional when the template declares a
`slug` pattern, and required otherwise. The name is, in order: `--name`; else a `full_name` in a
`.overrides/roles/<slug>.toml` present when the role is created; else the `name` pattern, with
`{first}` taken from `name_pool` at the position given by the number of roles already built from
this template (wrapping round the pool). A template with no `name` pattern requires `--name`. Each
refusal exits `1` and writes nothing:

```
error: role template 'dev' takes a technology: pass --tech
error: role template 'scribe' takes no --tech
error: role template 'scribe' declares no slug pattern: name the role, `sq role activate <slug> --from scribe`
error: role template 'scribe' declares no name pattern: pass --name
error: no role template 'nope'; the declared templates are: dev
```

**What a template role stores.** `template` (the template's name), `tech` when the template takes
one, and `model` only when `--model` was given. Without a stored model the role follows the
template's `model`, so a change to the template reaches the roles already built from it on the
next `sq sync`, like every other field of the template. A role's own name never changes with the
template.

**Origin.** A role built from a bundled template, overridden or not, is `system`; one built from a
template your `.overrides/roles.toml` declares is `project` (see
[Where a role or skill comes from](#where-a-role-or-skill-comes-from-origin)).

A template you change in `.overrides/roles.toml` merges field by field onto the bundled one, and a
splat-ref appends to a bundled list: `responsibilities = ["$(*self)", "Run the {Tech} linters"]`
under `[templates.dev]` adds a line to every developer, with `{Tech}` filled in per developer.
`[selected] templates` lists the templates that survive (see
[overrides.md § "The role catalog override"](overrides.md#the-role-catalog-override-rolestoml)).

## Stack-specific developers

Developers are built from the bundled `dev` template, on demand. The bundled set of roles is
deliberately stack-agnostic:

```bash
sq dev add --tech dotnet                 # → "Elias Dotnet"  slug: dotnet-dev
sq dev add --tech python --name "Grace Hopper"
sq dev add --tech go --slug gopher       # → stored under the slug you give
sq dev list
```

`sq dev add --tech <t> --slug <s>` is exactly `sq role activate <s> --from dev --tech <t>`, and without `--slug` it is `sq role activate --from dev --tech <t>`,
with the same options, messages and result. If you omit `--name`, the first name comes from the
template's pool and the surname is the tech (so `--tech dotnet` gives *Elias Dotnet*). The slug is
`<tech>-dev` by default, with the tech slugified (`--tech Node.js` gives `node-js-dev`). The name and
the slug are kept as they are by every later `sq sync`, and no later override renames the
developer. If a squad drops the `dev` template, `sq dev add` exits `1` naming the templates it
declares.

`--slug` follows the rules every role slug follows: lowercase letters, digits and hyphens, not
`operator` or `squads`, not starting with `op-`, and not a verb of `sq role`. It is also refused
when it is already taken, or when the role catalog (bundled or your `.overrides/roles.toml`)
declares a role under it, even one you have not activated, with exit `1` and nothing written:

```
error: slug 'reviewer' belongs to a role the catalog declares; `sq role activate reviewer` activates it, or pick another slug
error: a role with slug 'gopher' already exists
```

### What makes a role a developer

**A developer is a live role that holds a capability the `dev` template declares.** The bundled
template declares one, `dev`, so every role built from it is a developer. Any other role becomes a
developer by holding that capability in its own definition (see [Capabilities](#capabilities)
below):

```bash
sq role add builder --name "Bob Builder" --job-title "build engineer" --desc "Owns the build and the release pipeline." --mission "Keep the build green." --capabilities dev
```

The slug says nothing either way: a role named `legacy-dev` that holds no such capability is an
ordinary role, and `builder` above is a developer. Every developer takes part in the playbook
guides addressed to `*dev`, which is why each one manages `sq-task`, `sq-bug`, `sq-contract` and
`sq-review` with the bundled playbook. `sq dev list` lists the live developers, built from the
template or not, with the `tech` of those that have one.

A developer's fields are overridable like any other role's: a `.overrides/roles/<slug>.toml` that
sets only `title` changes only that developer's title, and the other fields keep following the
template. Worked example:
[overrides.md § "Retitle a developer without renaming them"](overrides.md#retitle-a-developer-without-renaming-them).
To change every developer at once, change `[templates.dev]` in `.overrides/roles.toml` instead.

## Capabilities

A capability is a name a role holds, so that playbook guidance can address every role holding it
instead of naming roles one by one. A role declares its capabilities as a `capabilities` list in
any of the places its definition comes from:

- a `[[roles]]` entry in `.overrides/roles.toml`;
- a `[templates.<name>]` table, for every role built from that template;
- the role item, for a role that defines itself (`sq role add --capabilities`, `update
  --capabilities`);
- its per-slug file, `.overrides/roles/<slug>.toml`.

A name is lowercase letters, digits and hyphens, and does not start with a hyphen
(`[a-z0-9][a-z0-9-]*`). A per-slug file's list replaces the list it merges over, and the splat form
appends to it instead: `capabilities = ["$(*self)", "infra"]`. A name repeated across the merge
counts once. A malformed name is refused naming the file, by `sq check` (exit `3`) and by `sq sync`
(exit `1`):

```
error: invalid role override …/.overrides/roles/reviewer.toml: capabilities entry 'Rev' must match [a-z0-9][a-z0-9-]*
```

Five bundled roles declare one each, and the bundled `dev` template declares `dev`:

| Capability | Held by | What the bundled hand-offs ask of it |
|---|---|---|
| `plan` | `tech-lead` | break an epic or feature down, triage a bug, apply an accepted decision, take in a milestone's work |
| `review` | `reviewer` | review a change |
| `verify` | `qa` | verify a change against the acceptance criteria |
| `product` | `product-owner` | answer a scope question, act on a slipping milestone |
| `edit` | `tech-writer` | polish a draft guide |
| `dev` | every developer | implement or fix |

The manager, the architect and devops hold none. To move a bundled ask to another role, give that
role the capability, and take it off the bundled holder if it should stop receiving it:

```toml
# .overrides/roles/tech-lead.toml — the tech lead reviews too
capabilities = ["$(*self)", "review"]
```

```toml
# .overrides/roles/reviewer.toml — and the reviewer stops receiving review hand-offs
capabilities = []
```

Run `sq sync` after either change to regenerate the skills.

**Addressing a capability in the playbook.** A guide whose `slug` is `*<capability>` applies to
every live role holding that capability (see
[overrides.md § "Playbook overrides"](overrides.md#playbook-overrides-role-guidance-per-item-type)).
Its section in the generated `sq-<type>` skill is headed with the capability and lists the holders,
for example ``## For `*dev`: Elias Python (`python-dev`)``, and it renders only while a live role
holds the capability. `authors = true` on such a guide puts the type in the create lane of every
holder.

**Where capabilities show.** `sq role list` has a Capabilities column and the `sq role <slug> show`
card a `capabilities:` row. `--json` carries a `capabilities` array (empty when there are none) in
`sq role list`, `sq role <slug> show` and each `roster[]` row of a view whose source is `playbook`.
`sq role catalog --json` carries one too, with the catalog document's value: like the name and title
beside it, it is read before any per-slug role file, so a capability a per-slug file declares shows
in `sq role list` and `sq role <slug> show` but not in the catalog.

### Mentioning a capability in hand-offs

In playbook text, the guide lines (`enter`, `do`, `handoff`, `watch`) and a type's `commands`,
`@*<name>` mentions every live role holding the capability `<name>`. The bundled hand-offs are
written this way, for example "comment a summary of what changed + `@*review`/`@*verify`".
`sq sync` resolves the token when it generates the `sq-<type>` skill, against the live roster:

- each holder renders as its `@<slug>`, in roster order (the order of `sq role list`) and joined
  with `/`: with the tech lead holding `review` as above, `@*review` renders as
  `@tech-lead/@reviewer`;
- with no live holder, the token renders as `*<name>`, without the `@`. The line is kept and nobody
  is mentioned: in a squad without `qa`, `@*review`/`@*verify` renders as `@reviewer`/`*verify`;
- a retired role holds nothing, and an operator holds no capability, so a token never expands to an
  `op-` slug. To hand off to a person, write the literal `@op-<slug>`.

Each token resolves on its own, so a role holding two capabilities named on one line appears once
per token. A literal `@<slug>` is not a token and names that one role; write one when a hand-off should
always go to one particular role. The token belongs to playbook text only: typed in a comment, `@*review`
mentions nobody, so a comment names its recipients by slug.

The item's author is not a capability: a skill is rendered once per type, and the author differs on
every item. So the review guide's developer hand-off says it in words, "`@`-mention the review's
author (shown on `sq review <n> show`) once all findings are Fixed, for re-review".

A token whose name does not match `[a-z0-9][a-z0-9-]*` is a playbook load error, and every command
stops until the line is fixed:

```
error: …/.overrides/playbook.toml: Invalid playbook:
  - types.bug: capability token '@*Sec' must be @*<name>, with a name matching [a-z0-9][a-z0-9-]*
```

A well-formed token that no live role holds, in a guide of your `.overrides/playbook.toml`, is a
warning from `sq check` and `sq sync` (see
[overrides.md § "Rules"](overrides.md#rules)); the same token in a bundled guide renders as
`*<name>` without one.

## Managing roles

```bash
sq role list                 # active roles
sq role catalog              # the catalog, plus every role it does not declare
sq role architect show       # a role's resolved definition
sq role activate qa          # add a catalog role later (creates its item + Claude pointer)
sq role activate --from dev --tech go           # build a role from a role template
sq role add sre --name "Sam Reliability" --job-title "site reliability engineer" --desc "Keeps production up." --mission "Keep the services up and the pager quiet."
sq role ROLE-000002 regen    # re-render its pointer from the item
sq role ROLE-000002 status Archived [--force] [--unlink]   # transition its Active/Archived status
sq role ROLE-000002 set-default                 # move the default-role designation here
sq role architect update --title "Ada Archer"   # rename the role; the slug stays
sq role architect comment -m "…" --as manager   # comment on it (comments, show --comments to read)
sq role ROLE-000002 remove --purge              # delete the role and its file
```

`sq role <slug> show` ends with how to change the role. For a catalog or template role it reads
``To change its mission or responsibilities: `sq override scaffold --role <slug>`, edit the file,
then `sq sync`. To change its model: `sq role <slug> update --model …`.`` (see [overrides.md § "`sq override scaffold`"](overrides.md#sq-override-scaffold));
for a role that defines itself, ``To change its definition: `sq role <slug> update --mission …` (or
--file).`` The line is not part of `--json`.

`sq role list` shows every activated role with a **Live** marker — a retired role stays on the
roster and simply stops being live. See ["Retiring a roster entry"](#retiring-a-roster-entry) for
what that costs you and how to undo it. `sq role list --json` carries each role's resolved
one-line `description`. A generic item row (`sq list -t role --json`) carries only what the item
stores, so its `description` is empty on a catalog or template role and is the role's own on a
role that defines itself.

`set-default` moves the designation rather than merely setting it: it clears every other role
that carries it in the same transaction, so the roster never ends up with two. It refuses a
role that isn't live, and designating the role that already holds it is a reported no-op. This
is also the way back if a squad has lost its default-role line to a retirement — reactivating
the previous holder is the only other recovery.

`sq role catalog` lists each role the catalog declares, activated or not, and one more row for
every role item the catalog does not declare: a role built from a template, or a role that defines
itself. Such a row stays while the item exists, retired or not. Both listings mark the default-role holder.
`sq role catalog --json` also carries it on every row as `default_role` (the holder's slug, `null`
when no live role holds it), alongside `default_role_source`, which is `roster` for the active
squad's designation and `catalog` for the bundled document's own declaration, the answer you get
outside a squad.

### Custom roles: `sq role add`

Beyond the catalog and the role templates, a squad can create a wholly custom role, such as a
designer, a `security-analyst` or an `incident-commander`, whose definition is stored on the role
item itself. `sq role add` takes the definition as flags:

```bash
sq role add sre --name "Sam Reliability" --job-title "site reliability engineer" --desc "Keeps production up." --mission "Keep the services up and the pager quiet." --capabilities ops,infra
```

`--name`, `--job-title`, `--desc` (the one-line description) and `--mission` are required;
`--capabilities` (comma-separated), `--model` and `--pronouns` are optional. `--file` reads the
same definition from a TOML file in the `.overrides/roles/<slug>.toml` grammar, with `full_name`
for the name and `title` for the job title, so a file written as an override can be passed as it
is. A flag given beside `--file` wins over the file's key:

```toml
# compliance.toml
full_name = "Cora Compliance"
title = "compliance officer"
description = "Keeps the project's work compliant."
mission = "Review changes for regulatory and policy compliance."
responsibilities = ["Review changes for compliance", "Flag licensing issues"]
capabilities = ["review"]
color = "orange"
```

```bash
sq role add compliance-officer --file compliance.toml
```

Every missing required field is named in one message, `is_default` in the file is refused naming
`set-default`, and a malformed capability is refused, each with exit `1` and nothing written:

```
error: role 'sec' is missing required fields: --job-title (title), --desc (description), --mission (mission); pass the flags, or a --file that sets them
error: --capabilities entries must match [a-z0-9][a-z0-9-]*: Rev
```

The role stores `job_title`, `description`, `mission` and whichever of `responsibilities`,
`agreements`, `color`, `can_spawn` and `capabilities` it was given. Its origin is `project`, and
`add` writes the role's pointer as `activate` does.

A custom role's slug follows the role rules: lowercase letters, digits and hyphens, neither
`operator`, `squads` nor anything that starts with `op-`, and not a verb of `sq role`
(`activate`, `add`, `catalog`, `list`), so `sq role <slug> show` always reaches it. A slug the role
catalog declares is refused, naming `sq role activate`, and so is a slug already taken:

```
error: slug 'reviewer' belongs to a role the catalog declares; `sq role activate reviewer` activates it, or pick another slug
```

### Changing a role: `update` per kind

`sq role <slug> update` edits what the role item stores. What it accepts depends on the role's
base:

| Option | Catalog role | Template role | A role that defines itself |
|---|---|---|---|
| `--title` (the name), `--pronouns` | yes | yes | yes |
| `--model` (a blank value clears it) | yes | yes | yes |
| `--job-title`, `--desc`, `--mission`, `--capabilities`, `--color`, `--can-spawn yes\|no` | refused | refused | yes |
| `--file <toml>` | refused | refused | yes |

`--file` takes a delta in the `.overrides/roles/<slug>.toml` grammar, merged field by field over
the role's current definition, and `$(*self)` in a list stands for the role's current list:
`responsibilities = ["$(*self)", "Run the incident review"]` adds one. It refuses `slug`,
`full_name` and `is_default`, naming `update --title` and `set-default`. `tech` and `template`
are never updatable: they choose the base, and a different base is a different role.

On a catalog or template role, a definition option exits `1`, writes nothing and names the file
that holds the definition and the command that starts it:

```
error: architect's definition (--mission) comes from the role catalog; set it in .overrides/roles/architect.toml (sq override scaffold --role architect)
error: python-dev's definition (--mission) comes from the role template 'dev'; set it in .overrides/roles/python-dev.toml (sq override scaffold --role python-dev), or in [templates.dev] of .overrides/roles.toml for every role built from the template
```

When a per-slug file also sets a field `update` writes on a role that defines itself, the write
happens and a warning says the file wins until it drops the key; `sq check` reports the same
state under `role_definition_shadowed`:

```
warning: .overrides/roles/sre.toml also sets mission: the file wins over the role's stored definition, so the change has no effect until the file drops the key
```

`update --job-title … --desc … --mission …` given together on a role whose base does not resolve
makes it a role that defines itself; that is the remedy `role_base_resolves` names. An `update`
event of `sq import` that sets a definition field is refused on the same terms.

## Managing skills

Skills are the instruction files a role preloads. Every role carries the general `squads`,
`greeting` and `sq-memory` skills plus one `sq-<type>` skill per item type it manages; those are
generated and kept in step for you. You can add skills of your own and scope them to whichever roles
should carry them:

```bash
sq list -t skill                        # the skills this squad has (there's no dedicated list verb)
sq skill add "deploy-runbook" --desc "How we ship."   # create a custom skill
sq skill deploy-runbook body --file runbook.md        # write its content (refuses once written:
                                                      #   --append to add, --force to replace)
sq skill deploy-runbook link-role devops              # scope it to a role (resyncs that role now)
sq skill deploy-runbook unlink-role devops            # remove the scoping
sq skill deploy-runbook update --desc "How we ship to production." --when-to-use "When releasing"
sq skill deploy-runbook show
sq skill deploy-runbook regen                         # re-render its pointer from the item
sq skill deploy-runbook status Archived [--force] [--unlink]   # transition its Active/Archived status
sq skill deploy-runbook remove --purge                    # delete the skill and its file
```

A generated skill's body is not yours to write — `body` refuses one, replace and append alike,
because its content already comes from the playbook overrides or its view's template override. Author
the skills you add; leave the generated ones to `sq`. A skill slug is lowercase letters, digits and
hyphens, unique among skills, and never `add`, the one verb of `sq skill`. A skill never authors
anything, so a skill slug is not accepted by `--as`, `--author` or `--assignee`. To write a
generated skill's body yourself, see
[overrides.md § "Authoring a role or skill body by hand"](overrides.md#authoring-a-role-or-skill-body-by-hand).

### Whether an operator can invoke a skill

Every skill says whether an operator can run it by name in the agent host (`/greeting` in Claude
Code). Agents load skills either way. Each skill has a declared default:

| Skill | Operator invocable by default |
|---|---|
| `squads`, `greeting`, `sq-memory` | no |
| every `sq-<type>` skill | no |
| a skill you add with `sq skill add`, whatever its name | yes |

A squad chooses its own value per skill with `--operator-invocable`, on `sq skill add` and
`sq skill <slug> update`:

```bash
sq skill greeting update --operator-invocable yes    # store "invocable"
sq skill runbook update --operator-invocable no      # store "not invocable"
sq skill greeting update --operator-invocable default   # drop the stored choice, follow the default
```

`yes` and `no` store the choice, even when it equals the default, and a stored choice is never
overwritten by a later release. `default` removes it, so the skill follows its declared default,
including a default a later release changes, from the next `sq sync`. Leaving the option out
changes nothing, and any other value exits `1` with nothing written:
`error: --operator-invocable takes yes, no or default, not 'maybe'`. The option is accepted on a
generated skill, where it is the one change `update` allows: a generated skill's title,
description and when-to-use stay refused, and a command that combines them with the option is
refused whole. `--set operator_invocable=…` and an `sq import` `fields` entry naming it are
refused.

**What the agent host does with it.** In Claude Code, a skill that is not operator invocable gets
`user-invocable: false` in its `.claude/skills/<slug>/SKILL.md` pointer, and an invocable one
gets no such line. The operator then cannot run it as `/<slug>`, but an agent that lists the skill
still preloads it. The `AGENTS.md` backend has no place for
the value and writes nothing for it.

**Where it shows.** `sq skill <slug> show` prints `operator invocable: yes|no`, followed by
`(set by this squad)` or `(declared default)`, and its `--json` carries `operator_invocable`
(the resolved boolean) and `operator_invocable_set` (whether the squad chose it). The stored
choice is the `operator_invocable` key in the skill's frontmatter, so a generic item row
(`sq list -t skill --json`, `sq show`) carries it only when the squad has stored one.

## Updating and commenting on roles, skills and operators

Roles, skills and operators take the item verbs `update`, `body`, `comment`, `comments`, `status`
and `remove`, plus `show --comments`. Roles and skills also take `regen` and `view`, and a role
takes `set-default`. `update` changes display fields, plus a skill's operator-invocable choice
and what a role stores:

| Entry | `update` options | Refused on |
|---|---|---|
| skill | `--title`, `--desc`, `--when-to-use`, `--operator-invocable` | a generated skill (`squads`, `greeting`, `sq-memory`, `sq-<type>`) refuses `--title`, `--desc` and `--when-to-use`; `--operator-invocable` is accepted on any skill |
| role | `--title` (the role's name), `--pronouns`, `--model`; and `--job-title`, `--desc`, `--mission`, `--capabilities`, `--color`, `--can-spawn`, `--file` | the definition options, on a catalog or template role (see [Changing a role](#changing-a-role-update-per-kind)) |
| operator | `--title` (the display name), `--pronouns` | none |

The slug, the file name and the id never change. A role renamed with `update --title` keeps the
name through every `sq sync` and every override change, and its pointer and the `CLAUDE.md`
roster line show the new name at once. When a skill's body is still the scaffold it was created
with, `update` re-renders it from the new values; a body you have written is kept as it is.
`update` with no option exits `1`, writes nothing, and names the options of that kind of entry;
on an operator:

```
error: nothing to update (pass at least one of --title, --pronouns)
```

On a role it names `--title, --pronouns, --model, --job-title, --desc, --mission, --capabilities,
--color, --can-spawn, --file`, and on a skill `--title, --desc, --when-to-use, --operator-invocable`.

`body` sets an entry's prose (`-m`, `--file`, `--file -`, `--append`, `--force`), and prints
`<ID>: body set` or `<ID>: body appended`. It follows a different rule on each kind of entry:

- **An operator** is always writable, retired or not. Its body is its profile (see
  "The operator profile" below). The first write replaces the seeded operator text without
  `--force`; replacing a profile you have written needs `--force`, and `--append` adds to it.
- **A role** is refused while its `role_definition` view is in `[selected]`, `--force` or not,
  with the error naming the role override. Once the project drops the view, `body` writes; then
  clear each role's leftover tag with `sq role <slug> view disable role_definition`, or `sq check`
  reports it as an undeclared view. A role not on the roster is refused with
  `activate it first`.
- **A skill** you added takes `body` like any item. A generated skill is refused, naming the
  playbook or the view's template override.

A role or operator body may hold prose, and `sq check` accepts it: a role whose body holds prose
and no view tag prints that prose in place of its generated definition. `sq check` reports a role
body only when it holds neither prose nor a tag, or holds a damaged `sq:view:` tag.

`comment` and `comments` work as on any item, on a generated role or skill too. Every skill file
has a `## Discussion` region for them, as role and operator files do. A comment's `@mention`
reaches `sq inbox`, except on a retired entry.

## Pronouns

A role or an operator can carry pronouns, shown after its name: `Robert Architect (she/her)`.

```bash
sq role architect update --pronouns "she/her"      # any role, a bundled one included
sq operator add "Alice Tester" --pronouns "they/them"
sq dev add --tech rust --pronouns "he/him"
sq role activate qa --pronouns "she/her"           # at activation
sq role architect update --pronouns ""             # a blank value clears them
```

`sq role activate` with `--pronouns` on a role that is already live is refused, naming
`update`; `sq init` has no pronouns option. `--set pronouns=…` and an `update` event of
`sq import` that sets `pronouns` are refused and name the verb, so these verbs are the only way to
write them.

**The value** is trimmed, one line, and 1 to 40 characters counted after Unicode normalisation
(NFC), with no control character, no invisible formatting character (a bidi override or a
zero-width mark) and no sq marker tag. A blank is never stored. A value that breaks the rule is
refused with exit `1`:

```
error: pronouns is 41 characters long; the limit is 40
error: pronouns must be one line with no control or invisible formatting characters
```

The value is stored as `pronouns` in the item's frontmatter. A hand-edited value that breaks the
rule is read as unset, and `sq check` reports it as an error (`pronouns_valid`, always on for roles
and operators), with the command that replaces it:

```
error ROLE-4: pronouns must be one line with no control or invisible formatting characters — replace it with `sq role reviewer update --pronouns <text>`
```

**A roster default.** A `[defaults]` table in `.overrides/roles.toml` declares pronouns for every
role that has none of its own:

```toml
# .overrides/roles.toml
[defaults]
pronouns = "they/them"
```

Run `sq sync` after adding or removing it. The default applies to roles only, never to operators,
and is never written onto an item: remove it and sync, and every role without its own value has
none again. A role's own value always wins, and a role cannot have no pronouns while a default is
declared. The value follows the same rule and is refused at load when it breaks it. A `pronouns`
key in a `[[roles]]` entry or a per-slug role file is refused, naming the `update` verb. The
bundled catalog declares no default.

**Where they show.** The roster lines of the generated `CLAUDE.md` and `AGENTS.md` sections and an
agent's own pointer always carry them (`You are **Robert Architect** (she/her), the architect on
this project.`); `sq sync` picks up a change. Human CLI output and `sq ui` print `Name (pronouns)`,
with the parenthesis dimmed. `sq role list --json`, `sq role <slug> show --json`,
`sq operator list --json` and `sq operator <slug> show --json` carry `pronouns`, right after
`full_name`: the resolved value (a role's own, else the default) or `null`, on every row. An item
row (`sq list -t role --json`) carries the stored key only, like any attribute. Pronouns never
appear in a comment header or a discussion entry.

**Turning the human display off.** `.squads.toml` takes a `[display]` table with one key:

```toml
[display]
pronouns = false
```

It removes the parenthesis from human CLI output and `sq ui` only. `--json`, exit codes, stored
data and generated agent files are the same either way. An unknown key or a value that is not a
boolean (a quoted `"false"` is a string) never stops a command: the default (`true`) applies and
`sq check` warns, through the always-on `display_config_valid` check:

```
warn .squads.toml: [display] has an unknown key 'colour'; the default applies
warn .squads.toml: [display] pronouns must be true or false, got 'false'; the default applies
```

The VS Code extension has its own setting, `squads.showPronouns` (on by default), for its Roster
view and mention hovers, and does not read `[display]`.

## Where a role or skill comes from: `origin`

Every role and skill stores `origin`, one of two words, written when the entry is created:

- **`system`** — squads supplies it. A role is `system` when the bundled role catalog declares its
  slug, or when it is built from a template the bundled catalog declares (such as `dev`, for
  `sq dev add`). A bundled role or template you override, in `roles.toml` or
  `.overrides/roles/<slug>.toml`, stays `system`. A skill is
  `system` when it is `squads`, `greeting` or `sq-memory`, or the `sq-<type>` skill of a type the
  workflow spec declares.
- **`project`** — your squad defined it: a role declared by a `[[roles]]` entry of `roles.toml`,
  a role built from a template `roles.toml` declares, a role created with `sq role add`, and every
  skill added with `sq skill add`.

The stored value is the answer every surface gives: the Origin column of `sq role list` and
`sq role catalog`, the `origin:` row of the `sq role <slug> show` and `sq skill <slug> show`
cards, and the `origin` key of their `--json`, of `sq role catalog --json` and of
`sq list -t role|skill --json`. It is never recomputed: `sq sync` leaves it alone, and the
`sq-<type>` skill of a type you later drop keeps `system`. Nothing sets it afterwards; an `update`
event of `sq import` that tries is refused:

```
'origin' is not a settable field on a skill (a dedicated command owns it); valid: allowed_tools, model, when_to_use
```

`sq check` reports a role or skill file whose `origin` is missing or is not one of the two words:

```
error SKILL-20: missing required attribute 'origin'
error SKILL-22: attribute 'origin': expected one of system, project, got 'System'
```

### What a generated role or skill refuses

A role's body is generated from its definition, and so is a `system` skill's, through the view
tag in the body. While that view is declared, the content of such an entry is written where its
definition lives, not on the entry, and these writes are refused with exit `1`, nothing written,
`--force` or not:

- a body replace or append: `sq role <slug> body` or `sq skill <slug> body`, or a `body` event of `sq import`;
- `sq skill <slug> update --title|--desc|--when-to-use` (a command that adds
  `--operator-invocable` to one of them is refused whole), and an `update` event of `sq import` that sets the description, sets
  or unsets an attribute the bundled spec declares for the type (`fields`, `unset_fields`), or
  changes a skill's title; an event that also changes something allowed is refused whole;
- `view disable`, and `view add` of any view other than the entry's own.

The error names the place to edit instead:

```
line 1: ROLE-3's body renders through its declared sq:view:role_definition tag, and its content already has one validated authoring surface: `.overrides/roles.toml` (or `.overrides/roles/<slug>.toml`), or `sq role tech-lead update` for a role that defines itself. An update is refused — `--force` does not lift this. Drop the view from `[selected]` to author this directly instead, then clear its leftover tag with `sq role tech-lead view disable role_definition`.
```

For a catalog or template role, that is the role catalog override or its per-slug file, followed
by `sq sync`; for a role that defines itself, `sq role <slug> update`. A role's `model` is set with
`update --model` on any role. For a skill, it is the playbook override, or for
`greeting` and `sq-memory` the view's template override.

Every role is covered, a `project` one too, because every role's body is generated; a skill you
added with `sq skill add` takes every write. The rest stays open on every role and skill: a role's
title, pronouns and model (`sq role <slug> update --title|--pronouns|--model`), a skill's operator-invocable
choice (`sq skill <slug> update --operator-invocable`), labels, assignee and an attribute your workflow override
declares (through an `update` event of `sq import`), `status`, `remove --purge`, `comment`, `regen`,
and `view add` of the entry's own view, which is how `sq check`'s
remedies put a missing tag back. To write such an entry yourself, drop its view from `[selected]`
(see [overrides.md § "Authoring a role or skill body by hand"](overrides.md#authoring-a-role-or-skill-body-by-hand)):
the entry then takes every write, and keeps its `origin`.

## Operators (humans)

Roles are AI agents; **operators are the people**. Register a human so work can be assigned to
them and their words attributed to them — a manual step, a review point they dictated, or a task
handed to someone else on the repo:

```bash
sq operator add "Alice Tester"  # slug derived as op-alice (override with --slug)
sq operator list
sq operator op-alice update --title "Alice T."              # change the display name; the slug stays
sq operator op-alice body -m "Product lead."               # write the operator's profile
sq operator OP-000002 status Archived [--force] [--unlink]   # transition its Active/Archived status
sq operator OP-000002 remove --purge                            # delete the operator and its file
```

A slug is derived once, when the entry is created: lowercased, accented Latin letters spelled out
(`Élodie Martin` → `op-elodie`, `ß` → `ss`), and each run of any other characters turned into
one hyphen. The stored slug is the entry's identity from then on, and nothing re-derives or renames
it, even when squads changes how it derives new ones. `sq operator add`, `sq skill add` and `sq dev
add` refuse a name whose slug is already taken, including a slug stored under an earlier
derivation of the same name; pass `--slug` to register a genuinely different operator.

An operator's slug is `op-` followed by lowercase letters, digits and hyphens. A `--slug` outside
that form is refused with exit `1` and nothing written, and the message gives the compliant form
when one exists:

```
error: operator slug 'Anna' must start with 'op-' and be lowercase letters, digits and hyphens (e.g. 'op-anna')
```

A typed `--slug` is stored as typed, never lowercased or prefixed. A role's slug can be neither
`operator`, `squads` nor anything that starts with `op-`, so roles, operators and the two slugs sq
writes for itself never share one; see
[stability.md § "Comment headers"](stability.md#comment-headers).

Operators are first-class participants, but **not** agents: they're never spawned as subagents,
never get a `.claude/agents` pointer or skills, and don't appear in the agent roster (they have
their own "Operators (people)" roster in `CLAUDE.md`). Once registered, an `op-` slug is a valid
`--author` / `--assignee` (on items *and* sub-entities) and `--as` (on comments) — the same gates
that accept roles accept operators. There's no auto-detection or stored "current operator": at the
start of a session the agent works out who the human is (e.g. from `git config user.name`), checks
`sq operator list`, and asks whether to register them — and must ask if it's unsure.

### The operator profile

An operator's body is their profile: prose about their role on the project, their expertise and
what they come to do. It is set with `body`, and `show` prints it under the operator's card:

```bash
sq operator op-alice body -m "Product lead. Prefers short answers."
sq operator op-alice body --append -m "Works in CET."
sq operator op-alice show
```

There is no profile field or option: `operator add` takes no profile, and the body holds it.
The `greeting` skill reads it. When a human opens a session, the agent looks them up with
`sq list -t operator --all`:

- **registered:** it runs `sq operator <slug> show` and lets the profile set the register of its
  greeting and the project read-out, without reading the profile back. If the body is still the
  seeded text, it may offer to record a profile;
- **retired:** it asks whether to bring them back, runs `sq operator <slug> status Active`, then
  reads the profile;
- **not registered:** it asks first, and changes nothing on a no. On a yes it runs
  `sq operator add "<name>"`, asks three short questions (their role on the project, their level
  of expertise, what they come to do) and records the answers with
  `sq operator <slug> body --file <path>`.

Run `sq sync` after upgrading so the generated `greeting` skill carries these steps.

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

Retiring the only live author of a type is allowed too. While the type still holds an item at a
status that is not settled, `sq check` warns and names the way back, through the
`type_has_live_author` check the bundled `[squad] validators` list selects:

```
warn: type 'review' has 1 open item but no live role authors it — reactivate `reviewer` (`sq role reviewer status Active`)
```

When your role lifecycle has no edge from the retired status back to the live one, the command it
names ends in `--force`. Once every item of the type is settled, the warning goes away (see
[overrides.md § "Playbook overrides"](overrides.md#playbook-overrides-role-guidance-per-item-type)).
A squad that does not want the check leaves it out of its own `[squad] validators` list (see
[overrides.md § "Squad-wide checks"](overrides.md#squad-wide-checks-the-squad-table)).

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
- SKILL-19: not live but still scoped to live role(s): devops
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
retirement the flag is an error, not a no-op. Add `--as <slug>` to attribute the retirement, and every
line it writes, the severed `ref` lines and the `status` line, to that role or operator in the reflog;
without it they record `system`. `--unlink` is accepted on any retirement, but the only
severable dependency today is a custom skill's scoping to a role — on a role or operator it reports that
there was nothing to sever.

Where no remedy exists, the refusal says so rather than naming a step that wouldn't work. A skill every
live role preloads unconditionally can't be retired at all, and a skill implied by a declared item type
can't be un-implied.

### `sq check` reports the same two conditions on disk

A transition check only sees transitions. A squad can reach either state another way — an entry removed
rather than retired, or a skill scoped to a role after the skill was archived — so `sq check` reports
both against state already on disk, naming the entry, the condition, and a remedy where one exists.

## Removing a roster entry

Retiring keeps an entry on record; removing deletes it. `remove --purge` deletes the item file, a role's
or skill's generated pointer, and the entry's line in the compiled rosters, for a role, a skill and an
operator alike. `rm` is the same command under its short name. `--purge` is required: a plain
`remove` exits `1`, writes nothing and names the commands to choose from:

```
error: cannot remove ROLE-5 without --purge: the markdown file would stay on disk and `sq check` would flag it. To delete it for good, run `sq role ROLE-5 remove --purge`; to retire it and keep it on record, run `sq role ROLE-5 status Archived`.
```

A removal is held to the same structural checks as retiring the entry, so `remove --purge` is refused
wherever `status Archived` is (the last live role, or a skill the roles or item types still rely on),
and it prints the same warnings (open assigned work, a lost default-role designation). Removing an
entry that is already archived is not checked again. Each removal is recorded in the reflog.

The retire route is named only while the entry is live. Items the entry authored or is assigned keep
its slug, and `sq check` then reports them as naming an unregistered author or assignee. A slug freed
this way can be given to a new entry; see
[stability.md § "A roster slug never changes"](stability.md#a-roster-slug-never-changes).

## How roles, skills, and items connect

Roles ↔ item types is the **playbook**. It drives two things: which roles appear as sections in each
`sq-<type>` skill, and which skills a role's pointer preloads. It is customisable:
`.overrides/playbook.toml` reworks a type's guidance, or gives a role you defined yourself a section
in a type's skill — see [overrides.md](overrides.md#playbook-overrides-role-guidance-per-item-type).
See [workflow.md](workflow.md) for the team flow and
[internals.md](internals.md#8-roles-and-the-playbook) for the mechanics. A role item stores its slug, its
name and the values its verbs set, plus its base: a template role's `template` and `tech`, or a
self-defined role's definition. The rest is resolved from the catalog, the template and your
overrides when `sq role <slug> show` runs (see
[Where a role's definition comes from](#where-a-roles-definition-comes-from)).

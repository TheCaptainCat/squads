---
id: FEAT-961
sequence_id: 961
type: feature
title: Pronouns on agent and operator identity
status: Done
author: product-owner
refs:
- MILE-934:targets
- FEAT-977:depends-on
subentities:
- local_id: US1
  title: Pronouns as data on roles and operators
  status: Todo
- local_id: US2
  title: Declare a roster-wide default pronouns once
  status: Todo
- local_id: US3
  title: Pronouns in --json output
  status: Todo
- local_id: US4
  title: Render pronouns after names, dimmed, in human UIs
  status: Todo
- local_id: US5
  title: Typed display table in .squads.toml
  status: Todo
created_at: '2026-09-24T09:30:03Z'
updated_at: '2026-10-17T10:12:31Z'
---
<!-- sq:body -->
## Why

An agent's or operator's first name does not reliably signal pronouns: "Robert Architect" reads
he/him to most readers but that is an assumption, not a declaration, and a first name alone never
disambiguates a non-binary person. Three concrete adopter scenarios motivate this:

- An adopter's operator (a real person on their team) is non-binary and wants they/them recorded
  and shown, the same way squads already records their full name.
- An adopter wants every generated agent persona to read as they/them by default — a deliberate,
  roster-wide choice made once, not a per-agent chore.
- An adopter simply wants pronouns visible next to a name anywhere squads shows one, the way many
  chat and email tools already do, because the agents (and the human) address each other by name
  and pronoun in conversation and handoff comments.

Neither roles nor operators carry a pronoun field today, `init_names` in `.squads.toml` only seeds
`full_name`, and no config surface exists for a display preference.

## Scope

Design is ruled in ADR-981; this feature delivers it.

- **Data**: a pronouns value stored as the top-level `pronouns` attribute, declared in the spec, on role items and operator items. Settable
  on creation (`sq role activate`, `sq dev add`, `sq operator add`) and editable afterwards through
  the `update` verbs FEAT-977 introduces. The setter works on a bundled role: pronouns are identity
  the operator sets, like the name. Unset means the key is absent; a blank is never stored. The
  value is free text with a checked shape: one line, stored trimmed, 1 to 40 characters, no control
  characters, no sq marker tag.
- **Roster default**: declared once, in the role catalog document (`.overrides/roles.toml`), as
  `[defaults]` with a `pronouns` key. A role's pronouns resolve as its own value, else the declared
  default, else unset. The default applies to agents only, never to operators, and is never written
  onto items. Declaring it and running `sq sync` is the same act at init and on an existing roster;
  there is no bulk-apply verb. `sq init` may offer a flag as shorthand, provided it only writes that
  declaration through the override scaffold path and writes nothing per item. The bundled catalog
  declares no default and no pronouns for any bundled role.
- **`--json`**: `sq role list`, `sq role <addr> show`, `sq operator list` and `sq operator <addr>
  show` gain a top-level `pronouns` key beside `full_name`: the resolved value, a string, or `null`
  when unset, always present. Nothing is added to item rows or discussion entries; a client joins a
  slug to the roster viewers.
- **Display**: a typed `[display]` table in `.squads.toml` with one key, `pronouns`, a boolean that
  defaults to true. When true, a name with pronouns renders as `Name (pronouns)` with the
  parenthesis dimmed, in the CLI's human output and `sq ui`. Pronouns follow a name only; surfaces
  that print a slug (assignee columns) do not change. The VS Code client always receives the data
  and follows a setting of its own, default on, not `.squads.toml`.
- **Generated agent-facing files**: the roster section of `CLAUDE.md` / `AGENTS.md` and an agent's
  own identity pointer always carry pronouns, whatever `[display]` says. A changed pronouns value
  or declared default is picked up by `sq sync`.
- **Config**: `[display]` is a typed, closed table whose keys change only what sq's own human
  renderers print. An unknown key or unusable value never stops a command: it falls back to the
  default and `sq check` reports it by name. An existing `.squads.toml` is rewritten byte-identically
  when nothing differs from the defaults.

## Does not belong here

- Implementation: no tasks or code in this drafting pass.
- A generic settings system: no key registry, no `sq config get/set` verbs, no per-user file, no
  environment override.
- A closed list of pronouns, or a per-role `pronouns` entry in the role catalog or a per-slug role
  file (refused; the refusal names the verb).
- Pronouns for an agent that has none under a declared default: an agent's own value replaces the
  default, nothing erases it.
- Any change to how names are chosen/generated (dev name pool, `dev_role()`) — pronouns are an
  additional attribute on top of the existing name.
- Pronoun-aware grammar in generated prose.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 961 add-story "As a <role>, I want … so that …"`; track with `sq feature 961 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Pronouns as data on roles and operators

<!-- sq:story:US1:body -->
As an adopter setting up an agent or registering an operator, I want to record that person's or
persona's pronouns, so that the roster reflects how they should be addressed instead of a guess
from their first name.

Acceptance:
- `sq role activate`, `sq dev add` and `sq operator add` each accept a pronouns option; the value
  is stored as `pronouns` in the item's frontmatter.
- After FEAT-977 ships, the `update` verb of a role and of an operator sets, changes and clears
  pronouns; setting pronouns on a bundled (system) role succeeds, while a content-changing edit on
  that same role is still refused.
- An accepted value is one line, stored trimmed, 1 to 40 characters. Each of these is refused with
  exit 1 and a message, and nothing is stored: 41 characters, an embedded newline, a tab or other
  control character, a string containing an sq marker tag (a tag of the form sq:body wrapped in an HTML comment).
- A value of exactly 40 characters and one of 1 character are accepted; surrounding whitespace is
  trimmed before the length check.
- A blank value (empty or whitespace only) on `update` clears the value: the key is absent from the
  frontmatter afterwards. A blank on creation stores nothing.
- A role or operator created without pronouns has no `pronouns` key; a squad upgraded with no
  declaration shows no new output on any surface.
- A `pronouns` key in a `[[roles]]` entry or a per-slug role file is refused, and the refusal
  names the verb that sets pronouns.
- A sync never rewrites or removes a stored `pronouns`.
- `sq check` reports a stored value that fails the shape check (hand-edited file); renderers treat
  such a value as unset.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Declare a roster-wide default pronouns once

<!-- sq:story:US2:body -->
As an adopter who wants a they/them-for-everyone roster (or any other single default), I want to
declare it once, so that I don't have to edit each agent by hand.

Acceptance:
- The role catalog document (`.overrides/roles.toml`) accepts a top-level `[defaults]` table with a
  `pronouns` key; the value is checked with the same shape rules as US1 and an invalid one is
  reported by `sq check` and refused on load as any invalid override is.
- With `[defaults] pronouns = "they/them"` declared, every agent role without its own value shows
  `they/them` as its pronouns on every surface (`sq role` JSON, human output, generated files)
  after `sq sync`; no role item's frontmatter gains a `pronouns` key.
- A role that has its own value shows that value, not the default.
- No operator ever takes the default: an operator with no own value has `pronouns` null.
- Removing the declaration and running `sq sync` returns every role without its own value to
  unset, with no leftover in any item file.
- No verb applies pronouns in bulk; there is no bulk-apply command.
- If `sq init` takes a pronouns-default flag, running it produces only the `[defaults]`
  declaration in the override document and no per-item `pronouns`; without the flag the
  document carries no `[defaults]`.
- The bundled `roles.toml` is byte-identical to before, and an existing catalog override reports no
  drift because of this feature.
- An agent cannot be given "no pronouns" under a declared default; this limit is stated in the
  user documentation.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Pronouns in --json output

<!-- sq:story:US3:body -->
As a client or script consuming squads data, I want pronouns in `--json` output for roles and
operators, so that another UI (or the VS Code client) can render them without re-deriving them.

Acceptance:
- `sq role list --json`, `sq role <addr> show --json`, `sq operator list --json` and
  `sq operator <addr> show --json` each carry a top-level `pronouns` key beside `full_name`.
- The value is the resolved one (own, else the role default, else unset): a string, or `null` when
  unset. The key is always present, never omitted.
- For a role that takes the declared default, `pronouns` shows the default although the item's
  `pronouns` is absent.
- Item rows, `discussion[]` entries and comment headers gain no pronouns key.
- The output is the same whether `[display] pronouns` is true or false.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Render pronouns after names, dimmed, in human UIs

<!-- sq:story:US4:body -->
As someone reading squads output — the TUI, the VS Code client, or a CLI table/show — I want a
name's pronouns to appear next to it in parentheses and visually de-emphasised, so that I can read
them at a glance without them competing with the name.

Acceptance:
- With `[display] pronouns` true (the default, including when `.squads.toml` has no `[display]`) and
  a pronouns value set, `Name (pronouns)` renders in `sq ui` and in the CLI's human output wherever
  a role or operator name is printed, the parenthesis in a dimmed style.
- With a name that has no pronouns, or with `[display] pronouns = false`, the name renders exactly
  as today: no empty parentheses and no trailing space.
- A surface that prints a slug (such as an assignee column) is unchanged in both cases.
- The pronouns text is escaped like any content string: a stored value containing square brackets
  prints literally.
- The generated `CLAUDE.md` / `AGENTS.md` roster section and an agent's own identity pointer carry
  the pronouns whether `[display] pronouns` is true or false.
- The VS Code client shows pronouns after a name by default and has its own setting that turns this
  off; changing `[display]` in `.squads.toml` does not change the VS Code client, and changing the
  VS Code setting does not change the CLI or `sq ui`.
- The VS Code client gets pronouns by joining a slug to the roster `--json` viewers, and its
  version-skew check accepts the new key.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Typed display table in .squads.toml

<!-- sq:story:US5:body -->
As an adopter, I want a typed `[display]` table in `.squads.toml`, so that presentation
preferences have one place to live without a general settings system.

Acceptance:
- `.squads.toml` accepts `[display]` with one key, `pronouns`, a boolean defaulting to true;
  `sq check` and every command accept a file without the table.
- A `.squads.toml` with no `[display]`, or with every value at its default, is rewritten
  byte-identically by a version or schema stamp; a non-default `pronouns = false` survives a stamp.
- An unknown key under `[display]`, or a non-boolean `pronouns`, never stops a command: the
  default applies and `sq check` reports the offending key by name.
- The table changes only what the CLI's human output and `sq ui` print; `--json`, exit codes, stored
  data and generated files are identical with the setting true or false.
- There is no `sq config` verb, per-user file or environment override for it.
- Upgrading an existing squad needs no migration step and no schema version bump.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-24T09:31:24Z] `product-owner` Nina Product:
  - @architect open design questions for FEAT-961, all still open — framed with a recommendation, not a decision:
    
    1. **Field home**: first-class `pronouns` field on the role/operator model, or an `Item.extra` key (`ExtraKey.PRONOUNS` in `_models/_extras.py`)? Frontmatter is the source of truth either way, but `extra` is the lighter-weight, precedent-following slot (see `SEVERITY`, `TECH`, `TARGET_DATE`) versus a first-class field that other item types can't accidentally acquire. Recommendation: `extra` key, since precedent already puts comparable per-type-only metadata there and it avoids touching the shared `Item` model. Flag either way: does this field count as part of the `docs/stability.md` JSON stability contract once shipped (i.e. can it be renamed/dropped later without a compat window)?
    
    2. **Generic config-params system**: what shape? A flat `[display]` table in `.squads.toml` (per-squad, checked in) vs. a separate per-user file (e.g. `~/.config/squads/`) for preferences that are about *how I like to view things* rather than *how this project is configured*. Recommendation: per-squad `[display]` table in `.squads.toml` for a first cut — pronouns-visibility is arguably a team-wide, not per-viewer, choice (like `init_names`), and a per-user file is a bigger surface (new config file, new precedence rules) that nothing else here needs yet. Also: does a generic settings bag need schema/migration handling the way `SquadsConfig` fields do, or is it deliberately loose (untyped dict, `extra: ignore`-shaped) so future keys don't each need a schema bump?
    
    3. **Default-at-init mechanism**: a CLI flag on `sq init` (e.g. `--default-pronouns`) that seeds every scaffolded role's `extra.pronouns`, versus a bulk command (`sq role bulk-set-pronouns` or similar) usable both at init and later against an existing roster. Recommendation: both — a thin init flag that seeds the value at creation time (cheapest, matches how `init_names` already seeds `full_name`), plus a general bulk-apply path for a roster that's already running, since US2 asks for after-the-fact adoption too.
    
    4. **Value shape**: free text (adopter types whatever they want — "she/her", "ze/zir", a custom set) or a small validated/curated set with an "other: <text>" escape hatch? Recommendation: free text, no validation — pronouns are exactly the kind of field where a closed enum will be wrong for someone, and squads doesn't currently validate `full_name` either; the display renderer just prints whatever string is stored.
- [2026-09-24T09:31:31Z] `op-pierre` Pierre Chat:
  - let's draft a new feature, pronouns in the agent/operator data, because he/she/they is not always obvious from the firstname and some adopters may want to initialize all agents as they/them and some ops are non-binary. Pronouns should appear in the json as a key (maybe in the extra, idk) and in the ui between () and lightly greyed out. Maybe set a param to display pronouns? That kind of params could live in the config, as a generic param system, not specifically designed for pronouns
- [2026-09-24T09:53:56Z] `op-pierre` Pierre Chat:
  - - Rulings: no parent epic for now. Pronouns DO appear in the generated agent-facing files (the roster section of CLAUDE.md/AGENTS.md, and an agent's own identity pointer) — agents are the ones writing prose about each other, so that is where the value is. The display setting governs the human UIs only; generated agent-facing files always carry pronouns. Parked for later — not scheduled.
- [2026-10-09T15:36:30Z] `architect` Robert Architect:
  - @product-owner the four design questions of 2026-09-24 are ruled in ADR-981 (Proposed; accepting it is op-pierre's call). Nothing in this feature is edited by me. If ADR-981 is accepted, these are the changes it implies here:
    
    1. **Field home (Q1): agreed, `extra.pronouns`.** US3: the key is a top-level `pronouns` beside `full_name` on `sq role list`, `sq role <addr> show`, `sq operator list` and `sq operator <addr> show`, `null` when unset, and it is the *resolved* value. It joins the `--json` contract on the same terms as `full_name`. `extra.pronouns` in the generic item JSON is not the surface a client reads. Nothing is added to item rows or comment entries: a client joins a slug to the roster viewers.
    2. **Config (Q2): a typed `[display]` table in `.squads.toml`, per squad, as you recommended, but not a loose bag.** US5: replace "generic, extensible settings mechanism" with a typed, closed table whose keys change only what sq's own human renderers print; an unknown key or bad value never stops a command and is reported by `sq check`. No registry, no `sq config` verbs, no per-user file.
    3. **Display default: on, a departure from US5 and US4.** US5's last bullet ("unset defaults to no pronouns rendered") becomes: unset renders pronouns wherever one is set. Upgrading still needs no migration, since an existing squad has none to render. Flagged to op-pierre as his to weigh.
    4. **VS Code** is out of the `.squads.toml` setting's reach: US4 should say the CLI and `sq ui` follow `[display]`, and the VS Code client follows a setting of its own.
    5. **Default (Q3): a departure. Declared once, not stamped.** US2 changes most: a `[defaults]` table with `pronouns` in the role catalog document (`.overrides/roles.toml`), resolved at read time as own value, else default, else unset. Agents only, never operators. The "separate bulk-apply path" bullet goes: declaring the default and running `sq sync` is the path for an existing roster. The "never overwrites an explicit value" bullet holds by construction and no longer needs a rule. `sq init` may keep a flag, as shorthand that writes the declaration. New limit to state: an agent cannot have no pronouns under a declared default.
    6. **Value (Q4): free vocabulary as you recommended, but not unchecked.** US1 gains: one line, trimmed, 1 to 40 characters, no control characters, no sq marker tag; a blank clears the value and is never stored.
    7. **Scope, Data bullet:** the setter must work on a bundled role, and editing after creation rides the `update` verbs FEAT-977 introduces. FEAT-977 US4's refusal on system roles must not cover pronouns; that feature needs the same note.
    8. **Scope, Display bullet:** the "open question" on the generated roster is closed by op-pierre's ruling above and can go. Pronouns render after a *name* only; surfaces that print a slug (assignee columns) do not change.
    9. **"Does not belong here":** the two bullets deferring the config shape, the field home and the value shape to the architect can point at ADR-981.
- [2026-10-09T18:16:15Z] `product-owner` Nina Product:
  - 2026-10-09: prose rewritten to match accepted ADR-981; depends-on FEAT-977 for the update verbs. Ready; blocker is independent.
- [2026-10-16T19:58:51Z] `tech-lead` Olivia Lead:
  - Task TASK-1071 (Draft) carries the breakdown; dependencies in its body.
- [2026-10-16T19:59:53Z] `manager` Catherine Manager:
  - Confirmed TASK-1071's calls: no sq init pronouns flag; pronouns pinned for operators and roles; pronouns_valid and display_config_valid checks. Dependency moved from FEAT-977 to its task TASK-1070.
- [2026-10-17T10:12:31Z] `op-pierre` Pierre Chat:
  - 2026-10-17: in VS Code, a role's and an operator's preview should show their pronouns after the name too, not only the Roster tree and the mention hover.
<!-- sq:discussion:end -->

---
id: FEAT-961
sequence_id: 961
type: feature
title: Pronouns on agent and operator identity, with a generic display-settings config
status: Draft
author: product-owner
subentities:
- local_id: US1
  title: Pronouns as data on roles and operators
  status: Todo
- local_id: US2
  title: Bulk default pronouns at init and for the existing roster
  status: Todo
- local_id: US3
  title: Pronouns in --json output
  status: Todo
- local_id: US4
  title: Render pronouns next to names, dimmed, in the UIs
  status: Todo
- local_id: US5
  title: Generic display-settings mechanism in config
  status: Todo
created_at: '2026-09-24T09:30:03Z'
updated_at: '2026-09-24T09:53:56Z'
---
<!-- sq:body -->
## Why

An agent's or operator's first name does not reliably signal pronouns: "Robert Architect" reads
he/him to most readers but that is an assumption, not a declaration, and a first name alone never
disambiguates a non-binary person. Three concrete adopter scenarios motivate this:

- An adopter's operator (a real person on their team) is non-binary and wants they/them recorded
  and shown, the same way squads already records their full name.
- An adopter wants every generated agent persona to read as they/them by default — a deliberate,
  bulk choice at `sq init` (or applied after the fact across the roster), not a per-agent chore.
- An adopter simply wants pronouns visible next to a name anywhere squads shows one, the way many
  chat and email tools already do, because the agents (and the human) address each other by name
  and pronoun in conversation and handoff comments.

Today neither roles (`_specs/roles.toml`, `Item.extra` via `ExtraKey` in
`src/squads/_models/_extras.py`) nor operators carry a pronoun field, `init_names` in
`.squads.toml` (`src/squads/_models/_config.py`) only seeds `full_name`, and no config surface
exists for a display preference at all — `SquadsConfig` has no generic "how do we render things"
section, only `squad_dir` / `active_backends` / `squads_version` / `init_names`.

## Scope

- **Data**: a pronouns value on a role/agent item and on an operator item, settable at creation
  and editable afterwards (`sq role <slug> update` / `sq operator <slug> update`-shaped surface —
  exact command TBD by the tech lead), present in `--json` output for both.
- **Bulk / default-at-init**: a way to set pronouns for the whole roster at once — at minimum a
  default applied to every agent at `sq init` (e.g. "initialize all agents as they/them"), and
  ideally also a bulk-apply for an existing roster, not only new agents.
- **Display**: when a display setting is enabled, render pronouns right after a name, in
  parentheses and visually de-emphasised ("dimmed"/grey), everywhere a full name currently appears
  in an agent-facing or human-facing surface:
  - `sq ui` (TUI) wherever an assignee/author/role name is shown.
  - the VS Code client's tree/detail views.
  - CLI tables and `show` output wherever a name is printed.
  - **Open question, flagged below**: the generated roster in the managed CLAUDE.md/AGENTS.md
    section (`claude_section.md.j2`), since that is the text agents read to address each other by
    name — decide whether pronouns belong there too or are display-surface-only.
- **Config**: a display-settings toggle for whether pronouns render at all, living in a **generic**
  mechanism in `.squads.toml` — a small extensible bag for this class of "how do we render things"
  preference — explicitly not a `show_pronouns` field bolted directly onto `SquadsConfig`. Pronouns
  is the first consumer, not the only intended one.

## Does not belong here

- Implementation: no tasks, ADRs, or code in this drafting pass.
- Deciding the generic config system's exact schema/storage shape, or the data-model home for the
  pronouns field itself (first-class vs `extra` key) — both are open design questions for the
  architect, see the comment on this feature.
- Free-text vs a validated/controlled set of pronoun values — also an open question below.
- Any change to how names are chosen/generated (dev name pool, `dev_role()`) — pronouns are an
  additional attribute on top of the existing name, not a naming-scheme change.
- Per-message or per-comment pronoun mentions in generated prose beyond the name-adjacent badge
  described above (e.g. squads is not adding pronoun-aware grammar to generated text).
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
- A pronouns value can be set when a role/agent is created or activated, and when an operator is
  created.
- The value can be edited later on an existing role or operator without recreating it.
- Leaving it unset is a valid, supported state (no default pronoun is invented for an existing
  roster on upgrade).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Bulk default pronouns at init and for the existing roster

<!-- sq:story:US2:body -->
As an adopter who wants a they/them-for-everyone roster (or any other single default), I want to
set pronouns for the whole agent roster in one action, so that I don't have to edit each agent by
hand.

Acceptance:
- `sq init` accepts a default pronouns value applied to every scaffolded agent.
- A separate bulk-apply path sets pronouns across the existing roster after init, for an adopter
  who decides this later.
- A bulk default never overwrites a pronouns value an adopter already set explicitly on one agent,
  unless they ask it to.
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
- `sq role <slug> show --json` and `sq operator <slug> show --json` include the pronouns field
  (present-but-null when unset, not omitted).
- Any roster listing JSON used to build a UI (e.g. what feeds the VS Code client's tree) carries
  the same field.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Render pronouns next to names, dimmed, in the UIs

<!-- sq:story:US4:body -->
As someone reading squads output — the TUI, the VS Code client, or a CLI table/show — I want a
name's pronouns to appear next to it in parentheses and visually de-emphasised, so that I can read
them at a glance without them competing with the name.

Acceptance:
- When the display setting (US5) is on and a pronouns value is set, "(they/them)" (or the stored
  value) renders immediately after the name, styled as secondary/dimmed text, in: `sq ui`, the
  VS Code client, and CLI tables/`show` output that print a role or operator name.
- When the value is unset, or the display setting is off, nothing extra renders — no empty
  parentheses.
- The generated CLAUDE.md/AGENTS.md roster section is explicitly decided one way or the other
  (include or omit) rather than left inconsistent with the other surfaces.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Generic display-settings mechanism in config

<!-- sq:story:US5:body -->
As an adopter, I want a generic display-settings section in `.squads.toml`, so that pronouns (and
future preferences of the same kind) have one place to live instead of each growing its own
bespoke top-level config field.

Acceptance:
- `.squads.toml` gains a generic, extensible settings mechanism (not a `show_pronouns` field on
  `SquadsConfig` itself) that a specific preference plugs a key into.
- The "show pronouns next to names" toggle is the first entry in that mechanism.
- Unset/missing settings default to today's behavior (no pronouns rendered), so upgrading an
  existing `.squads.toml` needs no migration.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-24T09:31:24Z] Nina Product:
  - @architect open design questions for FEAT-961, all still open — framed with a recommendation, not a decision:
    
    1. **Field home**: first-class `pronouns` field on the role/operator model, or an `Item.extra` key (`ExtraKey.PRONOUNS` in `_models/_extras.py`)? Frontmatter is the source of truth either way, but `extra` is the lighter-weight, precedent-following slot (see `SEVERITY`, `TECH`, `TARGET_DATE`) versus a first-class field that other item types can't accidentally acquire. Recommendation: `extra` key, since precedent already puts comparable per-type-only metadata there and it avoids touching the shared `Item` model. Flag either way: does this field count as part of the `docs/stability.md` JSON stability contract once shipped (i.e. can it be renamed/dropped later without a compat window)?
    
    2. **Generic config-params system**: what shape? A flat `[display]` table in `.squads.toml` (per-squad, checked in) vs. a separate per-user file (e.g. `~/.config/squads/`) for preferences that are about *how I like to view things* rather than *how this project is configured*. Recommendation: per-squad `[display]` table in `.squads.toml` for a first cut — pronouns-visibility is arguably a team-wide, not per-viewer, choice (like `init_names`), and a per-user file is a bigger surface (new config file, new precedence rules) that nothing else here needs yet. Also: does a generic settings bag need schema/migration handling the way `SquadsConfig` fields do, or is it deliberately loose (untyped dict, `extra: ignore`-shaped) so future keys don't each need a schema bump?
    
    3. **Default-at-init mechanism**: a CLI flag on `sq init` (e.g. `--default-pronouns`) that seeds every scaffolded role's `extra.pronouns`, versus a bulk command (`sq role bulk-set-pronouns` or similar) usable both at init and later against an existing roster. Recommendation: both — a thin init flag that seeds the value at creation time (cheapest, matches how `init_names` already seeds `full_name`), plus a general bulk-apply path for a roster that's already running, since US2 asks for after-the-fact adoption too.
    
    4. **Value shape**: free text (adopter types whatever they want — "she/her", "ze/zir", a custom set) or a small validated/curated set with an "other: <text>" escape hatch? Recommendation: free text, no validation — pronouns are exactly the kind of field where a closed enum will be wrong for someone, and squads doesn't currently validate `full_name` either; the display renderer just prints whatever string is stored.
- [2026-09-24T09:31:31Z] Pierre Chat:
  - let's draft a new feature, pronouns in the agent/operator data, because he/she/they is not always obvious from the firstname and some adopters may want to initialize all agents as they/them and some ops are non-binary. Pronouns should appear in the json as a key (maybe in the extra, idk) and in the ui between () and lightly greyed out. Maybe set a param to display pronouns? That kind of params could live in the config, as a generic param system, not specifically designed for pronouns
- [2026-09-24T09:53:56Z] Pierre Chat:
  - - Rulings: no parent epic for now. Pronouns DO appear in the generated agent-facing files (the roster section of CLAUDE.md/AGENTS.md, and an agent's own identity pointer) — agents are the ones writing prose about each other, so that is where the value is. The display setting governs the human UIs only; generated agent-facing files always carry pronouns. Parked for later — not scheduled.
<!-- sq:discussion:end -->

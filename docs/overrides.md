# Project-level overrides

Your squad may want to customize how squads renders items, roles, or backend artifacts — a custom
task template to match your team's style, or different names for roles. **Overrides** are how you
do that without forking the entire squads package.

Overrides live under `.overrides/`, a directory in your squad folder that mirrors the bundled
template structure. You own and maintain them; squads detects when an upgrade changes the bundled
originals and warns you to reconcile. The [`sq override`](#the-sq-override-command-group) command
group handles the full authoring + upgrade workflow.

---

## TL;DR: Get a custom task template

```bash
# Copy the bundled task template into your squad as a starting point
sq override scaffold items/task.md.j2

# Edit it
$EDITOR .overrides/templates/items/task.md.j2

# Check for drift warnings
sq check

# Later, if squads upgrades and the bundled task template changed:
# See what both your edit AND the upgrade changed
sq override diff items/task.md.j2

# Merge manually (the diffs show what you customised and what the upgrade added)
$EDITOR .overrides/templates/items/task.md.j2

# Tell squads you're done reconciling
sq override update items/task.md.j2

# Verify the warning is gone
sq check
```

---

## Override layout

All overrides live under a single umbrella directory, **`<squad-dir>/.overrides/`**:

```
<squad-dir>/.overrides/
  templates/
    items/
      epic.md.j2
      feature.md.j2
      task.md.j2
      bug.md.j2
      review.md.j2
      guide.md.j2
      decision.md.j2
    subentities/
      story.md.j2
      subtask.md.j2
      finding.md.j2
      block.md.j2
      summary.md.j2
    agents/
      role.md.j2
    claude/
      pointer_agent.md.j2
      pointer_skill.md.j2
      claude_section.md.j2
  workflow.toml
  roles/
    architect.toml
    tech-lead.toml
    tech-writer.toml
    manager.toml
    python-dev.toml
    custom-role.toml
```

**Key points:**

- **`templates/`** mirrors the bundled `_rendering/templates/` tree exactly. An override is named by
  its **template path** (e.g., `items/task.md.j2`, `agents/role.md.j2`). You don't override
  everything — drop a single file and only that template changes; the rest still use the bundle.
- **`roles/`** holds TOML files for role data: one file per role slug (e.g., `architect.toml`). You
  can override bundled roles (like changing the architect's name or model) or define entirely new
  custom roles.
- **`workflow.toml`** defines custom item types, statuses, lifecycles, and badge collections (see
  below). This is how you customize the vocabulary — type names, status machines, and the priority/severity
  badge axes.
- The directory is discovered automatically by the same walk-up that finds `.squads.toml`. It
  travels with your squad folder, so it's portable across projects.

---

## Precedence rule

Override lookup is **per-file, project → bundled default**:

1. If `.overrides/templates/<template-name>` exists, squads uses it.
2. Otherwise, squads uses the bundled template from the package.

There is **no whole-squad override mode** — presence of a file is the override, and you can mix
and match:

```
.overrides/
  templates/
    items/task.md.j2          # ← custom task template
    items/bug.md.j2           # ← custom bug template
    (no feature.md.j2)        # ← use bundled feature template
    agents/role.md.j2         # ← custom role body shape
```

**Template overrides are whole-file:**
If you override `items/task.md.j2`, the entire file is replaced. squads does not attempt line-by-line
merging of template content. (The required `<!-- sq:* -->` marker regions must still be present —
see [Staleness and drift](#staleness-and-drift) below.)

**Role overrides merge by field:**
A `roles/architect.toml` override only replaces the fields you set. Fields you omit inherit from
the bundled role definition:

```toml
# .overrides/roles/architect.toml
full_name = "Chief Design Officer"
model = "opus"
# title, mission, responsibilities, etc. inherit from the bundled architect
```

A brand-new role slug (one not in the bundle) defines a wholly custom, non-dev role — e.g. a
`security-analyst` or `compliance-officer` — from the TOML. Start it with:

```bash
sq override scaffold --new compliance-officer
```

This writes `.overrides/roles/compliance-officer.toml` with the essential fields stubbed and the
advanced fields present as commented-out lines to uncomment and fill in:

```toml
# .overrides/roles/compliance-officer.toml
full_name = "Compliance Officer"
title = "The keeper of standards"
description = "Ensures all code meets compliance requirements."
mission = "Keep the team on the right side of policy."
responsibilities = ["Review all PRs for policy violations", "Maintain the compliance handbook"]
model = "opus"
# can_spawn = true   # opt this role into spawning/orchestrating subagents (default: false)
```

Then `sq role activate compliance-officer` creates the role the same way it does for a bundled
slug. See [roles.md](roles.md) for the activation flow.

---

## Workflow overrides: item types, statuses, and badge collections

By default, squads uses a bundled set of **seven work-item types** (epic, feature, task, bug,
decision/ADR, review, guide), **status lifecycles** (state machines for each type), and
**badge collections** (priority and severity, the reusable axes that label findings, tasks, etc.).
If your squad needs custom vocabulary — new item types, additional statuses, or renamed badge axes —
you define it in **`.overrides/workflow.toml`**.

### Creating a workflow override

To scaffold a starter override file:

```bash
sq override scaffold workflow
```

This creates `.overrides/workflow.toml` in your squad directory with a commented-out worked example.
Edit this file to add your custom types, statuses, lifecycles, and collections.

### Format and sections

The override file uses standard TOML with four sections: `[items.*]`, `[statuses.*]`, `[lifecycles.*]`,
and `[collections.*]`. The bundled defaults already define all seven work types and the built-in
status machines; your override is **additive-only** — you can extend by adding new types and
statuses, but cannot redefine or remove built-ins. (To rename an existing type or status across
your squad's items, use `sq migrate rename-type` or `sq migrate rename-status`; see
[workflow.md](workflow.md) § "Renaming existing types and statuses".) The complete reference is in
[workflow.md](workflow.md) § "Project workflow overrides".

#### Items: custom work types

Define a new item type (e.g., an `incident` type for on-call workflows):

```toml
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident"      # reference a built-in or custom lifecycle
```

Required fields:
- `prefix` — uppercase letter(s) for the type's ID prefix (e.g., `INC` for `INC-<n>`)
- `folder` — subdirectory under `squads/` where items of this type are stored
- `lifecycle` — the lifecycle name (built-in or custom) governing the type's state machine

Optional:
- `parents` — list of allowed parent item types; empty or omitted means no hierarchy constraint
- `aliases` — list of short command aliases (e.g., `["inc"]` allows `sq inc <n>` as shorthand)

#### Statuses: custom state labels

Define new statuses (e.g., states for your custom incident lifecycle):

```toml
[statuses.Triage]
terminal = false

[statuses.Mitigating]
terminal = false

[statuses.Resolved]
terminal = true
```

Required fields:
- `terminal` — boolean; `true` if this status is terminal (items at terminal statuses are
  "done" and hidden from `sq inbox` by default)

Optional:
- `badge` — emoji or short symbol displayed in sub-entity roll-up tables (used only for sub-entities)
- `role` — special marker for specific statuses (used only for ADRs; e.g., `role = "superseded"`)

#### Lifecycles: custom state machines

Define a new lifecycle (the state transitions for a custom item type):

```toml
[lifecycles.incident]
initial = "Triage"

[lifecycles.incident.transitions]
Triage = ["Mitigating", "Resolved"]
Mitigating = ["Resolved", "Triage"]
Resolved = ["Triage"]
```

Required fields:
- `initial` — the starting status when a new item of this type is created
- `transitions` — a map of `SourceStatus = [TargetStatus1, TargetStatus2, …]` showing which
  transitions are allowed

#### Collections: custom badge axes

Define a custom badge collection (a reusable axis like priority or severity):

```toml
[collections.impact]
ordered = true
default_code = "medium"

[[collections.impact.badges]]
code = "low"
label = "Low impact"
emoji = "🔵"

[[collections.impact.badges]]
code = "medium"
label = "Medium impact"
emoji = "🟡"

[[collections.impact.badges]]
code = "high"
label = "High impact"
emoji = "🔴"
```

Required fields:
- `ordered` — boolean; `true` if the badges have a meaningful ranking (low → high), `false` for unordered
- `default_code` — the code of the default badge when no value is set
- `badges` — list of badge definitions (each with `code`, `label`, `emoji`)

Each badge's `code` is the identifier used in commands (e.g., `sq task <n> update --impact medium`).
Ordered collections support `--min-` filters (e.g., `sq list --min-impact high`).

See [workflow.md](workflow.md) § "Project workflow overrides" for a worked example.

---

## Staleness and drift

Overrides are authored against a bundled template or role from some version of squads. When you
upgrade squads, the bundled original may change — a new required marker, a new context variable, a
new role field. We **detect and warn you** about this drift; you **merge by hand** to reconcile it.

### How staleness is detected

When you scaffold an override (via `sq override scaffold`), the file carries a **provenance stamp**:

```
<!-- squads:override-base:0.4.2 -->
```

This is an HTML comment, inert to rendering. It records: "This override was branched from squads
0.4.2." When you later upgrade squads and run `sq check`, it compares:

- Your override's `override-base` stamp against the current `squads_version`.
- The bundled template at your override's `override-base` version against the bundled template
  in the *current* version (recovered from the shipped `templates_manifest.json`, which indexes
  all bundled templates by version and hash).

If the bundled original **changed** between those versions, `sq check` warns:

```
.overrides/templates/items/task.md.j2: override may be stale — bundled task.md.j2 changed since
v0.4.2; run `sq override diff items/task.md.j2`, merge, then `sq override update items/task.md.j2`
```

**Important:** squads only warns if the bundled original **actually changed**. If you scaffold an
override at v0.4.2 and upgrade to v0.4.3, but the bundled task template didn't change, there is no
warning. The stamp alone is never a problem.

**Structural errors:**
Independently, `sq check` detects if an override is **missing a required marker region** (the
`<!-- sq:* -->` anchors that the marker-safe editing depends on). This is an error, not a warning:

```
.overrides/templates/items/task.md.j2: missing required marker <!-- sq:body -->
```

If your override has clean markers and renders without error, it will render even if its stamp is
old.

### The end-to-end reconciliation workflow

This is how you handle an override after a squads upgrade:

#### Step 1: Check for drift

```bash
sq check
```

If any override's bundled counterpart changed since its `override-base` stamp, you'll see a warning
per override. Structural errors (missing markers) are shown as errors.

#### Step 2: Inspect the drift with two-sided diffs

```bash
sq override diff items/task.md.j2
```

This shows **two separate diffs**, side by side, so you see both what you customised *and* what the
upgrade changed:

- **Δ-mine:** your override vs. the **current** bundled task template. This shows your
  customisation — what the team designed differently from the default.
- **Δ-upgrade:** the **base-version** bundled template (the one from `override-base`) vs. the
  **current** bundled template. This shows what the upgrade itself changed in the default since you
  last branched the override.

Read Δ-upgrade to spot any new required markers or context variables the upgrade added — you'll
need to fold those into your override.

Omit the template name to diff **every drifted override**:

```bash
sq override diff
```

#### Step 3: Merge by hand

Edit `.overrides/templates/items/task.md.j2` (or the override you're reconciling) to fold the
upgrade's changes into your version while keeping your customisations:

```bash
$EDITOR .overrides/templates/items/task.md.j2
```

This is not automated; you own the merge. The goal is to keep your edits (from Δ-mine) while
adopting any required structural changes from the upgrade (from Δ-upgrade) — typically new markers
or variables that the current version of squads needs.

Run `sq check` often while editing to catch structural errors (missing markers) early.

#### Step 4: Re-stamp after the merge

```bash
sq override update items/task.md.j2
```

This rewrites the `squads:override-base:` stamp to the current `squads_version` — **and nothing
else**. The body you just merged is untouched. Re-stamping is your assertion: "I have reconciled
this against the current bundled default."

The next `sq check` recomputes drift against the new base and the warning clears. Your override is
now current.

#### Bulk re-stamp after a review pass

Once you've reviewed and merged all drifted overrides, re-stamp them all at once:

```bash
sq override update
```

With no argument, this re-stamps every structurally-valid override (ones with clean markers). Broken
overrides (missing required markers) are skipped — fix those first.

---

## The `sq override` command group

The four commands below are your complete override-authoring and upgrade toolkit.

### `sq override scaffold`

Copy a bundled template or role into `.overrides/` as a starting point for editing.

```bash
# Copy a template
sq override scaffold items/task.md.j2

# Copy a template by name (all bundled template paths work)
sq override scaffold agents/role.md.j2
sq override scaffold subentities/story.md.j2

# Copy a role TOML override (a bundled role, to change its name/model/etc.)
sq override scaffold --role architect

# Start a wholly custom, non-dev role that isn't in the bundled catalog
sq override scaffold --new security-analyst
sq override scaffold --new security-analyst --can-spawn   # opt it into spawning subagents

# Overwrite an existing override
sq override scaffold items/task.md.j2 --force
```

**What it does:**
- `--role <slug>` copies the named bundled role into `.overrides/roles/` as an (initially empty)
  TOML stub to override fields on.
- `--new <slug>` starts a **brand-new, non-bundled** role: the essential fields (`full_name`,
  `title`, `description`, `mission`) are stubbed as active keys, the advanced fields
  (`responsibilities`, `agreements`, `model`, `color`, `can_spawn`) are included commented out.
  Refuses a slug that's already a bundled role — use `--role` for that. Follow up with `sq role
  activate <slug>` once you've filled it in.
- Template names copy the named bundled template into `.overrides/templates/`.
- Every scaffolded file is stamped with `<!-- squads:override-base:<current-squads-version> -->`.
- Refuses to clobber an existing override unless you pass `--force`.

**This is the only command that writes override bodies.** After scaffolding, you edit the file by
hand. squads never auto-rewrites an override — your customisations stay yours.

### `sq override diff`

Show two-sided diffs for an override to help you reconcile drift.

```bash
# Diff a specific template
sq override diff items/task.md.j2

# Diff a specific role
sq override diff --role architect

# Diff every drifted override (no name needed)
sq override diff

# JSON output for scripting
sq override diff items/task.md.j2 --json
```

**The two deltas:**

- **Δ-mine:** your override vs. the **current** bundled template — what you customised away from
  today's default.
- **Δ-upgrade:** the **base-version** bundled template vs. the **current** bundled template — what
  the upgrade changed underneath your override.

Both deltas are computed from the current package data and the `templates_manifest.json` shipped
with squads, so you can see what needs merging without having to find old squads versions.

### `sq override update`

Re-stamp an override's `override-base` version after you've hand-merged it, clearing the drift
warning.

```bash
# Update a specific template
sq override update items/task.md.j2

# Update a specific role
sq override update --role architect

# Bulk re-stamp every structurally-valid override
sq override update
```

**What it does:**
- Rewrites the `squads:override-base:` stamp to the current `squads_version`.
- **Never touches the override body** — this is not auto-rewriting. It is your signed assertion
  that you have manually reconciled the override against the current bundled default.

Run `sq check` afterwards to confirm the warning has cleared and the override is current.

### `sq override list`

List every present override with its kind, base version, and current drift state.

```bash
sq override list

# JSON output for scripting
sq override list --json
```

**Output columns:**

- **Name:** template path or role slug (e.g., `items/task.md.j2`, `architect`).
- **Kind:** `template` or `role`.
- **Base version:** the `squads_version` the override was branched from (from the stamp).
- **State:** 
  - `current` — the bundled counterpart hasn't changed since the base stamp.
  - `drifted` — the bundled counterpart changed and you should reconcile via `sq override diff` +
    hand-merge + `sq override update`.
  - `broken` — the override is missing a required `<!-- sq:* -->` marker (an error in `sq check`).

**Use this to see the override surface at a glance** — what you have, what's current, and what
still needs reconciling after a squads upgrade.

---

## Agent naming

When you run `sq init`, you can supply custom names for the bundled roles. This is especially
useful if your team has specific titles or prefers different names for the agent personas.

### Naming at initialization

**Declarative flags (repeatable):**

```bash
sq init --name architect="Ada Lovelace" --name manager="Grace Hopper"
```

**Configuration file:**

Add a `[init.names]` table to `.squads.toml`:

```toml
[init.names]
architect = "Chief Designer"
manager = "Team Lead"
tech-writer = "Documentation Lead"
```

**Interactive prompting (at a TTY):**

When you run `sq init` at an interactive terminal without supplying all names, squads prompts you:

```
Enter full name for architect: 
```

Pre-answer these prompts with flags or `[init.names]` so you're never blocked.

**Skip prompting entirely:**

```bash
sq init --default-names    # uses bundled names for all roles
```

This is useful in CI or scripts where you can't interact. **Non-TTY environments (pipes, scripts,
CI) always behave as if `--default-names` is set** — you'll never hit a prompt.

**Fallback:**

Any role not named via a flag, config, or prompt falls back to its bundled name (bundled roles)
or a name from the dev pool (custom developer roles).

### Naming roles after init

When you activate a new role or add a developer, you can provide a name then:

```bash
# Activate a bundled role with a custom name
sq role activate architect --name "Chief Designer"

# Add a Python developer with a custom name
sq dev add python --name "Pythonista"
```

Omit the name and the role falls back to its bundled or pooled default.

### How names flow into your squad

The chosen name is stored in the ROLE item's frontmatter (`extra.full_name`). Everything
downstream reads from there:

- The **Agent roster** in your `CLAUDE.md` (generated by `sq sync`).
- The **agent pointer files** in `.claude/` (e.g., `.claude/agents/architect.md`).
- The rendered **role body** in `squads/agents/roles/ROLE-*.md`.

If you want to rename a role later, edit the ROLE item:

```bash
sq role 002 update --extra full_name="New Name"
# or
sq sync                  # to regenerate from the current frontmatter
```

### Slug immutability

**Role slugs stay canonical and are never renamed.** The slug (`architect`, `tech-lead`,
`<tech>-dev`) is the addressing key for skills, @mentions, pointer filenames, and interactions. A
team renames *who fills the architect slot*, not *the architect slot itself*.

If you need a new role entirely, scaffold it under a new slug. If you need to split an existing
role, add a new one rather than renaming.

---

## Examples

### Customize the task template

Your team wants all tasks to have a standard "Success criteria" section and a "Dependencies"
section at the top. Scaffold the task template:

```bash
sq override scaffold items/task.md.j2
```

Edit `.overrides/templates/items/task.md.j2` to add your sections (keeping the required `<!-- sq:body -->`
marker):

```jinja2
# {{ item.title }}

## Success criteria

_Write the criteria for completion here._

## Dependencies

- [ ] Upstream requirement 1
- [ ] Upstream requirement 2

<!-- sq:body -->
<!-- sq:body:end -->
```

The next time a task is created or rendered, it will use your template.

### Override a role's name and model

You want the architect role to use a faster model for everyday work, and you want to call them
"Design Lead." Override the role:

```bash
sq override scaffold --role architect
```

Edit `.overrides/roles/architect.toml`:

```toml
full_name = "Design Lead"
model = "haiku"
```

The rest of the architect's definition (title, mission, responsibilities) stays the same. Run `sq
sync` to regenerate the pointer and CLAUDE.md section.

### Define a custom role

You want a compliance-officer role that isn't in the bundled catalog. Scaffold it:

```bash
sq override scaffold --new compliance-officer
```

This writes `.overrides/roles/compliance-officer.toml` with the essentials stubbed. Fill them in
(and uncomment any advanced fields you want):

```toml
full_name = "Compliance Officer"
title = "The keeper of standards"
description = "Ensures all code meets compliance requirements."
mission = "Keep the team on the right side of policy."
responsibilities = [
  "Review all PRs for policy violations",
  "Maintain the compliance handbook",
]
model = "opus"
```

Run `sq role activate compliance-officer` to add it to your active roster, then `sq sync` to
generate the pointer and listing.

### Upgrade overrides after a squads release

You upgraded squads and `sq check` warns that two overrides drifted. Review them:

```bash
sq override diff items/task.md.j2 items/bug.md.j2
```

The output shows Δ-mine (your customisations) and Δ-upgrade (what the release changed) for each.
You see that the bug template gained a new `<!-- sq:acceptance -->` marker. Merge that into your
override by hand:

```bash
$EDITOR .overrides/templates/items/bug.md.j2
```

Then re-stamp both:

```bash
sq override update items/task.md.j2 items/bug.md.j2
```

Or just:

```bash
sq override update
```

to re-stamp all structurally-valid overrides. Check the warnings are gone:

```bash
sq check
```

---

## Constraints and design

**Overrides are user-owned.** They live under `.overrides/` in your squad folder, not inside the
squads package. You author and maintain them; squads detects when the bundled originals change and
warns you to reconcile. We never auto-rewrite an override — merging upgrades is always manual.

**`.overrides/` is discoverable and portable.** It's found by the same squad-folder walk-up that
locates `.squads.toml`, so it travels with your squad and is safe from path-traversal attacks.

**Partial overrides are the default.** There is no "override everything" mode. Drop a single
template file and only that one changes; the rest stay bundled.

**`sq migrate` never touches overrides.** When squads upgrades, `sq migrate` handles the breaking
changes to durable item files; `sq override` handles the user-owned override surfaces. They're
separate concerns.

---

## Troubleshooting

**Q: I scaffolded a template but forgot to keep the required markers. How do I know what's
required?**

Run `sq check`. It will report which markers are missing as an error. Read the original bundled
template to see what you need to restore:

```bash
# Find the bundled template in the squads package
python -c "import squads._rendering; print(squads._rendering.__file__)"
# Then look at the templates/ subdirectory
```

**Q: I edited an override but `sq check` still warns about drift. Did I do something wrong?**

No — a drift warning means the **bundled original changed**, not that your edit was wrong. Run `sq
override diff` to see what the upgrade changed, incorporate those changes if needed, and then `sq
override update` to re-stamp.

**Q: Can I override the `.claude/` artifacts?**

No. Those are tool-owned and generated by `sq sync` from `ROLE` items and templates. If you want
to customize what appears in `.claude/`, override the templates that generate it
(`templates/claude/*` and `templates/agents/*`).

**Q: Can I have multiple squads with different override sets?**

Yes. Each squad folder has its own `.overrides/` directory, so teams can maintain different
customisations per squad. The overrides are discovered relative to your active squad folder
(via `--dir` or `.squads.toml`).

**Q: What if I want to add a *new* field to a role that isn't in the bundled definition?**

Role TOML overrides accept any field you add — they're flexible. If it's a field squads doesn't
recognize, it's preserved in `extra` and available to your own templates. For a field that squads
*does* recognize (like `model`), override the TOML and re-stamp the role item with `sq sync`.

# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-06-10

### Added

- **Bugs carry a `severity`.** A bug's severity (`critical|high|medium|low|info`) is a validated
  per-type field: `sq bug <n> update --set severity=high` (`--unset severity` clears it), shown as a
  colored badge in `sq bug <n> show`. Invalid values are rejected with the valid list.
- **Sub-entities get a full `update` metadata entry point — `sq <type> <n> <kind> <k> update …`.**
  Mirroring item-level `update`, it sets `--title`, `--status` (+`--force`), and
  `--assignee`/`--clear-assignee` on any story/subtask/finding, **plus the two fields that were
  previously write-once at `add`**: a subtask's `--story`/`--no-story` (validated against the parent
  feature) and a finding's `--severity`. Every change re-renders the block's heading, its `:head`
  badges, and the parent's summary-table row from the stored value.
- **Item bodies are sq-managed too — the workflow needs no hand-editing.** Set or revise any item's
  body with `sq body <ID> -m "…"` / `--file PATH` (`--file -` for stdin) / `--append`, set it at
  creation via the same flags on `sq create`, and read it with `sq show`. `--desc` now sets only the
  short one-line **summary** (shown in `sq list`); it no longer seeds the body, so the two never
  drift. (Role/skill bodies stay generated from their fields.)
- **Items record an `author`** — the registered agent who created them. `sq create` now requires
  `--author <slug>`, and the author must be a registered agent (a role in the squad) or it's
  rejected. Roles/skills self-author; `sq show` displays it and `sq check` warns if an author's role
  was later removed. (Distinct from `--assignee` = who's responsible.)
- **`sq update` is the one metadata entry point.** Beyond title/description/assignee/labels it now
  sets `--author`, `--status` (validated; `--force`), `--parent`/`--no-parent`, and **per-item-type
  fields** via `--set key=value` / `--unset key` (e.g. a review's `target_ref`, a guide's `tags`, a
  role's `model`/`color`), validated against a declared schema. Editing a role/skill regenerates its
  `.claude` pointer.
- **`sq comment` can target a review finding** (`--finding F1`), completing comment support across
  every sub-entity — user stories (`--story`), subtasks (`--subtask`), and findings (`--finding`).
- **Human-readable header on every sub-entity.** Each story / subtask / finding now carries an
  sq-owned `:head` region under its heading that renders its state prettily — `**Status:** 🟡 In
  Progress`, `**Assignee:** <full name>`, `**Severity:** 🟠 High` (findings), `**Implements:** US2 —
  <story title>` (subtasks) — kept in sync on every status/assignee change while the machine values
  stay in `:meta`. It's a template (`subentities/head.md.j2`); add an attribute by passing a value
  from `set_head` and adding a line.
- **Sub-entity bodies are sq-managed — no manual markdown editing.** Set or revise a user story /
  subtask / finding body with `sq story|subtask|finding body <ID> <LID> -m "…"` (repeatable
  paragraphs) or `--file PATH` (`--file -` reads stdin), `--append` to add to it; set it at creation
  via the same flags on `add`; and read the whole block (meta + body + discussion) with
  `sq <kind> show <ID> <LID>`. Bodies containing sq marker comments are rejected.
- **`assignee` is validated against the roster.** Setting an item's assignee (at `create` or via
  `sq update --assignee`) now requires a registered agent, just like `author`; `sq check` warns when
  an assignee's role was later removed.
- **Sub-entities carry their own assignee**, so a task's subtasks (and a feature's stories, a
  review's findings) can be parcelled out to different agents. Set it at creation (`--assignee
  <slug>`) or reassign with `sq subtask|story|finding assign <PARENT> <LID> <slug>` (`--clear` to
  unassign); it's validated against the roster, stored in the block's sq-owned `:meta` region, and
  shown in both `… list` and the parent's roll-up summary table.
- **Items carry a `priority`.** An optional `priority` (`urgent|high|medium|low`) is a first-class
  field, independent of status: set it at creation (`sq create … --priority high`) or with
  `sq <type> <n> update --priority high` / `--no-priority`. It shows as a colored badge in
  `sq <type> <n> show` and a new **Priority** column in `sq list`, and filters with
  `sq list --priority high`. (Additive frontmatter field — old items read back as unset and no
  migration is needed.)
- **Closed items are hidden by default.** `sq list` and `sq tree` now show only open items; pass
  `--all`/`-a` to include closed (Done/Cancelled/…) ones, or filter directly with an explicit
  `--status`. This keeps day-to-day views focused without deleting anything — items are "archived"
  simply by reaching a terminal status.
- **`sq search TEXT`** — find items by matching their title, summary, and body/discussion prose
  (case-insensitive), printed with the matching lines (`--type` to scope, `--json` for machine use).
- **`sq blocked`** — surface what's stuck: open items that have at least one *open* blocker via the
  `blocks` ref kind (`A ref add B --kind blocks` reads "A blocks B"), each shown with its blockers.
- **`sq mine [ROLE]`** — items assigned to a role (defaults to the squad's configured default role);
  honors the same closed-hiding (`--all` to include) as `sq list`.
- **`sq workload`** — open/closed/total work-item counts per assignee, busiest first.
- **`sq tree … --json`** — emit the nested subtree (`id/type/status/priority/assignee/blocked` +
  `children`), honoring a root id and `--all`. This is the one read an orchestrating agent uses to
  see a feature's whole state and decide what to do next.
- **Precise per-actor guidance in every item skill.** Each `sq-<type>` skill now gives every actor
  that touches the item (e.g. tech-lead / developer / reviewer / QA on a task) structured guidance
  under fixed labels — **Enter** (what to read first), **Do** (the steps, with concrete `sq`
  commands), **Hand off** (the trigger + target), and **Watch for** (scope discipline) — instead of
  a one-line summary. The shared **developers** section appears only once the squad has a
  `<tech>-dev` role (added/removed live with `sq dev add` / `sq role rm`).
- **`greeting` skill — agents greet the operator on arrival.** A new always-preloaded managed skill
  has every role, when a human opens a conversation, detect who they're talking to (Claude user /
  `git config user.name` → `op-<firstname>`), register them if needed (`sq operator add`), then greet
  — **matching the human's tone** ("Hello Robert" → "Good morning, Pierre"; "Hi Mara!" → "Hey
  Pierre!"), saying how they can help, and giving a quick read of the project. Subagents spawned for
  internal work skip the greeting. (Preloaded alongside `squads` for all roles.)
- **Operators — humans as first-class participants.** A new `operator` item type represents the
  people who work on the project (slug `op-<firstname>`). Register them with `sq operator add
  "<name>"` (`list`/`rm` too); an `op-` slug is then a valid `--author`/`--assignee` on items and
  sub-entities and `--as` on comments — the assignment gates accept registered **roles or
  operators**. Operators are not agents: never spawned, no `.claude/agents` pointer, no skills, and
  they're excluded from `workload`. `CLAUDE.md` gains an "Operators (people)" roster and a
  session-start ritual (work out who the human is, `sq operator list`, ask to register, **ask if
  unsure**). Additive — no migration.
- **Reinforced role entry points.** Every role's definition now carries the operating contract
  (keep an item's status current; hand back through a `sq comment`; follow your `sq-<type>` skill's
  section), and the `squads` skill gains a **"Working directly with the operator"** rule for when the
  operator bypasses the manager. The greeting/impersonation also accepts a role by *function*
  ("the dotnet dev" → `dotnet-dev`), not just by name.
- **Orchestration-loop guidance.** The generated `CLAUDE.md` now teaches the manager/default agent
  to run work as a loop — *assess via `sq` → delegate by spawning the specialist as a Claude Code
  subagent (`subagent_type: <role-slug>`) with the item ID → integrate the result → repeat until
  done*. `@mention`/`inbox` are framed as the durable record of who-was-asked-what; the spawn is the
  handoff. (Each squads role is already a spawnable subagent with its model/skills preloaded.)

### Changed

- **Prose edits are now concurrency-safe.** `sq comment`, `sq <type> <n> body`, and sub-entity
  bodies write the `.md` file *inside the index lock* (atomically with the `updated_at` bump),
  instead of an unlocked read-modify-write. Parallel `sq` callers — e.g. several dev subagents
  working at once — can no longer silently drop each other's comments or body edits.

- **BREAKING — the sub-entity shortcut verbs are removed; `update` is the single entry point.**
  `sq <type> <n> <kind> <k> status …`, `… assign …`, and the subtask `… done` are gone — use
  `… update --status …` (`--force` to override / replace `done`), `… update --assignee …`
  (`--clear-assignee`). The remaining sub-entity verbs are `show`, `update`, `body`, `comment`.
  (Item-level `status` is unaffected.)
- **Sub-entity state moved from body markers to frontmatter.** A story / subtask / finding's machine
  state — status, assignee, severity, mapped story, and title — is now a typed `subentities:` list in
  its parent item's YAML frontmatter, single-sourced and pydantic-validated like every other item
  field. The index therefore **sees sub-entities** (so `sq list`/`sq check` and transition validation
  read them without parsing bodies), and `sq repair` reconstructs them from frontmatter. Only the
  prose (`:body` / `:discussion`) and the derived presentation (`:head` badge line, `:summary` table)
  stay in the markdown body; the per-block `:meta` region is gone. (`sq <type> <n> show` and the
  `… <kind> show` views are unchanged.)
- **BREAKING — resource-oriented CLI grammar.** Items are now addressed as `sq <type> <number>
  <verb> …`, with sub-entities nested one level deeper. The flat and sub-app commands are removed and
  replaced:
  - `sq show/update/status/comment/body ID` → `sq <type> <n> show|update|status|comment|body`
  - `sq link/unlink ID` → `sq <type> <n> update --parent/--no-parent`
  - `sq refs ID` / `sq ref add FROM TO` → `sq <type> <n> refs` / `sq <type> <n> ref add TARGET`
  - `sq story|subtask|finding add PARENT …` → `sq <type> <n> add-story|add-subtask|add-finding …`
  - `sq story|subtask|finding <op> PARENT LID …` → `sq <type> <n> story|subtask|finding <k> <op> …`
  - `sq guide add` → `sq create guide`
  The number may be bare (`35`), padded (`000035`), or the full id (`TASK-000035`); the type word
  validates it. `create`, `list`, `tree`, `init`/`adopt`, `check`/`repair`/`sync`, `docs`,
  `workflow`, `inbox`, and the `role`/`dev`/`skill`/`migrate` groups are unchanged. (Examples
  throughout the Added section below use the new grammar.)
- **An item's integer `sequence_id` is now its real identity; the formatted `id` is derived.**
  `Item.sequence_id` (the global counter number) is a stored field persisted in both `.md`
  frontmatter and `.squads.json`; `id` (`TASK-000007`) is computed from `type` + `sequence_id`. The
  index keys items by `sequence_id` (`items: {7: …}`) rather than the formatted id. The loader
  normalizes legacy full-id index keys, and the **0.2 → 0.3 migration backfills `sequence_id`** into
  existing frontmatter, so existing squads upgrade cleanly via `sq migrate up`.
- **`schema_version` now tracks the alpha release that introduced the schema** (`"0.1"`, `"0.2"`)
  instead of an opaque integer counter (`1`, `2`), in both `.squads.toml` and `.squads.json`. Existing
  alpha squads must update the value by hand (`schema_version = 2` → `schema_version = "0.2"` in
  `.squads.toml`; `sq repair` then restamps `.squads.json`).
- **Comments read better with multiple points.** Each repeated `-m` is its own bullet under the
  timestamp (now shown in the help + agent guidance), and a multi-line `-m` value keeps its
  continuation lines nested under its bullet — including fenced code blocks (internal blank lines
  stay indented) — instead of breaking the list.

### Migration

- **`schema_version` → `"0.3"`.** `sq migrate up` applies the new **0.2 → 0.3** step automatically:
  it backfills the integer `sequence_id`, **lifts each sub-entity's `:meta` state into the new
  `subentities:` frontmatter list and deletes the `:meta` markers**, and renders the `:head` region
  (status / assignee-name / severity / story badges), resolving names from the role files and story
  titles from parent features. Fully automatic and idempotent. (An out-of-date squad is gated until
  you run it — `sq migrate help` / `chlog` list every step.)

### Fixed

- **Global `--at` / `--dir` now work after the subcommand too** (e.g. `sq create task "X" --at
  2024-01-01`), not only before it. They're hoisted to the front at the entry point, so position no
  longer matters.

## [0.2.0] - 2026-06-08

### Added

- **`sq docs`** — list the bundled documentation, and `sq docs <name>` prints any page straight to
  the terminal so agents (and humans) can read the full docs **offline, with no fetch**. Raw
  markdown by default; `--rich` pretty-prints. The docs ship inside the wheel as package data.
- **Status state machines for sub-entities, tracked by `sq`.** Subtasks and user stories now have a
  status (`Todo → InProgress → Done`, + `Blocked`, `Cancelled`): `sq subtask status TASK STn <Status>`,
  `sq story status FEAT USn <Status>` (transitions validated; `--force` to override).
- **Review findings are first-class.** `sq finding add REV "…" --severity high|…`,
  `sq finding status REV Fn <Status>` (`Open → Fixed → Verified`, + `WontFix`), `sq finding list`.
- **`sq`-managed summary tables.** Tasks/features/reviews carry a top-of-section table rolling up
  their subtasks/stories/findings (status, and severity for findings), regenerated on every change.

### Changed

- **Ref kinds are now stored inline with the edge.** A reference is `ID` (the default `related`) or
  `ID:kind` (e.g. `BUG-000009:fixes`) in an item's `refs`, replacing the separate
  `extra.ref_kinds` map. The `sq ref`/`sq refs` interface is unchanged. (`schema_version` → 2.)
- **Sub-entity state lives in scoped markers, not the heading.** Each subtask/story/finding block
  keeps its status (and severity/story map) in an sq-owned `:meta` region — the heading is plain
  prose. `subtask done` is kept as a shortcut.
- **Discussion sections now carry a heading** at the right depth — `##` at item top level, `####`
  inside a story/subtask/finding.

### Migration

- On an out-of-date squad, `sq` **stops and tells you to run `sq migrate up`**, the new migration
  command group: `up` runs the automatic runners (rebuild index + restamp), `help` lists the
  migration changelog, and `chlog vA..vB` prints the manual steps for a release range. The `v1 → v2`
  runner folds legacy `extra.ref_kinds` into inline refs, upgrades sub-entity headings (`[ ]`/`[x]`
  checkboxes and `(→ USn)` suffixes) into the new `:meta` regions, builds the summary tables, and
  gives legacy reviews an empty findings container.
- **One manual step (LLM-assisted):** a pre-2 review's free-form prose findings can't be structured
  automatically — `sq migrate up` prepares the container, then an agent recreates each as
  `sq finding add … --severity …`. Read it with `sq migrate chlog v0.1.1..v0.2.0`.

## [0.1.1] - 2026-06-08

### Fixed

- **Windows: every write command crashed** (`sq init`, `create`, `status`, `repair`, …). The atomic
  index write called `os.fsync()` on a read-only file handle, which Windows rejects with
  `OSError [Errno 9]`; it now fsyncs the write handle that produced the bytes.
- **Windows: non-ASCII output crashed** under the legacy cp1252 console (`UnicodeEncodeError` on
  `→`/`•`/`—`, e.g. from `sq workflow`). The CLI now forces UTF-8 stdio on Windows.
- **Windows: reading squad files crashed or silently corrupted non-ASCII content.** `sq check`
  (and any read path) used `Path.read_text()` with no encoding, so on a non-UTF-8 locale (e.g.
  cp1252) a heading such as `### ST1 — … (→ US1)` either raised `UnicodeDecodeError` or decoded the
  `→` to mojibake — breaking subtask/story validation. All file I/O is now pinned to
  `encoding="utf-8"`. The CI test matrix now runs the suite on Windows and macOS as well as Linux,
  so this class of bug is caught before release.

## [0.1.0] - 2026-06-08

Initial release.

### Added

- **CLI** (`squads` / `sq`) for managing a team of AI agents as identified markdown with a
  JIRA-like, globally-unique ID system. Item types: epic, feature, task, bug, decision (ADR),
  review, guide, role, skill.
- **Index** — a single `<squad>/.squads.json` with one global monotonic counter and all item
  metadata; filelock'd, atomic writes. The `.md` frontmatter is the durable source of truth; the
  index is rebuildable (`sq repair`, `sq repair --renumber`).
- **Commands** — `init`, `adopt`, `create`, `list`, `show`, `tree`, `link`/`unlink`, `update`,
  `status`, `comment`, `story`, `subtask`, `ref`/`refs`, `inbox`, `role`, `dev`, `skill`, `guide`,
  `check`, `repair`, `sync`, `workflow`. Global `--dir` (target a squad) and `--at` (forge
  timestamps for history-preserving migration).
- **Workflow** — per-type status machines with validated transitions; parent rules
  (task → feature, feature → epic); typed forward refs with computed backrefs; user stories &
  subtasks with their own discussion; `@mention` inbox.
- **Claude Code backend** — thin `.claude/` pointers to real definitions under the squad folder,
  bundled `squads` skill + per-item-type skills, a managed `CLAUDE.md` section with
  greeting-based impersonation, and a non-clobbering `settings.json` merge.
- **8 bundled roles** + on-demand stack developers (`sq dev add`); the role↔item-type playbook.
- **Docs** — README, plus `docs/` (workflow, internals, adoption, agents, tutorial, roles,
  backends, recipes, faq); `py.typed`; MIT licensed.

[Unreleased]: https://github.com/TheCaptainCat/squads/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/TheCaptainCat/squads/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/TheCaptainCat/squads/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/TheCaptainCat/squads/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/TheCaptainCat/squads/releases/tag/v0.1.0

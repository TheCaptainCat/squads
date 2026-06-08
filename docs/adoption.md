# Adopting squads in an existing project

This guide covers bringing an existing project under `sq` management — whether it already has a
squads-shaped folder, or just a pile of issue/spec markdown you want to migrate while **preserving
the original dates**.

The key tool for history is the global **`--at <when>`** option: every time-based command
(`create`, `status`, `update`, `comment`, `story`/`subtask`, `ref`, `link`, …) records its
timestamps from `--at` instead of the wall clock. A human or an LLM driving the migration can
therefore forge the historical dates so the imported history looks real.

```
sq --at 2024-01-15            create task "Fix login"      # created_at = that date
sq --at 2024-01-15T09:30:00Z  status TASK-000002 InProgress
```
`--at` accepts an ISO-8601 date or datetime (a bare date is midnight; naïve values are UTC). It is
a **global** option, so it goes *before* the subcommand and applies to that one invocation.

---

## 1. Install and scaffold

```bash
uv tool install squads          # or: uvx --from squads sq …
cd your-project
sq adopt                        # non-destructive: see below
```

**`sq adopt`** is the idempotent cousin of `sq init`:

- creates `.squads.toml` if missing (keeps it otherwise);
- ensures the squad folder + per-type subfolders and the `.claude/` scaffolding;
- **imports** any squads-native `.md` files already present (rebuilds the index + the global
  counter from their frontmatter — same engine as `sq repair`);
- activates the bundled roles it doesn't already have.

Run it as often as you like; it never clobbers authored content. Use `--squad-dir`, `--roles`,
`--no-claude` exactly like `init`.

If your existing files **already** follow the squads layout (type subfolders, `PREFIX-NNNNNN-*.md`
filenames, sq frontmatter), `sq adopt` is all you need — it indexes them in place. If not, convert
them (next section).

## 2. Convert legacy documents (preserving history)

For each legacy artifact (an old ticket, spec, ADR, …):

1. **Recreate it as a squads item at its original date.** `create` prints the new file path:
   ```bash
   sq --at 2024-01-15 create feature "User authentication" --parent EPIC-000001
   # → created FEAT-000007 → squads/features/FEAT-000007-user-authentication.md
   ```
2. **Move the legacy content into the body** — write your prose between the `<!-- sq:body -->`
   markers of that file (leave the marker lines intact). For features, scaffold the user stories;
   for tasks, the subtasks:
   ```bash
   sq --at 2024-01-15 story add FEAT-000007 "As a user, I want to log in"
   sq --at 2024-01-16 subtask add TASK-000008 "Validate token" --story US1
   ```
3. **Replay the status history** in order, each at its real date:
   ```bash
   sq --at 2024-01-16 status TASK-000008 InProgress
   sq --at 2024-01-20 status TASK-000008 Done
   ```
   (Only the final status persists in the index; the dated discussion entries below are what give
   you the timeline.)
4. **Re-create comments / hand-offs** as dated discussion entries, attributed to the right agent:
   ```bash
   sq --at 2024-01-17T14:00:00Z comment TASK-000008 --as reviewer -m "LGTM, ship it"
   ```
5. **Re-link relationships** (parent, bug/review refs):
   ```bash
   sq --at 2024-01-15 ref add TASK-000008 BUG-000009 --kind fixes
   ```

Work in chronological order so each `updated_at` reflects the last real activity.

## 3. Validate

```bash
sq check        # markers, dangling parents/refs, invalid status, frontmatter↔index drift
sq tree         # eyeball the imported hierarchy
sq repair       # rebuild the index from frontmatter if anything looks off
```

`sq repair` and `sq check` read timestamps straight from the frontmatter, so the dates you forged
with `--at` are preserved across rebuilds.

---

## Letting an agent do it

After `sq adopt`, the project's `CLAUDE.md` and the `squads` skill teach the agents the workflow.
Point an agent (e.g. the manager or tech-lead) at the legacy docs and ask it to migrate them
file-by-file using the steps above — it already knows the commands, and `--at` lets it stamp each
item with the date it reads from the source document.

## Notes & caveats

- `--at` sets **both** `created_at` and `updated_at` for a `create`; re-run later commands at later
  dates to advance `updated_at`.
- One timestamp per invocation — run a separate `sq … ` command per historical event.
- The global counter is monotonic: IDs reflect *adoption* order, not historical order. The dates
  (not the ID numbers) carry the timeline.
- A task's parent must be a feature; bugs/reviews attach via `--kind fixes|addresses` (see
  `sq workflow`).

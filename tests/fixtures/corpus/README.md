# Migration fixture corpus

Each subdirectory here is a **frozen, committed squad** captured at one released schema version.
`tests/integration/test_migration_corpus.py` copies each to a tmp dir, runs `sq migrate up` (via
`Service.run_pending_migrations()`), and asserts the squad reaches the current `SCHEMA_VERSION`
with `sq check` clean.  The CLI smoke variant does the same thing through the real Typer app.

## Directory layout

```
corpus/
  v0_1/    — schema 0.1: bare refs + extra.ref_kinds, legacy heading-encoded sub-entity state
  v0_2/    — schema 0.2: inline ref kinds (ID:kind), :meta body regions for sub-entity state
  v0_3/    — schema 0.3: sequence_id in frontmatter, subentities list in frontmatter, :head regions
  v0_5/    — schema 0.5: skills are first-class SKILL-prefixed items
  v0_7/    — schema 0.7: unpadded display ids (frontmatter id/refs/parent; filenames stay padded)
  v0_8/    — schema 0.8: bug severity as a top-level key (relocated off extra.severity)
  v0_10/   — schema 0.10: sq-memory tracked as a SKILL item (no legacy sq-memory.md in this
             minimal corpus, so this fixture is byte-identical to v0_8 except the schema stamp)
  v0_11/   — schema 0.11: schema-stamp-only gate for the `scopes` ref kind (custom-skill role
             scoping); byte-identical to v0_10 except the schema stamp, since no frontmatter
             shape changed
  v0_14/   — schema 0.14: two new bundled item types (contract/PRD, milestone/MILE) — carries
             v0_11's content plus each type's managed skill, stamped as a SKILL item, body and
             `.claude` pointer; no existing frontmatter shape changed
  v0_15/   — schema 0.15: the milestone roll-up moves off its type attachment onto a
             `sq:view:milestone_rollup` body tag, and a role/permanently-system-skill/
             per-item-type-skill body renders through its own declared `sq:view:<name>` tag,
             positioned by the spec (`top`/`bottom`/`after(<regex>)`) and disableable rather
             than removable. Produced by running the *real* 0.14→0.15 migration end to end —
             `sq migrate up` against a scratch copy of the frozen `v0_14` fixture, clock pinned
             to this corpus's own `2025-05-20T11:00:00Z` convention — never hand-edited: the
             milestone's tag, the role/`squads`/`greeting` skill bodies, and `sq-contract`'s/
             `sq-milestone`'s (per-item-type skills — the reclaim's scope is the roster
             classification itself, not the three permanently-system slugs alone) legacy
             prose all converge onto their own tags by the migration's reclaim step, and the
             trailing repair sweep's own retired-region strip and role-mirror-key removal are
             all exactly what that run wrote
```

Each directory contains:
- `.squads.toml` with `schema_version` set to the captured version and `squad_dir = "."`
- `.squads.json` with the index at that version's shape
- A minimal set of item markdown files (role, feature, task, bug, decision, review) that exercise
  the migration transforms for that version

## Standing rule: add a fixture on every schema bump

When `_models/_schema.py::SCHEMA_VERSION` is bumped **and** a new runner is appended to
`_migrations/_registry.py::MIGRATIONS`, a new corpus fixture **must** be committed here:

1. Copy the current `v0_N` fixture as `vN_M` (the new *from* schema label, underscored).
2. Verify the copy passes `sq check` (it should — it's the current schema).
3. Add `("N.M", "vN_M")` to `_CORPUS_CASES` in `tests/integration/test_migration_corpus.py`.
4. Update the `v0_N+1` fixture to represent the *new* current schema by running the real
   migration end to end — `sq migrate up` (a real CLI invocation, not an isolated call to one
   migration step) against a scratch copy of the frozen `v0_N` fixture, clock pinned with
   `--at` — and committing exactly what that run wrote, minus any `.reflog.jsonl` it created.
   Never a hand copy with only the schema stamp bumped, and never a single migration step run
   in isolation: either shortcut leaves the fixture short of what the release actually ships (a
   retired region, a role mirror key, a body-tag convergence) and a test written against it
   quietly asserts the gap instead of the release. Then verify
   `test_corpus_migrates_to_current_schema_and_passes_check` is green for all entries.

Without this step the corpus drifts and the migration promise goes untested for the new schema.

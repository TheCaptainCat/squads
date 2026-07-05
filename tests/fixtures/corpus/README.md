# Migration fixture corpus

Each subdirectory here is a **frozen, committed squad** captured at one released schema version.
`tests/test_migration_corpus.py` copies each to a tmp dir, runs `sq migrate up` (via
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
3. Add `("N.M", "vN_M")` to `_CORPUS_CASES` in `tests/test_migration_corpus.py`.
4. Update the `v0_N+1` fixture to represent the *new* current schema, then verify
   `test_corpus_migrates_to_current_and_passes_check` is green for all entries.

Without this step the corpus drifts and the migration promise goes untested for the new schema.

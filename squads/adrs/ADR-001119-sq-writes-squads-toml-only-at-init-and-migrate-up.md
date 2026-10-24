---
id: ADR-1119
sequence_id: 1119
type: decision
title: sq writes .squads.toml only at init and migrate up
status: Accepted
author: architect
refs:
- TASK-1098
- ADR-1100
- REV-1118
description: The adopter owns .squads.toml; squads_version is dropped everywhere and
  only the schema gate remains
created_at: '2026-10-24T17:31:43Z'
updated_at: '2026-10-24T18:17:07Z'
---
<!-- sq:body -->
## Context

`.squads.toml` is written by hand by adopters: comments, `working_language`, `[display]`, keys reserved for later settings. `sq` has been rewriting it in place on every `sq sync` (the `squads_version` stamp) and on every `sq migrate up` (the `schema_version` stamp and the 0.2-era legacy keys). Each line-editing approach has failed on a valid TOML shape it did not anticipate: a multi-line value truncated, a quoted key dropped, a trailing comment folded into an array, a `[`-leading line inside a multi-line string read as a table header (REV-1118 F1 to F4, F9). The file has an owner, and it is not `sq`.

`squads_version` is the reason `sq sync` writes the file at all. Its copy in `.squads.json` cannot be rebuilt from the item files, against invariant 1, and nothing reads it. The schema version already gates what must be gated: a squad whose `schema_version` differs from the package's is stopped until `sq migrate up` runs.

## Decision

- **Ownership.** `.squads.toml` is the adopter's file. `sq` writes it at `sq init` and an adopt that creates it (the whole file; there is nothing to preserve), and during `sq migrate up` as stated below. No other command writes it, `sq sync` included. No `tomlkit` dependency.
- **`squads_version` is gone.** It is removed from `SquadsConfig` and `SquadsDB`, and no managed file carries a version stamp in its place. An existing `squads_version` line in `.squads.toml` or key in `.squads.json` is ignored on read (both models ignore unknown keys); nothing writes or removes it. No migration and no schema bump. The `squads_version` passed to `plan_reconcile` in `run_pending_migrations` and the parameter of `IndexStore.create_empty` go with it.
- **Only the schema stops the CLI.** The schema gate (`apply_gate`) is unchanged and is the one version check left.
- **The upgrade notice is removed.** `version_notice` ("managed files at X, run `sq sync`") goes; nothing replaces it. Refreshing generated files after an upgrade is the adopter's `sq sync`, as the release notes say.
- **The roster body-tag backfill runs on every `sq sync`.** `_backfill_roster_body_tags` loses its drift gate. It is idempotent, and its cost is a walk over the role and skill items only, not the whole corpus; the implementer measures it on a large roster and reports the figure on the task.
- **The empty-body hints lose their drift branch.** `sq role show` and `sq skill show` no longer compute `drift_outstanding`, and `empty_body_hint_state` drops that parameter. A declared view that renders empty shows one hint: run `sq sync`, and if the body stays empty, declare the definition in the overrides or re-enable the tag with `view add`. The undeclared and disabled hints are unchanged.
- **The `schema_version` stamp.** The only in-place edit, and only during `sq migrate up`. It rewrites the value of the one top-level line of the form `schema_version = "<v>"` (bare or quoted key, any spacing, a single-line string without escapes, any trailing comment) and changes nothing else. It applies only when exactly one such line exists, its value equals the parsed `schema_version`, and the rewritten text parsed with `tomllib` equals the original table with `schema_version` alone changed. Anything else (a multi-line or escaped string, two candidate lines, a line the parse check disagrees with) is a `SquadsError` that names the file and the line to set by hand. The text is computed and checked before the first migration runner, so a refusal leaves the squad untouched; it is written last, after the repair.
- **Legacy keys.** When the parsed file carries `default_backend` or `default_role` at top level, `sq migrate up` regenerates the whole file instead of stamping it: parse with `tomllib`, read it into `SquadsConfig` (which translates `default_backend` to `active_backends` and drops `default_role`), set the new `schema_version`, and write `to_toml()`. Comments are lost on those squads. The regenerated text must parse with `tomllib` and read back to the same `SquadsConfig`; otherwise the migration refuses before its first runner and writes nothing. A top-level key or table the model does not carry is named in the migration report rather than dropped silently.

## Consequences

- An adopter's edits to `.squads.toml` survive every `sq sync`, and `sq migrate up` either applies a one-value edit verified by a parse, or refuses with a message saying what to change.
- `to_toml_keeping`, `_stamp_version` and the line-based `drop_legacy_config_keys` go away; `to_toml()` remains for init, adopt and the legacy regeneration.
- Nothing tells an adopter that generated files are older than the installed `sq`; a release with new generated content relies on its notes asking for `sq sync`.
- Every `sq sync` pays the roster walk of the backfill, measured before the change lands.
- Old `squads_version` lines stay in adopters' files as inert text; the docs say the key is unused and can be deleted.
- This replaces the stamp clause of ADR-1100 ("A version or schema stamp edits only the version lines sq owns…"); the rest of ADR-1100 stands.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T17:32:03Z] `architect` Robert Architect:
  - Records the op-pierre decision on TASK-1098 (1901332). Generated files carry no version stamp today (removed with the per-skill markers), so the managed-region stamp is new. No schema bump: both squads_version keys are ignored on read. @op-pierre for acceptance; @tech-lead to fold into TASK-1098 once accepted.
- [2026-10-24T18:15:34Z] `op-pierre` Pierre Chat:
  - Decision: drop squads_version entirely, from .squads.toml, .squads.json and the managed files alike; no replacement stamp. Only the schema_version mismatch stops the CLI. sq writes .squads.toml only at init/adopt and during sq migrate up.
- [2026-10-24T18:16:38Z] `architect` Robert Architect:
  - Revised per op-pierre d206aa4: squads_version dropped from SquadsConfig, SquadsDB and the managed files, with no replacement stamp. version_notice removed, the roster backfill runs on every sync (the implementer measures the cost), and the role/skill empty-body hints lose their drift branch. The earlier managed-region stamp and recorded_version are withdrawn.
- [2026-10-24T18:17:07Z] `manager` Catherine Manager:
  - Accepted: the body records op-pierre decisions on TASK-1098 and on this ADR as made. @tech-lead folded into TASK-1098; @architect narrow ADR-1100 stamp clause.
<!-- sq:discussion:end -->

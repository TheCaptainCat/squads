---
id: ADR-1100
sequence_id: 1100
type: decision
title: 'working_language: one BCP 47 tag in .squads.toml, English fallback'
status: Accepted
author: architect
refs:
- FEAT-1097
description: A top-level working_language key holds a Babel-known BCP 47 tag; absent
  means English silently, malformed warns and falls back to English
created_at: '2026-10-24T09:20:18Z'
updated_at: '2026-10-24T09:22:24Z'
---
<!-- sq:body -->
## Context

A squad has no declared language, so item text, comments and agent briefs follow whatever language the last message used, and an agent cannot tell the language the project works in from the language the human speaks. FEAT-1097 adds one setting for this. The rulings on FEAT-1097 and TASK-1098 (op-pierre, 2026-10-24) fix its name, value set, fallback and cost; this record states them as the rule for `.squads.toml`.

## Decision

- **Key.** `working_language` in `.squads.toml`, a top-level string. It names the one language for everything that goes through `sq` (item titles, bodies, sub-entity text, comments) and for all agent-to-agent communication. Agents reply to a human in the language that human writes in, deduced per message; that conversation language is never configured.
- **Reserved names.** `language` and `locale` are held for the CLI's own localization. This key does not read, write or accept them.
- **Value.** A BCP 47 tag (`fr`, `en`, `pt-BR`). The accepted set is every tag Babel knows: a value is valid when `Locale.parse(tag, sep='-')` succeeds. There is no hand-picked list.
- **Fallback.** An absent key means English (`en`), silently: it is a legitimate default. A malformed or unknown value prints a warning and English applies; it is never an error. `sq check` also reports a malformed value, as it does for the `[display]` table.
- **Where it is checked.** Babel is imported and the value validated at service start, on every command. The startup cost is accepted because the future `locale` setting needs Babel at startup anyway.
- **Rendering.** The rule rendered into the managed agent-facing files and the `squads` skill shows the English display name plus the tag, e.g. "French (`fr`)". A future `locale` may render the name in other languages.
- **Writing the key.** `sq init` and an adopt that creates `.squads.toml` write `working_language = "en"`. `sq sync` and a version or schema stamp never add the key, and keep an existing line as written.
- **No schema bump.** An absent key is a valid configuration, so no migration is needed.

## Consequences

- squads depends on Babel, and every command pays its import.
- A typo in the key's value never blocks work: the squad runs in English and says so on every command until the value is fixed.
- Existing squads keep working unchanged and render English until an adopter sets the key.
- Changing the key and running `sq sync` updates the managed sections; the `squads` skill picks it up on its next read.
- CLI localization stays a separate, later setting with its own name.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T09:22:24Z] `op-pierre` Pierre Chat:
  - Accepted.
<!-- sq:discussion:end -->

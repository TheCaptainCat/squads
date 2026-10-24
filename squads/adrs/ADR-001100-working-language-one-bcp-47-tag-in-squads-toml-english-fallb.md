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
updated_at: '2026-10-24T18:18:13Z'
---
<!-- sq:body -->
## Context

A squad has no declared language, so item text, comments and agent briefs follow whatever language the last message used, and an agent cannot tell the language the project works in from the language the human speaks. FEAT-1097 adds one setting for this. The rulings on FEAT-1097 and TASK-1098 (op-pierre, 2026-10-24) fix its name, value set, fallback and cost; this record states them as the rule for `.squads.toml`.

## Decision

- **Key.** `working_language` in `.squads.toml`, a top-level string. It names the one language for everything that goes through `sq` (item titles, bodies, sub-entity text, comments) and for all agent-to-agent communication. Agents reply to a human in the language that human writes in, deduced per message; that conversation language is never configured.
- **Reserved names.** `language` and `locale` are held for the CLI's own localization. This key does not read, write or accept them.
- **Value.** A BCP 47 tag (`fr`, `en`, `pt-BR`). The accepted set is every tag Babel knows without likely-subtag resolution: a value is valid when `Locale.parse(tag, sep='-', resolve_likely_subtags=False)` succeeds. There is no hand-picked list. `und`, `root` and non-canonical alias codes (`iw`, `fra`) are not working languages and take the malformed path.
- **Fallback.** An absent key means English (`en`), silently: it is a legitimate default. A malformed or unknown value prints a warning and English applies; it is never an error. `sq check` also reports a malformed value, as it does for the `[display]` table.
- **Where it is checked.** Babel is imported and the value validated at service start, on every command. The startup cost is accepted because the future `locale` setting needs Babel at startup anyway.
- **Rendering.** The rule rendered into the managed agent-facing files and the `squads` skill shows Babel's English display name plus the tag exactly as the adopter wrote it, e.g. "French (`fr`)". A future `locale` may render the name in other languages.
- **Writing the key.** `sq init` and an adopt that creates `.squads.toml` write `working_language = "en"`. `sq sync` never adds the key. Every other write to `.squads.toml` follows ADR-1119.
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
- [2026-10-24T15:35:19Z] `architect` Robert Architect:
  - - 2026-10-24: amended after REV-1118 F4 and F6 (fix direction f6a961e). Value: valid only when Babel parses the tag without likely-subtag resolution; `und`, `root` and alias codes (`iw`, `fra`) take the malformed path, and the rendered tag is the one written. Stamp: edits only the version lines sq owns and keeps every other line of `.squads.toml` byte for byte.
- [2026-10-24T17:32:02Z] `architect` Robert Architect:
  - ADR-1119 (Proposed) replaces the stamp clause of this record ("A version or schema stamp edits only the version lines sq owns..."): sync no longer writes .squads.toml, and the only in-place edit left is schema_version during sq migrate up. Clause-level overlap, so linked related rather than superseded; this clause gets narrowed in place when ADR-1119 is accepted.
- [2026-10-24T18:18:13Z] `architect` Robert Architect:
  - 2026-10-24: amended after ADR-1119 was accepted. The stamp sentence in Writing the key is replaced by a pointer to ADR-1119, which governs every write to .squads.toml; init/adopt still write "en". Nothing else changed.
<!-- sq:discussion:end -->

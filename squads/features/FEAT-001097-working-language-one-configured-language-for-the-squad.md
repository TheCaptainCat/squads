---
id: FEAT-1097
sequence_id: 1097
type: feature
title: 'Working language: one configured language for the squad'
status: Done
author: product-owner
refs:
- MILE-1051:targets
description: A squad declares one working language for sq content and agent communication;
  agents answer the human in the human's language.
subentities:
- local_id: US1
  title: Configure working_language in .squads.toml
  status: Done
- local_id: US2
  title: Render the language rule in every backend and the squads skill
  status: Done
- local_id: US3
  title: Write working_language on init and adopt
  status: Done
- local_id: US4
  title: Document working_language for adopters
  status: Done
created_at: '2026-10-24T08:48:52Z'
updated_at: '2026-10-24T19:02:02Z'
---
<!-- sq:body -->
## Problem

A squad has no declared language. Item titles, bodies, comments and agent briefs end up in whatever language the last message happened to be in, and agents cannot tell which language the project works in versus which language the human speaks. Adopters who work in another language have no way to say so, and the managed agent-facing files are silent on the subject.

## Scope

A squad declares exactly one **working language**. Agents then always have two clearly separated languages:

- **Working language**, configured: everything that goes through the `sq` CLI (item titles, bodies, sub-entity text, comments) and all agent-to-agent communication (briefs, handbacks, `@mention` comments).
- **Conversation language**, deduced: the language the human operator writes in, followed message by message. Agents reply to the human in it.

Pieces:

- A `working_language` key in `.squads.toml`. Default: English (`en`). The value is any standard BCP 47 language tag (e.g. `fr`, `en`, `pt-BR`), not free text and not a hand-picked list. An absent key falls back to English silently, with no warning. A malformed value is not an error: it emits a warning and falls back to English (`en`).
- The rule reaches agents through the managed section of every backend (CLAUDE.md and AGENTS.md) and the `squads` skill, rendered from templates so `sq sync` regenerates it. The tag is resolved to the language's display name and that name is rendered into the text.
- Babel is the dependency. It is imported when the service starts, and `working_language` is validated there on every command, parsing the tag with `Locale.parse(tag, sep='-')` and resolving its display name. The startup import is accepted because the future `locale` setting needs Babel at startup on every command anyway.
- `sq init` and adopt write the key (default English) so the setting is visible; an existing squad without the key behaves as English.
- Rule wording, stated once and identically across backends: sq content and agent-to-agent communication are in the working language; replies to the human are in the language the human writes in; there is always exactly one of each.

## Out of scope

- Localizing the CLI itself (messages, help, errors). Its display language will be a separate setting, likely `locale`. This feature neither uses nor reserves-by-implementation the keys `language` or `locale`.
- Translating existing items or enforcing the language on content (no language detection or validation in `sq check`).
- Per-item or per-role language overrides.

## Acceptance criteria

- `.squads.toml` accepts `working_language` as any standard BCP 47 tag; an absent key falls back to English (`en`) with no warning; a malformed value emits a warning and falls back to English, never an error.
- `working_language` is validated at service start, on every command.
- `language` and `locale` are not read, written or accepted by this feature.
- After `sq sync`, the managed section of CLAUDE.md and AGENTS.md and the `squads` skill state the configured working language and the human-conversation rule; changing the key and syncing updates all of them.
- A fresh `sq init` and an adopt produce the key and the rendered rule; an existing squad without the key renders English.
- The rule text is unambiguous: one configured working language, one deduced conversation language, which applies to what.
- The key is documented for adopters.
- Service-level and CLI tests cover default, valid tags (`fr`, `pt-BR`), an absent key (English, no warning) and a malformed value (warning plus English fallback), and rendering in each backend.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1097 add-story "As a <role>, I want … so that …"`; track with `sq feature 1097 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Configure working_language in .squads.toml

<!-- sq:story:US1:body -->
As an adopter, I set `working_language` in `.squads.toml` to any standard BCP 47 language tag (e.g. `fr`, `en`, `pt-BR`). The value is validated when the service starts, on every command; an absent key falls back to English (`en`) silently; a malformed value emits a warning and falls back to English, never an error. The keys `language` and `locale` are left untouched.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Render the language rule in every backend and the squads skill

<!-- sq:story:US2:body -->
As an agent, the managed section of CLAUDE.md and AGENTS.md and the `squads` skill tell me the language name resolved from the configured tag (via Babel, `Locale.parse(tag, sep='-')`) and the human-conversation rule, rendered from templates so `sq sync` regenerates them. Changing the key and syncing updates all of them.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Write working_language on init and adopt

<!-- sq:story:US3:body -->
As an adopter, `sq init` and adopt write the `working_language` key (default English, `en`) so the setting is visible, and an existing squad without the key falls back to English silently, with no warning.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Document working_language for adopters

<!-- sq:story:US4:body -->
As an adopter, the docs explain `working_language`, the two-language model (configured working language, deduced conversation language), and that CLI localization is a separate later setting.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T08:48:56Z] `op-pierre` Pierre Chat:
  - Everything that goes through sq, and all communication between agents, is in one configured working language; the agent talks to the human in the language the human writes in. Adopters must be able to do the same. Name: `working_language`, because `language` is reserved for the CLI's own localization later.
- [2026-10-24T08:55:35Z] `op-pierre` Pierre Chat:
  - Goes in 0.17. Every standard language code is accepted as the working_language value (the standard tag set, not a hand-picked list).
- [2026-10-24T09:00:37Z] `op-pierre` Pierre Chat:
  - For now babel is needed only to render the working language's name into the managed CLAUDE.md section (and its siblings), so the agents read which language the team works in. No babel import on any other command path.
- [2026-10-24T09:03:22Z] `op-pierre` Pierre Chat:
  - Supersedes my earlier babel scoping: import babel when the service starts and validate working_language there. A malformed or absent value emits a warning and falls back to English; it is not an error. The startup import is accepted because the future locale setting will need babel at startup on every command anyway.
- [2026-10-24T09:05:27Z] `op-pierre` Pierre Chat:
  - Absent working_language: English, silently (a legitimate default). Malformed value: warning, then English.
- [2026-10-24T09:12:29Z] `tech-lead` Olivia Lead:
  - @product-owner US3's last clause says an existing squad without `working_language` falls back to English "with a warning"; op-pierre's ruling 594b2d8 and the acceptance criteria say silently. TASK-1098 plans silent; please correct US3's text.
- [2026-10-24T09:13:47Z] `product-owner` Nina Product:
  - Corrected: US3 now says an existing squad without the key falls back to English silently, with no warning, in line with ruling 594b2d8.
- [2026-10-24T19:02:02Z] `manager` Catherine Manager:
  - Done: TASK-1098 delivered all four stories; review REV-1118 Approved.
<!-- sq:discussion:end -->

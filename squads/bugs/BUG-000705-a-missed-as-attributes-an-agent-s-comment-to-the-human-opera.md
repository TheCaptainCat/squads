---
id: BUG-705
sequence_id: 705
type: bug
title: A missed --as attributes an agent's comment to the human operator
status: Verified
author: manager
priority: high
description: comment defaults to the operator's voice, so provenance silently inverts
created_at: '2026-07-30T12:31:12Z'
updated_at: '2026-07-30T14:07:00Z'
---
<!-- sq:body -->
`sq <type> <n> comment` defaults `--as` to `operator`. An agent that omits the flag has its words recorded in the human's voice, and because the discussion is append-only the only remedy is a second comment correcting the first — the false attribution stays in the record permanently.

This happened three times in one session: twice by the manager (a scope correction and a milestone ruling, both later corrected in place) and once by a developer recording a fix. The discussion is the team's shared memory and later agents read it as decided-by-the-operator, so a misattributed line does not merely look untidy — it manufactures an operator decision that was never made, and a future agent will act on it.

Directions worth weighing, not decided here: require `--as` explicitly and drop the default; resolve the default from the invoking agent's identity where the backend can supply it; or keep the default but render an unattributed comment distinctly from a genuine operator comment so the ambiguity is visible in the record.

The same default applies to `sq board post --as`, so a board notice can acquire operator authority the same way.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-30T12:40:05Z] Pierre Chat:
  - 0.13.
- [2026-07-30T13:07:04Z] Pierre Chat:
  - --as becomes required. A default author is not a good idea: attribution is only knowable at the moment the command is typed, and a default silently invents provenance. This matches sq create, which already requires --author.
- [2026-07-30T13:11:25Z] Operator:
  - test
- [2026-07-30T13:31:53Z] Elias Python:
  - Fixed: --as is now a required option at the three sites (item comment, sub-entity comment, board post) — no default, no fallback (not current_actor(), not "system", not config's default_role). Missing --as fails with a clean, terse message ("--as is required: the actor's slug") rather than Typer's bare usage line.
  - Audited beyond the three named sites: sq import's --as also silently fell back to the squad's configured default_role when neither the file nor an event supplied one — removed that fallback too (an event with no actor anywhere in its chain is now a validation issue naming the missing actor, same as any other bad line). sq create's --author was already required; no other authorship-recording verb found.
  - The earlier '- test' discussion line above (attributed to Operator) is an artifact from demonstrating the live pre-fix defect on this very bug, not a real record — noting it here since discussion is append-only.
- [2026-07-30T13:56:22Z] Elias Python:
  - Second instance fixed: _services/_base.py's _create_model() no longer falls back to config.default_role when author is omitted (Service.create()'s library seam — reachable by the bulk importer, a future MCP connector/server, or any non-CLI caller, none of which have a --author flag to forget). Kept author: str | None = None (keyword-with-default) rather than making it syntactically required — hundreds of existing service-level test call sites pass no author and don't care about attribution for what they're testing; making it hard-required would turn pyright red across the whole test tree rather than the same runtime failure. Missing/empty author now raises SquadsError('author is required: the actor's slug').
  - Caller audit: _services/_roster.py's four self-create calls (activate_role, add_dev, add_skill, add_operator) already pass author=<own slug> explicitly (a roster entry authors itself — the honest author, since these are the entity's own bootstrap, not a human/agent act on someone else's behalf). _services/_maintenance.py doesn't call create()/_create_model() at all — it constructs Item(...) directly with author=slug already explicit. The import engine's two create dispatch points (_sim_create, _apply_one) already pass author=ev.actor, which BUG-705's first fix made non-optional in the parse chain. No caller needed an invented author.
  - Also removed SquadsConfig.default_role entirely per the operator's follow-up ruling: verified no reader remained anywhere (src/, clients/, templates) beyond the fallback just deleted and to_toml()'s own serialization; verified extra='ignore' means an existing .squads.toml with the stale key (this repo's own included) still loads clean, no migration/schema bump; sq init/adopt no longer write the key. The CLAUDE.md 'no agent named -> default to X' text and the Claude backend's default-role pickup are unaffected — sourced from the roster item's is_default flag, never this field.
  - Falsified both changes: restored the config-default fallback (config.default_role literally gone, so had to restore the field too for a faithful test) and watched the new create-without-author test go red (DID NOT RAISE SquadsError); removed the restoration and watched it go green. Real output in the return to the coordinator.
- [2026-07-30T14:06:31Z] Mara Tester:
  - Verified against a fresh scratch squad (never this repo's data): item comment / sub-entity comment / board post all refuse cleanly without --as (exit 1, 'error: --as is required: the actor's slug'); a role slug and 'op-<slug>' both land the right author name; an unregistered slug is still rejected ('unknown slug ...; valid slugs: ...').
- [2026-07-30T14:06:39Z] Mara Tester:
  - Bulk import: inline-actor and inherited-actor events applied correctly; an actorless event with no --as fails validation naming the missing actor ('no actor: missing '\''as'\''') with nothing written — verified identical in --dry-run and a real run. Service seam: Service.create('task', ..., author=None) raises SquadsError('author is required: the actor'\''s slug') with no item created (sequence counter unchanged).
- [2026-07-30T14:06:41Z] Mara Tester:
  - Config: fresh sq init writes no default_role; a hand-edited .squads.toml with a stale default_role key still loads (extra='ignore') and --as is still enforced (no resurrected fallback). Generated surfaces (CLAUDE.md, AGENTS.md, sq-memory + all sq-<type> skills in a freshly-initialised squad) all show comment/board post examples with --as already included — nothing teaches the old defaulted form.
- [2026-07-30T14:06:48Z] Mara Tester:
  - Two named suspicions: (1) other attribution-writing paths — _actor.current_actor() still defaults to 'system' and feeds the reflog (migrate/repair/sync ops, plus _index/_store.py's generic txn logger) when no --as/--author set the ambient actor; this is a separate, pre-existing, self-documented ('best-effort, untrusted, observability-only') machine-tag, never a human/agent impersonation, and CLI update --author stays an explicit opt-in re-authorship, not a fallback — not a gap in BUG-705's sense, but worth knowing the reflog still has an ambient default. (2) sq import --dry-run vs a real run on an actorless event: identical failure, same message, same line number, nothing written either way — consistent.
- [2026-07-30T14:06:50Z] Mara Tester:
  - All acceptance points hold. Moving to Verified.
<!-- sq:discussion:end -->

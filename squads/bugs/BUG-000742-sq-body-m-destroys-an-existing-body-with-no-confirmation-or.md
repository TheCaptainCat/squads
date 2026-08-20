---
id: BUG-742
sequence_id: 742
type: bug
title: sq body -m destroys an existing body with no confirmation or dry-run
status: Verified
author: qa
description: 'A full-replace verb with no guard: probing it cost 66 lines of a committed
  skill body, recoverable only because it was committed'
created_at: '2026-08-06T21:36:19Z'
updated_at: '2026-08-15T19:55:22Z'
---
<!-- sq:body -->
Driven, and it cost real content today. A tech-writer ran `sq skill 508 body -m "probe"` to test whether the verb was permitted on a custom skill. It was — and `body` REPLACES, so that single command wiped all 66 lines of the release runbook. It was recoverable only because the file happened to be committed; on an uncommitted body the content is simply gone.

The hazard is the combination, not the replace semantics on their own:

- the verb is destructive by default with no `--force` and no confirmation prompt;
- there is no dry-run, so there is no safe way to ask "would this be permitted here?" other than performing it;
- it succeeds silently on a non-empty body, so nothing distinguishes "set a body that was empty" from "discarded 66 lines";
- `--append` exists, which means the non-destructive intent is already expressible and simply is not the default for an occupied body.

This sits directly against invariant 3, which the project states as marker-safe edits only and never rewrite an agent-authored body. The marker regions are respected; the prose inside one is not.

Worth deciding rather than assuming: whether the fix is a confirmation on a non-empty body, a `--force` requirement, printing what is about to be discarded, or a dry-run — and whether the same exposure exists on the sub-entity body verb and anywhere else a `-m` sets rather than appends. The reporter has already recorded the workaround as role memory (read the body first, or use `--append`); a workaround an agent has to remember is not the fix.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-06T21:36:44Z] Catherine Manager:
  - Reported by the tech-writer against himself, unprompted, immediately after recovering. Filing it because the lesson generalises past one agent: every agent on this project writes bodies through this verb, and the only thing that saved 66 lines today was that the file happened to be committed.
- [2026-08-15T14:38:22Z] Elias Python:
  - Recommendation, then built: refuse the replace, do not prompt for it. Setting a body over content that has already been written raises, names the line count, quotes the opening lines, and writes nothing; --append is unchanged and --force performs the replace deliberately.
  - Why not a confirmation. Agents are the primary caller and cannot answer one. A prompt either aborts every non-interactive body write or grows a skip flag that gets passed reflexively on every invocation, which is strictly worse than a flag that only appears on the destructive path. The failure I am choosing is: a caller who genuinely means to replace has to say so once, and sees what it costs first.
  - Why not a dry-run. A dry-run only helps someone who thought to use it, and the reporter already made the point that a workaround an agent has to remember is not the fix. With refuse-by-default the plain command IS the dry run — the exact probe that cost 66 lines now answers "is this permitted here?" without performing the destruction.
  - Precedent followed: sq override scaffold --force ("Overwrite an existing override") is the same occupied-destination shape, and within the item group --force already uniformly means "proceed past the guard you just hit" (status, remove). Not a new vocabulary word.
  - The hard part was not the guard, it was "occupied". A freshly created item body is NOT empty — it holds the type template rendered scaffold (## Description / _TODO: ...), and a sub-entity holds its placeholder line. An emptiness test would have refused the FIRST write on every item, i.e. broken every agent. So authored means "differs from what a fresh item of this type would carry", derived by re-rendering the item type own template through the same squad-aware loader (ServiceCore.pristine_body) rather than pattern-matched — the scaffold differs per type, interpolates, and an adopter can replace it via .overrides/templates/. Unreproducible render is treated as authored: refusing a first write is recoverable, discarding a body is not.
  - Every door, as asked, not one: sq <type> <n> body, sq <type> <n> <kind> <k> body, sq skill <addr> body, and the bulk importer body / sub-body events, which take a force field of their own so a replayed import cannot silently erase prose in a squad that already has it (the apply is one transaction, so the refusal aborts rather than half-applies). --append needs no guard anywhere, it destroys nothing. Audited for other set-not-append prose doors: comments are append-only by construction, role and system-skill bodies are generated and already refused, board and memory have no set-over-prose verb.
  - Secondary: a forced replace now records {"replaced_lines": N} in its reflog delta, so sq reflog --op body distinguishes a body that was written from one that was overwritten. Nothing else could tell those apart after the fact.
  - Tests: tests/service/test_replacing_an_authored_body_is_refused.py (28, table-driven — every bundled item type scaffold, the custom-skill scaffold, all three sub-entity kinds, a create-time body, plus append/force/message/reflog) and CLI smoke across all three doors. Falsified twice: swapping the derived rule for the naive emptiness rule reddened 20 (including every first-write case, which is the shape that matters), and removing the sub-entity guard reddened its 3. Both reverted by exact reverse substitution.
  - Dogfooded: replacing this repo BUG-731 body hit the refusal first, then went through with --force. Adopter-visible — @tech-writer, CHANGELOG entry is in under 0.13.0 Fixed and docs/roles.md line 98 and docs/workflow.md line 235 both describe body without mentioning the guard.
- [2026-08-15T19:55:22Z] Catherine Manager:
  - Verified by driving all three paths. First write over the template scaffold exits 0. Second write refuses at exit 1, names the line count, quotes the content, offers --append and --force, and says nothing was written -- md5 of the file is byte-identical before and after the refusal, so "safe to run as a probe" is literally true. --force replaces at exit 0.
<!-- sq:discussion:end -->

---
id: REV-633
sequence_id: 633
type: review
title: FEAT-574 docs accuracy + drift guard
status: Approved
author: reviewer
refs:
- FEAT-574
subentities:
- local_id: F1
  title: Drift guard does not validate options/flags on leaf commands
  status: Verified
  severity: medium
created_at: '2026-07-23T09:35:33Z'
updated_at: '2026-07-23T09:50:14Z'
---
<!-- sq:body -->
Independent review of FEAT-574 (TASK-628/629/630/631): CLI-verb + version drift corrections across 12 docs/*.md, plus a drift guard that walks every documented sq invocation against the live Typer command tree.

Scope: uncommitted docs diff + the new drift-guard test. Full suite left to the main loop.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 633 add-finding "…" --severity medium`; track with `sq review 633 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | Drift guard does not validate options/flags on leaf commands |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Drift guard does not validate options/flags on leaf commands

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The resolver walks the subcommand PATH token-by-token but stops validating once it reaches a leaf command: remaining tokens (options AND positionals) are treated as the leaf's own args and never inspected. So flag-level and positional-arg drift silently PASS.

Verified against the live tree: 'sq create feature X --status Draft', 'sq role list --available', and 'sq dev add python' (old positional form) all RESOLVE (return a path, not None) — i.e. if any of these drifted forms were reintroduced into the docs, the guard would not catch them. Two of the three original REV-565 field-report items (--available, and the positional dev add) are exactly this flag/positional class.

The guard's docstring overclaims: 'a doc can never silently cite a verb/FLAG that no longer exists' — only the verb PATH (and pre-leaf global/group options) is actually enforced. The primary drift class from the field report (verb rename / address-before-verb word order, e.g. 'story add' -> 'add-story', 'role show architect') IS caught, and the anchor test proves non-vacuity, so this is a scope/claim-accuracy gap, not a broken guard.

Suggested fix (small, helper already exists): after reaching a leaf, validate each remaining '-'-prefixed token via _own_option_arity(leaf, tok) and fail on an unknown option; leave bare positionals alone (a title/value is legitimately opaque). Minimum acceptable: soften the docstring from 'verb/flag' to 'verb' and note the leaf-option limitation so a maintainer doesn't over-trust it to catch --status/--available reappearing.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T09:36:09Z] Paul Reviewer:
  - RECOMMENDED VERDICT: Approve-with-nits. The doc corrections are correct and the guard is sound for its core purpose; F1 is a Medium follow-up, not a blocker.
  - Lead #1 (corrections correct?): YES — independently verified against the live CLI. role catalog + role list(roster); address-before-verb 'sq role <addr> show|regen|rm' and 'sq operator <addr> rm'; 'dev add --tech <x>' (required option, not positional); 'sq create feature' has --author required and NO --status; 'override diff|update [NAME]' single-or-omitted; the backends.md AgentBackend ABC matches _base.py exactly (async ensure_scaffold/write_managed(+operators)/generate_role_entry/generate_skill_entry/remove_artifacts + sync managed_paths), and the removed claude_dir/version claims on BackendContext are correct; 'sq show <n>' any-type; migrate help/chlog/repad exist; 'sq link' is gone (reflog row correctly dropped). The full resolve test passes across all 12 docs — every documented verb-path resolves.
  - Lead #2 (guard not vacuous?): NOT vacuous for verb-path drift — anchor test asserts real resolutions and I confirmed old forms ('story add', 'role show architect', 'status TASK-2 …') now fail. Extraction rule (sh/bash fences + inline spans, comment/placeholder/elision exemptions) and structural address-skip (Argument / hidden _addr, no digit/slug guessing) are correct; the _ILLUSTRATIVE_CUSTOM_TYPES allowlist (incident/inc/postmortem) is minimal and genuinely unresolvable against the bundled spec — justified, not masking real commands. The one gap is F1: leaf-command options/positionals are never validated, so flag drift is not caught despite the docstring's 'verb/flag' claim.
  - Adopter-facing: clean — no sq-ticket/dev-process/CI/packaging leakage in the added doc prose (the 'BUG-9' in adoption.md is an illustrative placeholder in the ref-add walkthrough, not a real reference); version-drift handled by pointing at the live source / placeholder forms, which is acceptable. No over-reach: prose changes stay within drift correction and don't lose adopter-useful content.
  - Conventions: clean — no ticket IDs / no 'meta' wording / no bare type aliases / no SCHEMA_VERSION bump in the test. GATE GREEN: pyright 0 errors, ruff check + format clean (repo-wide), pytest tests/meta 37 passed (incl. the new guard). Full suite deferred to the main loop.
- [2026-07-23T09:47:39Z] Elias Python:
  - F1 fixed: tests/meta/test_documented_commands_resolve_against_cli.py now validates leaf-level flags/positionals, not just the verb path.
  - _resolve reorders the leaf check ahead of the generic flag-skip branch and adds _leaf_tokens_are_declared: every remaining -/--token must be one of the leaf's own declared options (_own_option_arity), and a bare token is only legitimate if the leaf declares a positional Argument at all -- so sq role list --available, sq create feature X --status Draft, and sq dev add python (all reproduced from the review) now fail to resolve.
  - Two follow-on fixes the stricter check needed to avoid new false positives: shell metacharacters (|, ||, &&, ;, >, <) end leaf-token validation instead of being read as a bogus positional (sq check || exit 1, a piped sq list --json | jq ...); a bracket-wrapped optional flag ([--purge]) is unwrapped and checked the same as a bare one (docs/roles.md's existing role/operator rm examples).
  - Also had to fix a regression the leaf-check surfaced in the address-skip logic itself: the auto-consume-one-token-as-address step now only fires when the freshly-matched child is itself a group (hasattr 'commands'), not any command with a positional -- previously it wrongly ate a leaf's own title arg (sq create feature Login ... was resolving as 'create feature <n>' instead of 'create feature X' with X validated as an ordinary positional).
  - Two small, commented exemptions the extended check needed: _ILLUSTRATIVE_CUSTOM_FLAGS (--impact/--min-impact, the same hypothetical custom-collection worked example _ILLUSTRATIVE_CUSTOM_TYPES already covers) and a one-entry _ALLOWLISTED_HISTORICAL_CITATIONS for stability.md's 'sq role list --available is gone' -- citing removed syntax for contrast, not a live example. No doc content changes were needed this round; every other flag/positional surfaced by the stricter check was one of these two classes, not real drift.
  - New anchor tests: a bogus leaf flag and an unexpected positional on a flag-only leaf both fail to resolve (proves non-vacuity for flags, per the finding's ask); a real-flags/positionals sanity test guards against over-firing. Docstring updated to describe what's now actually checked.
  - Gate: pyright/ruff check/ruff format clean repo-wide; tests/meta 40 passed (incl. the 3 new anchors); sq check clean.
- [2026-07-23T09:50:12Z] Catherine Manager:
  - Manager verification: guard now validates leaf options/positionals (via _own_option_arity) — confirmed it catches --available, create --status, and positional dev add; 2 non-vacuity anchor tests + 1 anti-over-firing test; the two new exemptions (_ILLUSTRATIVE_CUSTOM_FLAGS = the hypothetical custom-collection example, _ALLOWLISTED_HISTORICAL_CITATIONS = stability.md's citation of the removed --available) are minimal and justified. Lead #1 (corrections match live CLI) confirmed. Full suite green. Approving.
<!-- sq:discussion:end -->

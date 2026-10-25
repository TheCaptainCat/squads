---
id: REV-1130
sequence_id: 1130
type: review
title: 'Review of TASK-1106: capability hand-offs, compact list, role scaffold'
status: Approved
author: reviewer
refs:
- TASK-1106
subentities:
- local_id: F1
  title: Templated developers get a role-show hint to a missing file and an empty
    role scaffold
  status: Verified
  severity: medium
- local_id: F2
  title: Unheld capability tokens in override-declared commands are never reported
  status: Verified
  severity: low
- local_id: F3
  title: Role scaffold CLI message still says to add fields instead of uncommenting
    them
  status: Verified
  severity: low
- local_id: F4
  title: Scaffold placeholder teal for an unset color misstates the bundled value
  status: Verified
  severity: info
- local_id: F5
  title: Duplicate test coverage across layers and hand-copied pinned capabilities
  status: Verified
  severity: low
created_at: '2026-10-24T23:13:14Z'
updated_at: '2026-10-24T23:41:34Z'
---
<!-- sq:body -->
## Scope

Commit f88a0abb, TASK-1106, against the task spec and ADR-1121. Covers the `@*<name>` resolver and the bundled hand-off conversion, the unheld-token report, `sq role show` hint, the `sq override scaffold --role` field list, `sq list --compact`, and the tech-writer narration sweep in orchestration-loop step 5.

## What was exercised

I drove the dev build in scratch squads:
- tokens with zero, one and two holders (two templated developers), including a retired holder;
- override capabilities, added with `$(*self)` and removed with `[]`;
- one role holding two capabilities named on one line, and a literal slug next to a token;
- malformed tokens: `@*`, `@*Bad`, `@*plan_x`, `@*-plan`, `@**plan`, the literal prose `@*<name>`, and `x@*plan`;
- unheld tokens in override guides against bundled ones, and in override commands;
- `@*dev` in an override guide, which is not falsely reported;
- `sq list --compact` with `[x]`/`[bold]` and CJK titles at widths 200, 40, 30, 12 and 5, when piped, on an empty result, and with `--json` (exit 2);
- every bundled role's scaffold, each line uncommented alone and then all lines together, all of which loaded back equal to the bundled role;
- loop step 5 with zero, one and two live `edit` holders;
- `role show` on bundled, project and templated-developer roles.

The bundled playbook carries no hardcoded slug mention. I checked that with a grep, after confirming the same grep finds 19 mentions in the parent commit. The targeted tests (60) pass.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1130 add-finding "…" --severity medium`; track with `sq review 1130 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Templated developers get a role-show hint to a missing file and an empty role scaffold

<!-- sq:finding:F1:body -->
A developer added with `sq dev add --tech <t>` is built from the bundled `[dev]` table. It is not in `PREDEFINED`, so both bundled-role checks in this change treat it as project-defined.

- `sq role python-dev show` (`_change_role_hint` in `src/squads/_cli/_role.py`) ends with "To change it: edit `.overrides/roles/python-dev.toml`, then `sq sync`." That file does not exist after `sq dev add`. Seen in a scratch squad: `ls squads/.overrides/roles/` showed only an unrelated override.
- `sq override scaffold --role python-dev` (`scaffold_role` gates on `_BUNDLED_ROLE_SLUGS`, which is `PREDEFINED`) succeeds, but the file it writes holds only the stamp and the "Uncomment a field to override it." header, with no commented fields at all.

So the most common adopter role, a developer, gets a hint that points at nothing and a scaffold whose header promises fields it doesn't have. The spec says the scaffold-hint path applies to a bundled role and the own-file path only to a project-defined role ("no bundled entry"). A templated developer has a bundled entry (the `[dev]` table), so it should take the scaffold hint, and its scaffold should list the templated values (model, color, capabilities and the rest).

Missing test rows: `role show` and `scaffold --role` on a developer added through `sq dev add`.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-24T23:27:35Z] `python-dev` Elias Python:
  - Fixed: a templated developer now takes the scaffold hint (role show) and scaffold_role takes the resolved base, so the file lists the [dev] template fields. CLI rows added for both.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Unheld capability tokens in override-declared commands are never reported

<!-- sq:finding:F2:body -->
ADR-1121 section 2 makes `@*<name>` valid in a type's `commands` as well as in guide text. `unheld_capability_tokens` (`src/squads/_interactions/__init__.py`) reads only guide lines, so an unheld token in commands that the adopter wrote is never reported.

Reproduced: a `.overrides/playbook.toml` with `[types.task] commands = ["$(*self)", "sq task <n> comment -m 'ping @*nope'"]` renders `ping *nope` in sq-task, and neither `sq sync` nor `sq check` says anything. The same token in a guide in that file is reported.

The developer read section 5 ("it fires only for a guide the adopter declared") as excluding commands. I disagree with that reading. The ADR gives one reason for the exemption: a bundled line produces a warning "no adopter can clear". That reason doesn't hold for a commands list the adopter wrote in their own override, which they can edit. A typo there (`@*reveiw`) silently mentions nobody, which is the exact failure the report exists to catch. Provenance is as easy to get as it is for guides: `types.<t>.commands` is present in the raw override mapping, so the lines that come from the override are the non-splat entries.

Fix: report unheld tokens in commands lines the override declares (or record the narrower scope in an amendment to ADR-1121). Add one service row.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-24T23:27:37Z] `python-dev` Elias Python:
  - Fixed: unheld tokens in override-declared commands lines are reported like guides (playbook_override_command_lines). Service row added; message now says "playbook text".
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Role scaffold CLI message still says to add fields instead of uncommenting them

<!-- sq:finding:F3:body -->
After writing the file, `sq override scaffold --role <slug>` still prints "Edit <path> to add fields to override (e.g. full_name, model), then verify with sq override diff --role <slug>." (`src/squads/_cli/_override.py:123`). For a bundled role the file now holds every field commented out, and its own header says "Uncomment a field to override it.", so the CLI message points the adopter at the wrong action. Make the message match the file: uncomment and edit a field for a bundled role, add fields for a role with nothing to scaffold. Seen in a scratch squad. The tech writer found this first.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-24T23:27:38Z] `python-dev` Elias Python:
  - Fixed: the scaffold message says to uncomment the fields for a role with a base, and to add fields otherwise. CLI row added.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Scaffold placeholder teal for an unset color misstates the bundled value

<!-- sq:finding:F4:body -->
`_ROLE_UNSET_FIELD_PLACEHOLDERS` (`src/squads/_overrides/_service.py`) writes an unset bundled `color` as `"teal"` and an unset `model` as `"inherit"`. Every bundled role sets both, so neither branch is reachable today (checked: all eight roles in `roles.toml` carry `model` and `color`). If one is ever reached, the scaffold contradicts its own contract. The line claims to show the bundled value, but uncommenting `color = "teal"` gives the role a colour it did not have. The test for this row (`test_a_field_the_bundled_role_leaves_unset_is_written_so_it_still_loads`) asserts only `color is not None`, so it pins the contradiction instead of the spec ("rendered so it still loads", which the task also requires to equal the bundled role).

Suggested fix: leave an unset field out, or write it as a comment that says it is unset (for example `# color = "<unset: any Claude Code colour>"`), and drop the placeholder table. That also removes the mutable-state allowlist entry this change added. If a placeholder stays, `model = "inherit"` is the only one that equals unset.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-24T23:27:39Z] `python-dev` Elias Python:
  - Fixed: an unset field gets no line; placeholder table and its allowlist entry removed. The test now asserts the omitted lines.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Duplicate test coverage across layers and hand-copied pinned capabilities

<!-- sq:finding:F5:body -->
These rows break the one-table-per-behaviour, one-layer rule set in the task's Tests section:

- `tests/unit/test_a_capability_token_renders_the_live_holders_of_the_capability.py`: `test_an_unheld_token_keeps_its_line_and_mentions_nobody` repeats the `no-live-holder` table row (same roster, same shape). Fold the `extract_mentions(...) == set()` assertion into the table and delete the test.
- `tests/service/test_an_unheld_capability_token_is_reported_for_override_guides_only.py`: three of its four tests also assert rendered skill text (`ask *audit to look`, `*review`/`*verify`), which the unit resolver table already owns. The one service-level rendering assertion that adds coverage is the held case (`@auditor`), because it proves an override-declared capability reaches the production roster. Keep that one and drop the other rendering assertions.
- `tests/unit/test_item_skill_dev_gate.py` and `tests/unit/test_managed_section_and_cheatsheet_goldens.py` each hand-copy the bundled capabilities into a pinned roster. A later change to `roles.toml` capabilities leaves the pins silently stale. Derive the capabilities from `PREDEFINED`, as the CLI test in this change already does.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-24T23:27:40Z] `python-dev` Elias Python:
  - Fixed: duplicate unit test folded into the table (mentions column), rendering assertions dropped from the service file except the held case, pinned roster capabilities derived from PREDEFINED.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T23:14:17Z] `reviewer` Paul Reviewer:
  - Verdict: ChangesRequested. F1 (medium): a templated developer gets a role-show hint to a missing file and an empty scaffold. F2, F3 and F5 are low, F4 is info. Resolver, bundled conversion, compact list and step 5 behave per spec and ADR-1121.
  - @python-dev please address the findings, then @-mention the review author for re-review.
- [2026-10-24T23:41:14Z] `reviewer` Paul Reviewer:
  - Re-review of 9bed669a: F1-F5 all Verified by re-driving the repros on the dev build. A templated developer now gets the scaffold hint, and its full scaffold loads back unchanged when uncommented. An unheld token in an override command line is reported by sync and check. The scaffold CLI message matches the file. Unset fields are omitted. The test duplication is folded and capabilities are derived from PREDEFINED. Targeted tests pass. Verdict left to the approver.
- [2026-10-24T23:41:34Z] `manager` Catherine Manager:
  - Approved: all five findings Verified by the reviewer at 9bed669a; full suite green (14060 passed).
<!-- sq:discussion:end -->

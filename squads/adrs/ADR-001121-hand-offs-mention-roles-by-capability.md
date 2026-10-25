---
id: ADR-1121
sequence_id: 1121
type: decision
title: Hand-offs mention roles by capability
status: Accepted
author: architect
refs:
- TASK-1106
- REV-1099
description: A handoff names a capability (@*review) and renders as the @-mentions
  of its live holders.
created_at: '2026-10-24T20:03:12Z'
updated_at: '2026-10-25T21:41:28Z'
---
<!-- sq:body -->
## Context

The bundled playbook names its hand-off recipients by slug. Its guide text carries nineteen `@`-mentions: `@tech-lead` seven times, the `@<developer>` placeholder six times, `@reviewer`/`@qa` twice, `@reviewer` on the review guide, `@product-owner` twice and `@tech-writer` once. A slug names one particular role in the bundled catalog, so it fails as soon as an adopter's roster differs from that catalog. A project that gives reviews to a second role, renames a role, or has no `qa` gets hand-offs that reach the wrong inbox or none (REV-1099 F17). Today the only fallback is `live_roster_text`, which rewrites an absent slug to `@<slug>`.

Guide subjects already avoid this problem: a guide addressed to `*<capability>` applies to every live role holding that capability (`addresses()` in `_interactions/_role_guidance.py`). Today only one capability exists: `dev`, which every templated developer gets from the `[dev]` table of `roles.toml`. No bundled role declares one.

The decision has to cover three things: what each hand-off asks for, how a guide line names that ask, and what a line renders as when nobody holds the capability.

## Decision

**1. Bundled capabilities.** There is one capability per distinct ask in the bundled hand-off lines, and only those:

| Capability | Held by | The ask in the bundled lines |
|---|---|---|
| `plan` | `tech-lead` | break an epic or feature down, triage a bug, apply an accepted decision, slot work under a milestone |
| `review` | `reviewer` | review a change |
| `verify` | `qa` | verify against the acceptance criteria |
| `product` | `product-owner` | answer a scope question, own a slipping target |
| `edit` | `tech-writer` | polish a draft |
| `dev` | every developer (`[dev]` table, unchanged) | implement or fix |

The manager and the architect hold none of these, because no bundled line hands off to them. A capability is a name that roles hold. Nothing registers capabilities: one exists because a role declares it.

**2. Syntax.** In any playbook guide text (`enter`, `do`, `handoff`, `watch`) and in a type's `commands`, the token `@*<name>` mentions every live holder of capability `<name>`. `<name>` matches `CAPABILITY_NAME_PATTERN`, the same spelling the `*<name>` guide subject uses. A literal `@<slug>` keeps working exactly as today, including the existing rewrite to the `@<slug>` placeholder when the roster lacks that role. A project that wants a fixed recipient writes the slug. The bundled lines become, for example, "`@*plan` to break it down", "comment a summary of what changed + `@*review`/`@*verify`", and "`@*dev` with the findings", which replaces the `@<developer>` placeholder. The `--assignee <developer>` placeholder is a single-value flag, not a mention, so it stays as it is.

**3. Rendering.** Resolution happens when `sq sync` generates the `sq-<type>` skill, against the live roster. It is the same pass and the same roster that `live_roster_text` and the capability guide headings already use.
- Several holders: each one renders as `@<slug>`, in live-roster order, joined with `/`. For example, `@*dev` renders as `@python-dev/@typescript-dev`. Each token resolves on its own. A role that holds two capabilities named on the same line appears once per token.
- No live holder: the token renders as `*<name>`, with the `@` dropped. The line is kept, so the instruction around the token survives. Nobody is mentioned, because `_MENTION_RE` does not match `*<name>`. `*<name>` is also how generated skills already spell a capability, in the `` `*dev`: … `` guide headings.
- A retired role is not live, so it holds nothing. A guide subject treats it the same way.
- An operator is not a role and holds no capability, so a token never expands to an `op-` slug. To hand off to a person, a project writes the literal `@op-<slug>`.

**4. The item's author stays prose.** A skill is rendered once per item type, but the author differs on every item, so no render-time token can resolve it. A token for the author would promise a substitution that never happens. Where the right recipient is whoever opened the item, the line says so in words. The review's `*dev` hand-off reads: "`@`-mention the review's author (shown on `sq review <n> show`) once all findings are Fixed, for re-review". This is the original F17 fix and it stays. `@*review` would bring the bug back whenever a role other than the reviewer opened the review. The task and bug `*dev` hand-offs use `@*review`/`@*verify`, because there the ask is a role's function, not a return to the item's author. This replaces the author wording TASK-1106 ST4 planned for those two guides.

**5. Customisation and reporting.**
- To give a capability to a project role, declare `capabilities = ["review"]` in that role's `.overrides/roles/<slug>.toml`.
- To change a bundled role, override its `capabilities` list. Either restate the list, or append with `["$(*self)", "verify"]`, the same splat-ref idiom every list field uses.
- Override playbook lines use the same `@*<name>` token.
- A token whose name does not match the pattern is a playbook load error. The loader already reports a malformed `*<name>` subject the same way.
- A well-formed token that no live role holds, whether a typo or a capability whose only holder is retired, is reported once by `sq check` and `sq sync`. The report goes through the same path as `orphaned_playbook_guides`, under the same exemption: it fires only for a guide the adopter declared in `.overrides/playbook.toml`, and names the capability, the type and both remedies (declare it on a live role, or edit the line). An unheld token in the bundled playbook degrades silently to `*<name>`. A minimal roster would otherwise produce warnings that no adopter can clear. There is no separate "unknown capability" class, because there is no capability registry to be unknown to.

**6. Generated output and schema.**
- The `sq-<type>` skills of every type whose guides carry a token regenerate: epic, feature, task, bug, decision, milestone, review and guide.
- The CLAUDE.md and AGENTS.md managed sections render no hand-off lines, so they do not change.
- `sq role <slug> show` lists the new capabilities. The role pointers do not render capabilities.
- Goldens to regenerate: the skill goldens, the role catalog golden, the playbook golden lock (`tests/unit/test_playbook_spec_artifact.py`), the content store and the template manifest. The vocabulary probe in `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` must give its roster the capabilities it expects to see resolved, or assert the `*<name>` form.
- No schema bump. Capabilities are resolved from the catalog and never stored on a role item (`_roles/_catalog.py`), so an existing squad picks up the change on its next `sq sync`, with no migration.

## Consequences

- A bundled hand-off reaches whoever performs the function in this squad. This includes a second reviewer, a renamed role and several developers, and no adopter has to edit the playbook.
- An adopter changes the recipient by declaring a capability on a role. That is one list field in a file they already own. They do not restate a whole `roles` array of the playbook.
- The rule fits in one sentence: `@*x` means every live role that holds `x`, `/`-joined in roster order, or `*x` when none does. Literal slugs are unchanged.
- The author-addressed review hand-off is the one exception, and it stays prose. Adopters must not expect a token for item-level data.
- One new resolver in the skill-rendering path. Its tests need the boundaries: zero, one and several holders, a retired holder, a malformed token, and an override-authored unheld token against a bundled one.
- Existing adopter overrides that spell `@reviewer` keep rendering as before.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T21:20:49Z] `op-pierre` Pierre Chat:
  - Accepted as written: capability names plan, review, verify, product, edit (plus dev) and the rendering rule.
- [2026-10-25T21:41:28Z] `architect` Robert Architect:
  - Audited 2026-10-25: holds. roles.toml declares plan/review/verify/product/edit, the playbook uses @*<capability> tokens, live_roster_text renders them, and unheld override tokens are reported by sq check and sq sync.
<!-- sq:discussion:end -->

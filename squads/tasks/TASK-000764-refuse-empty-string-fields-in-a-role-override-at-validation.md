---
id: TASK-764
sequence_id: 764
type: task
title: Refuse empty-string fields in a role override at validation
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-760:fixes
description: One refusal at the merge/validate choke point instead of hardening four
  render sites
created_at: '2026-08-21T19:36:54Z'
updated_at: '2026-08-22T09:26:27Z'
---
<!-- sq:body -->
A role override declaring empty strings is accepted, and every generated surface renders the break.
Driven on a fresh squad with a `python-dev` role added and `.overrides/roles/python-dev.toml`
declaring `full_name = ""`, `title = ""`, `mission = ""` — `sq sync` exits 0 and all four surfaces
ship it:

- `sq role python-dev show` — a card with an empty name line and an empty `title:` row;
  `--json` emits `"full_name": "", "title": "", "mission": ""`.
- `CLAUDE.md` roster line — ``- **** —  (`python-dev`)``.
- `AGENTS.md` roster line — the same, plus a role-section heading rendered as ``###  (`python-dev`)``.
- `.claude/agents/python-dev.md` — the worst one, because it is prose an agent reads as its own
  identity: `"You are ****, the  on this project."`

`sq check` is silent. Removing the override and re-running `sq sync` restores the real values, so
nothing is lost durably — this is a validation gap, not a corruption one.

## Refuse at validation, not at render

An empty string is not a usable "inherit the base value" signal: **omitting the key already means
that.** Hardening the renderers would mean defending four-plus independent call sites (the human and
`--json` role-show renderers, both backends' roster-line templates, and the Claude Code pointer
template) against a value with no legitimate reason to exist, and a fifth surface added later would
start the gap over. Refusing once, where the override is merged and validated, closes it for every
current and future render site and fails the adopter at the point they made the mistake.

## Which layer owns the refusal, and why

`_apply_override` in `src/squads/_roles/_resolver.py` is the single choke point: every path that
materialises a role override — `sq sync`'s catalog refresh, `sq role <slug> show`, `sq dev add`, the
dev-base paths, and `sq check`'s override reporter — reaches the merged mapping there and validates
it as a `RoleSpec` before anything renders. It already carries `origin` (the override file's path)
into every violation it raises, and already performs one post-validation vocabulary check of exactly
this shape (the `model` whitelist), so the pattern to follow is in the function.

Two implementations are defensible and the dev picks one and states the reason on the item:

- **Declarative** — length constraints on `RoleSpec`'s string fields in `src/squads/_roles/_models.py`,
  so the shape itself refuses and every consumer of the model inherits it. Note that `RoleSpec` also
  validates the bundled catalog: confirm the bundled roles and the scaffolded override examples still
  load (there is a meta test covering the scaffolded examples), and that the resulting message still
  names the file and the field once wrapped by `_apply_override`.
- **Explicit** — a check alongside the existing `model` whitelist in `_apply_override`, which gives
  full control of the message at the cost of living beside the model rather than in it.

Either way the refusal must name **the file and the field**, in the style of the refusals already
raised there.

## Whitespace-only strings

`title = "   "` renders identically broken. State explicitly which treatment you implemented and
test it — do not leave it implicit. The expectation is that a whitespace-only string is refused the
same way, on the same reasoning (it is not an inherit signal and it renders as a hole), but say so
in the handoff rather than letting a reader infer it from the code.

## `sq check` gets the report for free — verify, do not rebuild

`_check_role_override_resolves` in `src/squads/_overrides/_service.py` already resolves **every**
role override file through `resolve_role_with_base` — the same seam `sq sync` and `sq role <slug>
show` use — specifically so `sq check` reports whatever those consumers refuse, and deliberately
without re-implementing any validation. Once the resolver refuses the empty string, that reporter
should surface it with no new code. **Verify it does and cover it with a test; do not add a second,
parallel check.** If it turns out not to surface, say why on the item before changing that function.

## Scope

- Every field on the role override document that accepts a string: `full_name`, `title`,
  `description`, `mission`, and the optional `model`/`color`. The three that were driven are not the
  whole gap — all of them are plain unconstrained `str`, so the mechanism is the same for each.
- State whether **list entries** are covered too (an empty string inside `responsibilities` or
  `agreements`), and either cover them or say why they differ.
- Report, without fixing, whether the same unconstrained-`str` pattern exists on the other override
  document shapes. That is a separate item if it does — note it in your handoff comment rather than
  widening this one.

## Acceptance criteria

- The driven reproduction is refused: `sq sync` exits non-zero on the empty-string override, and the
  message names the override file and the offending field.
- The refusal reaches every consumer of a role override: `sq sync`, `sq role <slug> show` (human and
  `--json`), and `sq dev add`.
- **`sq check` reports it** — it is silent today. Covered by a test that a squad carrying an
  empty-string role override does not pass `sq check`.
- **A test per field that accepts a string**, not one test standing in for the family — table-driven
  over the fields is the right shape here.
- Whitespace-only handling is implemented deliberately, tested, and stated in the handoff.
- **Omitting a key still inherits.** A partial override that simply omits `title` keeps the base
  value, exactly as today. The refusal must not turn a legal partial override into an error — this is
  the regression the change risks, so it gets its own test.
- A valid override with real values still applies unchanged, and the bundled role catalog still loads.
- No renderer or template is hardened as part of this: the four broken surfaces are proved fixed by
  the refusal upstream, not by defensive rendering downstream.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.

## Handoff

**Do not edit `CHANGELOG.md`.** Several items in this batch run concurrently and a shared file would
have them racing. Put your adopter-facing changelog entry text in your handoff comment on this item
and the tech lead applies it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 764 add-subtask "<title>"`; track with `sq task 764 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T19:37:35Z] Olivia Lead:
  - Named the refusal layer from source: _apply_override in _roles/_resolver.py is the single choke point every consumer reaches (sync, role show, dev add, dev-base paths, check reporter); it already carries origin into refusals and already does one post-validate vocabulary check (the model whitelist), so the pattern is in the function. Body offers the declarative RoleSpec-constraint vs explicit-check fork and requires the dev to state the choice.
  - One correction to the ask: sq check needs no new reporter. _check_role_override_resolves in _overrides/_service.py already resolves EVERY role override file through resolve_role_with_base precisely so check reports whatever the consumers refuse. So the refusal surfaces there for free — body says verify and test it, and explicitly do NOT add a second parallel check.
- [2026-08-21T19:48:17Z] Elias Python:
  - Fixed declaratively, on RoleSpec itself (src/squads/_roles/_models.py), not as an explicit check beside the model whitelist in _apply_override. Reasoning: emptiness is a shape constraint the type system can express (unlike the model whitelist, a closed-vocabulary lookup pydantic can't express), so it belongs where every other shape rule already lives — the same place a wrong type or an unknown key is already caught — keeping _apply_override's own code limited to what genuinely can't be declared. A new model_validator(mode="after") (_no_blank_strings) checks full_name/title/description/mission (required, never None) and model/color (optional — None still means 'not set' and is untouched; only a declared blank string refuses) after strip(), plus each entry of responsibilities/agreements. One raise names every blank field found at once (not just the first), e.g. 'field(s) blank or whitespace-only (omit the key instead to inherit): full_name, title, mission' — matching the existing 'missing required fields: ...' phrasing. _apply_override's existing except Exception wrapper adds the file path (origin), so the final message names both.
  - Whitespace-only: treated identically to empty, deliberately, on the same reasoning the bug names (renders exactly as broken, is exactly as clearly unintentional) — implemented as .strip() before the length check, tested explicitly with a '   ' variant alongside every '' case in the parametrized table (not folded in silently).
  - sq check needed no new code — verified, not rebuilt: _check_role_override_resolves already resolves every override through resolve_role_with_base, so once RoleSpec refuses, check surfaces it for free. Covered by test_check_json_carries_the_blank_field_error (--json, not just the table) with zero changes to _overrides/_service.py.
  - Driven before/after across all four surfaces on a fresh squad (python-dev added, override setting full_name/title/mission to ""): BEFORE (pre-fix): sq sync exit 0; sq role python-dev show renders an empty name line, --json emits full_name:""/title:""/mission:""; CLAUDE.md and AGENTS.md roster lines read '- **** —  (`python-dev`)' (AGENTS.md also a blank ### heading); .claude/agents/python-dev.md reads 'You are ****, the  on this project.'; sq check silent. AFTER (this fix): sq sync exit 1 naming the file and full_name/title/mission; sq role show and --json both exit 1 the same way; sq check exit 3, --json carries the error naming the file; none of the four generated files were ever touched by the refused sync, so all four kept their real prior values (asserted byte-for-byte in test_sync_refuses_naming_the_file_and_every_blank_field). sq dev add on a pre-existing blank override also refuses (SquadsError naming full_name).
  - Scope: covered full_name, title, description, mission, model, color (every plain-str RoleSpec field except slug, which is filename-derived with its own refusal), plus list entries in responsibilities/agreements (an empty bullet is the same defect class, mechanically identical to add, so I covered rather than excluded it). Omitting a key still inherits — regression-tested. Bundled catalog (8 roles) and the scaffolded override examples (existing meta test) still load.
  - Reported, not fixed (separate-item territory per the task body): the same unconstrained-str pattern exists on the other override document shapes — _workflow/_models.py (StatusBadgeSpec.label, TypeSpec.plural/folder/placeholder, etc.) and _interactions/_models.py (RoleGuideSpec.overview/lifecycle) all have plain str fields with no blank-value guard. Not driven end-to-end to confirm an actual render break for those, since that's exploration for a new item, not this one.
  - CHANGELOG entry text (for the tech lead to place under Fixed, I did not touch the file): **A role override declaring an empty or whitespace-only value is refused, not rendered.** `full_name = ""`, `title = ""`, `mission = ""` (or any other string field — `description`, `model`, `color`, or an entry inside `responsibilities`/`agreements`) used to pass validation silently and reach every generated surface broken — an empty bold roster line in `CLAUDE.md`/`AGENTS.md`, a blank role-section heading, and a Claude Code agent pointer telling the agent it was "the  on this project" as its own identity. `sq sync` now refuses immediately, naming the override file and every blank field; `sq check` reports the same failure. Omitting a field is unaffected — it still inherits the base value exactly as before; only a field the file itself sets to nothing, or only whitespace, is refused.
  - Gates: pyright 0 errors; ruff check/format clean; tests/meta 172 passed (incl. the scaffolded-override-examples load test); targeted role/override/sync/check modules + 2 new test files, 387 tests, all green; sq check clean on this repo.
  - Commit 472e7b6 on release/0.14, unpushed. Touched only src/squads/_roles/_models.py + tests/ — no _cli/, no _overrides/_service.py changes, no CHANGELOG.md.
- [2026-08-21T19:57:12Z] Elias Python:
  - Fixed the message-quality regression. Chose: don't raise through pydantic for this check at all, rather than catching ValidationError in _apply_override's wrapper and extracting messages. Reasoning: the wrapper-extraction option touches the SAME except Exception block every OTHER pydantic-raised refusal on this seam goes through (e.g. a wrong-type value), so a generic fix there would have silently cleaned those up too — exactly what I was told not to do silently. Moving the blank-check off RoleSpec entirely and into an explicit post-validation check in _apply_override (right beside the existing model-whitelist check, same pattern, same placement) fixes only this one refusal, touches nothing else, and can't flatten or otherwise affect the whitelist message since that code is untouched.
  - src/squads/_roles/_models.py: reverted to its pre-task-764 shape — no model_validator, RoleSpec back to a plain field list. src/squads/_roles/_resolver.py: new _refuse_blank_strings(spec, origin), called in _apply_override right after RoleSpec.model_validate succeeds and right before the model-whitelist check, raising SquadsError directly (never through pydantic) with the same clean shape as the whitelist: 'invalid role override {origin}: field(s) blank or whitespace-only (omit the key instead to inherit): full_name, title, mission'.
  - Before (verbatim, from my own drive): error: invalid role override /…/python-dev.toml: 1 validation error for RoleSpec\n  Value error, field(s) blank or whitespace-only (omit the key instead to inherit): full_name, title, mission [type=value_error, input_value={'slug': 'python-dev', 'f...lse, 'can_spawn': False}, input_type=dict]\n    For further information visit https://errors.pydantic.dev/2.13/v/value_error
  - After (verbatim): error: invalid role override /…/python-dev.toml: field(s) blank or whitespace-only (omit the key instead to inherit): full_name, title, mission — one line, no pydantic class name, no input_value dump, no doc link. Confirmed identical clean shape at sq role show and sq check. Confirmed the sibling model-whitelist message (model 'gpt-9' is not one of [...]) is byte-for-byte unchanged.
  - Sibling leak found and left alone as instructed: a wrong-TYPE value on this same seam (e.g. full_name = 7) still raises the raw pydantic ValidationError text — '1 validation error for RoleSpec', the input_value dump, the pydantic.dev link — because that refusal was never moved off RoleSpec and this task only owned the blank-field case. Pinned with a dedicated test (test_a_wrong_type_refusal_still_leaks_pydantic_internals_not_fixed_here) documenting it as a known, out-of-scope sibling defect rather than fixing it here or leaving it unremarked.
  - New/extended tests assert the full message text, not just exit code: test_the_blank_field_refusal_names_only_the_file_and_the_fields and test_a_single_whitespace_only_field_refusal_is_equally_clean assert == on the exact SquadsError string plus absence of pydantic leak markers; test_the_sibling_model_whitelist_message_is_unchanged pins the untouched sibling; the CLI-level test now asserts the same on sq sync's actual stdout/stderr text, not only its exit code.
  - Gates: pyright 0 errors; ruff check/format clean on my files (scoped — a different, untracked meta test file from another concurrent agent has an unrelated pre-existing lint issue, not touched by me); tests/meta 180 passed; targeted role/override/sync/check modules + my test files, 399 tests, all green; sq check clean on this repo.
  - Commit f65bdf4 on release/0.14, unpushed. Touched only src/squads/_roles/_models.py, src/squads/_roles/_resolver.py, and my two test files — did not touch CHANGELOG.md (read back the entry you applied, it matches what I sent) or src/squads/_cli/.
<!-- sq:discussion:end -->

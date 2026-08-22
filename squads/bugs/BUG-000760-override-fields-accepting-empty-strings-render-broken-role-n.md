---
id: BUG-760
sequence_id: 760
type: bug
title: Override fields accepting empty strings render broken role names
status: Verified
author: qa
refs:
- REV-757
created_at: '2026-08-21T17:52:02Z'
updated_at: '2026-08-21T20:48:12Z'
---
<!-- sq:body -->
Driven end-to-end across every generated surface, on a fresh squad with a `python-dev` role
added.

`.overrides/roles/python-dev.toml` declaring:

    full_name = ""
    title = ""
    mission = ""

`sq sync` exits 0 and every one of the four generated surfaces renders the break:

- `sq role python-dev show` (human) -> a card with an empty name line and an empty `title:`
  row; `sq role python-dev show --json` -> `"full_name": "", "title": "", "mission": ""`.
- `CLAUDE.md` roster line -> `- **** —  (`python-dev`)`.
- `AGENTS.md` roster line (driven with `--backend agents_md` added) -> the identical
  `- **** —  (`python-dev`)`, plus a second broken spot further down the file: a role-section
  heading rendered as `###  (`python-dev`)`.
- The `.claude/agents/python-dev.md` pointer file -> the worst instance, because it is prose
  an agent reads as its own identity, not a table row: `"You are ****, the  on this project."`

`sq check` does not notice — its only output is the unrelated override-stamp warning. Removing
the override file and re-running `sq sync` restores the real values cleanly, so nothing is lost
durably; this is a validation gap, not a corruption one.

All three fields are plain `str` on `RoleDef` with no length constraint, so the same gap almost
certainly extends to every other free-text identity field on the role shape (e.g.
`description`), not just the three driven here — this was not exhaustively re-driven field by
field, since the mechanism (an unconstrained `str`) is the same for all of them.

**Verdict: refuse, at validation, not tolerate at render.** An empty string is not a usable
"inherit the base value" signal — omitting the key already means that, and the finding that
first drove this made the same point. Making every render site defensive would mean hardening
four-plus independent call sites (the human and `--json` role-show renderers, both backends'
roster-line templates, and the Claude Code pointer template) against a value that has no
legitimate reason to be empty in the first place, and a fifth surface added later would start
the gap over again. Refusing the empty string once, where the override is parsed/merged, closes
it for every current and future render site in one place, and fails the adopter loudly at the
point they made the mistake rather than shipping it silently into every generated file. That
also matches the fail-closed posture this project already applies to other override validation
(e.g. `sq workflow lint`).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T19:57:53Z] Catherine Manager:
  - Fix landed in 472e7b6 with the message cleanup in f65bdf4, on release/0.14 (TASK-764). Verified independently: a blank or whitespace-only field is refused naming the file and every offending field, zero pydantic leak markers in the output, and the sibling model-whitelist refusal is byte-for-byte unchanged. None of the four generated surfaces is touched by the refused sync, and omitting a field still inherits.
  - One residual pinned rather than fixed, correctly: a wrong-TYPE value on the same seam (full_name = 7) still surfaces raw pydantic ValidationError text. The dev left it alone because this bug owned the blank-field case only, and chose the narrow fix over catching ValidationError in the shared wrapper, which would have silently reshaped every pydantic refusal on that seam. Worth its own item if we want the whole seam clean.
- [2026-08-21T20:48:11Z] Mara Tester:
  - Drove the bug's own reproduction plus every extra check asked for, on a fresh throwaway squad with a python-dev role added. full_name/title="" + mission="   " (whitespace-only): sq sync exits 1 naming the file and all three fields, zero pydantic leak markers (no 'validation error for RoleSpec', no input_value dump, no errors.pydantic.dev link). Sibling model-whitelist message (model 'gpt-9' is not one of [...]) is byte-for-byte unchanged.
  - No generated file touched by the refused sync: md5sum of CLAUDE.md, .claude/agents/python-dev.md and the role's own frontmatter file identical before and after the refused sync. Omitting a field (title-only override) still inherits full_name/mission cleanly.
  - Optional vs required, None vs '': model/color omitted resolve to the inherited value (model: sonnet) -- None is a real inherit signal; model="" and color="" are each refused individually, so a declared blank is never confused with an absent key.
  - List entries: an empty string inside responsibilities (['Implement tasks','','Write tests']) and inside agreements (['   ']) are each refused by field name, same message shape.
  - sq check reports it (exit 3, --json carries the message naming the file); sq role show and --json show refuse identically; a valid override still applies and the bundled 8-role catalog still loads.
<!-- sq:discussion:end -->

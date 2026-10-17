---
id: REV-1089
sequence_id: 1089
type: review
title: 'Pronouns on roles and operators: shape rule, verbs, default, display table'
status: Approved
author: reviewer
refs:
- TASK-1071
subentities:
- local_id: F1
  title: Config stamp drops an explicit [display] default and unusable values without
    a report
  status: Verified
  severity: medium
- local_id: F2
  title: Pronouns shape rule accepts Unicode format characters such as bidi overrides
  status: Verified
  severity: medium
- local_id: F3
  title: display_problems can be set from .squads.toml and shows up as a check warning
  status: Verified
  severity: low
- local_id: F4
  title: Role-document pronouns refusal falls back to a malformed verb text
  status: Verified
  severity: low
- local_id: F5
  title: Display splice misreads a multi-line string and a quoted header
  status: WontFix
  severity: low
created_at: '2026-10-17T02:47:29Z'
updated_at: '2026-10-17T03:10:57Z'
---
<!-- sq:body -->
Scope: TASK-1071 ST1 to ST4 against 21aba9bb, from `git diff HEAD -- src tests` plus the untracked files. That covers the pronouns attribute and its shape rule, the creation and update verbs, the roles-only `[defaults]` pronouns default, the four roster `--json` payloads, and the `[display]` model and `display_config_valid` that landed ahead of ST6. Every claim was driven in a scratch squad, with a `git archive HEAD` tree for comparison with HEAD.

Checked and sound:

- Shape rule: empty, whitespace, 40 against 41, trimming at 40, tab, newline, U+2028, marker tag, `[x]` and `elle/iel` behave the same through `operator add`, `dev add`, `role activate` and both `update` verbs. A blank `update` clears the value. A blank on creation stores nothing.
- `role activate --pronouns` on a live role is refused and names `update`. Pronouns go through `update` as their own keyword, never through the roster write gate, so they work on system roles. A title update on `architect` behaves the same as on HEAD.
- `pronouns_valid` runs only in `sq check` because it needs the raw text, which is also why `attribute_valid` runs only there. A title update on an operator holding a hand-edited 41-character value passes and leaves that value as written. A stored value of another type is reported by `attribute_valid`.
- The `[defaults]` pronouns resolve for roles only. Operators show null. `sq sync` writes nothing, and removing the default leaves the tree clean. `--json` carries the resolved value. A stored value that fails the rule reads as unset.
- Comment headers and `discussion[]` carry no pronouns.
- Placing `_pronouns.py` at the top level is right: the marker check needs `_sections`, which `_models` may not import. The rows for the new import edges are correct. Loading the catalog per resolution costs about 1 ms, which does not matter.
- Comments and docstrings state present truth. No ticket ids appear.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1089 add-finding "…" --severity medium`; track with `sq review 1089 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Config stamp drops an explicit [display] default and unusable values without a report

<!-- sq:finding:F1:body -->
`sq sync` rewrites `.squads.toml` from the model every time it runs (`_stamp_version`), and `to_toml` writes `[display]` back only when a value differs from its default. Driven in a scratch squad, one `sq sync` each:

- `[display]` with `pronouns = true`: the table is deleted. This fails FEAT-961 US5 bullet 2, which requires a file whose values are all defaults to be rewritten byte-identically.
- `pronouns = "false"`, an unknown key `pronuns = false`, or `display = 3`: `sq check` warns, then the next `sync` deletes the value without saying so, and the warning is gone too. The user's intent (here, display off) is lost and nothing reports it.
- `pronouns = false`: the value survives, but the first stamp adds a blank line, so that rewrite is not byte-identical either.

HEAD does the same to comments and unknown top-level keys: on HEAD, `# my comment` and `foo = 1` are both dropped by `sq sync` (driven against a `git archive HEAD` tree). That loss is older than this change. `[display]` is new, though: it is a table users write by hand, and the ADR says a bad value is reported by `sq check`, not silently removed.

Simplest fix: keep the `[display]` mapping exactly as it was read and write it back unchanged when the file is stamped, including keys that failed to parse. The stamp then never changes what the user wrote in `[display]`. The older comment and unknown-key loss is a separate item: the stamp should edit only the line it stamps. That item should not be fixed inside this task.

Tests: the display parser and `display_config_valid` have no tests yet, apart from the tier-table rows. The file-after-stamp column of the ST6 table would have caught every case above.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-17T03:04:09Z] `python-dev` Elias Python:
  - Fixed. A stamp now splices the [display] text (or top-level display lines) from the file as read, so a default, a bad value, an unknown key, comments inside the table and its separating blank line survive byte for byte; to_toml no longer writes the table. New tests: parser, display_config_valid, stamp byte-compare and a second-stamp no-op over 11 contents. Reverting to the rebuilt table turns 9 tests red.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Pronouns shape rule accepts Unicode format characters such as bidi overrides

<!-- sq:finding:F2:body -->
`_LINE_BREAKING_CATEGORIES` rejects Cc, Zl and Zp but not Cf, the Unicode format characters. Driven with `sq operator add --pronouns`: U+202E (RIGHT-TO-LEFT OVERRIDE) and U+200B (ZERO WIDTH SPACE) are both stored, `sq check` reports nothing, and `operator show --json` returns them. A bidi override reverses the text that follows it on the same line, in a terminal and in any file that renders the value. That includes the `CLAUDE.md`/`AGENTS.md` roster line once ST5 lands. ADR-981 says "no control characters", and Unicode classes the bidi overrides as control characters.

Fix: add `"Cf"` to the rejected categories. Add U+202E, U+200B and U+FEFF rows to `VALUE_SHAPES` and to the verb tables.

Smaller point: the 40-character limit counts raw code points. `subentity_title_max` counts length after NFC normalisation. So a decomposed `é` (e followed by U+0301) uses 2 of the 40 characters here and 1 there. Normalise with NFC before counting, or say in the shape rule's docstring why the two counts differ.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-17T03:04:11Z] `python-dev` Elias Python:
  - Fixed. Cf is rejected and the 40-character count is taken after NFC. Rows added to the unit, stored, check and verb tables. Dropping Cf turns 27 tests red; counting raw code points turns 7 red.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — display_problems can be set from .squads.toml and shows up as a check warning

<!-- sq:finding:F3:body -->
`SquadsConfig.display_problems` is an ordinary pydantic field (`exclude=True` only keeps it out of the dump), so the config loader also fills it from the file. Driven: a top-level line `display_problems = ["injected"]` in `.squads.toml` makes `sq check` print `warn .squads.toml: injected; the default applies`. Make it a `PrivateAttr` that only `_tolerate_display` sets, or have the before-validator drop any incoming `display_problems` key.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-17T03:04:13Z] `python-dev` Elias Python:
  - Fixed. The config before-validator drops any incoming display_problems key; the problems are derived from display only. Letting the file set it turns 1 test red.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Role-document pronouns refusal falls back to a malformed verb text

<!-- sq:finding:F4:body -->
`refuse_pronouns_key` (`_roles/_loader.py`) uses `sq role update` as the verb when the entry has no string slug, and the message then reads `` `sq role update <text>` ``. That text names neither an address nor `--pronouns`. In practice the branch is never reached: a `[[roles]]` entry with no slug is refused earlier (driven: "roles[0] is missing a string 'slug'"), and the per-slug file path always passes the slug. Either remove the fallback, or make it `sq role <addr> update --pronouns <text>`.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-17T03:04:15Z] `python-dev` Elias Python:
  - Fixed. The fallback is now sq role <addr> update --pronouns, tested with and without a slug. Reverting it turns 1 test red.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Display splice misreads a multi-line string and a quoted header

<!-- sq:finding:F5:body -->
`_display_source` (`_models/_config.py`) finds the `[display]` text by matching header lines. It does not parse TOML, and that misreads two valid shapes. I drove both through `to_toml_keeping`, and the first one through `sq sync` as well:

- **A multi-line string inside `[display]` with a line that starts with `[`**, for example `note = """` then `[evil]` then `"""`. The splice stops at the fake header. `sq sync` then writes an unterminated string, and every later command stops with "malformed .squads.toml: Unterminated string". `pronouns = false`, which came after it, is lost. `sq check` had warned only about the unknown key `note`.
- **A quoted header `["display"]`** is not recognised, so the stamp drops the table without saying so. The setting it carried is lost.

Both shapes are unlikely. In each case a user who mistypes a key or quotes a header ends up with a file that sq broke, or with a setting silently removed.

Possible fixes: check the spliced result with `tomllib.loads` and keep the original file when it fails to parse or when its `display` value differs from what was read; or accept `["display"]` and stop the scan at a line that is inside a multi-line string. Stamping only the version line, as BUG-1090 proposes, would remove the splice altogether.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-17T03:10:54Z] `manager` Catherine Manager:
  - Folded into BUG-1090: a real TOML round-trip of .squads.toml fixes both shapes.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-17T02:48:46Z] `reviewer` Paul Reviewer:
  - Changes requested: two medium findings (F1 the config stamp drops [display] values without a report, F2 the shape rule admits bidi and zero-width format characters) and two low (F3, F4). ST1 to ST4 are otherwise sound; see the body for what was checked.
  - @python-dev fix F1 to F4 on TASK-1071; F1 belongs with ST6 tests. @manager the older loss of comments and unknown keys in .squads.toml on every sync is not this task; it should get its own item.
- [2026-10-17T03:10:27Z] `reviewer` Paul Reviewer:
  - Re-review of the final checkpoint (committed as 2deeb34d): F1 to F4 Verified by running them. Every [display] shape now survives a stamp byte for byte: a default, a bad value, an unknown key, inline, dotted, comments and a missing final newline. A second stamp changes nothing. Cf characters are refused, length is counted after NFC, and display_problems can no longer be set from the file.
  - The [display] table moving below [init.names] is acceptable: what it means is unchanged, and the reorder comes from rebuilding the whole file, which is BUG-1090. New finding F5 (low): the line splice misreads a multi-line string inside [display] (sync then writes a file sq cannot load) and a quoted ["display"] header (dropped).
  - Sound: the pin, since a merge override need not restate pronouns and the operator type cannot be dropped, so only a spec built whole by hand restates it; ST5 generated files carry pronouns whatever [display] says, as FEAT-961 rules; ST7 escaping, the unset case and the dim style on role, operator and dev list/show, the creation messages and the sq ui tree; comment headers carry no pronouns. @manager I recommend Approved, with F5 fixed here or folded into BUG-1090.
<!-- sq:discussion:end -->

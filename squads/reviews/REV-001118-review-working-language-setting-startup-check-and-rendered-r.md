---
id: REV-1118
sequence_id: 1118
type: review
title: 'Review: working_language setting, startup check and rendered rule'
status: Approved
author: reviewer
refs:
- TASK-1098
description: Review of the working_language commit for TASK-1098 against ADR-1100
subentities:
- local_id: F1
  title: A multi-line working_language value is truncated by a stamp, leaving .squads.toml
    unparseable
  status: Verified
  severity: high
- local_id: F2
  title: A quoted working_language key is silently dropped by a stamp
  status: Verified
  severity: medium
- local_id: F3
  title: sq sync crashes with a traceback when working_language is the last line,
    unterminated, after a display line
  status: Verified
  severity: medium
- local_id: F4
  title: A stamp deletes language and locale keys, contrary to US1's untouched claim
  status: Verified
  severity: low
- local_id: F5
  title: Problem text calls valid-but-unknown tags 'not a BCP 47 tag' and shows Python
    reprs
  status: Verified
  severity: medium
- local_id: F6
  title: und and root resolve silently to US English and to a non-language; aliases
    gain a region
  status: Verified
  severity: low
- local_id: F7
  title: The outside-a-squad warning test cannot fail
  status: Verified
  severity: low
- local_id: F8
  title: working_language defaults to English in the view renderers; derived in two
    places
  status: Verified
  severity: info
- local_id: F9
  title: sq migrate up corrupts .squads.toml when default_backend carries a trailing
    comment
  status: Verified
  severity: medium
- local_id: F10
  title: sq migrate up crashes with a traceback when a legacy file has an [init.names]
    slug that needs quoting
  status: Verified
  severity: medium
- local_id: F11
  title: sq migrate up turns a CRLF .squads.toml into LF; the crlf unit row tests
    input the CLI never sends
  status: Verified
  severity: low
- local_id: F12
  title: 'Valid files are refused with an instruction they already satisfy: an array
    line read as a header, a nan value'
  status: Verified
  severity: low
- local_id: F13
  title: Legacy regeneration drops unusable [display] entries and a non-table init.names
    without reporting them
  status: Verified
  severity: low
- local_id: F14
  title: The interrupted-write test for the migrate up config write was deleted with
    the stamp tests
  status: Verified
  severity: low
- local_id: F15
  title: A migrate refusal test still asserts against squads_version, which nothing
    reads
  status: Verified
  severity: info
created_at: '2026-10-24T15:25:35Z'
updated_at: '2026-10-24T19:01:13Z'
---
<!-- sq:body -->
## Scope

The commit that adds `working_language` (TASK-1098, contract ADR-1100 and the op-pierre rulings on FEAT-1097): the resolver in `src/squads/_language.py`, the config model and the stamp in `src/squads/_models/_config.py`, the startup notice in `src/squads/_cli/_common.py`, the `working_language_valid` check, the shared partial and its three includes, init and adopt, and the two new test files. ST5 (docs, CHANGELOG) is not built yet and is out of scope.

## Method

- Drove the dev build against scratch squads (both backends): 15 value shapes through `sq list`, `sq list --json` and `sq check --json`; 17 neighbour shapes through a `sq sync` stamp, the new build against the previous commit side by side; `-C` from inside and outside a squad; `--version`, `--help` and an unknown command.
- Fuzzed `resolve_working_language` with 45 tag shapes, looking for exceptions other than `ValueError`/`UnknownLocaleError` and for values that silently resolve to something other than what was written.
- Mutated a scratch copy of the tree to check whether the tests fail: the stamp's ordering branch, and the notice's outside-a-squad guard.
- Ran the targeted tests (tests/meta, the two new files, the goldens, the squad-global level tests): 489 passed. Ruff and pyright are clean on the changed modules.
- Timed startup against the previous commit, 30 interleaved runs per command.

## What holds

- The resolver never raises on any shape tried. Case variants (`FR`, `PT-BR`, `pt-br`) resolve and normalise; `fr_FR`, `x-klingon`, `en-x-foo`, empty, whitespace, int, bool, array and inline table all warn once and fall back to English. Absent is silent.
- The warning is exactly one line, on stderr only, with Rich markup escaped (`[bold red]x` prints literally). `--json` stdout still parses. Nothing is printed outside a squad, for `--version`, for `--help` or for an unknown command. `-C` warns for the target squad, not for the cwd. `open_service` never reads the key (read).
- A duplicated key is the existing TOML parse error, exit 1, with no traceback.
- `init` and an adopt that creates the config write `"en"`. An adopt over an existing config leaves it untouched, and a sync does not add the key.
- CLAUDE.md, AGENTS.md and the squads skill show the name plus the tag, and update after the key changes and `sq sync`.
- The rule text is unambiguous: one configured working language for `sq` content and agent-to-agent traffic, and one conversation language deduced from the human.
- `working_language_valid` reports only malformed values, at warn. It is always-on, so its level cannot be overridden: `[squad] validators = ["working_language_valid@error"]` is refused as a workflow lint error, as for `display_config_valid`. That matches the always-on rule in docs/overrides.md. The level-override item in the task's test plan cannot apply, so it is not a gap.
- Layering, the import-edge table and the mutable-state guard pass. Comments are short, with no IDs or history.

## Startup cost

Medians over 30 interleaved runs on a small squad: `sq list` went from 751 to 774 ms (+23 ms), and `sq board list` from 755 to 772 ms (+17 ms). The isolated cost is about 13 ms for the Babel import plus about 14 ms for the first `Locale.parse` and display-name load. The ruling accepts this cost, so it is reported for information only.

## Note, not a finding

`backend_reconciled` checks only that the managed files exist, so after the key changes and before `sq sync`, CLAUDE.md and the skill disagree (the skill is rendered at read time) and `sq check` says nothing. This follows the ruled design and the existing check; it is recorded here so the claim that `backend_reconciled` stays clean is not read as a content check.

## Verdict

Request changes. The stamp re-reads the key's line with a line regex instead of from the parsed TOML, and that produces three defects: a valid multi-line value corrupts `.squads.toml` (F1, high), a quoted key is silently dropped (F2), and a final line with no newline crashes `sq sync` (F3). Everything else is low or info.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1118 add-finding "…" --severity medium`; track with `sq review 1118 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A multi-line working_language value is truncated by a stamp, leaving .squads.toml unparseable

<!-- sq:finding:F1:body -->
**Label: driven.**

`_working_language_line` (`src/squads/_models/_config.py:63-70`) takes only the first physical line of the key, and `to_toml_keeping` (`:189-213`) writes that one line back. A multi-line value therefore loses its continuation lines, and the stamped file is no longer valid TOML. `"""\nfr"""` is a valid value: TOML trims the newline after the opening delimiter, so it reads as `fr` and the squad renders French. After one `sq sync`, every command fails.

Reproduction, in a scratch squad:

```
working_language = """
fr"""
```

1. `sq sync` exits 0 and renders "**French** (`fr`)". The file now ends in `working_language = """`.
2. `sq list` then fails with: `error: malformed …/.squads.toml: Unterminated string (at end of document)`, exit 1.

The same thing happens with a multi-line array (`working_language = [\n  "fr",\n]`), whose file ends in `working_language = [` and reports `Invalid value`. The version stamp in `_stamp_version` and the schema stamp in `_stamp_schema` (`src/squads/_services/_maintenance.py:1659-1667`) both go through this path. Run under the previous commit, the same inputs leave a parseable file.

Fix direction: find the key's span with the TOML parser, or with a scan that follows multi-line strings and arrays, instead of a one-line regex. Pin it with the two shapes above.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-24T15:33:55Z] `python-dev` Elias Python:
  - Stamp now edits only the two version lines in the original text; a multi-line value stays byte for byte (pinned by the multi-line string and array rows).
- [2026-10-24T15:46:08Z] `reviewer` Paul Reviewer:
  - Verified (driven): multi-line string and array values survive sq sync byte for byte and parse. Residual edge, not reopened: a top-level multi-line string with a line starting with [ before squads_version is read as a table header, and the stamp line is inserted inside the string.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — A quoted working_language key is silently dropped by a stamp

<!-- sq:finding:F2:body -->
**Label: driven.**

`_WORKING_LANGUAGE_RE = r"^[ \t]*working_language[ \t]*="` (`src/squads/_models/_config.py:60`) does not match a quoted key. TOML treats `"working_language" = "fr"` and `'working_language' = "fr"` as the same key, so the model loads `fr`. The stamp then removes the line that `to_toml()` regenerated (`:195`), finds no original line to carry over, and writes the file without the key.

Reproduction: a scratch squad with a stale `squads_version` and `"working_language" = "fr"`.

1. `sq sync` exits 0 and renders "**French** (`fr`)".
2. The rewritten `.squads.toml` has no `working_language` line.
3. The next `sq sync` renders "**English** (`en`)" with no warning.

The setting is lost silently. That contradicts ADR-1100: a stamp keeps an existing line as written.

Fix direction: decide presence from the parsed table (`tomllib`) rather than from the regex, and when the parser finds the key but the line scan does not, keep the original text rather than drop the key.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-24T15:33:57Z] `python-dev` Elias Python:
  - Same fix: a quoted key is never touched by the stamp (quoted-key row).
- [2026-10-24T15:46:09Z] `reviewer` Paul Reviewer:
  - Verified (driven): a quoted working_language key, and a quoted or literal squads_version, are kept and stamped in place.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — sq sync crashes with a traceback when working_language is the last line, unterminated, after a display line

<!-- sq:finding:F3:body -->
**Label: driven.**

`to_toml_keeping` (`src/squads/_models/_config.py:196-204`) adds a `"\n"` to the key's line when it has none (`_working_language_line`, `:69`), then looks that newline-terminated text up with `original.index(language)`. When the key is the file's last line with no trailing newline and a top-level `display.*` line exists, the lookup raises `ValueError: substring not found`. `sq sync` exits 1 with a Rich traceback, and the stamp never happens.

Reproduction:

```
squads_version = "0.0.1"
display.dense = true
working_language = "fr"
```

with no final newline. `sq sync` exits 1, and the traceback ends at `_config.py:201 in to_toml_keeping`. Without the display line the same file stamps fine. An editor that strips the final newline is enough to hit this.

The same branch also reorders an interleaved file: `display.a`, `working_language`, `display.b` is written back as `display.a`, `display.b`, `working_language`.

The branch has no test. In a scratch copy, forcing `language_first = True` leaves the stamp tests in `tests/unit/test_working_language_resolves_any_babel_tag_and_falls_back_to_english.py` and `tests/service/test_display_table_is_tolerated_reported_and_kept_through_a_stamp.py` green (64 passed).

Fix direction: work on line indices rather than on substring search, and pin a display neighbour before the key, after it and interleaved with it, plus the no-final-newline case.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-24T15:33:59Z] `python-dev` Elias Python:
  - Same fix: no line search remains; no-final-newline, display-before and interleaved rows pass.
- [2026-10-24T15:46:10Z] `reviewer` Paul Reviewer:
  - Verified (driven): no final newline after a display line stamps cleanly with exit 0; interleaved display lines keep their order.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — A stamp deletes language and locale keys, contrary to US1's untouched claim

<!-- sq:finding:F4:body -->
**Label: driven.**

FEAT-1097 US1 says the keys `language` and `locale` are left untouched, and ADR-1100 reserves them for the CLI's future localization. A stamp deletes them. `to_toml_keeping` (`src/squads/_models/_config.py:189`) rebuilds the file from the model and carries over only `display` and `working_language`.

Reproduction: put `language = "de"` and `locale = "it"` under a stale `squads_version`, then run `sq sync`. Both lines are gone. Comments and blank lines are dropped too.

The previous commit behaves the same way: every unknown top-level key has always been dropped. So this commit does not cause it, but US1's "untouched" claim is not true, and the future `locale` key would be wiped by the first version stamp after an adopter sets it.

Disposition options: carry every unrecognised top-level line verbatim, which would also replace the per-key carry-over and close F1–F3. Or record a WontFix on FEAT-1097 that narrows US1 to "not read or written by this feature".
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-24T15:34:01Z] `python-dev` Elias Python:
  - Same fix: language, locale, unknown keys and comments survive a stamp. Side effect reported on TASK-1098: legacy default_backend/default_role are no longer rewritten or dropped.
- [2026-10-24T15:46:11Z] `reviewer` Paul Reviewer:
  - Verified (driven): sq sync keeps language, locale, unknown keys and comments byte for byte. CRLF is normalised to LF by the IO layer, as before this change.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Problem text calls valid-but-unknown tags 'not a BCP 47 tag' and shows Python reprs

<!-- sq:finding:F5:body -->
**Label: driven.**

`resolve_working_language` (`src/squads/_language.py:36-39`) builds one message for every failure: "… is not a BCP 47 language tag; using English (en)". `sq check` reuses it, and the new `docs/overrides.md` row has the same wording.

That is false for well-formed BCP 47 tags that Babel has no data for. `tlh`, `qaa`, `x-klingon`, `en-x-foo`, `art-lojban`, `en-GB-oed` and `zh-min-nan` are all valid or registered BCP 47 tags, yet each gets the message. ADR-1100's own wording is "malformed or unknown", and an adopter told that `tlh` "is not a BCP 47 language tag" has been told something untrue.

The non-string shapes also print a Python repr rather than what the user wrote. `working_language = 5` prints `'5'`, which cannot be told apart from the string `"5"`. `true` prints `'True'`, and `["fr"]` prints `"['fr']"`. This comes from the `repr` in `_tolerate_working_language` (`src/squads/_models/_config.py:156-160`).

Fix direction: say "is not a language tag squads recognises" or similar, in the resolver and in the docs row. For a non-string value, name its TOML type ("is a number, not a language tag").
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-24T15:34:03Z] `python-dev` Elias Python:
  - Problem text now says 'not a language tag squads recognises'; non-string values are shown as written in TOML (5, true, ["fr"]); docs row updated.
- [2026-10-24T15:46:34Z] `reviewer` Paul Reviewer:
  - Reopened (driven). The wording is fixed, but `_written` (`src/squads/_language.py:28-30`) calls `json.dumps`, which raises `TypeError` on a TOML date, time or datetime.
    
    Reproduction: `working_language = 1979-05-27`.
    
    - `sq list` exits 1 with a traceback (`TypeError: Object of type date is not JSON serializable`).
    - `sq check` does the same.
    - So does `sq init --force`, which is the recovery path.
    
    Every command now fails on a value that ADR-1100 says must never be an error. The previous code (`repr`) handled it. Fix direction: fall back to `str(raw)` for any type `json.dumps` rejects (or format it per TOML type), and add a date row to the malformed table.
- [2026-10-24T18:35:33Z] `python-dev` Elias Python:
  - - A TOML date, time or datetime working_language no longer crashes the problem text: _written falls back to str(raw) when JSON cannot spell the value, so it takes the malformed path (one warning, English). Date, time and datetime rows added to the malformed table; verified through the resolver, not yet driven through sq list/check/init --force.
- [2026-10-24T18:47:29Z] `reviewer` Paul Reviewer:
  - Verified (driven) against ab391d82: a TOML date, time, offset and local datetime, plus 5, true, ["fr"], an inline table, 3.5 and inf, each give one warning with exit 0 through sq list and sq check --json; sq init --force recovers from a date value. Residue, not reopened: a datetime prints as 1979-05-27 07:32:00+00:00, an inline table as {"a": 1} and inf as Infinity, not as written in TOML.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — und and root resolve silently to US English and to a non-language; aliases gain a region

<!-- sq:finding:F6:body -->
**Label: driven.**

`_parse` (`src/squads/_language.py:18-22`) renders whatever `Locale.parse` returns. Babel expands aliases and likely subtags, so some written values reach the agent files as a different language or a non-language, with no warning:

| written | rendered |
|---|---|
| `und` (undetermined) | English (United States) (`en-US`) |
| `root` | root (`root`): "This squad's working language is **root**" |
| `iw` | Hebrew (Israel) (`he-IL`), region added |
| `fra`, `eng` | French (France) (`fr-FR`), English (United States) (`en-US`), region added |
| `de-CH-1996` | German (Switzerland) (`de-CH`), variant dropped |

The ruling accepts any tag Babel knows, so these values are valid. But `root` is not a language, and `und` explicitly means "no language". Rendering the first as a language name, and silently turning the second into US English, are the opposite of what someone writing those values meant. The region that `iw` and `fra` gain is not what the adopter configured.

Fix direction: refuse `root` and `und` as malformed (Babel's root locale is not a working language). Optionally keep the written language subtags instead of Babel's likely-subtag expansion, for example by comparing `locale.language`/`territory` against the input before rendering.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-24T15:34:05Z] `python-dev` Elias Python:
  - und, root and Babel aliases (iw, fra) are malformed (no likely-subtag expansion); the rule shows the tag exactly as written.
- [2026-10-24T15:46:12Z] `reviewer` Paul Reviewer:
  - Verified (driven): und, root, iw, fra, eng and de-CH-1996 now warn and fall back to English; a valid tag renders as written (pt-br stays pt-br).
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — The outside-a-squad warning test cannot fail

<!-- sq:finding:F7:body -->
**Label: driven (mutation).**

`test_outside_a_squad_a_command_prints_no_language_warning` (`tests/service/test_working_language_is_validated_rendered_and_kept_by_the_commands.py:115-118`) runs `sq list` with no squad and asserts that "working_language" is not in the output. With no squad there is no value to report, so no implementation can print that warning. The assertion holds whatever the notice does.

Falsified in a scratch copy: removing the `try/except SquadsError` guard from `working_language_notice` (`src/squads/_cli/_common.py:1717-1726`) leaves the test green (1 passed). Meanwhile `sq list` outside a squad, and `sq init --help`, now end in an uncaught `NotInitializedError`.

Fix direction: assert what the guard protects, which is that the command's own outcome is unchanged (the clean `no .squads.toml found` error and its exit code, with no traceback). A better check is `sq init` in an empty folder succeeding. Otherwise drop the test.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-24T15:34:07Z] `python-dev` Elias Python:
  - Replaced by a test that fails when the guard is removed (list still exits 1 cleanly, sq init succeeds); falsified.
- [2026-10-24T15:46:13Z] `reviewer` Paul Reviewer:
  - Verified (mutation): removing the guard from working_language_notice now fails the rewritten test; restored, 9 passed.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — working_language defaults to English in the view renderers; derived in two places

<!-- sq:finding:F8:body -->
**Label: read.**

`render_source_view`, `expand_view_tags` and `_render_resolved_source_or_raise` (`src/squads/_views.py:576, 1124, 1240`) take `working_language: WorkingLanguage | None = None` and fall back to English (`:628`). All three current callers pass the value. But a future caller that forgets it renders English for a French squad, and nothing fails, because English is also a valid rendering. The sibling `squad_dir_display` is a required positional argument for the same reason.

The resolution is also written twice: once as `ServiceCore.working_language` (`src/squads/_services/_base.py:544-547`) and once as `BackendContext.working_language` (`src/squads/_backends/_base.py:99-102`). The task asked for one derivation point.

Fix direction: make the parameter required, and derive the service property from one shared helper (or from the backend context).
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-24T15:34:09Z] `python-dev` Elias Python:
  - working_language is a required argument of the three view renderers; callers and tests updated. The backend and service properties stay as two one-line derivations.
- [2026-10-24T15:46:15Z] `reviewer` Paul Reviewer:
  - Verified (read): working_language is a required argument of the three view renderers. The two identical properties remain; the fix direction did not ask for that part.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — sq migrate up corrupts .squads.toml when default_backend carries a trailing comment

<!-- sq:finding:F9:body -->
**Label: driven.**

`_DEFAULT_BACKEND_RE` (`src/squads/_migrations/_legacy_config.py:7`) captures everything after `=` as the value (`(.*)$`), and `drop_legacy_config_keys` (`:25-26`) wraps all of it in `[...]`. A trailing comment therefore ends up inside the array.

Reproduction: a scratch squad at schema 0.15 with:

```
default_backend = "claude_code"  # legacy
```

1. `sq migrate up` exits 0 and writes `active_backends = ["claude_code"  # legacy]`.
2. `sq list` then fails with `malformed .squads.toml: Unclosed array`.

The re-serialising stamp this replaces handled the same file.

The same line-based scan also breaks a multi-line `default_role = """…"""`: only the first line is dropped, and the leftover `manager"""` makes the file unparseable. A quoted `"default_backend"` key is left in place, which is harmless because the model still translates it on load.

Fix direction: capture only a quoted-string value and keep the rest of the line (as `_stamp_line` does), and skip a multi-line value's continuation lines. Pin the trailing-comment shape.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-24T18:35:34Z] `python-dev` Elias Python:
  - - The line-based drop_legacy_config_keys is gone (ADR-1119). A file with default_backend or default_role is now regenerated from tomllib plus to_toml(), read back and compared before the first runner, so a trailing comment or a multi-line default_role can no longer corrupt it; a file the regeneration cannot reproduce is refused, and keys the model does not carry are listed in the migrate report. Table rows pin the trailing-comment, multi-line and quoted-key shapes.
- [2026-10-24T18:47:31Z] `reviewer` Paul Reviewer:
  - Verified (driven) against ab391d82: sq migrate up on a 0.15 corpus regenerates a trailing-comment default_backend, a multi-line default_role and a quoted "default_backend" key into active_backends; the file parses and sq list exits 0 afterwards.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — sq migrate up crashes with a traceback when a legacy file has an [init.names] slug that needs quoting

<!-- sq:finding:F10:body -->
**Label: driven.**

The legacy regeneration crashes with a traceback when an `[init.names]` slug needs quoting in TOML. `SquadsConfig.to_toml()` (`src/squads/_models/_config.py`, the `[init.names]` loop) writes each slug as a bare key. The read-back check in `_regenerated` (`src/squads/_migrations/_config_text.py:44-47`) catches only `tomllib.TOMLDecodeError`.

Reproduction: a 0.15 corpus with this config:

```
schema_version = "0.15"
squad_dir = "."
default_role = "manager"
active_backends = ["claude_code"]
[init.names]
"a.b" = "X"
```

`sq migrate up` exits 1 with a Rich traceback ending in `ValidationError: 1 validation error for SquadsConfig init_names.a Input should be a valid string`. `to_toml()` wrote `a.b = "X"`, which TOML reads as the dotted key `a.b`, so the read-back gives a nested table. No file changed. A slug with a space (`"my role"`) instead gives a TOMLDecodeError, which is refused cleanly.

ADR-1119 says a regeneration that does not read back is refused before the first runner. Here it is a traceback instead. `sq init` is not affected, because it writes roster slugs only.

Fix direction: quote any slug that is not a bare TOML key in `to_toml()`, and treat a `ValidationError` in the read-back like a decode error. Pin a dotted slug and a slug with a space.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-24T18:54:12Z] `python-dev` Elias Python:
  - Fixed: to_toml quotes any init.names slug that is not a bare key (and escapes backend names); the regeneration read-back also catches ValidationError, so an unreadable result is refused cleanly. Rows: dotted slug, slug with a space, non-string init name.
- [2026-10-24T19:00:48Z] `reviewer` Paul Reviewer:
  - Verified (driven, 1104c03f): a legacy file with "a.b", "my role" and ok-slug under [init.names] migrates with exit 0, the slugs that need quoting are written quoted, and the file parses.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — sq migrate up turns a CRLF .squads.toml into LF; the crlf unit row tests input the CLI never sends

<!-- sq:finding:F11:body -->
**Label: driven.**

ADR-1119 says the stamp "changes nothing else". On a CRLF file, `sq migrate up` rewrites every line ending to LF. `run_pending_migrations` reads the file through `_aio.read_text` (`Path.read_text`, universal newlines), so `plan_config_rewrite` never sees a `\r`. `atomic_replace_sync` then writes with `newline=""`.

Reproduction: a 0.15 corpus whose `.squads.toml` uses CRLF throughout. `sq migrate up` exits 0, and `cat -A` shows every line ending in `$` instead of `^M$`. The content is correct and the file parses.

The `crlf` row of `tests/unit/test_migration_config_text_edits_one_value_or_regenerates_or_refuses.py` passes CRLF text straight to `plan_config_rewrite` and asserts that it is kept. That holds at the unit level, but the CLI never sends that input. The row proves something the pipeline does not deliver.

Fix direction: read this one file with `newline=""` (or as bytes decoded to UTF-8) so the edit sees the real endings, and add a service-level CRLF row. Otherwise, drop the unit row and narrow the ADR wording.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-24T18:54:14Z] `python-dev` Elias Python:
  - Fixed: migrate up reads .squads.toml as bytes decoded to UTF-8, so the edit sees the real line endings and the write keeps them. The unit crlf row is replaced by a service-level row that runs sq migrate up on a CRLF file.
- [2026-10-24T19:00:51Z] `reviewer` Paul Reviewer:
  - Verified (driven, 1104c03f): a CRLF config keeps CRLF on every line after sq migrate up, and a file with mixed endings keeps each line ending as written.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Valid files are refused with an instruction they already satisfy: an array line read as a header, a nan value

<!-- sq:finding:F12:body -->
**Label: driven.**

Two valid files with a single-line, unescaped `schema_version` are refused, and the error tells the adopter to do what the file already does.

1. **Array element read as a table header.** `_HEADER` (`src/squads/_migrations/_config_text.py:17`) matches a line such as `  [1, 2]` inside a multi-line array. `top` stops there, so a `schema_version` line after the array is not seen. Driven: `note = [\n  [1, 2]\n]\nschema_version = "0.15"\n…` gives `must have exactly one top-level schema_version line (found at: none); write schema_version = "0.15" on a single line`.
2. **`nan` anywhere in the file.** The parse check compares `tomllib.loads(text) == {**table, …}` (`:81`). Two separately parsed `nan` floats are never equal, so any file holding `x = nan` is refused with `cannot edit .squads.toml line 1 safely: write schema_version = "0.15" on a single line`.

The squad is untouched in both cases, so this is not corruption. But the adopter cannot act on the instruction: the line is already in the requested form.

Fix direction: for the header scan, skip lines inside an open bracket or multi-line string, or locate the key with the parsed table as the authority. For the check, compare in a NaN-aware way, or compare the two parses with `schema_version` removed from both after a `repr` round-trip. Either way, the refusal should name the actual cause. Pin both shapes.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-24T18:54:17Z] `python-dev` Elias Python:
  - Fixed: the schema line is no longer found with a header heuristic. Every line starting like the key is tried, and the one whose edit changes only the parsed top-level schema_version is used; the comparison is nan-safe. Rows: nested array line, nan elsewhere, table-like line in a string before, second candidate in a string.
- [2026-10-24T19:00:53Z] `reviewer` Paul Reviewer:
  - Verified (driven, 1104c03f): an array element line before the key and nan/-nan values now stamp. Tried decoys in a table, an array of tables, a dotted key, basic and literal multi-line strings and a backslash continuation: only the real top-level line is ever edited, and no shape gave two passing candidates. An escaped real value next to a string decoy is refused and lists both lines, which is acceptable.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Legacy regeneration drops unusable [display] entries and a non-table init.names without reporting them

<!-- sq:finding:F13:body -->
**Label: driven.**

ADR-1119: "A top-level key or table the model does not carry is named in the migration report rather than dropped silently." The regeneration drops some content without naming it. `_uncarried` (`src/squads/_migrations/_config_text.py:30-38`) checks top-level keys and `init.*`, but not what `parse_display` discards, and not an `init.names` that is not a table.

Reproduction: a 0.15 corpus with

```
schema_version = "0.15"
squad_dir = "."
default_backend = "claude_code"  # legacy
[display]
pronouns = "false"
foo = 1
```

`sq migrate up` exits 0. The new file has no `[display]` table, and the report has no "dropped" line. The same happens for `[init]\nnames = 5`. The read-back still passes, because `display_problems` is `exclude=True`, so `model_dump()` does not compare it.

The adopter's `pronouns = "false"` was already unusable, and `sq check` reported it. After the migration, that record is gone, and so is the hint of what they meant.

Fix direction: add `display.<key>` for every problem `parse_display` reports, and `init.names` when it is not a table, to the dropped list. Pin both.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-24T18:54:19Z] `python-dev` Elias Python:
  - Fixed: the dropped report now lists display.<key> for each unusable [display] entry, display when it is not a table, and init.names when it is not a table. Rows added.
- [2026-10-24T19:00:56Z] `reviewer` Paul Reviewer:
  - Verified (driven, 1104c03f): the report now names display.pronouns, display.foo and init.names.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — The interrupted-write test for the migrate up config write was deleted with the stamp tests

<!-- sq:finding:F14:body -->
**Label: read.**

The commit deleted `test_an_interrupted_schema_stamp_leaves_the_previous_config_intact` from `tests/service/test_squads_toml_writes_stay_atomic.py` along with the sync stamp test. The behaviour it covered still exists: `run_pending_migrations` writes `.squads.toml` through `_aio.atomic_write_text` (`src/squads/_services/_maintenance.py:1681`). It is now the only write besides init. The module docstring now covers init only, and nothing pins that an interrupted migrate write leaves the previous config intact.

Fix direction: keep one row that fails `Path.replace` during `sq migrate up` (or during the final config write) and asserts the previous bytes survive and still load.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-24T18:54:21Z] `python-dev` Elias Python:
  - Fixed: test_an_interrupted_migrate_config_write_leaves_the_previous_config_intact fails Path.replace on the config during run_pending_migrations and checks the previous bytes survive and load.
- [2026-10-24T19:00:58Z] `reviewer` Paul Reviewer:
  - Verified (read and run): test_an_interrupted_migrate_config_write_leaves_the_previous_config_intact fails the replace of the config during run_pending_migrations and asserts the previous bytes and that they still load; passes.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — A migrate refusal test still asserts against squads_version, which nothing reads

<!-- sq:finding:F15:body -->
**Label: read.**

`test_a_refusal_names_a_release_that_reads_the_squads_schema_not_the_last_sync` (`tests/integration/test_migrate_up_checks_the_corpus_before_the_runners.py:816-825`) still reads `squads_version` from the fixture's `.squads.toml`. It asserts that the refusal does not name that version. No code reads the key now, so the assertion cannot fail for the reason the test was written for. The schema assertions above it still carry the test.

Fix direction: drop the `synced` read and its assertion, and the "not the last sync" part of the name.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-24T18:54:24Z] `python-dev` Elias Python:
  - Fixed: the squads_version read and its assertion are gone from the refusal test, and the name no longer says not the last sync.
- [2026-10-24T19:01:00Z] `reviewer` Paul Reviewer:
  - Verified (read): the squads_version read and its assertion are gone, and the test name drops "not the last sync".
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T15:26:51Z] `reviewer` Paul Reviewer:
  - Review done: 8 findings (F1 high, F2 and F3 medium, F4 to F7 low, F8 info). The three stamp defects share one root cause, the regex line carry-over in to_toml_keeping. Recommended verdict: request changes. @python-dev for F1 to F3, F5 to F8; F4 needs a scope call (@tech-lead).
- [2026-10-24T15:27:58Z] `manager` Catherine Manager:
  - Fix direction (manager): F1-F4 share one cause, so the stamp stops rebuilding .squads.toml. It edits only the lines sq owns (the version stamps) in the original text and keeps every other line byte for byte, including working_language in any valid TOML form, language, locale, unknown keys and comments. F5: name the cause as an unrecognised tag, show non-string values as written. F6: und and root take the malformed path; the rendered tag is the one the adopter wrote. F7: make the test able to fail. F8: working_language becomes a required argument of the view renderers.
- [2026-10-24T15:46:47Z] `reviewer` Paul Reviewer:
  - Re-review: F1-F4 and F6-F8 Verified (driven, F8 read). F5 reopened and raised to medium: a TOML date value now crashes every command, sq init --force included. New F9 (medium): sq migrate up corrupts the config when default_backend has a trailing comment. Not approving. @python-dev for F5 and F9.
- [2026-10-24T18:48:28Z] `reviewer` Paul Reviewer:
  - Re-review of ab391d82 (ADR-1119): F5 and F9 Verified (driven). The schema stamp holds on every quoting, comment, spacing, no-final-newline and string-candidate shape tried, and every refusal leaves the tree byte-identical, with or without an index. sync no longer writes the config. New: F10 medium (legacy regeneration traceback on a dotted init.names slug), F11-F14 low (CRLF normalised to LF, false refusals with an unusable instruction, unreported display drops, a deleted atomicity test), F15 info. Not approving while F10 is open. @python-dev for F10-F15.
- [2026-10-24T19:01:13Z] `reviewer` Paul Reviewer:
  - Approved: F10-F15 Verified against 1104c03f (driven repros re-run, decoy shapes tried against the candidate-line stamp, 48 targeted tests pass). All 15 findings Verified. @manager
<!-- sq:discussion:end -->

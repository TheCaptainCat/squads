---
id: REV-736
sequence_id: 736
type: review
title: Bundled-assumption sweep across src and clients
status: Approved
author: reviewer
description: Seven read-only shards over the CLI, services, models/index, backends/rendering,
  spec layer, VS Code client and TUI/board/memory/migrations, hunting the seven bundled-assumption
  categories against the 53 in-force decisions
subentities:
- local_id: F1
  title: sq workflow serves the bundled spec at exit 0 on a broken override
  status: Fixed
  severity: high
- local_id: F2
  title: find_markers is blind to every sub-entity marker
  status: Fixed
  severity: high
- local_id: F3
  title: An absent timestamp invents now and wedges the item permanently
  status: Fixed
  severity: high
- local_id: F4
  title: A role override bypasses every validator, and can grant spawn rights
  status: Fixed
  severity: high
- local_id: F5
  title: A declared type whose name matches a bundled alias runs the wrong command
  status: Fixed
  severity: high
- local_id: F6
  title: Generated agent text instructs --assignee qa on a minimal roster
  status: Fixed
  severity: medium
- local_id: F7
  title: The operator personal name and this repo ship in bundled templates
  status: Fixed
  severity: medium
- local_id: F8
  title: Generated text instructs status Cancelled and --story US1 under an override
  status: Fixed
  severity: medium
- local_id: F9
  title: A role override title never reaches the index, so the roster renders stale
  status: Fixed
  severity: medium
- local_id: F10
  title: sq sync never seeds bundled skills, leaving an unindexed skill file
  status: Fixed
  severity: medium
- local_id: F11
  title: A malformed override escapes as a raw traceback out of workflow lint
  status: Fixed
  severity: medium
- local_id: F12
  title: Renaming a sub-entity plural bricks add-kind on the existing corpus
  status: Fixed
  severity: medium
- local_id: F13
  title: A misspelled [selected] keep-entry silently drops the key it meant to keep
  status: Fixed
  severity: medium
- local_id: F14
  title: The create-lane advisory contradicts the tools own generated instructions
  status: Fixed
  severity: medium
- local_id: F15
  title: Sub-entity field flags are baked from the bundled spec on registration
  status: Fixed
  severity: medium
- local_id: F16
  title: The load boundary skips every adopter-declared badge field
  status: Fixed
  severity: medium
- local_id: F17
  title: A migration writes legacy sub-entity statuses with no mapping to the spec
  status: Fixed
  severity: medium
- local_id: F18
  title: Migrations persist a derivable path key that then goes stale
  status: Fixed
  severity: low
- local_id: F19
  title: The scaffolded workflow override example fails on a retired key
  status: Fixed
  severity: low
- local_id: F20
  title: Priority flag validates against the wrong collection, both ways
  status: Fixed
  severity: medium
- local_id: F21
  title: Priority flag is advertised on types declaring no priority field
  status: Fixed
  severity: low
- local_id: F22
  title: The client id regex breaks any hyphenated declared prefix
  status: Fixed
  severity: medium
- local_id: F23
  title: The preview sub-entity head hardcodes the severity field code and label
  status: Fixed
  severity: medium
- local_id: F24
  title: sq sync silently drops an unrecognised model from a role override
  status: Fixed
  severity: medium
- local_id: F25
  title: The AGENTS.md backend parses mission back out of its own generated text
  status: Fixed
  severity: medium
- local_id: F26
  title: The memory skill hardcodes the squads path and ignores squad_dir
  status: Fixed
  severity: low
- local_id: F27
  title: search and inbox abort whole-corpus on one unreadable file
  status: Fixed
  severity: high
- local_id: F28
  title: The TUI glance line hardcodes the priority field code
  status: Fixed
  severity: low
- local_id: F29
  title: Declared ref_rules are inert and the kind vocabulary is unvalidated
  status: Fixed
  severity: low
- local_id: F30
  title: The Records view goes silently blank on a type-catalog failure
  status: Fixed
  severity: low
- local_id: F31
  title: The client squad_dir regex misses valid single-quoted TOML
  status: Fixed
  severity: low
- local_id: F32
  title: The graph node-click round trip is lossy for an underscored prefix
  status: Fixed
  severity: low
- local_id: F33
  title: Derived pointer target uses the OS separator, breaking Windows
  status: Fixed
  severity: medium
- local_id: F34
  title: The runner duplicates a check sq check already makes
  status: Fixed
  severity: medium
- local_id: F35
  title: A runner docstring now denies that any runner threads the spec
  status: Fixed
  severity: low
- local_id: F36
  title: A stale path key on an already-migrated squad is never stripped
  status: Fixed
  severity: low
- local_id: F37
  title: The spec-load swallow is unreachable and hides a check regression
  status: WontFix
  severity: low
- local_id: F38
  title: search and inbox still abort whole-corpus on an out-of-squad path
  status: Fixed
  severity: medium
- local_id: F39
  title: repair invents created_at and the heal makes the loss permanent
  status: Fixed
  severity: medium
- local_id: F40
  title: The marker single-definition guard misses a wrapped regex
  status: Fixed
  severity: low
- local_id: F41
  title: Every scale test has failed in setup since the actor guard landed
  status: WontFix
  severity: low
- local_id: F42
  title: ADR-663 does not name the absent-timestamp skew exclusion
  status: Fixed
  severity: low
- local_id: F43
  title: The marker guard body label omits the remediation guidance
  status: Fixed
  severity: low
- local_id: F44
  title: sq graph mermaid merges two ids differing only by hyphen or underscore
  status: Fixed
  severity: low
- local_id: F45
  title: The preview stamps a clickable item id on every mermaid node
  status: Fixed
  severity: low
- local_id: F46
  title: A category reassignment that contradicts itself loads clean
  status: Fixed
  severity: high
- local_id: F47
  title: parent_required is read for hints but never enforced at create
  status: Fixed
  severity: medium
- local_id: F48
  title: Category consistency has no clause for a declared ref_rule
  status: Fixed
  severity: medium
- local_id: F49
  title: A broken role override is invisible to sq check
  status: Fixed
  severity: medium
- local_id: F50
  title: A declared type dispatches to No such command under a broken override
  status: Fixed
  severity: low
- local_id: F51
  title: lifecycle_edges is orphaned by the diagram removal
  status: Fixed
  severity: low
created_at: '2026-08-03T14:44:44Z'
updated_at: '2026-08-15T15:46:56Z'
---
<!-- sq:body -->
## Scope

_TODO: what is under review?_
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 736 add-finding "…" --severity medium`; track with `sq review 736 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — sq workflow serves the bundled spec at exit 0 on a broken override

<!-- sq:finding:F1:body -->
Fixed. A workflow override that will not resolve is now a refusal on every surface, never an
answer drawn from the bundled vocabulary the project did not declare.

**The mechanism.** `_bind_active_spec` returned `None` on any resolution error and
`get_active_spec()` read that as "use the bundled spec". The failure therefore only reached
commands that open a service; every surface that reads the spec directly answered from bundled.
Two changes: `_bind_active_spec` now returns `(spec, spec_error)` and distinguishes *nothing was
declared* (outside a squad, no override file — bundled remains the honest answer) from *a
declaration failed to load*, and the failure is carried on `RequestContext.spec_error`;
`get_active_spec()` raises on it. A spec that failed to load has no honest substitute, so there
is nothing to fall back to.

**One text, two failure points.** `spec_refusal()` in `_workflow/_loader.py` composes the
message where the file and the loader's own cause are both in hand, and both `open_service` and
the CLI binding use it — the same failure reported twice in two voices is how an adopter ends up
believing they have two problems. It names the file, the key-level cause, and the action,
including which command still runs.

**What still works, deliberately.** `sq workflow lint` (the diagnostic — it neither opens a
service nor reads the active spec), `sq --help`, and `sq check`/`sq repair`, which take the
refusal from `open_service` and degrade around it, reporting it as a finding. Reporting the
failure is the contract; dying on it is not. An earlier attempt gated this in the root callback
with an exemption list and broke exactly those degradation paths — the refusal belongs on the
surfaces that *answer*, not on the parser.

Driven before: with an override declaring a `widget` type and an invalid role colour, `sq list`
exited 1 while `workflow types/statuses/collections/roles/subentity-kinds`, `workflow` and
`workflow --raw` all exited 0 describing the bundled spec, `widget` absent from every payload.
Driven after: all of them exit non-zero with the same named cause.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — find_markers is blind to every sub-entity marker

<!-- sq:finding:F2:body -->
Driven, and independently verified by the manager. The regex at _sections.py:68 accepts only [a-z0-9], while every declared sub-entity local_prefix is uppercase (US/ST/F). On a real repo file, 16 well-formed markers present and find_markers returns 8. Two consumers go blind. reject_markers (_services/_base.py:299) accepts a forged sub-entity marker inside an agent-authored item body; the next finding body write then lands in the forged region and destroys the prose around it, leaving the genuine region empty -- invariant 3 broken. _marker_issues (_services/_maintenance.py:94) cannot see a duplicated or unclosed sub-entity marker, so sq check, the must-pass gate, reports clean. Any declared kind whose prefix is not all-lowercase is equally invisible.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-06T19:24:03Z] Elias Python:
  - Fixed. Driven before the change on the real corpus: REV-736's own file carries 240 well-formed sq marker comments and find_markers returned 8. Forgery driven end to end on a scratch squad — a review body containing a forged finding-body marker pair was accepted, and the next `finding body` write replaced the two paragraphs of scope prose the forged pair spanned while the genuine region kept its old text. Duplicate-marker blindness driven with a control: a duplicated top-level sq:summary pair is reported by check, the same duplication on a finding-body pair is reported clean.
  - Fix: one case-blind definition, sections.MARKER_RE, tag class widened from [a-z0-9] to a Unicode-aware word class (\w plus : and -). The verbatim copy of the old pattern in _overrides/_service.py (_SQ_OPEN_RE) is deleted; _required_markers_from_bundled now calls find_markers, so there is a single place to widen. Strictness kept: the documentation placeholders in our own agent-facing prose still do not lint as markers.
  - Corpus fallout, deliberate: with the fix in, sq check on this repo went from clean to reporting BUG-727 for an unclosed finding-discussion marker. It is not corruption and not a false positive — the bug body quoted a well-formed marker tag inside backticks, which reject_markers has always forbidden ("backtick-wrapping does not neutralize a well-formed tag") and only accepted because it was blind. Judged the refusal correct rather than softening the regex, and de-wrapped the tag in that body; prose otherwise unchanged. A scan of every authored prose region in the whole corpus found that one instance and no other.
  - Tests: tests/unit/test_marker_recognition_across_prefix_casings.py (eight local_prefix shapes x open/close/nested sub-regions, every declared kind driven off the spec, eight non-marker shapes, plus a whole-text count over production-rendered blocks); tests/service/test_marker_injection_guard.py extended with the forged-region refusal per kind, the file-untouched + real-region-intact assertion, check reporting a duplicated and an unclosed sub-entity marker, and a whole-file marker-count property on service-written files. Guard: tests/meta/test_sq_marker_recognition_has_one_case_blind_definition.py — no second sq-marker regex outside the primitive (migrations' frozen legacy readers exempt, with a liveness test on the exemption), plus a behavioural probe that the live primitive sees every declared local_prefix and still refuses the placeholder.
  - Falsified: restoring the old lowercase class reddens 21 tests across those two files; restored and green.
- [2026-08-06T20:12:42Z] Paul Reviewer:
  - Verified at 366752a in an isolated worktree. Falsification confirmed: restoring the lowercase tag class reddens exactly 21 tests across the two named files.
  - Corpus scan re-run independently over all 767 files with three passes (a marker sharing a line with prose, a standalone tag whose shape the renderer cannot produce, and marker balance). Zero at the reviewed commit; exactly one at the tree before the de-wrap, BUG-727 line 17, which the balance pass also reports as an unclosed marker. The one-instance claim holds, and the de-wrap is the right call rather than softening the regex, because accepting that line leaves a structurally broken file.
  - Scale of the blind spot, driven: the fix makes 10080 of the corpus's 15156 well-formed markers visible that were not before. Override surface unaffected - old and new tag classes give an identical required-marker set on all 27 bundled templates.
  - Two follow-ups filed rather than reopening this: F43 (the body seam prints the terse message, so the judgement this rests on is argued from text that seam never shows) and F40 (two driven holes in the new meta guard).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — An absent timestamp invents now and wedges the item permanently

<!-- sq:finding:F3:body -->
Driven. _parse_dt (_models/_item.py:557) returns datetime.now(UTC) for a missing created_at/updated_at, bypassing clock.now() -- an ADR-77 violation, and the module already imports clock for iso(). Because _itemfile.frontmatter_skew round-trips both sides through from_frontmatter, the disk side re-invents now on every read and can never equal the index. Every mutation is then refused with a run sq repair pointer, and repair cannot clear it because repair rebuilds the index and never rewrites markdown. Two full repair-then-mutate rounds both refused; sq check silent. The item is permanently unmutatable. Entry point is sq adopt or any hand-authored .md.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-06T19:31:56Z] Elias Python:
  - Fixed. Driven before the change, both through the CLI and as a shape matrix. CLI: stripping created_at from one item's frontmatter made every mutation refuse; two full repair-then-mutate rounds were both refused, exactly as reported, with sq check silent throughout. Matrix through frontmatter_skew, per field x per value shape: absent -> skew, null -> skew, unparseable -> already a clean SquadsError at the load boundary, present-and-equal -> no skew. Both fields behave identically, so this was never one bad call site.
  - Fix, two parts. (1) _parse_dt's absent-value default now goes through clock.now() instead of datetime.now(UTC) - the ADR-77 half. (2) The wedge itself is not fixed by that: clock.now() is still a value the file never said. frontmatter_skew now excludes a timestamp the raw on-disk frontmatter carries no value for, read off the parsed frontmatter before the round trip (itemfile.INVENTED_WHEN_ABSENT + _invented_timestamps). The exclusion is absence-only: a present timestamp that disagrees is still refused, and an unparseable one still fails the load boundary.
  - Healed on write AND reported, not either/or. Every write seam persists the whole to_frontmatter_dict, so the first mutation writes the index's real created_at back into the file - verified end to end: the healed value is the index's original, not a fresh now. Until that write lands the file still reports a date it does not contain, so sq check now emits a warning naming the missing field (warning, not error - the item is fully usable). Scanned all 712 item files in this repo: none is missing either field, so the repo stays clean.
  - One extra site in the same class, fixed while here: _services/_import_model.utc_now_floor read datetime.now(UTC) directly, so an sq import with no --at ignored a forged instant. Now clock.now(). That leaves _clock.py as the only wall-clock reader in the tree, which is what the guard below can then assert without an allowlist.
  - Tests: tests/unit/test_absent_frontmatter_timestamp_is_not_a_skew.py (the matrix, both fields x absent/null/unparseable/present-equal in both YAML spellings/present-different, plus stability across three reads at three different instants, plus absent-does-not-mask-a-real-skew) and tests/service/test_item_with_an_absent_timestamp_stays_mutable.py (mutate-and-heal per field combination, the repair-then-mutate sequence converging, the check warning clearing after a write, and a genuinely diverged timestamp still refusing). Note the clock is advanced between setup and mutation on purpose: under a single frozen instant the invented placeholder coincides with the item's real creation time and the whole class is invisible - which is how it survived a passing suite. Guard: tests/meta/test_wall_clock_time_is_only_read_through_the_clock_module.py, an AST scan for any direct wall-clock call outside _clock.py, with a planted-shape test and a probe that the sanctioned seam really honours its override.
  - Falsified: removing the skew exemption reddens 13 tests; reverting _parse_dt to datetime.now reddens the 2 injectable-clock tests. Both restored and green.
- [2026-08-06T20:12:43Z] Paul Reviewer:
  - Verified at 366752a. Falsification confirmed: removing the skew exemption reddens 13; reverting the parse default reddens the 2 injectable-clock parametrisations plus the wall-clock meta guard.
  - Matrix driven independently through frontmatter_skew, both fields against absent, null, YAML tilde-null, empty string, unparseable, present-equal, present-different and an unquoted PyYAML datetime. Absence-only holds in every cell, an absent timestamp does not mask a divergence on another field, and the result is stable across three reads at three forged instants. End to end: the check warning names the field, the mutation succeeds, and the healed value is the index's original.
  - The exemption does not over-widen ADR-663's clause - it withholds a comparison whose premise was never satisfied rather than permitting a skew on a mirrored key, and it is conditioned on observed disk state per read, which is narrower than the key-name condition beside it. But the ADR is the authority and does not say so: F42.
  - One case the fix does not cover: a repair between the strip and the heal replaces the index's real created_at with a placeholder, and the heal then makes that permanent in the markdown. F39.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — A role override bypasses every validator, and can grant spawn rights

<!-- sq:finding:F4:body -->
Fixed. A role override now goes through the shared merge engine and is validated typed, like
every other override document.

**The mechanism.** `_apply_override` assigned raw TOML values into a plain dataclass: unknown
keys silently discarded, no typed validation, the bundled model whitelist never run, splat-refs
never resolved. It now composes the bundled `RoleDef` into a raw mapping, runs
`_specmerge.merge_override` against it with the closed top-level key space derived from
`RoleSpec.model_fields`, validates the result as a `RoleSpec`, and applies the model whitelist
the bundled catalog already enforces on itself.

Each symptom, driven before and after:
- `can_spawn = "false"` was a non-empty string and therefore truthy — a quoting mistake *granted*
  spawn authority. Now `false`, along with `"no"/"off"/"0"`; `"true"/"yes"/"on"/"1"` still mean
  yes, and `"maybe"` is refused naming the field. Quoting stops changing the answer.
- `is_default = "no"` likewise. (The multi-default *state* was already an error-level `sq check`
  finding on the live-item plane — `default_designation_duplicated` — so that half needed no new
  check, only the truthiness fix.)
- `model = "opuss"` was stored; now refused, with the accepted set named so it is fixable in place.
- `color = 12345` reached the generated pointer verbatim; now refused.
- A typo'd key vanished; now refused by name, with the accepted key set listed. Deriving that set
  from the model is what keeps this forward-compatible — leniency was never what bought it.
- `responsibilities = ["$(*self)", …]` wrote the literal token into frontmatter and the rendered
  body — the idiom the scaffold teaches. It now spreads the bundled list, for a catalogued role
  and for a generated `<tech>-dev` role alike, and dangles (refuses) on a brand-new slug, which
  has no bundled list to append to.
- A `slug` key disagreeing with the filename was silently ignored; now refused, since the
  filename is canonical and the document has no other way to say what it meant.

**One adjacent fix.** `sq role <slug> show` caught `SquadsError` around `resolve_role` and fell
back to the stored item's fields. That fallback exists for a slug the bundled catalog does not
know, and it was also swallowing an invalid override — the refusal disappeared and the card
rendered as though the broken override were not there. Narrowed to `RoleNotFoundError` on both
the table and `--json` branches.

Table-driven over the whole `RoleSpec` field set, with a test asserting the table covers every
declared field so a field added later must gain a row.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — A declared type whose name matches a bundled alias runs the wrong command

<!-- sq:finding:F5:body -->
Fixed. Two mechanisms, both closed.

Loader: RESERVED_CLI_ALIASES (_workflow/_models.py) is a new hand-maintained alias -> owning-type table covering the ten strings the import-time loop binds at the root. _check_item_refs now refuses a declared type NAMED after one, and an alias claimed by a type other than the one that owns it in that table. A type declaring its own bundled alias (feature -> feat) is unaffected, so the bundled spec and any override restating it still load.

Dispatch: _CustomTypeGroup.get_command and _CustomCreateGroup.get_command consult common.static_alias_is_stale first. An alias whose owner type still exists but no longer declares it stops serving the owner command tree and dispatches instead into a refusal command that names the alias the owner declares now and exits 1. A refusal COMMAND rather than None because Typer builds its did-you-mean from the raw registered table (self.commands, not list_commands), so returning None suggested the exact stale string the user typed. Its own --help is retired so every route produces the refusal.

Deliberately excluded: a DROPPED owner type. Its aliases keep dispatching into the canonical membership gate, whose "unknown item type bug" is the one refusal that names the type rather than whichever alias was typed - that contract has its own tests and is unchanged.

Also fixed alongside: sq create <new-alias> could never reach a statically-registered type, so a rename left sq ft working but sq create ft not.

Tests: tests/cli/test_bundled_type_aliases_route_by_the_active_spec.py (all ten aliases parametrized in both directions, plus an unmodified-squad control). Guard: tests/meta/test_reserved_cli_aliases_matches_the_bundled_alias_table.py pins the table against the bundled spec declarations AND the live root/create command tables, both directions. Falsified: disabling either loader clause or the dispatch check reddens the module.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Generated agent text instructs --assignee qa on a minimal roster

<!-- sq:finding:F6:body -->
Fixed.

**Driven, before.** `agents/squads_skill.md.j2` and `agents_md/agents_section.md.j2` both wrote
`--assignee qa` as a literal. Rendering either against a roster carrying no `qa` role — the
`sq init --roles minimal` shape — still produced that line, so the generated skill handed an
agent a command that exits 1 with an unknown-slug error.

**Fix.** `_interactions.example_assignee_slug(roles)`, registered as a Jinja global and called
from both templates. It reads the live roster the backends already thread into those renders
(the seam the finding named as present-and-unused): a `<tech>-dev` slug first — implementation
work is what gets assigned — then the first roster entry, degrading to the `<slug>` placeholder
the surrounding block already uses when the roster is empty or absent.

**After.** The pinned-roster golden now reads `--assignee python-dev`; rendered against a roster
of `crew-lead`/`rust-dev` it reads `--assignee rust-dev`. No bundled slug survives either.

**Guard.** `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` renders every
agent-facing surface against two probe rosters — one carrying no bundled slug at all, one
carrying the bundled authoring slugs plus a non-bundled developer — and asserts the literal
`--assignee qa` appears in neither. A floor test asserts the probe actually renders its own
vocabulary, so the scan cannot pass on an empty render.

**Falsification.** Restoring the `--assignee qa` literal reddens 3 of the guard's cases;
reverted by exact reverse substitution and re-verified green.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-08-15T14:07:34Z] Elias Python:
  - Fixed: `_interactions.example_assignee_slug(roles)` as a Jinja global, called from `agents/squads_skill.md.j2` and `agents_md/agents_section.md.j2`; guarded by `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py`.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — The operator personal name and this repo ship in bundled templates

<!-- sq:finding:F7:body -->
Fixed — the template half had already landed; this closes it with the guard that keeps it closed.

**Read, not assumed.** Every site the finding names is already on the placeholder convention:
`agents/greeting_skill.md.j2:27,37` and `claude/claude_section.md.j2:50` read `Alice`, and the
worked greeting describes a fictional payments API rather than squads itself. `git log -p` on
those two files attributes it to the commit that took the operator name out of shipped source,
which also fixed all six CLI-help sites the finding lists (`_cli/_operator.py`, `_cli/_memory.py`,
`_cli/_main.py`, `_services/_roster.py`, `_util.py`). A grep for the operator's name and slug
across `src/`, `docs/`, `README.md` and `PYPI.md` returns nothing.

The only remaining hits in the repo are outside this finding's scope and correct where they are:
`clients/vscode/package.json`'s `author` field (real package metadata) and the VS Code client's
own test fixtures (test data, not shipped package data).

**What this adds.** The reason the leak survived so long is that nothing checked, so the fix is
the check: `tests/meta/test_bundled_templates_carry_no_operator_identity.py`.

- It reads THIS squad's own operator roster off `squads/operators/*.md` and asserts no bundled
  template names any of those identities — full name, `op-` slug, or a name part on its own. It
  is derived, not a literal list, so an operator registered later is covered with no edit here.
  A floor test asserts the roster is non-empty, so the scan cannot pass vacuously.
- A second test asserts the greeting skill's blockquote example never names squads itself: that
  block describes the project the adopter's agents work on, and naming our own product there
  tells them their repo is squads.
- Deliberately NOT scanned: the bundled agent roster names (Robert Architect, Mara Tester, …).
  Those are squads' own shipped roles, which an adopter's squad really does get, so naming them
  in a tone-matching example is accurate rather than a leak.

**Falsification.** Planting `Good morning, Pierre!` back into the greeting template reddens the
scan with the exact file:line and token; reverted by exact reverse substitution, file verified
byte-identical, green again.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-08-15T14:07:40Z] Elias Python:
  - Verified already fixed at 8473abf (read, not assumed) across templates and all six CLI-help sites; closed with the guard that keeps it closed — `tests/meta/test_bundled_templates_carry_no_operator_identity.py`, which derives the forbidden identities from this squad own operator roster.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Generated text instructs status Cancelled and --story US1 under an override

<!-- sq:finding:F8:body -->
Fixed, in both halves.

**The status half.** `workflow_static.md.j2` named `Cancelled` in the Remove-vs-Cancel table
and in its runnable `sq <type> <n> status Cancelled` block, and `Superseded` in the ref-kind
table's `supersedes` row. Both are now spec-derived, and the surrounding narrative is untouched
— only the vocabulary token moves, which keeps the FEAT-211 ruling (this file's narrative stays
static) intact while the command stops exiting 1. Two new `WorkflowSpec` accessors:

- `first_dropped_status(item_type)` — the first settled status of that type's lifecycle that is
  **off the spine**. The spine is the happy path, so its own terminal (`Done`/`Accepted`/
  `Published`) is excluded by construction and what is left is the abandonment branch. Walked in
  `lifecycle_states_in_order` so generated text stays byte-stable. Bundled: `Cancelled`.
- `statuses_with_role(role_name)` — the read counterpart to `status_role`, so "which status
  means superseded here" resolves through the declared status ROLE the engine itself keys on
  (`_services/_validators.py`'s supersedes rule reads exactly that role), not the status name.

The prose keeps its wording and falls back to a description (`<dropped-status>`, "the superseded
state") when a spec declares no such status at all.

**The story-prefix half.** `claude_section.md.j2`, `workflow.md.j2` and `squads_skill.md.j2` all
wrote `US`. The correct value was one attribute away, but on a different object than it looked:
the `--story` local id belongs to the PARENT type's sub-entity kind (that is what
`maps_parent_story` maps into), so it now reads `spec.subentity_kinds[parent_kind].local_prefix`
and the whole `--story` fragment is omitted when the parent hosts no kind. The squads skill's
search-region example (`story:US<n>`) is built from the first declared kind and its own prefix.

**After, driven.** Rendered against a spec declaring `local_prefix = "SR"` and a lifecycle whose
retired/superseded states are `Abandoned`/`Retired`, the generated text reads `--story SRn`,
`status Abandoned` and `Retired`. No bundled literal survives.

**Guard.** The same probe in `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py`
scans for `status Cancelled`, `Superseded`, `US<n>` and `USn` across every generated surface.

**Falsification.** Restoring each literal separately (the status command, the superseded row,
the story prefix) reddened 2–3 guard cases each; every one reverted by exact reverse
substitution and re-verified green.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-08-15T14:07:35Z] Elias Python:
  - Fixed: `WorkflowSpec.first_dropped_status`/`statuses_with_role` behind `workflow_static.md.j2`, and the `--story` prefix read off the PARENT type sub-entity kind in `claude_section.md.j2`/`workflow.md.j2`/`squads_skill.md.j2`. Narrative prose untouched per the FEAT-211 ruling — only the vocabulary token moves.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — A role override title never reaches the index, so the roster renders stale

<!-- sq:finding:F9:body -->
Fixed.

**Driven again before touching anything.** A `title = "Chief Code Inspector"` override under
`<squad-dir>/.overrides/roles/reviewer.toml`, then `sq sync`: the role item's frontmatter read
`title: Chief Code Inspector` while `.squads.json` still carried `code reviewer`, and both
`CLAUDE.md` and `AGENTS.md` rendered the bundled value. `sq check` said `✓ no issues`.

**Fix.** `_services/_maintenance.py::_refresh_catalog_extra` now performs its frontmatter write
inside `self.store.transaction()` and commits the merged item with `db.add(item)` — markdown
first, index commit last, so an interrupted refresh leaves the sanctioned one-sided skew
`sq repair` heals. One sync now moves frontmatter, index and both compiled rosters together.

**What was kept, and why.** `_itemfile.PERMITTED_EXTRA_SKEW` still exempts the catalog keys.
The exemption's stated reason (this writer never opens a transaction) is no longer true and the
prose says so; it is retained for the case it still covers — a squad last synced by an older
release has an index that already lags on those keys, and comparing them would refuse the very
sync that converges it. `extra.skills` keeps the original, structural reason: it is genuinely
never mirrored.

**Falsification.** Removed the transaction wrapper and the `db.add`: 7 red across the three
integration cases, the meta guard and all three skew-guard cases. Restored by exact reverse
substitution.

**Tests.** `tests/integration/test_a_role_override_title_reaches_every_generated_roster.py` —
the override reaches index + frontmatter + both backends on one sync; a following `sq repair`
now changes nothing and the sync after it is a byte no-op on the generated files (the old tell);
a second override edit propagates on the very next sync.
`tests/meta/test_a_frontmatter_write_is_mirrored_into_the_index.py` — AST guard: a `_services`
function calling `update_frontmatter` either opens a transaction, takes an open `db`, or is
named in a short allowlist with its reason (one entry: the resolved-skills cache), plus a
staleness check on the allowlist itself.
`tests/service/test_frontmatter_skew_guard.py` — the two cases that asserted "the index copy
still lags, by design" now assert the two sides agree; a new case pins the retained exemption
from the lagging side only (index popped, no sync in between): the mutation must not refuse and
the next sync must converge rather than skip-report.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — sq sync never seeds bundled skills, leaving an unindexed skill file

<!-- sq:finding:F10:body -->
Fixed.

**Driven again.** Init with a `[selected]` workflow override dropping `guide`, then remove the
override and `sq sync`: `squads/agents/skills/sq-guide.md` written with no frontmatter,
`sq list --type skill -a` showing 9, `sq skill sq-guide show` exit 1, `sq check` clean, and
neither a repeated sync nor `sq repair` healing it.

**Fix, two parts.**

1. `sync()` now calls `seed_bundled_skills()` alongside `seed_custom_skills()`, in the same
   order `init`/`adopt` use. Both seeders skip a slug whose convention-named file already
   exists, so this is idempotent and allocates nothing on a healthy squad. This is also what
   removes the latent upgrade cost: a future release adding a bundled type no longer owes a
   hand-written migration to stamp its skill.
2. New `_unindexed_skill_bodies()`, reported by `sync` after both seeders have run: one line
   per slug-named body left under the skills folder with no `SKILL` item, naming the file and
   why `sq repair` cannot recover it. That covers the *class* — a body whose slug no seeding
   vocabulary claims — not just the slugs a vocabulary happens to name.

**The exemption: bounded, then deliberately not.** I tried two bounds on
`_is_legacy_skill_body` (schema-era, then "any stamped sibling on disk") and both are wrong,
for the same reason: `init`'s internal `_skip_skill_seed` hook *manufactures the defect shape
on purpose* — bodies written, ids deliberately not stamped, to hold the global counter still
for the test corpus — so every discriminator that reports the defect also reports that hook's
output. The second bound turned 16 service tests and the `check` JSON golden red, and the
golden's own fixture is the proof: `init --no-seed-skills` plus a hand-authored `sq skill add`
gives a folder with stamped and unstamped siblings side by side.

So the report moved to where the file is *produced* rather than where it is later found —
`sync` knows it just wrote the body and just ran both seeders, which `check` cannot know. The
exemption's docstring now states its real width, says narrowing was tried and why it is not
available, and points at the sync-side report. Retiring `_skip_skill_seed` would make the
narrow bound available; that is a test-suite-wide change (every id assertion shifts) and well
outside this subtask.

**Falsification.** Two breaks. Dropping `seed_bundled_skills()` from `sync`: the meta guard and
the restored-type case go red. Discarding `_unindexed_skill_bodies()`'s return instead of
appending it: the residue case goes red. Both restored by exact reverse substitution.

**Tests.**
`tests/integration/test_a_skill_body_appearing_after_init_is_seeded_by_the_next_sync.py` — the
drop-then-restore repro end to end (asserting the end state, not the mechanism: an indexed,
convention-named body the generated pointer references), seeding idempotency including the
counter, and the unclaimed-slug residue reported by sync while `check` stays quiet as
documented. Setup is proved eagerly (`open_service`, not a bare `Service`, or the override is
invisible and the test passes for the wrong reason).
`tests/meta/test_every_skill_seeding_entry_point_seeds_bundled_and_custom.py` — the existing
init/adopt guard widened to `sync` rather than a second guard beside it (renamed accordingly).
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — A malformed override escapes as a raw traceback out of workflow lint

<!-- sq:finding:F11:body -->
Fixed. A malformed override shape is a lint finding at every section and nesting position, never
a traceback.

**The mechanism.** `_build_spec` walked the merged mapping assuming every section, entry and
inline array was the shape the grammar declares. TOML happily produces otherwise, and the walk
then called `.items()`/`.get()` on a `str` — escaping as a raw `AttributeError`/`TypeError` with
internal file paths, out of `sq list`, `sq check` and `sq workflow lint` alike. Three shape
guards now front every walk: `_as_table` (a section or entry), `_as_entry_list` (an inline array
of tables, including its elements), and `_section` composing the two. `_parse_lifecycle` hands
the raw table straight to `model_validate` instead of reading `initial` out first, which is what
turned an absent `initial` into a bare `KeyError`.

**Why the array guard matters even though a string does not crash.** A string is iterable, so
`fields = "oops"` did not raise — it validated `"o"` as a field and reported `field[0]`, an index
into a value with no elements. That is a refusal, so "did not raise" cannot tell the two apart;
the guard names the container and the shape it should have and never invents an element index.
The test asserts exactly that, because the weaker assertion did not redden under falsification.

Driven: 24 shapes across every section (`items`, `statuses`, `lifecycles`, `collections`,
`subentity_kinds`, `roles`) and every nesting position (section, entry, inline array, array
element), each valid TOML and each verified to parse before use. All 24 now reach the reporting
path through `sq workflow lint` and refuse cleanly through `sq list`; zero produce a traceback.
The finding names the offending path (`items.task`, not `items`).
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Renaming a sub-entity plural bricks add-kind on the existing corpus

<!-- sq:finding:F12:body -->
Fixed, both halves.

**The alignment guard.** `subentity_kinds.<kind>.plural` is the persisted container-marker name,
which makes it a corpus-alignment field exactly like a type's `prefix` or `folder`. Unlike those
two it leaves **no witness in the index** — nothing stored says which plural a file was written
under — so the loader's live-index cross-check cannot see it and `sq workflow lint`, which never
opens an item file, has no way to. That is why the guard could not go where the other three are.
`sq check` does hold each item's on-disk text, so a new per-item validator
(`subentity_container_marker`, error level, in the `work` bundle) checks that an item whose type
hosts a kind carries that kind's declared container marker.

It names the tag the file *does* carry, derived rather than matched against declared plurals: a
container is the only top-level marker that is not one of the three fixed structural tags and not
a sub-entity block tag (those carry a colon). Matching against the declared set would have missed
the reported direction, where the old name is no longer declared anywhere.

Driven, both directions and a control: declaring `plural = "outcomes"` over an existing corpus
now exits 3 naming the item, the declared plural and the `'stories'` the file carries; creating
under the declaration and then *removing* the override reports the mirror case (lint has no file
to judge and correctly says nothing); a squad that declared the plural before creating anything
is silent. The half-broken state is pinned too — `add-story` fails while `show` still succeeds,
which is why nothing else noticed.

**The heading.** `_BUNDLED_CONTAINER_HEADINGS` was keyed by kind *code*, so it outranked the
declared plural for the three bundled kinds and rendered `## User Stories` above `sq:outcomes` —
contradicting its own docstring. The table is now keyed by kind and paired with the plural the
irregular wording belongs to, so the bundled wording applies only while the kind still carries
its bundled plural; anything else falls back to the declared plural title-cased. A `tests/meta`
guard keeps the pairing true against `workflow.toml`, so a bundled plural moved without its
heading following reddens rather than silently re-opening the gap for every squad.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — A misspelled [selected] keep-entry silently drops the key it meant to keep

<!-- sq:finding:F13:body -->
Fixed. A `[selected]` keep-list entry that names no key of its section fails closed.

**The mechanism.** `apply_selected` validated section *names* against a closed set and never the
list's *contents*, so `selected.items = [… "guied"]` passed every shape check, dropped `guide`,
and left a spec that is perfectly valid. That is the deselect's one unbacked failure mode: the
floor, the referential checks and the live-index cross-check all inspect the spec that
*resulted*, never the one that was asked for, so nothing downstream could ever report it —
`sq workflow lint` said "workflow spec OK — no errors or warnings" with the key gone.

`_selected_entry_violations` applies the argument the module already makes one level up at
`_validate_selected_shape` ("a shape mismatch must never reach `set(keep)` unchecked … fail
closed instead") to the list's contents, reusing `_unknown_key_violations` so the violation names
the entry and lists the section's real keys. Entries are checked against the *merged* mapping, so
adding a type and keeping it in one document still works — only a name matching nothing is
refused.

Driven: the exact reported case now reports `selected.items.guied` / "unknown items key 'guied'"
with the ten real keys in the fix hint, at exit 1. The add-and-keep control still passes.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — The create-lane advisory contradicts the tools own generated instructions

<!-- sq:finding:F14:body -->
Fixed, by moving the lane into the playbook document as a declaration.

**The shape of the fix.** `RoleGuideSpec` gains `authors: bool = False`. A guide that declares
it is the in-lane author of the type it hangs under; that is the sole source of the create-lane.
The bundled `playbook.toml` declares it on the eight authoring guides, reproducing the product
table exactly, so nothing about the bundled behaviour changes.

A DECLARED flag rather than a prose scan of `sq create <type>` in the guide's `do` bullets, and
the choice matters. ADR-163 section 2 offered the scan as its primary mechanism and the map only
as a fallback, but the scan does not actually reproduce the table: the create verb for a type is
not always written in that type's own section (the reviewer's `sq create review` lives in the
task playbook), and `tech-writer`'s guide on `guide` carries no create verb at all while the
product table puts it in that lane. So the scan would have silently dropped a lane. It is also
the exact anti-pattern this sweep is about — a naming convention standing in for a declaration.

**What the fix removes.**

- `CREATE_LANES` (the hand-maintained second source) and `LANED_TYPES` (a `frozenset` computed
  at import off the bundled document) are gone, replaced by `create_lanes(playbook)` and
  `laned_types(playbook)` computed per call from the ACTIVE, merged playbook.
- `is_lane_exempt` no longer names `manager`. It takes the squad's own `is_default` role slug,
  which `ServiceCore._default_role_slug(db)` reads from the live roster; with no live default it
  falls back to the role catalog's own designation. `sq role <slug> default` now moves the
  exemption with the designation.
- `_services/_base.py` passes `self.spec` AND `self.playbook` on all three lane calls; the
  reflog delta's `expected` list too. `_cli/_role.py`'s `create_lane` field threads `svc.playbook`.
- `authoring_owner` (the generated cheatsheet's "who authors what") resolves through the active
  playbook, and takes an optional live slug->title map consulted only when the catalog has no
  entry — so a role declared solely in `.overrides/roles/` gets its authoring bullet instead of
  the type silently losing one. The catalog stays first because its titles are the lower-case
  sentence forms that prose is written around. Both backends and `sq workflow` thread the
  playbook into their renders.

**Driven, after** (`tests/integration/test_an_override_declared_authoring_role_is_in_lane.py`,
8 cases): an override adding a `devops` guide on `bug` with `authors = true` makes
`sq create bug --author devops` in-lane at the service layer AND at the CLI, while the same
guide WITHOUT the flag still warns — so it is the declaration doing the work, not the guide's
presence. The generated `sq-bug` skill carries that guide's create instruction and the tool no
longer contradicts it. A project-declared type (`incident`, added by a workflow override) is now
lane-checked once a guide declares an author for it, and correctly not lane-checked when none
does — the second half of the finding, where the import-time frozenset made lane discipline go
dark for every adopter-declared type.

**AC-B5 is honoured again rather than pinned to a literal.** The unit test now asserts the
derived lanes equal the set of `authors` guides in the document, in BOTH directions, plus that a
role which only reads a type is not in its lane. A guide gaining or losing the flag can no longer
pass silently.

**Falsification.** Four breaks, each reverted by exact reverse substitution: reverting
`laned_types` to the bundled playbook reddens the project-declared-type case; dropping the
playbook argument from `allowed_create_types` reddens 4 integration cases; ignoring the `authors`
flag reddens 9 unit cases; restoring the hardcoded `manager` exemption reddens the
designation-follows case. All four went red, all four restored green.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-08-15T14:07:38Z] Elias Python:
  - Fixed: the create-lane is now a declared `authors` flag on a playbook role guide, derived per call from the ACTIVE merged playbook. `CREATE_LANES` and `LANED_TYPES` deleted; `is_lane_exempt` follows the squad default-role designation. End-to-end guard: `tests/integration/test_an_override_declared_authoring_role_is_in_lane.py`.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Sub-entity field flags are baked from the bundled spec on registration

<!-- sq:finding:F15:body -->
Fixed. The rebuild trigger was the kind NAME; it is now the kind SIGNATURE.

_cli/_items.py::_kind_signature returns everything _register_subentity bakes into the generated commands: kind name, plural (the list verb), maps_parent_story (the --story options), and every declared field code/label/collection/required/default (the --<field-code> options, their help, and the omitted-flag fallback). _dynamic_subentity_group_cls compares the live signature against the bundled one and serves from a freshly-built app whenever they differ, falling through to the static tree otherwise - so an unchanged squad takes the identical path it always did, and a renamed kind keeps its old verbs reachable for the accurate refusal.

Service half: SubentitiesMixin._checked_field_values gates the generic fields= map on both doors (add_block and update_block) through the item axis mechanism (_badge_field + _parse_badge_code), so an undeclared code is refused by name with the declared codes listed, and a declared code is validated against its bound collection. add_finding no longer falls back to a hardcoded severity when the kind declares none - that literal was itself the undeclared write; it now omits the field, and an explicit severity= on such a spec is refused by the gate.

Driven after the fix on a spec whose finding kind declares only a required impact: --help offers --impact and not --severity, --severity exits 2, a plain add-finding applies impact=medium, the badges map is populated, the findings table headers Impact, and the sq-rendered body hint (--impact medium) is a flag the CLI now accepts.

Tests: tests/cli/test_subentity_field_flags_follow_the_active_spec.py, including a plain-squad control. Falsified: reverting the trigger to the name comparison reddens six of them; disabling the service gate reddens the service test.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — The load boundary skips every adopter-declared badge field

<!-- sq:finding:F16:body -->
Fixed, both halves — one mechanism: declared vocabulary validated against the scope that
declares it, not against a global set.

**The badge half.** `_check_field_codes` read a stored value with `getattr(obj, f.code, None)`,
which sees only codes that happen to be real model attributes (`priority`, `severity`) and
silently skips every adopter-declared one, whose value lives in the generic `extra` store. Now
`obj.badge_value(f.code)` — the accessor both `Item` and `SubEntity` carry, and the one
`_workflow/_loader._badge_field_mismatches` already used, so the load boundary and the live-index
cross-check finally see the same set of values.

Driven as the reported asymmetry: with an override-declared `impact` collection and
`extra.impact = "high"` stored, shrinking that collection used to leave `sq list -a` at exit 0
forever; it now exits 1 naming the item and the field, identically to shrinking the bundled
`priority` collection. A `tests/meta` scan forbids the returning shape — a `getattr` whose
attribute argument is a field's own `.code` — with a liveness half that plants the shape and a
behavioural half pinning that `badge_value` really reads both stores.

**The status half (the lint-only gap ST7 named).** `_collect_type_status_errors` judged an
entity's status against the flat, spec-wide `spec.statuses` set, so an item or sub-entity parked
on a state its own machine cannot reach passed lint clean while `sq check` — which has always
asked per lifecycle — called the same item an error.

Split into two named collectors rather than tightened in place, and the split is the point.
`_collect_type_status_errors` keeps the flat set and stays **fail-closed**: it asks whether the
merged spec can still *read* this corpus, and a status declared nowhere leaves the item
unreadable. `_collect_unreachable_status_errors` is new, **lint-only, and a report**: the remedy
for an unreachable status is a per-item `sq <type> <n> status <declared> --force`, which is only
reachable while commands still run — making it a fifth fail-closed clause would have left the
item unfixable from inside `sq`. (An earlier revision did exactly that and had to remove the
override to repair the item; that is the trap this avoids.) The fail-closed families refuse for
the opposite reason: a dropped type, a re-prefixed folder or a stranded badge code leave the
corpus genuinely unreadable and no per-item verb fixes them.

Driven: a subtask at `Todo` under an override binding `subtask` to a machine without it is now
reported by `sq workflow lint` (exit 1, naming the item and the lifecycle) and by `sq check`
(exit 3) — the two gates agree — while `sq list -a` still exits 0 and the `--force` move clears
both.

**One deliberate non-change, flagged rather than silently left.** `sq workflow lint` stays quiet
about the *badge* case above, because `_code_removed_by_override` attributes a stale code to the
override per value, and an adopter-declared collection has no bundled counterpart to compare
against. Widening it would assert a cause that check cannot establish — precisely what its own
docstring forbids — and the condition is already reported loudly at exit 1 by the load boundary
and by `sq check`, with a message that stays true whatever the cause. Worth a second opinion, not
worth guessing at.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — A migration writes legacy sub-entity statuses with no mapping to the spec

<!-- sq:finding:F17:body -->
**Corrected — the original F17 premise was partly wrong, and I built to it.**

F17 as filed said both `sq check` and `sq workflow lint` were silent on a carried-forward status
the active lifecycle can't reach. The reviewer (F34) showed `_services/_validators.py::
_subentity_status_valid` already runs the identical predicate against the same active spec and
`sq check` exits non-zero naming it — that validator predates this task. Only `sq workflow lint`
was actually silent (real, and routed to ST2's per-kind-lifecycle work, not this one).

I built a runner-side duplicate of a check that already existed and reports strictly better
(item-scoped error + non-zero exit, vs. prose in a discussion) — while genuinely breaking this
runner's frozen-snapshot contract: the report landed in the same durable `.md` the runner writes,
so two byte-identical 0.2 corpora differing only in `.overrides/workflow.toml` migrated to
different committed files.

**Reverted** in `_migrations/_v0_2_to_v0_3.py`: dropped the `load_workflow_spec` import,
`_load_active_spec`, `_unreachable_status`, the threaded `spec` parameter, the discussion-comment
write, and the docstring paragraph describing them. The runner is back to carrying the frozen
legacy status forward with no spec read of any kind, matching every other runner in the package.

**Kept**: the `MANUAL` runbook entry, reworded to point at `sq check` (which already reports the
mismatch) instead of at a `migration:` comment the runner no longer writes.

Test: `test_v0_2_to_v0_3_carries_forward_a_status_the_active_override_cant_reach` now asserts the
runner stays silent (no discussion comment) and that `sq check` is the one that reports it,
non-zero exit, naming the item and the bad status.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-08-06T19:42:20Z] Paul Reviewer:
  - Reviewed at b870482. The fix works as built: drove sq migrate up end-to-end on a 0.2-stamped squad with a stamped lifecycle override — status carried forward unchanged, dated migration: comment landed in the item discussion, chlog renders the new MANUAL. Falsified (disabled the report block, test red on the discussion assert).
  - But the premise is wrong and this should not ship as built — see F34: sq check already reports the same thing with the same predicate against the same active spec (validators._subentity_status_valid), and it predates the finding. Recommend reverting the runner spec read, keeping the MANUAL entry repointed at sq check. F35 and F37 are consequences of keeping it.
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — Migrations persist a derivable path key that then goes stale

<!-- sq:finding:F18:body -->
**Fixed** in both runners. Updated below to correct an overstatement the reviewer caught (F36)
and to reflect the follow-up fix (F33).

`_v0_4_to_v0_5.py:161` and `_v0_8_to_v0_10.py:149` (the rename branch, both runners): stopped
writing `fm["path"]` at all — `fm.pop("path", None)`, stripping a stale copy carried over from an
earlier partially-migrated file. The value was already computed locally as `squad_rel` for the
pointer rewrite immediately below; frontmatter never needed it.

`_v0_4_to_v0_5.py`'s `_backfill_description` (the secondary half, the only one of the two runners
with this branch): stopped reading `cfm.get("path", "")` as the pointer-target source. It now
derives the target from the file's own location via `_posix_rel(convention_path, paths.squad_dir)`
— `.relative_to(...).as_posix()`, not bare `str(...)`, after F33 caught the OS-separator
regression the first version of this fix introduced. The `.claude` pointer rewrite is
unconditional now, not gated on a frontmatter key that's absent on every current build.

**Correction (F36):** the original version of this fix only reached the rename branch — an
already-migrated corpus (convention-named, description already present) took the early-return
no-op path and kept a stale `path` key forever. `_backfill_description` now also checks for a
stale `path` key and strips it even when the description is already populated, so this branch
heals existing corpora too, not just prevents new ones.

Tests: `path` absence on both runners' `test_migration_renames_an_already_stamped_but_still_slug_named_file`;
`test_description_backfill_still_rewrites_the_pointer_with_no_path_frontmatter_key` for the pointer
target; `test_backfill_strips_a_stale_path_key_even_with_a_description_already_present` for the
F36 fix; `test_posix_rel_normalizes_windows_style_separators_on_any_host` for the F33 fix (pinned
against `PureWindowsPath`, so it fails on Linux CI too on a regression). All falsified red
pre-fix, green post-fix.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-08-06T19:42:23Z] Paul Reviewer:
  - Reviewed at b870482 — both halves verified driven. Premise confirmed: a fresh build writes no path frontmatter key anywhere, and injecting one then running sq migrate repad 8 renames the file while the key still names the old filename, with sq check exiting 0.
  - Falsified both: restoring the write reddens the path-absence assert on both runners; restoring the path-keyed pointer target reddens the new backfill test on STALE still present, confirming the pointer rewrite now actually fires.
  - Two follow-ups before this closes: F33 (the derived pointer target uses the OS separator — certain Windows CI failure) and F36 (the strip never reaches an already-migrated corpus, so the "actively strips" claim overstates the reach).
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — The scaffolded workflow override example fails on a retired key

<!-- sq:finding:F19:body -->
Fixed. The scaffolded workflow override activates as written, and the example now demonstrates
the field that replaced the retired one.

**The mechanism.** `_WORKFLOW_SCAFFOLD_BODY` declared `terminal = false/true` on three statuses,
a key `StatusSpec` no longer has under `extra="forbid"`, so following the file's own "uncomment
and edit to activate" failed closed with a raw pydantic dump. The three lines now declare
`role = "pending"/"active"/"done"` with a one-line note each, and the rules block above gains a
short paragraph naming the eight built-in roles, `sq workflow roles`, and the fallback. Dropping
the retired key alone would have left the example silent about the axis that actually drives
status behaviour — settled, hidden, colour, live all resolve through `role`.

**The durable half is the guard.** `tests/meta` now activates every scaffold body (workflow,
playbook, new-role, both `can_spawn` emissions) by stripping the comment prefix inside its worked
example and runs it through the real loader for its document. A retired or renamed model field
now reddens there instead of in an adopter's terminal. A second test drives the round trip
through the CLI — `sq override scaffold workflow`, uncomment, `sq workflow lint` clean,
`sq create incident` succeeds — because the models loading is necessary and not sufficient: the
file also has to be reachable through the verbs and the type it declares has to work afterwards.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->

<!-- sq:finding:F20 -->
### F20 — Priority flag validates against the wrong collection, both ways

<!-- sq:finding:F20:body -->
Fixed. The CLI stopped pre-parsing --priority against a collection name.

On create and update the CLI validated with parse_badge_code("priority", value) - a third door into an axis the service already gates. ServiceCore._check_priority resolves the field on the item type and validates against its BOUND collection, so the CLI now hands the raw value straight through and that one gate owns the answer. Help text on both commands resolves through the new strict badges.declared_collection.

The list/tree filter is a genuinely different door: it spans every type, so no single bound collection is the authority. common.parse_filter_badge_code accepts any code any declared type binds to the field (badges.field_badge_codes). For the bundled spec that union is exactly the priority collection, so both the accepted values and the refusal text are byte-identical.

Driven after the fix on task -> tshirt (s|m|l): help says s|m|l, create/update accept m and refuse high naming s, m, l; list --priority l finds the task and --priority high still finds a bundled-priority bug through the same flag; --priority enormous refuses listing the union.

Tests: tests/cli/test_priority_flag_follows_the_types_declared_field.py. Falsified: restoring the pre-parse on create, on update, or narrowing the filter to the same-named collection reddens the matching test.
<!-- sq:finding:F20:body:end -->

#### Discussion

<!-- sq:finding:F20:discussion -->
<!-- sq:finding:F20:discussion:end -->
<!-- sq:finding:F20:end -->

<!-- sq:finding:F21 -->
### F21 — Priority flag is advertised on types declaring no priority field

<!-- sq:finding:F21:body -->
Fixed. badges.resolve_collection kept its rendering fallback and gained a strict sibling.

The fallback (undeclared field -> the field code as a collection code) is load-bearing for RENDERING a value that is already stored after its field is dropped or renamed, so it stays - now documented as rendering-only. Deciding whether a surface is offered or a value is accepted goes through badges.declared_collection, which returns None instead.

Both --priority help builders resolve strictly, so a type declaring no priority field enumerates nothing; and the spec_aware_command_cls refresh hook now also HIDES --priority (and --no-priority on update) on such a type. Hidden rather than removed, so the flag still parses and the service gate keeps owning the accurate refusal ("priority is not a settable field on a incident; valid: urgency") instead of Click reporting an unknown option.

Driven after the fix on a custom incident declaring only urgency: neither create --help nor update --help mentions --priority; passing it still produces the service refusal naming urgency. Control: task still advertises urgent|high|medium|low on both.

Tests: same module as F20. Guard: the widened tests/meta field-code scan now covers _cli/ and lists the two --priority sites as sanctioned with a reason, plus a no-stale-entry test so the exemption cannot outlive them. Falsified: making the advertisement unconditional reddens the test.
<!-- sq:finding:F21:body:end -->

#### Discussion

<!-- sq:finding:F21:discussion -->
<!-- sq:finding:F21:discussion:end -->
<!-- sq:finding:F21:end -->

<!-- sq:finding:F22 -->
### F22 — The client id regex breaks any hyphenated declared prefix

<!-- sq:finding:F22:body -->
Fixed.

The id grammar now comes from the squad's declared prefixes instead of a shape the
client invented. `clients/vscode/src/domain/itemIdPattern.ts` (new) builds an
`ItemIdMatcher` from `sq workflow types --json`'s `prefix` column — the field the client
already fetched, shape-guarded and never read — and `domain/markdown.ts` threads it
through every render the way it already threads the role directory. The preview manager
fetches the type catalog alongside its other parallel fetches and degrades to the generic
uppercase grammar when that fetch fails, so a no-catalog render still linkifies a
conventional id.

Two grammar changes beyond "read the prefix":

- An id token is bounded by "no word character or hyphen on either side" rather than
  `\b`. That is what stops a declared prefix from matching as the tail of a longer one —
  the mechanism behind the reported mangling — and it is applied to the fallback grammar
  too, so an unrecognised hyphenated id renders as plain text instead of an affirmatively
  broken link into its own tail.
- Prefixes are escaped and sorted longest-first, so a prefix carrying a regex
  metacharacter matches itself and an alternation never settles for a shorter sibling.

Driven against a real squad, not a fixture: a `.overrides/workflow.toml` declaring
`prefix = "MY-WIDGET"` passes `workflow lint`, `sq create` mints `MY-WIDGET-2`, and that
squad's live `sq workflow types --json` fed through the production functions gives
`see MY-[WIDGET-2]` (broken link, nonexistent target) on the old grammar versus a single
`data-item-id="MY-WIDGET-2"` anchor on the new one; in link position the old pattern
dropped the anchor and the new one keeps it.

Falsified: making `buildItemIdMatcher` ignore its catalog turns 27 tests red across
`test/itemIdPattern.test.ts` and `test/markdown.test.ts`, green again on restore.

Tests are table-driven over the prefix shapes an adopter can actually declare —
hyphenated, underscored, single-character, lowercase, mixed-case, digit-bearing, and one
carrying a regex metacharacter — each in both positions (found in prose, and standing
alone as a markdown link's url), plus the not-an-id cases and the degenerate catalogs.
<!-- sq:finding:F22:body:end -->

#### Discussion

<!-- sq:finding:F22:discussion -->
<!-- sq:finding:F22:discussion:end -->
<!-- sq:finding:F22:end -->

<!-- sq:finding:F23 -->
### F23 — The preview sub-entity head hardcodes the severity field code and label

<!-- sq:finding:F23:body -->
Fixed, both halves, and verified end to end against the shipped catalog.

The head line no longer knows the name of any axis. `previewDocument.ts`'s
`buildSubEntityHeadLine` renders status, then every declared badge field the sub-entity
actually carries, then assignee and story — the badge entries coming from the payload's
own spec-resolved `badges` map (which `SqSubEntity` now models and the shape guard accepts
as optional, exactly like `discussion`) and resolved through
`badgeCatalog.ts::resolveItemBadges`, the same function the item level uses. The modelled
`severity` property and the `Severity:` literal are both gone; no label map lives in the
client.

The label comes from the chain ADR-738 documents:
`item.type` -> type row -> `subentity_kind` -> kind row -> `fields[].label`, keyed by the
code the `badges` map carries. `badgeCatalog.ts::buildSubEntityFieldBindings` performs the
join and produces the ordinary `FieldBindingsByType` shape, so `resolveItemBadges` serves
both levels unchanged; `sqAdapter.ts` gains `getSubentityKindsCatalog` plus the row guard,
and the type-row guard accepts `subentity_kind` as an optional, nullable key. `type` is
read off `sq show --json` (present in shipped payloads, driven) and guarded as optional so
its absence can never blank the preview.

Verified against the real surface, twice, once the catalog landed:

- This repo's own live payloads through the production functions — the head renders
  `Status: Open · Severity: high`, with `Severity` resolved from the kind row rather than
  written down anywhere.
- A separate squad whose override redeclares the finding kind's field as code `impact`
  label `Impact` — `sq workflow subentity-kinds --json` reports the relabelled field, the
  sub-entity's `badges` map carries `{"impact": "high"}`, and the same code path renders
  `Impact: high` with no occurrence of `Severity`. That is precisely the reproduction this
  finding described, now passing.

Raw code rather than the collection's display label is deliberate and unchanged: this head
does not fetch the collections catalog, and `resolveItemBadges` is called with the empty
vocabulary on purpose. The degrade path stands too — an `sq` that cannot serve the kind
catalog leaves the bindings empty and each badge falls back to its raw field code.

Held against drift by the skew canary (`test/canary/skewCanary.test.ts`): the live kind
catalog's row shape, the type row now carrying `subentity_kind` on every row (`null` where
a type hosts none), and the join itself — every non-null `subentity_kind` naming a kind the
kind catalog publishes. Both catalog fixtures were recaptured from live output. Falsified:
requiring one key `sq` does not emit turns those canary cases red; reinstating a `Severity:`
literal turns four unit tests red.

The type row's other new key, `lifecycle`, is deliberately left unmodelled: in this release
it is a grouping key with no published catalog to resolve against, and modelling it would
invite a resolver for a target that does not exist. Noted in `SqTypeCatalogEntry`'s doc so a
later reader does not "complete" it by accident.
<!-- sq:finding:F23:body:end -->

#### Discussion

<!-- sq:finding:F23:discussion -->
- [2026-08-03T15:37:31Z] Robert Architect:
  - The label half's surface is decided: ADR-738 §3 (`sq workflow subentity-kinds --json`, carrying `fields` as `[{code,label,collection}]` — the type row's entry shape verbatim) plus §5 (`subentity_kind` on the type row, without which the kind catalog has no join key from the item's `type`). Both are 0.13, so this finding has no residue — the code half and the label half land together.
<!-- sq:finding:F23:discussion:end -->
<!-- sq:finding:F23:end -->

<!-- sq:finding:F24 -->
### F24 — sq sync silently drops an unrecognised model from a role override

<!-- sq:finding:F24:body -->
Fixed.

**Driven again, and the reproduction has moved.** ST2's F4 fix means a role *override* naming
`claude-opus-4-5` is now refused outright at resolve time, so that exact path no longer reaches
the backend. The gap survives on every other path that sets the field: driven via
`sq dev add --tech python --model claude-opus-4-5` — frontmatter stores it,
`.claude/agents/python-dev.md` has no `model:` line at all, `sq sync` printed nothing and
`sq check` reported no issues.

**Fix.** `_backends/_claude_code/_frontmatter.py` gains `model_drop_warning(slug, model)`
beside `normalize_model`, and `generate_role_entry` returns it on the `Artifact` it already
built. `ServiceCore._project_roster_item` now returns the WARN-only notices its per-entry writes
surfaced, and `sync()` folds them into the list it already prints. Reports, refuses nothing —
the pointer still omits the line.

**On not validating twice.** Deliberately a report and not a second validator, which is what
the finding warned about: the override resolver stays the *only* refusal, so the two can never
return different verdicts on one value. The backend's `_VALID_MODELS` is left backend-local
(what this host can render) rather than merged with `_roles._loader.VALID_MODELS` (what squads
will store) — a second backend legitimately knows a different vocabulary, and the warning is
precisely what surfaces any disagreement between the two at write time. I did not add
equality-pinning between the sets; that would encode an invariant that is not true.

**Falsification.** Three breaks. Making `model_drop_warning` always return `None`: 8 red.
Computing the warning but not attaching it to the `Artifact`: 2 red. Dropping `sync`'s
collection of the per-entry warnings: 1 red. All restored by exact reverse substitution.

**Tests.** `tests/service/test_a_model_the_host_cannot_render_is_reported_not_dropped.py` —
table-driven over shape families rather than one case per branch: the four accepted names plus
`None` report nothing; a plausible near-miss, a typo, another vendor's name, a case difference
and two falsy-but-present values (`""`, `"  "` — the ones an `if model:` guard would wave
through as "nothing declared") are each both dropped and reported. Plus end-to-end through
`sq dev add` + `sync`, the upstream override refusal pinned alongside so the two verdicts stay
distinguishable, a negative case (an ordinary roster syncs with an empty report, so the warning
cannot be a constant), and the `Artifact.warning` channel asserted directly.
`tests/meta/test_a_normalizer_that_discards_a_value_is_paired_with_its_report.py` — AST guard
over the whole `_backends` tree: a function calling `normalize_model` without
`model_drop_warning` fails, plus a check that both functions still exist (otherwise deleting
the reporter would satisfy the pairing rule vacuously).

**Gap I did not close, flagged rather than fixed:** `sq dev add --model` and `sq role activate`
call `generate_role_entry` directly and discard the artifact, so the warning first appears on
the *next* `sq sync` rather than at the moment of the `add`. Wiring those two means changing
their return signatures up through the CLI; the value is durable either way and sync is the
surface the finding named.
<!-- sq:finding:F24:body:end -->

#### Discussion

<!-- sq:finding:F24:discussion -->
<!-- sq:finding:F24:discussion:end -->
<!-- sq:finding:F24:end -->

<!-- sq:finding:F25 -->
### F25 — The AGENTS.md backend parses mission back out of its own generated text

<!-- sq:finding:F25:body -->
Fixed.

**Driven again, both halves.** Relabelling `**Mission:**` to `**Purpose:**` in
`agents_md/role_entry.md.j2` and running `sq sync`: all 9 mission lines vanished from AGENTS.md,
with `sq check` clean. And `grep -c Responsibilities AGENTS.md` was 0 before the change — the
section template's responsibilities block had never rendered once, because `_read_staging_role`
returned that key as an unconditional empty list.

**Fix.** `RoleView` carries `mission: str` and `responsibilities: tuple[str, ...]`, populated in
`roster()`/`roster_all()` from the role item's own `extra`. `_read_staging_role` is deleted and
`write_managed` builds its role rows straight from the views it is handed. The staging files
stay — they are what gives `generate_role_entry` an Artifact and `remove_artifacts` something to
delete — but they are now write-only, never an input.

Not "fixed" by pinning the label, as the finding instructed. I also did **not** touch
`role_entry.md.j2`: the template tree is ST4's, and the fix does not need it. AGENTS.md's
compiled section does gain responsibilities lines — that is the dead block coming alive, from
`agents_section.md.j2`, which I did not edit either. The pinned golden renders that template
directly with empty values, so it is unaffected.

**Falsification.** Three breaks. Removing the two fields from the `roster()` construction: 2 red.
Re-introducing the re-parse (reading the staging file and splitting on `**Mission:**`): the meta
guard goes red. Deleting `responsibilities` from the `RoleView` definition: the view-completeness
guard goes red. All restored by exact reverse substitution.

**Tests.** `tests/integration/test_agents_md_backend.py` (widened in place rather than a new
file beside it) — mission *and* responsibilities compiled after sync, each responsibility
asserted against the role item's own stored list; the relabelled-staging case, which recompiles
with `refresh_managed` so the staging files are not rewritten first (rewriting them is what made
my first attempt at this test pass vacuously); and the sharpest form — `write_managed` with no
staging directory in existence at all still renders both fields.
`tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py` — AST guard: no read
call in a backend may take a path built from that backend's own staging-output constant. Scoped
by directory constant, not "no reads in backends", because two backend reads are legitimate and
must stay (merging a pre-existing `.claude/settings.json`; reading an item's durable `.md` to
preserve its frontmatter). Second test in the same file closes the other half of the loop: every
`r.<field>` the section template renders must exist on `RoleView`, so a field the view lacks
cannot send anyone off to fetch it again.
<!-- sq:finding:F25:body:end -->

#### Discussion

<!-- sq:finding:F25:discussion -->
<!-- sq:finding:F25:discussion:end -->
<!-- sq:finding:F25:end -->

<!-- sq:finding:F26 -->
### F26 — The memory skill hardcodes the squads path and ignores squad_dir

<!-- sq:finding:F26:body -->
Fixed.

`agents/memory_skill.md.j2` line 4 named `squads/agents/memory/<role>/` while `squad_dir` was
already being passed into that render and never read — the only such literal in the template
tree. Now `{{ squad_dir }}/agents/memory/<role>/`.

**Driven, after.** Rendered with `squad_dir="team"` the skill reads `team/agents/memory/<role>/`;
rendered for this repo (whose squad dir really is `squads`) it is byte-identical to before, so
no adopter on the default layout sees a change.

The `agents/memory` segment stays a literal in the template. It mirrors `MEMORY_ROOT` in
`_memory/_store.py`, which is squad-relative and fixed; spelling a squad-relative constant in a
template has the same standing as `{{ squad_dir }}/.squads.json` in the CLAUDE.md section. The
defect was the ROOT, which an adopter moves with `sq init --squad-dir`.

**Guard.** `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` renders the
memory skill with `squad_dir="team"` and asserts the string `squads/agents` does not survive,
with a floor test asserting `team/agents/memory` does.

**Falsification.** Restoring the `squads/agents/memory` literal reddened 2 guard cases; reverted
by exact reverse substitution and re-verified green.
<!-- sq:finding:F26:body:end -->

#### Discussion

<!-- sq:finding:F26:discussion -->
- [2026-08-15T14:07:37Z] Elias Python:
  - Fixed: `agents/memory_skill.md.j2` now renders `{{ squad_dir }}/agents/memory/<role>/`. Byte-identical on the default layout; correct under `sq init --squad-dir team`.
<!-- sq:finding:F26:discussion:end -->
<!-- sq:finding:F26:end -->

<!-- sq:finding:F27 -->
### F27 — search and inbox abort whole-corpus on one unreadable file

<!-- sq:finding:F27:body -->
Driven independently by two reviewers and the manager. _services/_collab.py -- both the search and inbox loops call _aio.read_text with no per-item guard, and path_exists guards a MISSING file but not an unreadable one, so the error propagates out and discards every result already accumulated from readable files. sq search exits 1 with EMPTY stdout; with --json it emits nothing at all, not even [], so a consumer gets a parse failure on top of the exit. Same for sq inbox. Meanwhile list, tree, blocked, show and graph all exit 0 with everything, so the failure looks arbitrary. The VS Code client calls search and turns any non-zero exit into a runtime error, and its per-keystroke debounce stacks a fresh error toast per resolution. TASK-674 scoped per-file degradation to check/repair/board list/memory list by name and never claimed these two, so nothing regressed -- it is a coverage gap, and the release notes will say unreadable files degrade per file.
<!-- sq:finding:F27:body:end -->

#### Discussion

<!-- sq:finding:F27:discussion -->
- [2026-08-06T19:44:54Z] Elias Python:
  - Fixed. Driven before the change on a scratch squad with one readable item carrying the needle and one chmod-000 item: sq search exited 1 with completely empty stdout, discarding the readable hit; sq search --json printed nothing at all, not even []; sq inbox behaved identically; sq list exited 0 with everything. Confirmed as reported.
  - Fix: both loops in _services/_collab.py now read through one guard, _read_or_report, which mirrors the board store's split exactly - a decode failure or an OS refusal surfaces as a SquadsError naming the file and is reported; a FileNotFoundError is present-vs-absent, so a broken symlink (a present dirent whose target read failed) is reported and a file that is genuinely gone is skipped silently, since the missing direction is repair's report to make. search and inbox now return (results, unreadable), the same tuple shape board_list/memory_list/memory_search already use. Note an unreadable item still contributes a title or description match, because those need no file read - the degradation is per source, not per item.
  - Exit contract, decided rather than defaulted: results are printed first, skipped files are named (stderr under --json, console otherwise), then exit 1. That follows repair and board list, the nonzero members of the posture this extends; memory list is the exception at 0. Rationale: under --json stdout stays a bare parseable array with no added key, so the "partial" signal has to be out-of-band, and silently exiting 0 would hide corpus degradation from every script. Adopter-visible consequence for whoever owns the client: sq search still exits nonzero on a degraded corpus, so a client that treats any nonzero exit as fatal keeps toasting. The difference is that stdout is now valid JSON and complete for every readable file, so the right client behaviour is to parse stdout and treat exit 1 + parseable output as degraded, not fatal. I have not touched clients/vscode - flagging it for sequencing.
  - Also updated: the TUI search screen, which consumed the old list return. It now shows a "N item files could not be read - results are partial" status note, including the case where nothing matched at all, rather than a confident "No results" the corpus never got to answer.
  - Tests: tests/service/test_search_and_inbox_degrade_per_file.py - the three unreadable causes as a family (permission denied, invalid UTF-8, broken symlink; each reaches the reader as a different exception and only one was previously exercised anywhere), for both commands, plus the index-only contribution, plus a healthy corpus reporting nothing skipped, plus a genuinely missing file NOT being reported, plus the CLI contract: valid JSON on stdout with the error on stderr and exit 1, exit 0 on a healthy corpus, exit 0 on a legitimately empty result. Guard: tests/meta/test_corpus_walking_reads_degrade_per_file.py - a function that enumerates the corpus via list_items must not read an item file inline, plus a behavioural half asserting both commands actually return the skipped-file channel (a guard that catches and says nothing is no better than no guard).
  - Falsified: reverting _read_or_report to the old path_exists-then-read shape reddens 10 tests in that file, including all three causes on both commands and all three CLI-contract tests. Restored and green.
- [2026-08-06T19:47:20Z] Elias Python:
  - For the writer, not changed by me: docs/faq.md's exit-code table names 'sq board list and sq repair' by name in two places as the commands that exit 1 on a degraded read (the table row for code 1, and the 'A degraded read is a non-zero exit' paragraph below it). sq search and sq inbox now behave the same way and need adding to both. Worth noting while there that sq memory list/search deliberately exit 0 in the same situation, which the table does not currently say either way.
- [2026-08-06T20:12:44Z] Paul Reviewer:
  - Verified at 366752a. Falsification confirmed: the pre-fix path_exists-then-read shape reddens exactly 10 in the new file.
  - Driven as the five causes on both commands with and without --json: permission denied, undecodable, broken symlink, genuinely-missing and a clean corpus all behave as described, stdout stays valid parseable JSON on a degraded corpus, and a genuinely missing file is correctly not reported.
  - Exit 1 is the right contract. The three commands already in this posture exit non-zero, memory list is the documented exception, and under --json the payload must stay a bare array so the exit code is the only out-of-band channel left. Exiting 0 would make an incomplete search indistinguishable from a complete one to every script. Not acted on, inherited: exit 1 is also the code for outright failure here, so a script cannot separate degraded from failed - true of repair and board list too.
  - One shape is still open: an item whose path resolves outside the squad folder loses the whole answer, because item_file is evaluated outside the guard. F38.
<!-- sq:finding:F27:discussion:end -->
<!-- sq:finding:F27:end -->

<!-- sq:finding:F28 -->
### F28 — The TUI glance line hardcodes the priority field code

<!-- sq:finding:F28:body -->
Fixed. _tui/_reader.py::_glance_line iterates spec.fields_for(item.type) and renders one badge per declared field carrying a value - the same derivation _subentity_head_line twelve lines below already used and _tui/_filter.py already enumerated.

Driven after the fix on a spec declaring impact on bug: the header reads "Open · Blocker · unassigned" where it previously dropped the value entirely. Side effect on the bundled spec, intended: a bug now shows priority AND severity (declaration order) rather than only priority, matching every other badge readout.

Guard: the existing tests/meta field-code scan was widened rather than duplicated - it now covers src/squads/_tui/ and src/squads/_cli/ alongside the item templates, recognises the strict declared_collection sibling so swapping resolvers is not a way out, and carries a pinned-scope test so the scan cannot quietly shrink back to templates-only.

Tests: tests/tui/test_glance_line_shows_every_declared_field.py. Falsified: filtering the loop back down to the priority code reddens two of them; reintroducing the literal into the resolve_collection call reddens the meta guard.
<!-- sq:finding:F28:body:end -->

#### Discussion

<!-- sq:finding:F28:discussion -->
<!-- sq:finding:F28:discussion:end -->
<!-- sq:finding:F28:end -->

<!-- sq:finding:F29 -->
### F29 — Declared ref_rules are inert and the kind vocabulary is unvalidated

<!-- sq:finding:F29:body -->
Fixed for the inert-declaration half, which is the whole of what was in scope. The ref-kind
vocabulary is untouched.

**What landed.** `_parse_ref_rules` now validates a declared rule's `kind` against the closed
vocabulary and refuses one outside it, naming the accepted set. That is the genuinely inert case:
a rule for a kind every ref surface rejects can never fire, so it was a declaration that silently
did nothing — the adopter wrote it, nothing refused it, nothing could ever apply it. The stale
self-declared deferral ("Not yet consumed by the engine") is gone from `RefRule`, which was
already false, and both docstrings now state what a declaration actually drives.

**What a declared rule drives, pinned rather than asserted.** Two consumers, both keyed on the
declaring type: `parent_hint` appends the declared `hint` text, so a renamed type or a custom
rule gets its own wording instead of bundled prose; and `sq check`'s `supersedes_incoming`
validator runs *only* for a type that declares a `supersedes` rule, so a project that renames or
drops `decision` takes that check with it. Tests drive both, including the negative side (a type
declaring no rules contributes no hint and is not checked).

**Why the remaining half is not a fix but a different decision, with the evidence.** Reading
`ref_rules` as "the kinds this type may carry" would change what the field means rather than
enforce it, and two independent things say so:

1. **It contradicts the closed-vocabulary decision's own consequence** — the accepted `--kind`
   vocabulary is finite and lives in one place in code, explicitly *with no project-config lookup
   on the validation path*. Scoping `ref add` per declaring type introduces exactly that lookup.
2. **The bundled document does not describe an allowlist.** It declares rules on two types only;
   the navigational kinds (`related`, `depends-on`, `blocks`, `implements`, `duplicates`,
   `scopes`) are carried by every type and declared by none. Driven against this repo's own
   corpus: **115 live refs across 715 items** would become invalid under the whitelist reading —
   `addresses` on review (76), decision (28), bug (5) and feature (5), and `fixes` on decision (1)
   — every one of them a real, meaningful edge that squads itself writes.

So the enforcement question is not "apply the existing rule", it is "should `ref_rules` become an
allowlist" — a change of meaning that needs a decision. It belongs with the already-commissioned
ref-kind decision, since both turn on what a declared ref kind means. Both reasons are pinned as
tests so the boundary cannot be re-litigated from memory. @architect @tech-lead
<!-- sq:finding:F29:body:end -->

#### Discussion

<!-- sq:finding:F29:discussion -->
<!-- sq:finding:F29:discussion:end -->
<!-- sq:finding:F29:end -->

<!-- sq:finding:F30 -->
### F30 — The Records view goes silently blank on a type-catalog failure

<!-- sq:finding:F30:body -->
Driven by the sweep. recordsTreeDataProvider.ts:133-134 falls back to NO_CATEGORIES on a failed type-catalog fetch, recordsTypes returns an empty list and buildRecordsView returns nothing for both the grouped and flat paths, while refresh() calls notifyError only for the LIST fetch -- so nothing is reported. package.json declares no viewsWelcome, so the panel renders wholly blank with no message. One failed getTypeCatalog degrades the three views in three different directions: Work keeps everything, Roster keeps its three fixed buckets, Records shows nothing. Filed after the fact because the sweep reported it and I did not transcribe it -- my omission, not the reviewers.
<!-- sq:finding:F30:body:end -->

#### Discussion

<!-- sq:finding:F30:discussion -->
<!-- sq:finding:F30:discussion:end -->
<!-- sq:finding:F30:end -->

<!-- sq:finding:F31 -->
### F31 — The client squad_dir regex misses valid single-quoted TOML

<!-- sq:finding:F31:body -->
Driven by the sweep. squadDir.ts:22,28 hand-rolls squad_dir out of .squads.toml with a double-quote-only regex and falls back to squads. sq reads squad_dir = (single-quoted, valid TOML) fine at exit 0; the client misses it and resolves the wrong directory, so squadWatcher.ts:53s RelativePattern watches a path that does not exist and AUTO-REFRESH SILENTLY NEVER FIRES -- manual refresh still works and resolveSquadDir returns a non-undefined string, so the tree never hits its no-squad short-circuit and nothing looks wrong. The m flag is also unanchored to top level, so a future table-scoped key would false-match. Filed after the fact for the same reason as the Records finding.
<!-- sq:finding:F31:body:end -->

#### Discussion

<!-- sq:finding:F31:discussion -->
<!-- sq:finding:F31:discussion:end -->
<!-- sq:finding:F31:end -->

<!-- sq:finding:F32 -->
### F32 — The graph node-click round trip is lossy for an underscored prefix

<!-- sq:finding:F32:body -->
Fixed.

The mermaid node id is now an escape rather than a fold, so it is reversible for any
declared prefix. `graphDiagrams.ts::mermaidNodeId` escapes every non-alphanumeric character
as `_` plus exactly four lowercase hex digits (`-` becomes `_002d`, a literal `_` becomes
`_005f`) and leaves alphanumeric runs alone; the output stays inside the
`[A-Za-z0-9_]` alphabet mermaid accepts for a node identifier, and the diagram's visible
labels are untouched — they always carried the real id.

The reported symptom was the smaller half. A fold is many-to-one, so it did not only decode
wrong: two ids differing by hyphen-versus-underscore folded to the *same* node id, which
merged two distinct items into one diagram node before any click happened. Both are covered.

One authority for the escape, because the decoder ships as inlined webview script that
cannot import: `MERMAID_NODE_ID_ESCAPE_SOURCE` is exported from `graphDiagrams.ts` and
interpolated into `previewDocument.ts`'s render script, and a unit test asserts the emitted
page carries that exact pattern so the two ends cannot drift. `decodeMermaidNodeId` sits
next to the encoder so the round trip is testable without a DOM.

Fixed-width four hex digits, and no `u` flag on the encoder's pattern, are both deliberate:
the fixed width stops a decoder from eating an item number that happens to be hex-looking
(`A-1234` encodes to `A_002d1234`), and without the `u` flag a non-BMP character is escaped
as two surrogate code units and rebuilt from both, where the flag would capture only the
high surrogate.

Deliberately not the core CLI's `_safe_id` (`_services/_refs.py`), whose fold is fine
because `sq graph --format mermaid` output is display-only and never decoded back; the
comment claiming parity is corrected in place. Worth noting for the core: that fold has the
same node-merging behaviour on a hyphen-versus-underscore pair, in display only.

Tests: round trips per prefix shape family (hyphenated, underscored, both, single-character,
lowercase, mixed-case, digit-bearing, symbol-bearing, accented, non-BMP), the
no-longer-colliding pair asserted both at the id level and as two distinct nodes in a real
`buildSubtreeMermaid` render, and the same family driven through the decoder *lifted out of
the emitted page and executed*, so the assertion is on behaviour rather than on the presence
of a string. Falsified: restoring the fold turns 26 tests red across the two files.
<!-- sq:finding:F32:body:end -->

#### Discussion

<!-- sq:finding:F32:discussion -->
<!-- sq:finding:F32:discussion:end -->
<!-- sq:finding:F32:end -->

<!-- sq:finding:F33 -->
### F33 — Derived pointer target uses the OS separator, breaking Windows

<!-- sq:finding:F33:body -->
**Fixed** — a real regression, confirmed. `str(convention_path.relative_to(paths.squad_dir))`
renders with the host OS separator; on Windows that's a backslash, landing in a committed
pointer/frontmatter value that must be identical across platforms for the same corpus.

Added `_posix_rel(path, root) -> str` (`path.relative_to(root).as_posix()`, typed on `PurePath`)
in `_v0_4_to_v0_5.py` and used it at the flagged call site, matching the `.as_posix()` convention
already used at this exact kind of site elsewhere (`_workflow/_loader.py`, `_overrides/_service.py`).

**Pin**: `test_posix_rel_normalizes_windows_style_separators_on_any_host` calls `_posix_rel`
directly against `PureWindowsPath` inputs — pure path arithmetic, no real filesystem, no host OS
involved — so it fails on Linux CI too if this ever regresses to a bare `str(relative_to(...))`
(`PureWindowsPath.__str__` renders backslashes on every host, Linux included; only `.as_posix()`
is separator-stable). Falsified: reverted to plain `str()`, watched it redden, restored, green.
<!-- sq:finding:F33:body:end -->

#### Discussion

<!-- sq:finding:F33:discussion -->
<!-- sq:finding:F33:discussion:end -->
<!-- sq:finding:F33:end -->

<!-- sq:finding:F34 -->
### F34 — The runner duplicates a check sq check already makes

<!-- sq:finding:F34:body -->
**Fixed — recommendation adopted verbatim.** Reverted `_v0_2_to_v0_3.py`'s spec-threading: dropped
the `load_workflow_spec` import, `_load_active_spec`, `_unreachable_status`, the `spec` parameter
on `_migrate_subentities`/`migrate`, the discussion-comment write, and the docstring paragraph
describing the mechanism. The runner carries the frozen legacy status forward unchanged with no
active-spec read at all, restoring the frozen-snapshot contract every runner in this package
relies on — `_v0_2_to_v0_3.py`'s own docstring now says so again.

Kept the `MANUAL` runbook entry, reworded to point the operator at `sq check` — which already
runs the identical predicate against the same active spec and reports the mismatch as an
item-scoped error with a non-zero exit — instead of a `migration:` comment that no longer exists.

F17's own body corrected to say the premise was wrong rather than defend the reverted mechanism.
F35 and F37 addressed alongside this (see their own findings).
<!-- sq:finding:F34:body:end -->

#### Discussion

<!-- sq:finding:F34:discussion -->
<!-- sq:finding:F34:discussion:end -->
<!-- sq:finding:F34:end -->

<!-- sq:finding:F35 -->
### F35 — A runner docstring now denies that any runner threads the spec

<!-- sq:finding:F35:body -->
**Auto-resolved by F34's revert.** `_v0_2_to_v0_3.py` no longer threads the active spec — its own
docstring now says "matching every other runner in this package (none of them thread the active
spec)" and that is true again. Verified by direct read: `_v0_5_to_v0_7.py:35` and
`_v0_7_to_v0_8.py:15` make the same package-wide claim and are consistent with the reverted code
and with each other. No sentence needed correcting once the revert landed.
<!-- sq:finding:F35:body:end -->

#### Discussion

<!-- sq:finding:F35:discussion -->
<!-- sq:finding:F35:discussion:end -->
<!-- sq:finding:F35:end -->

<!-- sq:finding:F36 -->
### F36 — A stale path key on an already-migrated squad is never stripped

<!-- sq:finding:F36:body -->
**Decision: strip unconditionally, not accept the residue.** `_backfill_description` now checks
both "has description" and "has a stale `path` key" before deciding to no-op; it writes (and
strips `path`) whenever either is missing/present respectively, not only when a description needs
filling.

Reasoning: F18's own premise is that a durable lie in committed frontmatter is the defect worth
fixing, independent of whether anything currently reads it back — `_frontmatter_payload` ignoring
the key on read is exactly why the *original* bug was low/cosmetic-leaning rather than a functional
break, not a reason to leave the field lying once we're already rewriting this exact key at this
exact call site. Every already-migrated corpus that shipped under the pre-fix runner is carrying
this residue right now, and this migration is the only code path that will ever touch these files
again — there's no later pass that heals it otherwise. The alternative (accept + reword F18's body)
would have been the cheaper edit, but it leaves a known, named lie sitting in every affected
corpus indefinitely for a fix that costs one extra dict check.

Also corrected F18's own body, which overstated the original fix's reach ("actively strips a stale
copy") when it only did so on the rename branch.

Test: `test_backfill_strips_a_stale_path_key_even_with_a_description_already_present` — a
convention file with both a description and a stale `path` key gets the key stripped on the next
migration pass. Falsified: reverted to the description-only early return, watched it redden
(0 acted, key survives), restored, green.
<!-- sq:finding:F36:body:end -->

#### Discussion

<!-- sq:finding:F36:discussion -->
<!-- sq:finding:F36:discussion:end -->
<!-- sq:finding:F36:end -->

<!-- sq:finding:F37 -->
### F37 — The spec-load swallow is unreachable and hides a check regression

<!-- sq:finding:F37:body -->
**WontFix — moot.** Conditional on the runner's spec read surviving, and it didn't: F34's revert
dropped `_load_active_spec`, `_unreachable_status`, and the exception swallow entirely from
`_v0_2_to_v0_3.py`. There is no spec load in this runner to have an unreachable/concealing catch
around. The reviewer's own diagnosis (`sq migrate up` validates the override via `open_service()`
before any runner runs, so a broken override aborts upstream at exit 1) was correct and is now
simply inapplicable — nothing left to fix.
<!-- sq:finding:F37:body:end -->

#### Discussion

<!-- sq:finding:F37:discussion -->
<!-- sq:finding:F37:discussion:end -->
<!-- sq:finding:F37:end -->

<!-- sq:finding:F38 -->
### F38 — search and inbox still abort whole-corpus on an out-of-squad path

<!-- sq:finding:F38:body -->
Driven, on the reviewed commit in an isolated worktree. F27's guard covers the read but not the
path resolution that feeds it, so the whole-corpus abort F27 exists to remove is still reachable —
on one of the shapes F27's own fix description names by name.

In `_services/_collab.py`, both walks call `_read_or_report(item_file(self.paths, item), unreadable)`.
`item_file` is evaluated as the *argument*, outside the try. It resolves the item's stored `path`
through `SquadPaths.abspath`, which calls `Path.resolve()` (following symlinks) and raises
`InvalidIdError` — a `SquadsError` — for anything landing outside the squad folder. That escapes the
guard entirely.

Driven, two independent triggers, each on a scratch squad with one healthy item carrying the needle
and one victim:

- the victim's `.md` replaced by a symlink to a path outside the squad folder (broken *or* resolving
  to a real file). `sq search NEEDLE` exits 1 with **zero** lines of stdout; `sq search NEEDLE --json`
  emits nothing at all and a consumer gets a JSONDecodeError; `sq inbox qa` identical.
- no symlinks at all: the index's `path` for the victim hand-edited to
  `../outside/TASK-000020-traversal-victim.md`. Same result on all four invocations. This is the
  shape the traversal guard was written for, so it is reachable from a tampered or badly-imported
  index, not only from a symlink farm.

Contrast driven in the same run, which is what makes it a gap rather than a background limitation:

- a broken symlink whose target is *inside* the squad folder degrades per file exactly as claimed —
  results printed, file named, exit 1. That is the only broken-symlink shape the new test file
  exercises, so the family is covered in name but not in shape.
- `sq check` and `sq repair` both survive the out-of-squad symlink per file (check exits 3 naming
  the item, repair exits 1 naming it). They are the posture F27 extends, so search and inbox are
  now the two commands in that posture that still lose the whole answer.
- `sq list` / `sq tree` are unaffected, which is precisely the "looks arbitrary next to its
  siblings" symptom F27 was filed on.

Fix direction: move the path resolution inside the guard — have `_read_or_report` take the item (or
the paths + item) and resolve within its own try — so an `InvalidIdError` becomes one more reported
per-file message instead of an escaped exception. The `tests/meta` corpus-walk guard cannot see
this: it asserts the walk delegates its `read_text`, and the walk does; the throwing call is the
path helper.
<!-- sq:finding:F38:body:end -->

#### Discussion

<!-- sq:finding:F38:discussion -->
- [2026-08-06T20:34:32Z] Elias Python:
  - Fixed. Reproduced both triggers myself before touching anything, on a scratch squad with one healthy item carrying the needle and one victim. Out-of-squad symlink: sq search rc=1 with zero stdout lines, --json zero bytes, sq inbox identical. Index path hand-edited to ../outside/...: same on all four invocations. Confirmed exactly as filed.
  - Fix: _read_or_report now takes (paths, item) instead of a resolved path and calls item_file inside its own try, so an InvalidIdError becomes one reported per-item line. It is reported by item id rather than by path, because path resolution is precisely what failed - there is no trustworthy path to name it by. Verified on the same scratch squad across all three out-of-squad shapes (symlink to a real out-of-squad file, broken symlink to an out-of-squad target, tampered index path): results printed, victim named, rc=1, and --json now emits a parseable array.
  - You asked what else sits outside a try that should be inside one. I read both walks call by call rather than assuming. Nothing else can raise: is_open goes through role_for, which is documented total and degrades an undeclared status to a fallback role; item_subentity_kind returns None rather than raising for a type the spec does not declare; _build_regions, _classify_line, _hit_for_line, _authored_field_lines and extract_mentions are pure text operations; list_items reads the index once, outside the loop. item_file was the only one, and it is now inside.
  - The meta guard was wrong in the way you named, so I fixed the rule rather than adding a case. It now flags a corpus walk that calls read_text OR item_file OR abspath inline - the operation, not one of its steps - with a planted test for the exact defeating shape (delegated read, inline path resolution in the argument list). Broadening it surfaced one genuine hit outside search/inbox: ServiceCore._skill_paths, which walks skill items and calls paths.abspath inline. Exempted with a reason rather than changed: it builds the slug-to-body-path map the backends consume to regenerate managed files, so it is a build input rather than an answer, and a squad synced from a silently short map would write managed files with a skill body quietly missing. Loud refusal is correct there. The exemption is function-granular and has a liveness test.
  - Tests: two new causes in the existing family (symlink-outside-squad, broken-symlink-outside-squad) across search and inbox, plus a separate no-symlink test driving a traversal path written into the index, plus the assertion that an out-of-squad victim is named by item id. Falsified: reverting the guard to resolve outside reddens 6; reverting only the caller to pre-resolve (guard intact, the exact shape that was green before) reddens the meta guard. Both restored and green.
<!-- sq:finding:F38:discussion:end -->
<!-- sq:finding:F38:end -->

<!-- sq:finding:F39 -->
### F39 — repair invents created_at and the heal makes the loss permanent

<!-- sq:finding:F39:body -->
Driven, on the reviewed commit. The invented-timestamp default is not only read at a load boundary —
`sq repair` *persists* it into the index, and F3's heal-on-write then writes that fabricated value
back into the markdown as if it were the recovered truth.

Driven sequence on a scratch squad, one task, no other activity:

- t0 — index `created_at=19:59:26`, markdown `created_at: '2026-08-06T19:59:26Z'`. Agreed.
- the `created_at:` line is deleted from the markdown (a hand edit, a bad merge, a partial write).
- `sq repair` — exit 0, silent. Index now `created_at=19:59:29`. Repair rebuilt the entry from
  markdown, the field was absent, `_parse_dt` returned `clock.now()`, and repair committed that
  placeholder over the item's real creation instant.
- `sq task N update --status Ready` — exit 0. The heal writes the index's value back:
  markdown `created_at: '2026-08-06T19:59:29Z'`.

The real creation instant is now unrecoverable from either artifact. Nothing reported it at any
step: repair exits 0, and the `sq check` warning has already cleared because the field is present
again.

What ST1 changes here. The mechanism predates it — repair has always rebuilt from an invented value.
But before F3 the item was wedged: every mutation refused, loudly, so the fabricated index value
never reached the markdown and an operator was forced to look. After F3 the write succeeds, so the
fabrication becomes the durable value in the source of truth, silently. A loud unrecoverable state
became a quiet unrecoverable state, which is the worse of the two.

It also makes ST1's own new warning wrong in this case. `_missing_timestamp_issues` says the
placeholder is invented on each read "until any mutation writes the real value". Driven with no
intervening repair, that is true — the heal wrote the index's original `19:58:42`, exactly as
claimed. Driven with a repair in between, the "real value" the warning promises no longer exists
anywhere, and the mutation writes a second placeholder.

Fix direction (either, or both):

- repair should not adopt an invented timestamp over an entry it already holds: when the markdown
  carries no value for a key in `INVENTED_WHEN_ABSENT` and the previous index entry does, carry the
  previous value forward — the same "carry the previous entry forward" posture repair already takes
  for an unreadable file, applied to an unreadable *field*.
- the check warning should not promise a real value; it should say the value will be fixed at
  whatever the index currently holds, and that running `sq repair` first will replace it with now.
<!-- sq:finding:F39:body:end -->

#### Discussion

<!-- sq:finding:F39:discussion -->
- [2026-08-06T20:34:59Z] Elias Python:
  - Fixed, both halves. The characterisation is right and I accept it: my change converted a loud unrecoverable state into a quiet one, which is the worse of the two, and my own warning was making a promise the repair path had already broken.
  - Fix 1, the mechanism. _rebuild_index_from_disk now calls _carry_forward_indexed_timestamps: when the scanned markdown carries no value for a key in INVENTED_WHEN_ABSENT and the previous index entry has one, the previous value is kept. This is your first suggested direction, and it is the same carry-the-previous-entry posture the rebuild already takes for a whole unreadable FILE, applied to an unreadable FIELD. Driven end to end on a scratch squad: index and markdown agree at 20:20:33, the created_at line is deleted, sq repair exits 0 and the index still reads 20:20:33, and the next mutation heals the markdown back to 20:20:33 - the item's real instant, not a placeholder. sq check clean afterwards.
  - Gated on known_corpus, which is also what makes it safe rather than merely convenient. repair supplies the previous snapshot; renumber deliberately does not, and must not - a renumber shifts sequence numbers on purpose, so a lookup into the pre-renumber index would match a different item's entry and carry the wrong timestamp. Carrying nothing there is correct. The residue: a renumber over a corpus that is already missing a timestamp still invents one. I left that rather than thread a second snapshot, because the safe fix there is not the same fix, and renumber's own _scan_records already reads every file unguarded so it never runs over a damaged corpus. Flagging it rather than hiding it.
  - Fix 2, the warning. It no longer says "the real value". It now says the placeholder stands "until any mutation writes the value the index holds back into the file" - which is what actually happens, and is true whether or not the index still has the original. Your second suggested direction also asked it to say that running repair first replaces it with now; that is no longer true after fix 1, so saying it would be wrong. The docstring records why the wording must not over-promise.
  - Tests: repair preserves the indexed value per field combination (created / updated / both); the full repair-then-heal round trip restores the real instant; a never-indexed item still gets a placeholder and repair still succeeds (the carry-forward narrows the damage, it does not pretend to recover what was never recorded); and the warning asserts the new wording and asserts "the real value" is absent. Falsified: removing the carry-forward call reddens 4; restoring the old warning wording reddens 1. Both restored and green.
<!-- sq:finding:F39:discussion:end -->
<!-- sq:finding:F39:end -->

<!-- sq:finding:F40 -->
### F40 — The marker single-definition guard misses a wrapped regex

<!-- sq:finding:F40:body -->
Driven, two holes, both in the new marker single-definition guard
(`tests/meta/test_sq_marker_recognition_has_one_case_blind_definition.py`). Its stated job is "a
second regex is how this class comes back"; the most mechanical way it comes back walks straight
through.

Hole 1 — the scan is single-line. `_scan` skips any source line that does not itself contain
`re.compile` / `re.findall` / `re.search`, then matches the marker literal on that same line. A
compile call whose pattern sits on the next line is invisible. That is not a contrived shape: it is
what the project's own formatter produces the moment the call exceeds the line limit. Driven — a new
module `src/squads/_probe_second.py` containing

    _SECOND = re.compile(
        r"<!--\s*(sq:[a-z0-9][a-z0-9:_-]*)\s*-->"
    )

leaves all six tests green. The single-line form of the identical pattern is caught, which is what
the planted-duplicate test exercises, so the guard's own falsification test does not distinguish the
two.

Hole 2 — the exemption is module-granular, and the liveness test does not close it. Driven: appending
a brand-new general recogniser

    _GENERAL = re.compile(r"<!--\s*(sq:[a-z0-9][a-z0-9:_-]*)\s*-->")

to `src/squads/_migrations/_meta_compat.py` leaves all six tests green.
`test_every_exempt_module_is_still_produced_by_the_scan_without_it` only asserts the module still
yields *at least one* hit when un-exempted, which the six pre-existing frozen readers guarantee
forever. The exemption itself is genuine — the readers interpolate a frozen literal
`_LOCAL_ID_PREFIX = {"story": "US", "subtask": "ST", "finding": "F"}` and are imported only by
`_v0_1_to_v0_2` and `_v0_2_to_v0_3` (read) — but the guard blesses the whole file, not those lines.

Fix direction: scan the parsed AST (a `Call` to `re.compile`/`findall`/`search` whose first argument
is a string constant matching the marker shape) rather than raw source lines — the wall-clock guard
in the same batch already does exactly this and has neither hole. Pin the exemption to a hit count
or to the specific line contents so a seventh pattern in `_meta_compat.py` fails the liveness test.
<!-- sq:finding:F40:body:end -->

#### Discussion

<!-- sq:finding:F40:discussion -->
- [2026-08-06T20:35:29Z] Elias Python:
  - Fixed. Both holes reproduced first, using your exact probes against the real tree: a new module with a formatter-wrapped compile left all six tests green, and a general recogniser appended to _meta_compat.py left all six green. Then rewritten, then both probes re-run and each now fails the gate. The module_compat file was restored byte-for-byte afterwards (verified with git diff).
  - Rewritten on the AST, matching the wall-clock guard in the same batch: a Call whose callee name is a regex API (compile/findall/search/match/fullmatch/finditer/sub/subn/split) and whose first argument carries marker-shaped literal text. Formatting is now irrelevant, because a wrapped call and a one-line call are the same node. Went one step past the filed direction on the argument: an f-string is read too, with each interpolation collapsed to a {} placeholder, and so is a + concatenation of literals - "not a plain constant" was the other cheap way past a constant-only check, and _meta_compat's own patterns are f-strings, so I needed it regardless.
  - The exemption is now pinned to (module, pattern text), not the module. Both frozen _meta_compat readers are listed by their exact normalised pattern, and the liveness test asserts each PAIR is still produced rather than that the module still yields something - which is what made the old liveness test structurally unable to notice. A seventh pattern in that file fails.
  - Tests, one per hole plus the shapes that motivated the rewrite: the original single-line planted duplicate; the formatter-wrapped one; an f-string and a concatenated one; a general recogniser appended to an exempt module with only the frozen pattern exempted; and a negative case covering prose, a non-marker regex, and a marker CONSTRUCTOR (_markers.open_marker's f-string), which must never be flagged - restricting to regex-API calls is what keeps the constructor out, and that is now pinned rather than incidental.
<!-- sq:finding:F40:discussion:end -->
<!-- sq:finding:F40:end -->

<!-- sq:finding:F41 -->
### F41 — Every scale test has failed in setup since the actor guard landed

<!-- sq:finding:F41:body -->
Driven, and confirmed to pre-date the integrity-core work. Not one test — all five.

`tests/test_scale.py::_build_scale_squad_async` calls `svc.create("feature"|"task"|"bug", ...)`
without an `author`. `create` has required an explicit actor since commit c9cc1b4 (2026-07-31,
"Required an explicit actor and reported an unusable index cleanly"), which raises
`author is required: the actor's slug`. Every scale test builds its corpus through that helper, so
every one of them dies in setup before it measures anything:

    tests/test_scale.py --run-slow -n0  ->  5 failed in 0.51s

    test_scale_list_completes_within_bound
    test_scale_search_completes_within_bound
    test_scale_repair_completes_within_bound
    test_scale_cli_list_completes_within_bound
    test_scale_cli_tree_completes_within_bound

Driven at the reviewed commit and again with `src` and `tests` checked out at its parent: identical
failure, same line. So the integrity-core work is not implicated, and the report of one failing
search test understated it — the whole scale file has been inert for six days.

The consequence is the reason this is worth a ticket rather than a note: these are the only
performance bounds in the suite, they are skipped by default, and nothing else fails when they
break. Every timing regression since 2026-07-31 has gone unmeasured, including the ones this
release's own changes could have introduced (`_marker_issues` now walks roughly three times as many
tags per file on a real corpus, and the search walk gained a per-file guard).

Fix: pass an author in the helper. Worth pairing with something that makes the file's silence
audible — a scheduled `--run-slow` job, or a smoke case that builds a small corpus through the same
helper and runs unskipped.
<!-- sq:finding:F41:body:end -->

#### Discussion

<!-- sq:finding:F41:discussion -->
<!-- sq:finding:F41:discussion:end -->
<!-- sq:finding:F41:end -->

<!-- sq:finding:F42 -->
### F42 — ADR-663 does not name the absent-timestamp skew exclusion

<!-- sq:finding:F42:body -->
Read. `frontmatter_skew` now has two exclusion mechanisms, and only one of them is written down in
the decision that governs them.

ADR-663 §1 names its exemptions exhaustively, and pins the last one to a two-part test: a
post-commit item-`.md` write is permitted only for "a derived value the transaction did not mirror,
and reproducible by `sq sync`". `PERMITTED_EXTRA_SKEW` is the implementation of that clause, and
`frontmatter_skew`'s docstring cites it by name.

`INVENTED_WHEN_ABSENT` sits beside it, subtracts from the same key set, and meets neither half:
`created_at`/`updated_at` are transaction-mirrored index fields, and `sq sync` does not re-derive
them. On its face it therefore reads as the clause being widened by a second writer.

It is not, and the distinction is exactly what should be on the record. The §1 exemption covers a
key where **both sides hold real values that legitimately differ**. This one covers a key where the
disk side holds **no value at all** and the comparator's disk operand was fabricated by the loader —
so it is not a permitted skew, it is the removal of a comparison whose premise ("what the on-disk
frontmatter says") was never satisfied. It is also conditioned on observed disk state per read
rather than on a key name, which makes it strictly narrower than the exemption it sits next to, not
wider. All three of its stated bounds are driven and hold: absent and `null` are excluded,
present-but-different still refuses, unparseable and empty-string still fail at the load boundary as
a `SquadsError`, and an absent timestamp does not mask a divergence on any other field.

The defect is that a reader of ADR-663 cannot reach any of that. The ADR is the authority on what
may skew; a second exclusion in the same comparator, invisible to it, is how the next widening gets
argued from the wrong baseline — and this codebase's convention is that a rule of this kind lands in
an ADR rather than only in a docstring.

Fix: amend ADR-663 §1 (or a successor decision) with a short clause distinguishing a *permitted
skew* on a mirrored key from a *withheld comparison* on a key the file does not carry, naming
`INVENTED_WHEN_ABSENT` and its absence-only condition. No code change implied.

**Architect ruling (2026-08-06).** Upheld, with the clause corrected: the exclusion is within
ADR-663 as written, but not under the clause this finding measures it against.

§1's three-item exempt list is a test of *ordering* — what a writer may put on an item `.md` after
the commit — and `PERMITTED_EXTRA_SKEW` is its guard-side consequence. `INVENTED_WHEN_ABSENT` fails
both halves of that test and was never meant to satisfy them; it is not that clause acquiring a
second writer. Its home is **What the guard compares**, which already carried the governing
sentence: a correction that does not collapse through the shared round trip is registered
explicitly, in the same change that introduces it, "otherwise it becomes a false refusal". A
non-deterministic load-time default cannot collapse through a shared serializer — that trick
depends on both sides being a function of the file's bytes — so it was always in that clause's
scope. It went unregistered, and the predicted false refusal is the defect TASK-737 ST1 fixed.

The permitting/withholding distinction is sound and now sits in the ADR as a rule rather than a
ruling on one case. A *permitted skew* has two real operands that legitimately differ; a *withheld
comparison* has a disk operand the loader fabricated, so there is no second value to disagree with.
Four conditions bound the withholding form, all load-bearing: the operand is loader-fabricated
rather than read from the file; the fabrication is non-deterministic; the drop is conditioned on
the observed raw frontmatter per read, never on a key name; and it self-extinguishes at the first
successful write. The third is what makes it strictly narrower than the exemptions beside it.

A second clause landed with it, covering what the withholding owes in return, because the exclusion
alone is not sufficient. Declining to compare a field must not become declining to notice it (`sq
check` keeps warning on the file), and no path may commit a fabricated value over a known one — the
rebuild's carry-forward of the previously-indexed timestamp. Without the pair, an invented instant
reaches the index, a later mutation heals the markdown from it, and the item's true creation time
is gone from both artifacts unreported. That is the invariant #1 exposure, and it is the reason the
mechanism is judged as a two-sided arrangement rather than as one comparator's exclusion set.

No code change. The mechanism as it stands meets all four bounds and both obligations. The record
is the amended ADR-663 §1 plus its dated comment; no `supersedes` or `related` edge, since nothing
in another decision was narrowed.
<!-- sq:finding:F42:body:end -->

#### Discussion

<!-- sq:finding:F42:discussion -->
- [2026-08-06T20:46:12Z] Robert Architect:
  - Ruled within ADR-663, under **What the guard compares** rather than §1's exempt list — your two-part test governs ordering, and the registration clause you did not cite ("a future correction that does *not* collapse through the round-trip is registered explicitly … otherwise it becomes a false refusal") already covered this and predicted the exact defect. Your permitting-vs-withholding distinction is the right one and is now in the ADR as a general rule with four bounds, not a ruling on one case. No code change; ADR-663 §1 amended in place, dated comment on the ADR. @reviewer for verification of the amendment against the mechanism.
<!-- sq:finding:F42:discussion:end -->
<!-- sq:finding:F42:end -->

<!-- sq:finding:F43 -->
### F43 — The marker guard body label omits the remediation guidance

<!-- sq:finding:F43:body -->
Read, then driven. `reject_markers` (`_services/_base.py`) emits two different messages. The
`title` and `comment message` labels get the extended one:

    ... must not contain sq marker comments. Write the tag without its HTML-comment wrapper
    (e.g. sq:body rather than the comment form) — backtick-wrapping does not neutralize a
    well-formed tag.

The default `body` label gets only:

    body must not contain sq marker comments (<!-- sq:… -->)

Driven on the reviewed commit: `sq review N body -m` with a comment-wrapped `sq:finding:F1:body` tag
in the text prints the terse form; `sq review N comment` with that same text prints the extended
one. (Filing this finding drove it a second time by accident — the first draft of this body quoted
the wrapped tag and was refused with the terse message.) Every body seam
takes the default label — the item body, both sub-entity body writers, and the shared section-edit
core — so the *only* prose surface that does not carry the remediation hint is the highest-traffic
one.

Why it matters now rather than before. Widening the tag class is what makes a body refusal likely:
before, only a lowercase top-level tag could trip it; now every quoted sub-entity region tag does,
and that is the form an agent actually writes when it reports on the marker system (the one corpus
instance found was exactly that). The judgement that the refusal is correct rather than the regex
too strict rests on the guard telling the author what to write instead. On the seam being widened,
it does not.

The docstring's stated reason for the split is that the legacy message is "kept verbatim so existing
callers and tests stay unchanged" — a test-compatibility argument, which is the weakest reason to
leave the worse message on the busiest path.

Fix: give the `body` label the extended message and update whatever asserts the terse string.
<!-- sq:finding:F43:body:end -->

#### Discussion

<!-- sq:finding:F43:discussion -->
- [2026-08-06T20:35:30Z] Elias Python:
  - Fixed. reject_markers now emits the extended message for every label, including the default body one. The special case is gone, not widened.
  - Agreed on the reasoning, and it is the part I got wrong the first time: the judgement that the refusal is correct rather than the regex too strict rests entirely on the guard telling the author what to write instead, and I made that argument in a comment while leaving the seam where it actually fires unable to make it. The docstring now says every label carries the guidance and why - the old test-compatibility rationale is deleted rather than reworded.
  - Tests: the "message unchanged" regression test was the thing pinning the wrong contract, so it is replaced rather than patched. In its place, a table-driven test that every prose seam carries the remediation sentence - item body, sub-entity body, comment, sub-entity title - plus one asserting the per-input label survives (with four seams sharing one sentence, the label is the only thing locating the problem). Falsified: restoring the terse body branch reddens the two body seams and leaves the other two green, which is exactly the asymmetry that was shipped. Restored and green.
<!-- sq:finding:F43:discussion:end -->
<!-- sq:finding:F43:end -->

<!-- sq:finding:F44 -->
### F44 — sq graph mermaid merges two ids differing only by hyphen or underscore

<!-- sq:finding:F44:body -->
Reported by the typescript-dev while fixing F32, in the Python half she could not touch. _safe_id in _services/_refs.py folds non-alphanumeric characters the same way the client used to, and a fold is many-to-one -- so two declared prefixes differing only by hyphen versus underscore collapse to one node and sq graph --format mermaid draws two distinct items as a single node. Display-only: unlike the client there is no decode step, so nothing navigates to a wrong id. But the diagram is wrong before anyone clicks it, which is exactly the half of F32 the finding did not name. ItemSpec.prefix has no validator, so both spellings are legal. The client now escapes reversibly (non-alphanumerics to underscore plus four hex digits, fixed width); the same treatment applies here, and the two sides need not agree since neither decodes the others output.

---

## Disposition: fixed, matching the client's escape — and the merge was only half the defect.

**Match, and here is why**, since the finding leaves it open. Mermaid's node-id alphabet is
effectively `[A-Za-z0-9_]`. Any encoding into that alphabet that maps `-` to a single `_` is
non-injective no matter how the rest is handled: `A-005fB` and `A_B` both encode to `A_005fB`,
because the escape's own digits are alphanumerics that a folded character can be followed by.
Doubling collides too — `A-_B` and `A_-B` both give `A___B`. Fixed-width escaping of every
non-alphanumeric is the only context-free injective option, so "match the client or don't" turns
out to have one correct answer rather than two. Matching then costs nothing and buys one: the
client's existing decoder happens to work on CLI output, which neither side is obliged to
support but neither side now has to think about.

**The half the finding did not name.** `graph_to_mermaid` emitted no node labels, so the node id
*was* the visible box text. Escaping alone would have fixed the merge and made every node in
every diagram read `TASK_002d1` — a readability regression paid by 100% of users to fix a
collision reachable only by adopters who declare two prefixes differing exactly by `-` vs `_`.
So nodes are now declared with the real item id as an explicit label, and the escaped identifier
never reaches a reader. Only nodes an edge touches are declared, so the node set drawn is
unchanged.

Escapes UTF-16 code units, not code points, so a non-BMP prefix becomes two four-digit escapes
rather than one five-digit one that would break both the fixed width and the shared spelling.

**Falsified:** restored the fold; the merge test, the round-trip-family test and the label test
went red; restored by exact reverse substitution, green again.

**Adopter-visible:** `sq graph --format mermaid` output changes shape — node ids are escaped and
each node is declared with a label. Rendered diagrams read the same; pasted-source diffs will not.

**Cross-tree note, not touched:** `clients/vscode/src/domain/graphDiagrams.ts`'s `mermaidNodeId`
docstring says the scheme is "deliberately NOT the core CLI's `_safe_id` … which folds". That
sentence is now stale. It is in the typescript-dev's tree and I stayed out of it.
<!-- sq:finding:F44:body:end -->

#### Discussion

<!-- sq:finding:F44:discussion -->
<!-- sq:finding:F44:discussion:end -->
<!-- sq:finding:F44:end -->

<!-- sq:finding:F45 -->
### F45 — The preview stamps a clickable item id on every mermaid node

<!-- sq:finding:F45:body -->
Reported by the typescript-dev, read from `clientScript`'s `g.node[data-item-id]` handler rather
than driven in a host.

The webview's post-render pass stamped `data-item-id` on **every** node of **every** rendered
mermaid diagram, not only on the item-graph nodes it was built for, so any diagram whose nodes
are not items offered the reader a click that opens nothing — a status node reads
`data-item-id="InProgress"` and posts an open-item message for an id that does not exist.

## Which diagrams could actually reach it

The finding as first written named a hand-authored fence in a dossier body. That trigger does not
exist, and never did: `renderOutcomeHtml`, the comment renderer and the sub-entity body renderer
all call `renderMarkdownToHtml` with `renderMermaidFences` false, so a fence in an item body
renders as `<pre><code>` and never becomes a diagram at all. `renderWorkflowHtml` is the one
caller that passes true.

Which leaves the cheatsheet panel, and there the reachable case is narrower still:

- The bundled cheatsheet emits no mermaid — driven, `sq workflow --raw` on this repo returns zero
  ```mermaid``` fences, and `workflow.md.j2` contains no mermaid at all.
- A project's own `.overrides/templates/workflow.md.j2` can carry one. Driven on a scratch squad:
  an override template holding a fence flows through `sq workflow --raw` verbatim, and that text
  through `renderWorkflowHtml` produces a live `.sq-graph-source` element whose nodes the pass
  would have stamped.
- Read, not driven: the stamping loop only matches node ids of the form
  `-flowchart-<id>-<n>`, which is mermaid's flowchart id scheme, so a fence declaring some other
  diagram type may produce no match regardless. Whether a given diagram type renders that id
  shape is renderer behaviour not exercised here.

So: adopter-triggerable, live today, and narrower than filed.

## The guard

The source element now declares whether its node ids are item ids, and the pass stamps only when
it does. `ITEM_NODES_ATTRIBUTE` (`data-sq-item-nodes`) is emitted by `buildGraphSection` — the two
structured graphs, built from `sq tree`/`sq graph --json`, where every node IS an item — and by
nothing else; `mermaidRenderScript`'s `stampsItemNodes` gates the loop on it. Opt-in by
construction, so a future item-bearing diagram has to say so and anything else stays inert.

Tests: the gate is lifted out of the emitted page and executed, admitting a source that declares
the attribute and refusing one that does not; both producers are asserted at the section level
(two graph sections carry the marker, a fence-rendered diagram carries none, a failed graph fetch
renders no source element at all); and one case pins the reason the item surfaces were never
exposed — an item body's fence renders as plain code. Falsified three ways: forcing the gate true,
never emitting the marker, and keying the gate off a different attribute each redden exactly the
matching test.

One limit worth stating: the stamping loop itself needs a DOM, so its behaviour is not executed
here. The gate function is executed, and its wiring into the loop is asserted structurally.
<!-- sq:finding:F45:body:end -->

#### Discussion

<!-- sq:finding:F45:discussion -->
<!-- sq:finding:F45:discussion:end -->
<!-- sq:finding:F45:end -->

<!-- sq:finding:F46 -->
### F46 — A category reassignment that contradicts itself loads clean

<!-- sq:finding:F46:body -->
Fixed. A category reassignment that contradicts itself now fails Plane-1 load validation and
hard-stops, on every gate that was silent.

## The rule, and why it is written this way

`_check_category_consistency` in `_workflow/_models.py`, called from `WorkflowSpec._validate` —
the Plane-1 fail-closed pass the governing decision names. It is written against the type's
**effective validator set**, not against the category *name*, because the validator set is what
a category actually is: read across the tree, every other category consumer branches only on
`roster` versus not, so `work` and `records` differ in exactly one respect — which validators
they turn on. Two consequences of that framing, both intended:

- it is category-agnostic, so it catches a `work` type that adds `no_parent` to its own
  `validators` while still declaring `parents` — no reassignment involved at all;
- it needs no second table to keep in step with the bundles.

Two clauses, each catching a declaration that would otherwise silently do nothing:

1. **A type whose effective set includes `no_parent` may not declare `parents` or
   `parent_required`** — the records contract's own named example.
2. **A type declaring a `subentity_kind` must keep at least one validator whose subject is that
   kind.** The `records` bundle carries none, so a hosting type moved there keeps its
   sub-entities while every check on them stops running. "At least one" rather than "all four"
   deliberately: `validators` is extend-only from the closed catalog, so an adopter who really
   wants a record hosting sub-entities can name the checks they want back — and the refusal
   names them. That is what keeps this validation rather than prohibition.

`COMMON_CORE`/`CATEGORY_BUNDLES`/`effective_validator_names` moved from `_services/_validators.py`
into `_workflow/_models.py` so the Plane-1 pass can resolve the same effective set the engine
runs — one definition, not two. Same layering argument that already put `VALIDATOR_NAMES` there:
`_workflow` must not import up into `_services`.

## Driven

All four reported shapes reproduced first at `2fed334` — silent on `sq list` (0),
`sq workflow lint` ("no errors or warnings") and `sq check` (0) — with every fixture gated on
`sq list` exiting 0 first, so a fail-soft fallback could not fake a result.

After: cases 1, 2 and 4 hard-stop on all three gates with a message naming the type, the
category, the offending field(s) and both ways out. Wider shapes also now refused: a records type
declaring `parent_required` alone; one declaring `parents` alone; a work type adding `no_parent`
while declaring `parents`; a records type given a `subentity_kind`.

Still loading, deliberately — reassignment is permitted and only inconsistency is refused:
`bug`→records, `guide`→work, `task`→records with the forbidden fields dropped, and
`review`→records with the sub-entity checks named back. The bundled spec is unaffected.

**Correction, driven by the reviewer and confirmed here: `decision`→`work` does NOT still
load, and listing it above was wrong.** `decision` declares a `supersedes` ref rule, and the
only validator defined over that declaration — `supersedes_incoming` — sits in the `records`
bundle and nowhere else, so under `work` the rule keeps being reported by the loaded spec
while the check it drives silently stops running. That is the same shape as the clause above
for `subentity_kind`, and it was missed for a nameable reason: the clause set was written
against the capability *fields* that were in hand rather than against the validator set the
rule is actually defined over. It is now refused by a third clause, and the whole catalog is
closed against that omission — see the reachability audit.

## Two corrections to the report, both driven

**Case 3 (`guide`→`work`) is not a defect and is left loading.** Its stated basis — "bound to a
lifecycle that never reaches Done" — is not expressible from any declared property. Read off the
bundled spec: the `done` role is `settled=True, hidden=True, live=False`, and so are `retired`
and `superseded`; the three are identical on every declared flag, differing only in `color`,
which is presentation. Distinguishing a burn-down terminal would need either a literal role-name
binding — which the governing semantics decision forbids outright — or a new declared flag on the
status role, a spec-format change nobody has decided. Driven end to end besides: `guide` as
`work` declares no `parents`, no `parent_required` and no `subentity_kind`, so the work bundle
adds only vacuous checks; the type creates, transitions to its own settled state, and
`sq check` stays clean. Nothing it declares is silenced. That is a merely-unusual-but-valid
reassignment — the adopter's call. **Case 2 is still caught**, but by the sub-entity clause
(`review` hosts findings), not by the lifecycle argument.

**Half the stated consequence does not hold.** `sq create task` with no parent succeeded
*before* the reassignment too — driven against the bundled spec. `parent_required` is not a
create gate at all: it is read only by `subtask_story_mapping` and for hint text. What the
reassignment actually killed is the `parents` allowlist — `--parent FEAT-n` goes from accepted to
"task takes no parent" while the spec still reports `parents=['feature']`. The finding's core
stands; that one direction was overstated. **`parent_required` being weaker than it reads is a
separate, pre-existing gap** — not opened here, and flagged for triage rather than folded in.

## One defect this surfaced in my own earlier work, fixed here

`sq create <type>` and `sq <type> <n> update` re-derive `--priority`'s help from the active spec
inside Click's `get_params`, which runs *before* the command body and so outside the boundary
that turns a `SquadsError` into a clean message. Once the spec started refusing on an
unresolvable override, that hook escaped as a **traceback** — the one outcome the refusal
contract rules out. The help refresh is now fail-soft: presentation degrades to its baked text,
and the refusal fires from the command body a moment later. Same division the completion/help
path already uses. Regression tests pin both the absent traceback and that `--help` still
renders.

## Falsification

Five breaks, each applied in place and reverted by exact reverse substitution with the file
verified byte-identical after: the check not called at all; each clause disabled separately; the
check rewritten against the category name instead of the validator set; and the parse-time help
refresh allowed to raise. All five reddened the intended tests.
<!-- sq:finding:F46:body:end -->

#### Discussion

<!-- sq:finding:F46:discussion -->
<!-- sq:finding:F46:discussion:end -->
<!-- sq:finding:F46:end -->

<!-- sq:finding:F47 -->
### F47 — parent_required is read for hints but never enforced at create

<!-- sq:finding:F47:body -->
Flagged by the dev while writing the F46 test, and not opened by him -- correctly, since it is pre-existing and outside that findings scope. Driven: sq create <type> with no parent succeeds even where the type declares parent_required, and it did so BEFORE any category reassignment. parent_required is not a create gate at all; it is read only by subtask_story_mapping and by hint text. So the field reads as a constraint and enforces nothing.

This also corrects half of F46s stated consequence: the reassignment did not kill parent_required, because parent_required was never enforcing. What it killed is the parents allowlist, which is real and is what F46 fixed.

Same family as F29 -- a declared seam the engine does not consume -- and the same question applies: either the declaration enforces something or it should not be declared. Note the interaction with the records contract: a records-category type takes no parent at all, so whatever parent_required means must compose with that rather than contradict it.

Not folded into F46 because F46 is fixed and verified against the behaviour that actually changed; this is a separate, older gap that happens to have been found while testing it.

---

## Recommendation: neither arm as posed. `parent_required` is not an unenforced declaration — it is an enforced declaration whose name overpromises, plus a second contradiction nobody had reported.

**Driven, on the bundled spec, fresh squad:** `sq create task "Orphan" --author tech-lead` → exit 0; `sq check` → exit 0. The finding's premise reproduces exactly.

**Driven, same squad, same spec, no override:** `sq task <n> subtask ST1 update --story US1` →
exit 1, `error: TASK-19 has no feature parent; set one before mapping a subtask to US1`. The
word `feature` in that message is `parent_required`, read through `_validate_subtask_story`.
`subtask_story_mapping` reports the same as a `sq check` **error**. So the field is enforced,
hard, on a path that ships enabled — just not the path its name suggests.

That refutes the drop arm on evidence rather than on taste. It is also not derivable: `parents`
is a multi-valued allowlist with no way to say which member owns the stories, and
`_kind_is_story_target` inverts the same single value to decide whether removing a story could
orphan a mapped child. Dropping the declaration costs both.

### Why not enforce it on the bundled spec

`ValidatorEngine.gate()` (create/update) and `report()` (`sq check`) run **one** effective
validator-name set; `gate()` differs only by filtering to error level. There is no position from
which a check refuses the next parentless item while staying quiet about the parentless items
already on disk — the "error at create, silent on history" option does not exist in this
architecture, and a warn-level check is the exact inverse (advisory at create, noisy in check).

Read from this repo's own live index: **32 of 333 tasks have no parent.** Enforcing in the `work`
bundle turns those into `sq check` errors on a gate this repo must keep clean, and does the same
on every adopter's board, with nothing a migration can do — you cannot invent a parent.

### What was built

1. **`parent_present`**, a new member of the closed catalog, **in no `CATEGORY_BUNDLES` entry**.
   It refuses an item with no parent, naming the declared type when the spec declares one. A type
   opts in by naming it in its own `validators` — the same extend-only escape hatch
   `_clause_subentity_checked` already documents. Bundled behaviour is byte-identical: a bare
   `sq create task` still succeeds.
2. **The clause registry's exclusion of `parent_required` was an accurate report of a hole in the
   catalog, not a property of the field.** With a validator now defined over its requiredness,
   `_clause_parent_reachable` owns two new arms: `parent_present` + `no_parent` in one effective
   set (every item refused whichever way it is created — reachable both by naming both on a type
   and by naming the mandatory half on a `records` type), and the second gap below.
3. **`parent_required` naming a type the `parents` allowlist excludes.** Not in the report,
   found while working it, driven: `[items.task] parents = ["epic"]` with the inherited
   `parent_required = "feature"` **loaded clean** — `parent_allowed(task, "feature")` is `False`,
   so the one parent type the story mapping insists on is the one `parent_in` refuses. The
   mapping is dead in both directions while the loaded spec reports both fields: the exact shape
   of the contradictory reassignment, arrived at with no reassignment. Now refused at load.
4. `parent_required` stays out of the *reachability* audit, and this is now argued rather than
   asserted: it has a live consumer under every category (the `--parent` example in generated
   agent prose, and the anchor-type score), so no configuration exists in which declaring it
   reaches nothing. A reachability arm over it would fire on a correct spec.
5. The field's docstring and the bundled `workflow.toml` comment now say what it does and how to
   turn requiredness on — the naming lie is the part an adopter actually trips over.

### Falsified

`_parent_present` neutered → 3 integration tests red; both new clause arms neutered
independently → their own table rows red; each restored by exact reverse substitution, green
again. The allowlist arm was also confirmed through the real CLI, refusing a leftover scratch
override with the full message and fix hints.

### Adopter-visible

`parent_present` is a new opt-in validator name. No default behaviour changes. One spec that
loaded before is now refused: `parent_required` pointing outside a non-empty `parents`.
<!-- sq:finding:F47:body:end -->

#### Discussion

<!-- sq:finding:F47:discussion -->
<!-- sq:finding:F47:discussion:end -->
<!-- sq:finding:F47:end -->

<!-- sq:finding:F48 -->
### F48 — Category consistency has no clause for a declared ref_rule

<!-- sq:finding:F48:body -->
Fixed, and the finding was right about the shape twice over: right that `ref_rules` needed a
clause, and right that adding one and stopping would repeat the mistake that produced it.

## What was actually wrong, named

The clause set was written against the capability *fields* that were in hand — `parents`,
`parent_required`, `subentity_kind` — rather than against the **validator set the rule is
defined over**. The rule's own framing was correct; the enumeration under it was not. So the
question "is this complete?" had no answer, because completeness for a rule about validator
reachability is per validator, and nothing in the code said which validators were accounted
for.

## The audit, all thirteen

Each catalog member is now in exactly one of three buckets, and the buckets are closed against
`VALIDATOR_NAMES` by an import-time assert (`_workflow/_models.py`), the same idiom that
already pins `set(CATALOG) == VALIDATOR_NAMES`.

**Guarded by a clause** — the validator is defined over a declared capability, and some
category can leave it out:

- `parent_in` ← `parents`. Two arms: *contradicted* (the effective set holds `no_parent`, so
  neither `parents` nor `parent_required` can ever be satisfied — the original clause), and
  *unenforced* (neither `no_parent` nor `parent_in` is effective, reachable today only under
  `roster`, whose bundle is empty, so the allowlist is declared and read by nothing).
- the four `subentity_*` checks ← `subentity_kind`. Unchanged, "at least one" as before.
- `supersedes_incoming` ← a declared `supersedes` ref rule. The finding's case.
- `subtask_story_mapping` ← the hosted kind's `maps_parent_story`. Found by the audit, not
  reported: it is gated on a flag on the *kind*, not on the item type, which is exactly why it
  is not one of the sub-entity four. Independently reachable — an adopter who satisfies the
  sub-entity clause by naming one check back still loses the mapping check, silently.

**Needs no clause, unconditionally effective** — `item_status_valid`, `dangling_ref`,
`ref_kind_valid`, `agent_registered`, `no_status_banner`. Every type runs the common core under
every category, so no declaration can put one out of reach. There is no silent-loss shape to
catch.

**Needs no clause, argued** — `no_parent`. It is the inverse of a declaration: it enforces the
*absence* of a parent, so an adopter declares nothing it could stop enforcing. Its failure mode
is the opposite one, and that is the parent clause's first arm.

Two things deliberately excluded, each for a stated reason rather than by omission:

- **`parent_required` gets no clause of its own.** No validator is defined over it under *any*
  category — it is read for hint text and by `subtask_story_mapping`, never enforced — so its
  weakness is not category-dependent and this check is the wrong place to report it. That is
  F47, and it stays F47.
- **Non-`supersedes` ref rules get no clause.** They drive hint text only, which stays live
  under every category, so there is no enforcement half to go dark. The literal `"supersedes"`
  in the clause mirrors the validator's own gate rather than introducing a new binding.

## Driven

Against the real load path (`_build_spec(_bundled_raw())` with per-type fields replaced — the
same raw mapping an override merge produces):

- `decision`→`work` now refuses, naming the rule, the category, the validator, and all three
  ways out. It loaded clean before.
- `bug` given a `supersedes` rule while `work` — refused (no reassignment involved).
- `task`→`records` with the parent fields dropped *and* a sub-entity check named back — refused
  by the story-mapping clause, which nothing else catches.
- `role` given `parents = ["epic"]` — refused by the unenforced arm.
- Still loading: `decision`→`work` with the ref rule dropped; `decision`→`work` naming
  `supersedes_incoming` back in its own `validators`; `bug`→records; `guide`→work; `review`→
  records with sub-entity checks named back. Reassignment stays permitted — only incoherence
  is refused. The bundled spec is unaffected.

## Falsification

Four breaks, each applied in place and reverted by exact reverse substitution with the file
verified byte-identical after: clause 3 disabled, clause 4 disabled, the parent clause's new
arm disabled, and one clause's guarded-name set emptied so the coverage assert should have
caught it. All four reddened — the last as an import-time `AssertionError` carrying its own
message, which is the point of putting it at import rather than in a test.

One control the reviewer will want: `sq workflow lint`'s ref-rule test had a case declaring
`supersedes` on `epic` as its "a real kind still loads" control. That case is now correctly
refused, so the control moved to a `records` type plus a non-`supersedes` kind on a `work`
type — it was asserting the wrong thing, not failing.
<!-- sq:finding:F48:body:end -->

#### Discussion

<!-- sq:finding:F48:discussion -->
<!-- sq:finding:F48:discussion:end -->
<!-- sq:finding:F48:end -->

<!-- sq:finding:F49 -->
### F49 — A broken role override is invisible to sq check

<!-- sq:finding:F49:body -->
Fixed. `sq check` now resolves every `.overrides/roles/<slug>.toml` and reports a file that
will not load as an error-level issue, naming the file, the loader's own cause, and the
commands it blocks.

## Where it went, and why not where the finding suggested

Not a third branch in `sq check`'s own body beside the workflow and playbook ones, but in
`check_override_issues` (`_overrides/_service.py`) — the function that already walks
`.overrides/roles/*.toml` for the stamp obligation and is already wired into `sq check` through
`svc.check()`'s override-issue walk. Same reporting surface, one loop instead of two, and no
more config-loading logic in the CLI module. The workflow/playbook branches sit in `_main.py`
because their failure comes out of `open_service` itself; a role override is never on that
path, so it has no reason to be.

Resolution goes through `resolve_role` — the exact function `sq sync`'s catalog refresh and
`sq role <slug> show` both call — rather than a re-implemented validation, so the report cannot
claim a refusal the consumers do not make, or miss one they do.

## One correction to the finding, driven

The finding's fix shape says "resolve each `.overrides/roles/<slug>.toml` **for a live role**".
Scoping it that way would have left a hole: `sq role <slug> show` resolves an override for a
bundled role that was never activated, so on a roster that does not carry the slug the file is
still reachable and still refusable, with nothing reporting it. Every override file is
therefore resolved.

That makes the two consumers refuse at different times, and the message says so rather than
overclaiming: `sq role <slug> show` refuses now; `sq sync` refuses once the slug is on the
roster. Driven both ways — on a `minimal` roster, a broken `reviewer.toml` gives check exit 3
and sync exit 0, while a broken `manager.toml` gives check exit 3 and sync exit 1.

## Driven

Fresh squad, `sq init --default-names`, `.overrides/roles/reviewer.toml` with `model = "opuss"`
(the value F4's own test uses), fixture loaded eagerly first so a setup mistake could not pass
for the refusal:

- before — `sq check` `✓ no issues` exit 0, `--json` `[]`, while `sq sync` and
  `sq role reviewer show` both exit 1.
- after — `sq check` exit 3 with `error .overrides/roles/reviewer.toml: role override does not
  load: … model 'opuss' is not one of ['haiku', 'inherit', 'opus', 'sonnet'] …`, `--json`
  carrying the same as an error entry, `sq sync` unchanged at exit 1 with the same cause.
- the typo'd-key half (`titel = "Chief Inspector"`) reports too — both the load failure and the
  stamp warning, since they are independent obligations on one file and reporting only the
  second reads as "your override is fine, just re-stamp it".
- a valid override (`model = "opus"`) and a freshly scaffolded one both report nothing.

## Falsification

Two breaks, applied in place and reverted by exact reverse substitution with the file verified
byte-identical after: the resolution check removed entirely (7 of 8 tests red), and the check
made to report unconditionally instead of resolving (6 red — the controls, which is what they
are for: without them, a check that flagged every role override would pass every assertion
about the broken one).

## Adjacent defect found while driving this, NOT fixed here

A *dev*-role override is a documented shape — `resolve_dev_role` merges
`.overrides/roles/<tech>-dev.toml` over the generated `dev_role()` base, and `sq dev add` uses
it. But `sq sync` and `sq role <slug> show` both resolve through `resolve_role`, which has no
dev base, so a partial dev override refuses there. Driven on a fresh squad: `sq dev add --tech
python`, then a `python-dev.toml` containing only `title = "Senior Python developer"` →
`sq sync` exit 1 and `sq role python-dev show` exit 1, both `role override for new slug
'python-dev' is missing required fields: full_name, description, mission`. `sq check` now
reports it too, which is accurate — the squad genuinely cannot sync — but the underlying
refusal is wrong: that file is valid.

Left alone deliberately. `_refresh_catalog_extra`'s own docstring says it skips dev roles
(`is_dev=True`), and it implements that skip by catching `RoleNotFoundError` — which only fires
when no override file exists. Fixing it properly touches sync's skip and `sq role show`'s dev
path, and `resolve_role` cannot simply be widened: sync merges the resolved def's `to_extra()`
onto the item, and `dev_role(tech)` regenerates a pool name, so a naive widening would rename
live dev roles. That is its own analysis, not a quiet adjacent change here.
<!-- sq:finding:F49:body:end -->

#### Discussion

<!-- sq:finding:F49:discussion -->
<!-- sq:finding:F49:discussion:end -->
<!-- sq:finding:F49:end -->

<!-- sq:finding:F50 -->
### F50 — A declared type dispatches to No such command under a broken override

<!-- sq:finding:F50:body -->
Fixed — the note was made true rather than corrected. Every one of the four surfaces now exits
non-zero with the same named cause.

## The fix

`common.spec_error_command(cmd_name, ctx)`, modelled on the `static_alias_is_stale` /
`stale_alias_command` pair the finding points at: when a name reaches the end of the
classification path unresolved **and** a workflow-override refusal is in force, `get_command`
returns a one-off Click command that prints the shared refusal and exits 1, instead of
returning `None` and letting Click answer "No such command" at exit 2. Hooked into both groups
that classify a name against the spec — `_CustomTypeGroup` (root) and `_CustomCreateGroup`
(`sq create <type>`).

`resolve_spec_for_ctx` is untouched. It stays fail-soft by design; the refusal comes from the
*bound refusal string*, not from making the parser raise.

## The part the finding's fix shape did not cover

`RequestContext.spec_error` is set by the root callback, and Click resolves a subcommand name
**before** invoking that callback. So `sq create widget "x"` sees it (the root callback ran when
`create` was resolved) while `sq widget 19 show` does not — the first attempt fixed create and
left the leaf dispatch exiting 2, which is the same asymmetry one level down. `_pending_spec_error`
reads the bound context first and, only at the root group where nothing is bound yet, resolves
once through `bind_active_spec` itself — the same function the callback uses, so the refusal
text cannot drift into a second copy.

`bind_active_spec` moved from `_cli/__init__.py` to `_cli/_common.py` for that call, and is no
longer private: `_cli/__init__` already imports `_common`, so the dependency now runs one way
and there is no `reportPrivateUsage` reach-in.

## Scope of the refusal, stated

While the override is unresolvable, sq cannot know whether *any* unclassified word is a
declared type — so `sq nonsense` refuses too, not just the declared `widget`. That is the
honest answer, and it is the same claim F1 makes: a verdict on this squad's vocabulary must
never be read off the bundled spec. Conversely, with no refusal in force the helper returns
`None` and a typo keeps Click's "No such command" at exit 2, which is the accurate answer
there — pinned as a control.

## Driven

Squad with `[items.widget]` (prefix WID, folder widgets, lifecycle work), two live `WID-*`
items, then one adopter-shaped typo (`prefx`) in that block, verified valid TOML with `tomllib`
before use, and the pre-typo state gated on `sq list` exit 0:

| command | before | after |
|---|---|---|
| `sq list` | 1, named cause | 1, named cause |
| `sq widget 19 show` | 2, `No such command 'widget'.` | 1, named cause |
| `sq create widget "third"` | 2, `No such command 'widget'.` | 1, named cause |
| `sq widget --help` | 2, `No such command 'widget'.` | 1, named cause |

No traceback on any of them, before or after. `sq workflow lint` still exits 1 and diagnoses,
`sq --help` still renders at exit 0, and both remain the surfaces that keep working. With the
typo fixed: `sq widget 19 show` exit 0, `sq nonsense` back to exit 2 with `No such command`.
Outside a squad entirely, `sq nonsense` is unchanged at exit 2.

## Falsification

Three breaks, each applied in place and reverted by exact reverse substitution with the file
verified byte-identical after: the root-group hook removed, the create-group hook removed, and
the helper made to refuse unconditionally (which reddens the healthy-squad control, the test
that exists precisely to stop this fix from swallowing every typo).
<!-- sq:finding:F50:body:end -->

#### Discussion

<!-- sq:finding:F50:discussion -->
<!-- sq:finding:F50:discussion:end -->
<!-- sq:finding:F50:end -->

<!-- sq:finding:F51 -->
### F51 — lifecycle_edges is orphaned by the diagram removal

<!-- sq:finding:F51:body -->
Fixed by deletion. `lifecycle_edges` is gone from `_workflow/_models.py`.

## Checked before deleting, as asked

`sq graph`'s mermaid export is a different path entirely and is untouched: `graph_to_mermaid`
(`_services/_refs.py`) serialises a `GraphNode` ref tree via `_collect_edges`, imports nothing
from `_workflow/_models`, and has no lifecycle notion at all. It renders `flowchart LR` over
item refs; `lifecycle_edges` fed a per-type `stateDiagram-v2` in the cheatsheet template, which
no longer exists.

Repo-wide grep across `.py`, `.j2`, `.md`, `.ts`, `.toml` and `.json` found no caller. It was
never exported through `_workflow/__init__.py`'s shim list, so nothing outside the module could
reach it. `uv run vulture` no longer reports it; every remaining entry is a pre-existing
Textual/pydantic-shaped false positive. Full non-slow suite green after removal, so nothing
reached it dynamically either.

## Why deletion rather than a note

The repo's vulture convention is that `ignore_names` is for entries vulture *cannot see used* —
false positives — and that genuinely dead code is not silenced by allowlisting. This is
genuinely dead, so keeping it would mean keeping the vulture hit too, and the finding's own
point stands: an orphan reads as live API to anyone grepping for a lifecycle helper.

There is one named future caller — BUG-732 proposes a machine-readable transitions surface and
its body cites `lifecycle_edges` as a building block. It is a six-line pure comprehension over
`lifecycle_states_in_order`, which stays, so re-deriving it when that lands costs nothing.
BUG-732 has a comment recording this so its fix direction does not send someone hunting for a
function that is not there.

## Also corrected, one level up

`lifecycle_states_in_order`'s docstring still justified itself by "diagram-rendering callers (a
Mermaid `stateDiagram-v2`)" — the caller the same removal deleted. It now names its real one:
`WorkflowSpec.first_dropped_status`, which picks a status out of a machine for generated text,
where a hash-ordered pick would rewrite generated files at random. Same class of residue as the
finding itself, one function over.

## Falsification

The relevant break is not on the deleted function (there is nothing left to break) but on the
claim that distinguishes the two: `lifecycle_states_in_order` was made to raise, applied in
place and reverted by exact reverse substitution with the file verified byte-identical after.
Six tests reddened — so the asymmetry the finding asserts is real, and the surviving half is
load-bearing rather than a second orphan.
<!-- sq:finding:F51:body:end -->

#### Discussion

<!-- sq:finding:F51:discussion -->
<!-- sq:finding:F51:discussion:end -->
<!-- sq:finding:F51:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T14:49:06Z] Paul Reviewer:
  - Cosmetic and sanctioned observations, recorded so the sweep is complete without inflating the finding list. Sanctioned and verified against the named clause: every ref-kind literal and VALID_REF_KINDS check (ADR-49, as amended 2026-08-03 to nine kinds); all ROSTER_ROLE/SKILL/OPERATOR literals (the loaders roster type-key lock -- driven, an override adding a fourth roster type is refused); PERMITTED_EXTRA_SKEW on the resolved-skill cache (ADR-663 section 1, verbatim); the closed roster/work/records category axis client-side (ADR-541); active_backends defaulting to claude_code (ADR-141); the import-time CLI command tree (ADR-263 option 3 + ADR-534); _engine._env_cache and the backend registry (ADR-534 caches-are-code, both already allowlisted with reasons).
  - Cosmetic, no adopter-visible consequence: the dead item_type parameter on format_id/allocate_id; SquadsDB.backrefs hand-rolling the prefix split and ref match that _models/_item.py already provides; _models/_metadata.py using literal role/skill keys (the layering forbids importing _workflow from _models); _markers.py hardcoding the three bundled kinds (emits byte-identical strings to the generic path); _SIDE_PRIORITY ordering side states by five bundled names (display order only); custom_item_skill_name duplicating item_skill_name byte-for-byte; the seven optional-spec defaults in _badges.py (unreached -- every production call site threads a spec, and the frozen-migration-runner justification in the docstrings is false, _migrations never imports _badges); the roster epilogs hardcoding status Archived as the retirement example; several hand-rolled rpartition splits where prefix_from_id exists.
  - One structural conclusion worth recording separately: the module-level shim surface in _workflow/__init__ (WORKFLOWS, SUBENTITY_WORKFLOWS, ALLOWED_PARENTS, TERMINAL and the whole free-function block) has ZERO production consumers -- confirmed independently by two shards. It should not be closed citing ADR-249: that decision names these explicitly as a latent hazard and a documented stale-import footgun, and its selected option says the module-level machinery ARE DELETED and the free functions become methods on WorkflowSpec. The rebind machinery was deleted; the dead surface was not. Unfinished execution rather than a sanctioned exception. Three of the four are also plain mutable dicts (driven: assignment succeeds) while PLAYBOOK was deliberately wrapped in MappingProxyType with a comment arguing exactly this case. active_spec() is the concrete trap -- the name asserts active, the body returns the bundled spec.
- [2026-08-03T14:49:12Z] Theo Writer:
  - Operator-name purge, docs half done. Scope was docs/, PYPI.md, CHANGELOG.md, CLAUDE.md; replaced with the fixture placeholder `Alice Tester` / `op-alice`, and I drove `sq operator add "Alice Tester"` first to confirm the derived slug really is `op-alice` before writing it into examples.
  - Changed (4 hits, 3 files): docs/agents.md greeting-tone illustration; docs/roles.md operator-add example (its trailing comment names the derived slug, so both halves had to move together); docs/workflow.md operator example block (3 lines) and the reflog `actor` field table. Comment-column positions preserved exactly — verified against HEAD, unchanged at cols 47/48/48.
  - CHANGELOG ruling: exactly one hit, at line 848 in the released [0.3.0] section, and I changed it. It is the greeting entry using the name as an EXAMPLE of a matched-tone greeting — the same illustration as the docs/agents.md hit, not an authorship credit. Changing it alters no claim about what 0.3.0 shipped, so the historical-record concern does not apply. No entry anywhere in the file names him as author or contributor, so nothing in the other direction to preserve.
  - Left deliberately, both reported rather than fixed. (1) PYPI.md line 117 carries `itemName=pierre-chat.squads-vscode` — that is `publisher`.`name` from the extension manifest, i.e. the canonical Marketplace identifier; changing it 404s the link. Same exempt class as LICENSE/pyproject. If the operator wants it gone the fix is a Marketplace publisher rename plus republish, not a docs edit. (2) CLAUDE.md needed ZERO edits from me: both hits sit inside the squads:start/end managed region (229..341).
- [2026-08-03T14:49:30Z] Theo Writer:
  - The two CLAUDE.md hits are NOT the same kind of thing, and only one is a leak — worth separating so the dev does not purge the wrong one. Line 279 ("it's Pierre") is a literal string in `_rendering/templates/claude/claude_section.md.j2` line 50 — a real leak, his change covers it, I did not touch the template. Line 256 (`- **Pierre Chat** (`op-pierre`)`) is NOT a template string: it renders from `{{ o.full_name }}` in the operators loop, i.e. this squad's live operator roster (OP-10). That is sq-managed squad data, which the operator's own ruling explicitly permits, and purging it would be both wrong and futile — `sq sync` regenerates it from the roster. @manager please make sure the template pass does not try to neutralise the roster loop.
  - Adopter-facing neighbour sweep, as asked. One genuine finding: 16 `github.com/TheCaptainCat/squads` links across CHANGELOG.md and PYPI.md carry the repo owner's personal handle. All structurally load-bearing — CHANGELOG.md 1012-1017 are the Keep-a-Changelog version-compare link definitions, and PYPI.md 124-137 are the doc links, which cannot be relative on a package page. Same judgement class as the publisher id: a handle in a URL that must resolve, not example content. Reported, not touched.
  - Two axes I checked and found CLEAN, stated so rather than padded. (1) Illustrative ticket IDs (ROLE-000002, EPIC-000009, TASK-000011, …) are generic ID-format examples, not references to this repo's real tickets. (2) No doc in scope uses squads itself as the illustrative project — docs/tutorial.md runs a fully fictional one (authentication platform / login / lockout counter / argon2id), which is the pattern the bundled template that was caught should be moved to. The `uv run` and `CI` mentions I found are adopter-relevant (installing from source, gating their own CI), not our dev process.
  - Process note on my own probe: my first confirmation sweep ran `grep -rniE pierre ... | grep -viE "claude"`, and the exclusion silently swallowed every CLAUDE.md hit because the FILENAME contains "CLAUDE" — it would have let me report the file clean. Caught by re-running without the filter. Flagging because a path-matching exclusion in a content grep is a trap anyone doing this purge in other trees will hit.
- [2026-08-03T15:21:59Z] Olivia Lead:
  - All 29 findings now have a home on TASK-737 (addresses), one subtask per coherent surface: ST1 F2/F3/F27; ST2 F1/F4/F11/F12/F13/F16/F19/F29; ST3 F5/F15/F20/F21/F28; ST4 F6/F7/F8/F14/F26; ST5 F9/F10/F24/F25; ST6 F22/F23 (typescript-dev); ST7 F17/F18. Nothing is deferred to a later release, per op-pierre.
  - No deferral comment was ever written here, so there is nothing to retract: F17, F18, F19, F28 and F29 went into the task rather than getting a 0.14 home.
  - Two halves are scoped out of their subtask and named as gated, not dropped. Opening the ref-kind vocabulary (F29 second half) waits on the decision board notice 8 commissions, since ADR-49 closes the vocabulary for 1.0 with no escape hatch; ST2 fixes only the inert-declaration half. F23 declared-label half needs a machine surface for sub-entity field vocabulary, which does not exist anywhere today: ST3 adds the catalog, ST6 consumes it.
  - Two regroupings against the brief, both stated in the subtask bodies. F28 moved out of the migrations group into ST3, because its root cause is F20/F21 (a bundled field-code literal) and its guard is the same tests/meta field-code guard those fixes widen. F7, which no group named, is in ST4 with the rest of the bundled-template work; the tech-writer half is already done and ST4 says so.
  - Findings stay Open until the fixing dev closes each one Fixed citing its fix, per board notice 15. @manager TASK-737 is Draft and needs promoting at dispatch.
- [2026-08-06T19:35:14Z] Ada Typescript:
  - ST6 landed two VS Code fixes beyond F22/F23, routed to me by the manager but with no finding of their own on this review — recording them here so the sweep record is complete and you can file or fold them as you see fit. Both are the sweep pattern (a client assumption standing in for what sq actually declares/accepts) and both are covered by new tests.
  - (1) Records failed CLOSED on a type-catalog failure. recordsTreeDataProvider.ts fed NO_CATEGORIES into buildRecordsView, which then has no records type to bucket, so the panel rendered zero nodes — and with no viewsWelcome behind it, an empty panel indistinguishable from an empty squad. It is the one sibling where the type catalog is load-bearing rather than decorative (the work tree and the roster still have rows without it), so it now reports the failure as an error node plus a notification, and a genuinely empty successful build gets a placeholder naming which empty it is (recordsView.recordsEmptyStateMessage).
  - (2) The squad_dir reader missed valid TOML. domain/squadDir.ts hand-rolled /^\s*squad_dir\s*=\s*"([^"]*)"/m, so a single-quoted value fell through to the default and squadWatcher watched a directory that does not exist — auto-refresh then silently never fires. Driven against a real squad: sq reads squad_dir = 'board' fine (exit 0, roster listed). The reader now handles both TOML string flavours, all three key spellings, escapes inside a basic string, and is anchored to the document root so a squad_dir under a [table] is ignored the way sq ignores it.
  - Adjacent, NOT fixed, and worth a finding of its own if you agree: the mermaid graph node-click round trip is lossy for a declared prefix containing an underscore. graphDiagrams.mermaidNodeId folds every non-word character to _, and previewDocument.ts:349 inverts it with replace(/_/g, "-") — so MY-WIDGET-19 round-trips correctly but an underscored MY_WIDGET-19 comes back as MY-WIDGET-19 and the click navigates to an id that does not exist. Same family as F22, but fixing it means changing the encoding on both ends (and the comment claiming parity with the core _safe_id), which is past ST6 scope.
- [2026-08-06T20:14:19Z] Catherine Manager:
  - F41 (the dead scale suite) is a duplicate of BUG-740, which I filed from the same discovery and which a developer is fixing now. Marked WontFix on the review, tracked on the bug -- not dismissed. The reviewer independently confirmed all five tests fail in setup and that it predates ST1, which matches what I drove at 59fd0eb; the responsible commit is c9cc1b4, 2026-07-31.
- [2026-08-06T20:26:36Z] Theo Writer:
  - docs/migration.md reordered: the TL;DR now runs `sq check` BEFORE `sq sync`, with a second `sq check` after as confirmation. Reproduced the strip first — a hand-edited Draft roster entry, then `sq sync` deletes `.claude/agents/python-dev.md` and removes the CLAUDE.md line at exit 0 with no message, while `sq check` reports it at error level, exit 3. Then drove the corrected order end to end: check names the entry, one `--force` transition fixes it, sync keeps the pointer and the CLAUDE.md line, second check clean.
  - Pitched proportionately rather than as alarm, using the mitigations: the paragraph says plainly that nothing is lost either way, that durable definitions under `squads/agents/roles/` are never touched by sync, and that restoring a live status brings the pointer and the CLAUDE.md line back inside that same command with no second sync. I verified that reversibility myself before writing it — reactivate with no sync, pointer and line both back, check clean. The argument for checking first is therefore convenience, not data safety, and the doc says so.
  - Three surfaces reconciled without touching the generated one. The CHANGELOG entry now says "move it first — before `sq sync`" instead of the vaguer "before anything else", which matches the doc. The version notice is untouched: both strings (`_cli/_common.py:828` and `_cli/_migrate.py:50`) still say run `sq sync`, and migration.md now explains why they differ — the notice addresses the ordinary refresh case, the doc's order is for moving between versions. @manager if you would rather the notice itself change, that is the code route you flagged; I have not touched it.
- [2026-08-06T20:26:45Z] Theo Writer:
  - Corrected the Draft-population claim in the 0.13.0 notes, and verified QA's finding independently at the tags rather than taking it on report. At v0.12.2 all four roster create sites in `_services/_roster.py` pass `status=STATUS_ACTIVE` explicitly, and the role CLI has zero `status` verb hits at v0.12.2, v0.12.0, v0.11.0 and v0.1.0. So no released version could put a roster entry at Draft.
  - The old sentence "Only `--force` could ever put it there" was doubly wrong: the roster `status` verb that `--force` belongs to only exists in 0.13, so it could not have produced a pre-existing Draft entry either. Replaced with the stronger true claim — no released version could, every version back to the first created roster entries directly at Active and none had a roster status verb, so reaching Draft took a hand-edited frontmatter file or a custom lifecycle that declares it. Also folded the ordering fix into the same sentence ("move it first — before `sq sync`").
- [2026-08-06T21:09:27Z] Pierre Chat:
  - My name in the github.com/TheCaptainCat/squads URLs is not a problem -- that is the project home. Same for the pierre-chat marketplace publisher id, the LICENSE and pyproject author. What I wanted removed was my name used as EXAMPLE content in adopter-facing prose, CLI help and bundled templates, which is done.
- [2026-08-06T21:13:23Z] Theo Writer:
  - CHANGELOG compare-link block rebuilt. Was 5 definitions for 18 headings with `[Unreleased]` still comparing from v0.4.0; now 17 definitions covering every heading that has a tag. Generated the chain from `git tag -l` rather than typing it, after `git fetch --tags` first, and followed the existing URL shape exactly (compare/vPREV...vCUR, with the oldest release pointing at releases/tag/v0.1.0).
  - Validated structurally rather than by eye: every heading now resolves except `0.12.3` (left alone per the brief); zero orphaned definitions; every `vX.Y.Z` named in a URL exists as a real tag; and the compare chain is contiguous — each definition left side equals the previous version, no gaps or skips across all 16 tags.
  - Removed the `[Unreleased]` definition: there is no `## [Unreleased]` HEADING anywhere in the file, so it referenced nothing and had been dangling at a two-releases-stale tag. This repo names its unreleased section by its target version, so the working equivalent is `[0.13.0]: compare/v0.12.2...HEAD` — which renders as a live link showing exactly what is unreleased (132 commits), and cannot 404 because HEAD always resolves. Noting a runbook divergence for @manager: the releasing-squads skill step 2 says "move `[Unreleased]` into the new version section", which assumes a section this file has not had for 18 versions. The runbook and the file should agree; my change makes the release step a one-token edit (HEAD -> v0.13.0) but the skill wording still describes the other pattern.
- [2026-08-06T21:14:12Z] Theo Writer:
  - Judgement call 1 — 0.12.3: I agree with folding, for a stronger reason than the file describing releases that exist. That work has never reached a user and cannot. There is no v0.12.3 tag, and publish.yml is gated on `tag == pyproject version`, so the pipeline never fired: nothing went to PyPI, and because the extension is versioned from the core at publish time, no 0.12.3 VSIX was ever built either. A `## [0.12.3]` heading therefore advertises a version an adopter cannot install by any route, while the work it describes will actually first reach them as part of 0.13.0 — which currently under-claims by exactly that much.
  - Two concrete consequences of folding that whoever does it should not discover halfway. (1) The section opens "**No change to the `sq` CLI in this release.** The Python package behaves exactly as 0.12.2 did" — false the moment it sits under 0.13.0, so folding is not a pure move; that preamble has to be dropped or rewritten. (2) 0.13.0 already has a VS Code entry (the sub-entity discussion preview), and 0.12.3 carries a whole `### VS Code extension` section plus a `### Documentation` section, 12 bullets between them — folding naively leaves 0.13.0 with two separate VS Code areas. They want merging into one, which is a rewrite rather than a paste.
  - Judgement call 2 — the unreleased target: `compare/v0.12.2...HEAD` is right, and committing a `v0.13.0` comparison now would be wrong. Per the release runbook the tag is created when the operator PUBLISHES the GitHub release, which is after the CHANGELOG is merged — so a `compare/v0.12.2...v0.13.0` line committed today names a tag that does not exist and 404s for anyone reading CHANGELOG.md on main between merge and publish. HEAD never 404s; verified the range resolves locally at 132 commits. At release time it is a one-token edit.
  - One thing I am NOT sure of, flagged rather than guessed: whether the cutter should switch `[0.13.0]` from HEAD to the tag during prep (before the tag exists, so briefly broken on main) or as a follow-up after publishing. The runbook does not say, and the right answer depends on whether anyone reads CHANGELOG.md on main in that window. @manager worth pinning in the skill either way — this is the second release running where the block went stale.
- [2026-08-06T21:34:28Z] Theo Writer:
  - Compare block updated for the v0.12.3 publish, and I re-fetched tags and verified the tag myself before touching anything rather than taking the report — v0.12.3 exists at d0ca7b5, 17 tags now. Added `[0.12.3]: compare/v0.12.2...v0.12.3` and moved `[0.13.0]` to `compare/v0.12.3...HEAD`. Both ranges are real and non-empty: 25 commits in v0.12.2..v0.12.3, 109 in v0.12.3..HEAD.
  - Re-ran the structural validation rather than assuming the two edits were safe: 18 headings, 18 definitions, 17 tags. Every heading now resolves (0.12.3 was the only gap and is closed), zero orphaned definitions, every vX.Y.Z named in a URL is a real tag, the compare chain is contiguous with no gaps or skips, and [0.13.0] compares from the newest tag — checked programmatically against `git tag -l`, not by eye.
  - Runbook fixed (SKILL-508, via `sq skill 508 body --file`, markers untouched — verified no marker line added or removed). Step 2 no longer says to move an `[Unreleased]` section; it states the section is named by its target version and there is nothing to move. A new step-2 bullet covers the compare block: one line per heading or it renders as literal text, the unreleased line compares from the previous tag to HEAD because its own tag does not exist until publish, generate from `git tag -l`, and the four checks to run after. New §7 "After it is published" carries the post-publish follow-up you ruled on — switch the HEAD comparison to the tag, add the next unreleased line, `git fetch --tags` first because the tag is created on the remote.
- [2026-08-06T21:34:41Z] Theo Writer:
  - Two things I did wrong in this pass, both recovered, both worth knowing before you stage.
  - (1) I destroyed the skill body with a probe. I ran `sq skill 508 body -m "probe"` to test whether the verb was permitted on a custom skill — `body` REPLACES, it does not append, so that one command wiped all 66 lines of the runbook. Recovered with `git checkout` on the file (it was committed), verified 7 section headings back and a clean diff, then did it properly: extract the body between the markers, edit, write back with `--file`. The lesson generalises beyond me — `sq <type> <n> body -m` is a full replace, so never use it to probe, and read the body first or use `--append`.
  - (2) That recovery left the index ahead of the restored file, and `sq` refused the next write with "on-disk frontmatter has diverged from the index (updated_at) — run `sq repair`". Repair fixed it, but repair also RENORMALISED the item order in `.squads.json`, so `git diff --stat` on that file now reads 6561 insertions / 6561 deletions. I checked it rather than leaving you to wonder: parsed both versions and compared semantically — 714 items both sides, identical id set, identical key order within items, and exactly ONE field changed in the entire index (SKILL-508.updated_at, which is the legitimate result of my edit). The rest is pure reordering. A second repair is a byte-for-byte no-op, so it is stable and not a churn-every-time problem — the committed file had just drifted into a different order through incremental writes. @manager your call whether to take the renormalised index or restore it, but the huge diff is not a sign anything went wrong.
- [2026-08-15T14:43:12Z] Paul Reviewer:
  - Delta review of the four unreviewed subtasks - ST2 (with its F46 pass), ST3, ST4, ST5 - read at e7b25d7 in an isolated worktree, effort weighted by blast radius as briefed. All four verdicts: sound and genuinely done. Four new findings: F48 and F49 medium, F50 and F51 low. Nothing rises to changes-requested; F48 is the one I would want closed before the release.
  - The tenth adjacent defect, as predicted, is F48: F46's category-consistency check is written against the effective validator set and has a clause for subentity_kind but none for ref_rules, so decision-to-work silently turns off supersedes_incoming - the same silent-declaration shape, on a reassignment F46's own body lists as deliberately permitted. Driven end to end, with the warning present before and absent after and all three gates clean. The second newly-reachable one is F49: F4 made role overrides refusable, and the refusal reaches sq sync and sq role show at exit 1 but not sq check, which reports the workflow and playbook counterparts - so a squad can now read "no issues" while sq sync is impossible.
  - Falsifications spot-checked rather than taken on report: I broke twelve behaviours in place across the four subtasks and watched the intended tests redden, restoring each byte-identically - the spec_error raise (10 red), the category check and its clause 2 separately (12 and 4), the badge accessor (3), the selected-entry clause (1), the authors flag (9), example_assignee_slug (3), the story prefix (13), the catalog transaction (7), bundled-skill seeding (2) and RoleView.mission (13). No vacuous shape found; the two guards most at risk of it - the bundled-vocabulary scan and the broken-override sweep - both carry real floor tests, and the one weak-looking assertion I found (an "epic not in output OR widget in output" disjunction) still holds for the right reason.
  - Both load-bearing claims independently checked and reported on their own subtasks: ST2's two contradictions of F46 both hold, and ST5's _is_legacy_skill_body reasoning holds while its reported blast radius belongs to a different break. Gates on the reviewed tree: ruff check clean, ruff format clean, sq sync a byte no-op, sq check clean. I did not run the full suite, per the brief. @tech-lead @manager for F48 and F49; @architect F48 is adjacent to the F46 rule you own.
- [2026-08-15T14:47:51Z] Theo Writer:
  - Recast the three bug entries the developer drafted, rather than editing his — reverted his prose first and wrote from the shipped behaviour, which I drove for all three. His draft was good and two things in it were genuinely better than a summary would have given me: that the refusal is deliberately not a prompt because the callers are agents, and that `--append` is unchanged. Both survive in my version, reframed as what an adopter does rather than why it was built.
  - What I changed and why. (1) The `body` entry was written from the incident that prompted it ("a single command run to find out whether the verb was even permitted"), which is my accident, not an adopter story — recast to the general case, any second write. His draft also buried the rule an adopter needs to PREDICT the behaviour in a closing aside; "authored" vs "not empty" is now its own paragraph, because without it nobody can tell whether their next `body` call will fire. (2) The `role activate` entry read as design rationale ("the same split every other roster verb keeps") and omitted the action item: this is a behaviour change on a shipped command, so a script that calls `activate` to ensure liveness now gets a non-zero exit where it used to get success. That is the sentence an adopter needs and it was not there.
  - (3) The reflog entry made a claim about this change that is not true: it listed "the workflow guide table" among the three wrong copies. That table was already corrected to sixteen earlier the same day by ec9fb87, so this work did not fix it. Recast to what actually changed — two hand-maintained lists collapsed to one declared vocabulary, so they cannot drift again. I also corrected my OWN first draft of the docs/workflow.md preamble, which said the table is "generated from" the single source: the option help is generated, the table is checked against it. Wrote "both come from one declared list" instead.
- [2026-08-15T14:48:08Z] Theo Writer:
  - Verification for the three entries, all driven old-vs-new in throwaway squads. `body`: first write over a fresh scaffold succeeds; second write refuses naming "3 lines", quotes the opening lines, exit 1, and the file is byte-identical afterwards (md5 unchanged) — so the doc claim that you can run it to find out whether a body is occupied is literally true, not approximately. `--append` and `--force` both work. All four doors confirmed: item, sub-entity, custom skill, and I re-ran the exact `sq skill 508 body -m "probe"` that destroyed the release runbook — it now refuses with "… (89 more lines)" and the runbook is intact.
  - The scaffold subtlety verified both directions, since it is the part an adopter cannot guess: a fresh task body is NOT empty (it holds `## Description` + a TODO stub), so an emptiness test would have refused every first write. And under a `.overrides/templates/items/task.md.j2` carrying a different scaffold, the first write still succeeds — the guard re-renders the ACTIVE template, so a project scaffold is recognised as unwritten rather than mistaken for prose. That is the claim in the entry and it is driven, not inferred.
  - `role activate`: my first probe was wrong and I fixed the probe — I used `python-dev`, a dev role, which fails for an unrelated reason ("no predefined role and no project override"). Re-ran with a bundled role on a minimal squad: activate creates (exit 0), retire, then activate refuses naming the actual status and the exact remedy `sq role qa status Active` (exit 1, status unchanged), the remedy works, and activating an already-live role is still exit 0. `reflog`: extracted the op list from `--help` at COLUMNS=400 (Rich truncates it at normal width) and diffed it against the docs table — 16 each, IDENTICAL, `retype` present in both.
  - One claim I did NOT write in, because I could not drive it: that the remedy names a project-renamed live status rather than a hardcoded "Active". I verified it reads `Active` on a bundled squad; my attempt to rename the roster lifecycle to prove spec-derivation produced 6 lint errors (other roster types bind the same lifecycle) and I stopped rather than assert an unverified mechanism. @manager if that matters for the entry, it needs someone to build a valid renamed-roster override.
- [2026-08-15T14:48:19Z] Theo Writer:
  - Doc sites: the two he flagged plus three more I found by grepping every site that describes the body verb, so the rule is stated wherever it is taught rather than only where he happened to look. docs/roles.md:98 (the custom-skill example) and docs/workflow.md sub-entity reference — both his. Added: docs/faq.md "Can I edit the markdown by hand?", which is the reference answer for how bodies get set, and docs/agents.md operating rules, which is where an AGENT learns it and therefore where it would have saved me. Also rewrote the docs/workflow.md "Op names" preamble, replacing "this table is behind the code" (no longer true) with the single-source fact.
  - Deliberately did NOT annotate the ~14 example sites (tutorial, recipes, adoption, internals) that merely USE `body` on a fresh item — the guard never fires there and a note at each would be noise. Checked the one that could have been a real trap: docs/adoption.md step 2 tells an adopter to `create` and then move legacy content in with `body --file`. Drove it — that is a first write over the scaffold, exit 0, unaffected. Only a second write refuses. The documented migration flow needs no change.
- [2026-08-15T15:13:00Z] Elias Python:
  - F48, F49, F50, F51 all Fixed — bodies carry the driven evidence, the falsification breaks and the corrections. Gates: ruff + ruff format + pyright clean with --all-extras, sq check clean, 3582 passed across unit/meta/cli/integration/service/tui (17 new tests). Full suite with --run-slow is the main loop's.
  - F48 was fixed as a class, not a clause: the reachability rule is now a clause registry closed against VALIDATOR_NAMES by an import-time assert. The audit found a second unguarded validator nobody reported — subtask_story_mapping, gated on the hosted kind's maps_parent_story — and states why parent_required (F47's territory) and the non-supersedes ref kinds need no clause. F46's body is corrected: `decision`->`work` no longer loads, and the correction names why the original enumeration was wrong.
  - New defect found while driving F49, not fixed here and worth filing: a partial *dev*-role override is a documented shape (resolve_dev_role merges it over the generated base, sq dev add honours it) but sq sync and sq role <slug> show both resolve through resolve_role, which has no dev base — driven, both exit 1 on a python-dev.toml containing only a title. sq check now reports it too, which is accurate but the underlying refusal is wrong. Full analysis at the end of F49's body; resolve_role cannot simply be widened (sync would rename live dev roles). @reviewer
  - Observations: the ItemSpec "not yet consumed by the engine" docstring is corrected. is_lane_exempt(slug, None) — checked, and it is a latent API hazard rather than a live defect: the sole production caller passes _default_role_slug(db), which already resolves the bundled fallback itself with a documented rationale, so no wrong answer is reachable today. _probe_spec — checked and the premise does not hold: `Retired` is not in the bundled spec at all (the agent lifecycle uses Active/Archived), so the rename collapses nothing; 23 statuses before, 23 after. The --priority/"Size" label observation is the client's half, untouched.
- [2026-08-15T15:22:23Z] Ada Typescript:
  - F45 is Fixed, with its body corrected: the trigger it named — a hand-authored mermaid fence in a dossier body — does not exist and never did. renderOutcomeHtml, the comment renderer and the sub-entity body renderer all pass renderMermaidFences false, so a fence in an item body renders as plain code and never becomes a diagram. renderWorkflowHtml is the single caller that passes true. My own report was wrong on that point; correcting it rather than leaving it as filed.
  - What was actually reachable, driven: the bundled cheatsheet emits zero mermaid now (sq workflow --raw returns no fences, workflow.md.j2 has none), but a project .overrides/templates/workflow.md.j2 carrying a fence flows through sq workflow --raw verbatim and renders as a live diagram in the cheatsheet panel. So the guard was still owed — adopter-triggerable, just narrower than filed. One thing left read rather than driven: the stamping loop only matches mermaid flowchart node ids, so another diagram type may produce no match at all; that is renderer behaviour I did not exercise.
  - Guard: the source element declares whether its node ids are item ids (data-sq-item-nodes, emitted by buildGraphSection and nothing else) and the post-render pass stamps only when it does — opt-in by construction, so anything else is inert by default. The gate is lifted out of the emitted page and executed in tests, the same way F32 decoder is. Falsified three ways, each reddening exactly the matching test. Gates: typecheck, lint, format clean; 613 unit tests in 32 files; 19 canary against the repo sq build (check sq --version first — a stale 0.12.1 sits earlier on PATH here and reports drift that is not there).
  - On F44, asked whether the two mermaid escapings should match: no requirement, and I would not couple them. Neither side decodes the other output — the client builds its diagram source itself from sq tree/sq graph --json and never parses sq graph --format mermaid, which is display-only for a terminal or a file. What the core needs is any INJECTIVE encoding, to fix the half F44 shares with F32: a fold merges two distinct items into one node before any click is involved. The one case that would force agreement is a client that renders core-produced mermaid text directly; nothing does that today, and if that ever lands the encodings have to be shared rather than merely similar.
- [2026-08-15T15:24:10Z] Theo Writer:
  - Three entries written for the latest round. Change 3 (category consistency) EXTENDS the existing shadowing-override entry rather than becoming a second one, as you asked — it is a new member of the "broken override is a hard stop at load" class that entry already describes, so it lands in that paragraph as "a type may not declare a behaviour whose category then checks nothing". Also added a row plus a worked rule to docs/overrides.md § "When an override is wrong", whose table enumerates the ways to reach a hard stop and would otherwise have been wrong by omission.
  - Change 1 verified including the scope correction: a broken `.overrides/roles/qa.toml` on a MINIMAL squad where qa was never activated is still reported at error level, exit 3 — and `sq role qa show` does resolve it, so the report is real rather than defensive. Pre-fix baseline confirmed at 8015ac9^: only the stamp warning, exit 0. Drove all three ways out of change 3 too, including the third — naming `validators = ["supersedes_incoming"]` under `category = "work"` is accepted, exit 0 — and confirmed the refusal fires at ordinary command load (`sq list` exit 1), not only under lint.
  - TWO corrections to the summary on change 2, both found by driving, and the entry reflects the driven behaviour rather than the brief. FIRST: `sq <type> --help` does NOT refuse. On a broken override `sq --help`, `sq create --help`, `sq task --help` and `sq workflow --help` all exit 0 and print normal help — verified across two different breakage shapes. Only `sq incident --help`, for a type that exists ONLY in the override, exits 1, which is coherent (the file that would describe it is the file that will not load). I wrote the precise split instead of the blanket claim.
  - SECOND, and this is the substantive one: the before/after is not what the summary said. A BUNDLED type under a broken override ALREADY refused at exit 1 with the named cause before this change — I checked `sq task 9 show` and `sq create task` against 8015ac9^ and both were exit 1 already. What actually changed is the case of a type declared ONLY in the override: pre-fix `sq incident 1 show` gave `No such command 'incident'` at exit 2, now exit 1 with the cause. That matches the stated mechanism exactly — a custom type gets its command group FROM the spec, so a spec that will not load means the group was never registered and Click had nothing to match. My first draft repeated the summary and said `sq task` reported "No such command"; that was false and I rewrote it. The entry now says bundled-type commands are unchanged, which is both true and the more useful framing — the defect hit the adopter who had customised most.
- [2026-08-15T15:42:46Z] Elias Python:
  - F47 Fixed. Recommendation was neither arm as posed, and the reasoning is in the finding body. parent_required IS enforced — driven, bundled spec, no override: add-subtask --story on a parentless task exits 1 naming "feature", and subtask_story_mapping reports the same as a sq check error. So "drop it" is refuted on evidence, and it is not derivable from the multi-valued parents allowlist.
  - Why not enforce on the bundled spec: gate() and report() run ONE effective validator-name set, so there is no "error at create, quiet on history" position. This repo has 32 of 333 tasks with no parent — enforcing in the work bundle turns them into sq check errors, and no migration can invent a parent. Built parent_present instead: closed-catalog, in no category bundle, opt in via a type own validators list. Bundled behaviour byte-identical.
  - The clause-registry exclusion was an accurate report of a hole in the catalog, not a property of the field — with a validator now defined over its requiredness it enters the registry, and parent_present is classified unguarded for the same reason no_parent is. Second gap found and closed while working it, reported by nobody: parent_required naming a type the parents allowlist excludes loaded clean, leaving the story mapping dead in both directions. Refused at load now.
  - F44 Fixed, and matched to the client — the finding left that open, but there is one correct answer: any encoding into mermaid ids [A-Za-z0-9_] that folds - to a single _ is non-injective (A-005fB and A_B collide; doubling collides too), so fixed-width escaping is the only context-free option. The half the finding did not name: there were no node labels, so the node id was the visible box text — escaping alone would have made every node read TASK_002d1. Nodes now carry the real id as a label.
  - Gates: ruff + ruff format + pyright --all-extras clean; unit/service/cli/integration/meta/tui green (3597 passed, 1 skipped) — full suite with --run-slow is yours. sq check clean. Every mechanism falsified and restored by exact reverse substitution. @manager REV-736 has no Open findings left on the Python side.
- [2026-08-15T15:46:55Z] Catherine Manager:
  - Approved as second party. 51 findings across seven read-only shards: 48 Fixed, 3 WontFix with reasoning that engages the evidence, none left Open. Verified by me at e4a5f6: full suite 3603 passed with --run-slow including the scale bounds, pyright 0 errors, ruff and format clean, sq check exit 0.
  - The sweep found more than it was commissioned to find. Four findings (F44 F45 F46 F47) and two bugs came out of fixing the first forty-odd, and F46 -- category reassignment loading clean while contradicting itself -- was an unmet EPIC-538 acceptance bullet that nothing tracked. Ten consecutive fix rounds each left an adjacent gap; the eleventh closed F48 as a class rather than a clause, by pinning the category-consistency registry against the validator catalog with an import-time assert. That is the first round that ended without one.
<!-- sq:discussion:end -->

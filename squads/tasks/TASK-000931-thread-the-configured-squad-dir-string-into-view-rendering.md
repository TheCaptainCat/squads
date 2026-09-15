---
id: TASK-931
sequence_id: 931
type: task
title: Thread the configured squad_dir string into view rendering
status: Done
parent: FEAT-906
author: tech-lead
assignee: python-dev
refs:
- ADR-880:implements
- REV-926:addresses
subentities:
- local_id: ST1
  title: Thread config.squad_dir string into the view-rendering context (F11)
  status: Todo
  story: US2
created_at: '2026-09-08T13:52:17Z'
updated_at: '2026-09-10T09:40:29Z'
---
<!-- sq:body -->
## Scope

Fixes REV-926 F11 — a nested `squad_dir` still renders two different values in one template
corpus, narrowing rather than closing F2's regression.

## The defect

`_squad_dir_display` (`src/squads/_views.py`) recovers the squad folder name with `Path.name`
from the resolved absolute `Path` the view-rendering path threads. That equals the configured
value only when `squad_dir` is a single path segment, and nothing enforces that:
`SquadsConfig.squad_dir` (`_models/_config.py`) is a bare `NonEmpty`, and
`sq init --squad-dir docs/squad` is accepted and works today.

With a nested value, `sq skill squads show`/`sq skill sq-memory show` (view-rendered) print
`squad/` while `CLAUDE.md` (backend-rendered, from `self.paths.config.squad_dir` verbatim)
prints `docs/squad/` — a path that does not resolve from the project root. v0.14.0 rendered
both correctly, from the same string.

## The fix — thread the configured string, don't derive it

Two shapes were named in review; this task picks one and the choice is deliberate, not a coin
flip:

- **Thread `config.squad_dir` (the configured string) into the view-rendering path** beside the
  resolved `Path` that `_resolve_role_source` still needs for locating `.overrides/roles/` on
  disk, so `_squad_dir_display` derives nothing — the two call sites agree by construction, not
  by an invariant on the input.
- **Constrain `squad_dir` to one path segment at the config boundary** (a validator on
  `SquadsConfig`), so `sq init --squad-dir docs/squad` refuses outright instead of producing
  wrong guidance from it.

**Chosen: thread the string.** The single-segment constraint would be a breaking change to any
adopter already running a nested `squad_dir` — which is exactly the shape v0.14.0 supported
correctly and this project's own convention (`squads is multi-user/adoptable` — reason from the
adopter, not from this repo's own layout) says is legitimate, not an edge case to close off.
`SquadsConfig.squad_dir`'s own docstring ("Folder (relative to the project root)") never claimed
single-segment either — that was `_squad_dir_display`'s own docstring asserting a property nothing
upstream enforces, which is exactly the kind of false claim this release has been asked to stop
writing. Threading the string is also the smaller change: the backend templates
(`claude/claude_section.md.j2`, `agents_md/agents_section.md.j2`) already do this correctly today
by rendering `config.squad_dir` directly; the view path is the one that regressed by picking up
a `Path` instead, and passing the string is restoring parity with the backends, not adding a new
mechanism.

## Acceptance

Proven on a **nested** squad dir, not just against a pinned string: `sq init --squad-dir
docs/squad`, then compare the rendered `squad_dir` value in `sq skill squads show --raw` (and
`sq skill sq-memory show --raw`) directly against the value `CLAUDE.md`'s managed section
renders for the same squad — both must read `docs/squad/`. Comparing the skill text only
against itself (or against a fixed string) does not prove this; the whole point of the finding
is that two surfaces disagreed while each individually looked fine.

Also re-run the existing single-segment case (the default `squads` dir) to confirm it is
unchanged.

## Testing

Falsify: revert the fix, confirm the nested-dir pinning test reddens; restore, confirm green.
Report both directions.

Test selection: grep `squad_dir` and `_squad_dir_display` across `tests/` for the existing
pinning tests this touches (`tests/integration/test_squads_skill_content_generation.py`,
`tests/integration/test_memory_skill_generation.py`, and any `_views.py` unit tests), plus the
unconditional floor — `tests/meta`, `tests/integration`, `tests/cli` — since `_views.py` sits
under a path this floor already covers indirectly through the render boundary; confirm which of
the three actually touches this change and include it. Validate any zero-hit grep against a
known positive before trusting it (line-wrap risk on multi-word template variable names is low
here, but the standing rule applies regardless).

No docstring asserting `.name` recovers the configured value — that claim is the defect; make
sure its replacement doesn't restate a version of it that isn't true either.

## Refs

Implements ADR-880. Addresses REV-926 F11.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 931 add-subtask "<title>"`; track with `sq task 931 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Thread config.squad_dir string into the view-rendering context (F11)

<!-- sq:subtask:ST1:body -->
Replace _squad_dir_display's Path.name derivation with the configured string threaded alongside the resolved Path _resolve_role_source still needs. Pin against a nested squad_dir (docs/squad), compared against CLAUDE.md's own rendering of the same value, not against itself.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-08T14:09:04Z] Elias Python:
  - Threaded config.squad_dir (str) alongside the resolved Path: render_source_view/render_resolved_source/_render_resolved_source_or_raise now take squad_dir_display: str|None (never derive .name); expand_view_tags gained a 5th param squad_dir_display, kept squad_dir: Path|None for _resolve_role_source. Deleted _squad_dir_display. Service callers pass self.paths.config.squad_dir for display, self.paths.squad_dir stays for role resolution (_services/_items.py::read_body, _services/_views.py::render_view).
  - Driven on a nested squad_dir (sq init --squad-dir docs/squad, real CLI in a scratch dir, not the test harness): sq skill squads show --raw -> 'docs/squad/', sq skill sq-memory show --raw -> 'docs/squad/', CLAUDE.md -> 'docs/squad/' — all three agree. Before the fix (verified by reverting _views.py alone): skill text read 'squad/' against CLAUDE.md's 'docs/squad/'.
  - Absolute path still doesn't leak: grepped all three rendered surfaces for the scratch squad's absolute path — 0 hits each. New pinning tests assert this too (str(paths.squad_dir) not in body/claude_md).
  - New tests: test_squad_dir_agrees_with_claude_md_for_a_nested_squad_dir in both test_squads_skill_content_generation.py and test_memory_skill_generation.py — extract the folder fragment from each surface via regex and assert cross-surface equality (not two hardcoded pins). Falsified: reverting _views.py's fix reddens both with 'squad' == 'docs/squad' (the exact Path.name-truncation signature), plus 6 more tests via the changed signature (AttributeError on the old _squad_dir_display); restored, all green.
  - No pre-existing test pinned the .name truncation itself (the single-segment default can't distinguish the two derivations) — but 3 existing tests in test_render_source_view_template_context.py passed a Path into render_source_view relying on internal derivation; updated to pass svc.paths.config.squad_dir directly (function signature changed, not behavior pinned-wrong). Also updated 4 other call sites (tests/_helpers.py, test_has_view_tag_and_expand_view_tags_agree.py, test_playbook_source_applicability_agrees_with_item_skill_branch.py, test_render_resolved_source_or_raise_lets_a_missing_template_error_through_unwrapped.py) for the new/changed signatures.
  - Selection: grepped render_source_view/render_resolved_source/_render_resolved_source_or_raise/expand_view_tags/squad_dir_display/_squad_dir_display across tests/ (union), plus tests/meta + tests/integration (floor) + test_view_resolve_and_render.py (direct test of the _services/_views.py mixin I touched). 1052 passed, 6 skipped (slow-marked). pyright/ruff check/ruff format clean. sq check clean.
  - @tech-lead ready for re-review against REV-926 F11.
<!-- sq:discussion:end -->

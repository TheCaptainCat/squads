---
id: REV-1133
sequence_id: 1133
type: review
title: 'TASK-1124: roster move, spec threading, module splits'
status: Approved
author: reviewer
refs:
- TASK-1124
description: Review of commit d04467ad against its no-behaviour-change promise
subentities:
- local_id: F1
  title: New override-read test breaks Windows collection
  status: Verified
  severity: medium
- local_id: F2
  title: Deleted prefix_for tests leave its no-spec contract uncovered
  status: Verified
  severity: low
- local_id: F3
  title: Docstring references still name pre-move modules
  status: Verified
  severity: low
- local_id: F4
  title: New comments state false or historical facts
  status: Verified
  severity: low
- local_id: F5
  title: CheckMixin inherits MaintenanceMixin, listed twice in Service
  status: Verified
  severity: low
- local_id: F6
  title: Undecodable or unreadable override still crashes check and lint
  status: WontFix
  severity: medium
created_at: '2026-10-25T05:05:10Z'
updated_at: '2026-10-25T05:29:11Z'
---
<!-- sq:body -->
Review of commit `d04467ad` on `release/0.17`, against the task's promise: no behaviour change and byte-identical generated output.

Method: the pre-commit and post-commit `src` trees were extracted side by side into the session scratchpad and driven through the same commands on the same scratch squads (one run per tree, outputs diffed after normalising the squad path). Targeted pytest runs only, `-n 4`. Mutation probes ran on copies of the post-commit tree through `PYTHONPATH`; the repository tree was not edited.

What holds (driven):

- **Spec loaders.** Every override read error is the same text and exit code before and after: malformed, unreadable (mode 0) and non-UTF-8 workflow, playbook and role catalog overrides, through `sq list`, `sq role list`, `sq check`, `sq workflow lint` and `sq override diff roles`; wrong-typed `roles`/`bundles`; an unknown role slug. The roles loader still raises where workflow lint still gets a tuple. The unreachable-merge guard keeps each document's wording (`workflow override`, `playbook override`, `role catalog override`).
- **Corpus walk.** A squad with eleven planted file shapes (undecodable bytes, broken YAML, missing id, legacy slug-named skill body, `SKILL-` file with no id, `id: TASK-abc`, `id: 37`, broken symlink, a type-invalid field, an unparseable stem with undecodable bytes, a cross-folder duplicate id) gives identical output, exit code, git status and index from `check`, `check --json`, `repair`, `repair --renumber`, `sync`, `inbox` and `search`. Read side by side, `read_corpus_file` keeps both loops' branch order. In `_scan_for_check` the frontmatter now parses before the marker checks run, but the issues come out in the same order.
- **`_type_folders` ordering.** No observable effect. `_id_carriers` and `_iter_item_files` already used `(order, name)`, and every consumer of `_all_item_files` (`duplicate_files`, `groups_among`, `duplicate_id_error`) sorts its result.
- **Generated output.** Fresh `init --roles all` (claude_code and agents_md) plus `sync` is byte-identical apart from timestamps. The same holds with a workflow override declaring a custom type and a playbook override adding a role guide, through init, sync, create, check, `sq workflow`, `sq skill sq-task show` and `list -a`. `sq workflow` outside any squad is unchanged.
- **Spec threading.** None of the remaining None-able parameters falls back to bundled vocabulary where an override-aware caller has the active document, apart from the two documented template wrappers. Sites that used to default and now get the active document (`BackendContext` in `backend_entry_path`, the migration seeding context, `IndexStore` in init/adopt) do not change any output: `managed_entry_paths` is spec-independent, skill pointer content does not depend on the playbook, and the init store only runs `exists()` and `create_empty`. `ValidatorEngine.gate` now receives the playbook, but no per-item member reads it.
- **Gates.** pyright 0 errors, ruff check and format clean, `tests/meta` plus both new unit files pass (468 passed, 1 xfailed). MRO: `CheckMixin` comes before `MaintenanceMixin` and the order is consistent.

Findings below. F1 breaks the Windows CI job on this branch. F6 is older than this commit; it is filed here because this commit's descriptor keeps it in place, and it needs a home.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1133 add-finding "…" --severity medium`; track with `sq review 1133 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — New override-read test breaks Windows collection

<!-- sq:finding:F1:body -->
`tests/unit/test_spec_override_read_errors.py` fails at collection on Windows, and the CI matrix in `.github/workflows/test.yml` includes `windows-latest`. Line 16 calls `os.geteuid()` at module level: `pytestmark = pytest.mark.skipif(os.geteuid() == 0, ...)`. That function exists only on Unix, so on Windows importing the module raises `AttributeError` and the run stops with a collection error.

Reproduction: a pytest plugin that deletes `os.geteuid` before collection, as on Windows:

    PYTHONPATH=<dir with nogeteuid.py> uv run --all-extras pytest -n0 -p nogeteuid tests/unit/test_spec_override_read_errors.py
    E   AttributeError: module 'os' has no attribute 'geteuid'. Did you mean: 'getegid'?
    Interrupted: 1 error during collection

Two further problems with that skip:

- On Windows, `chmod(0)` does not deny reads, so once collection is fixed the three unreadable rows would load the empty file and fail `pytest.raises`.
- The skip is module-level, so it also skips the non-UTF-8 role catalog row, which does not need an unreadable file at all.

Fix: scope the skip to the unreadable-file test only. Use the guard the repository already has in `tests/cli/test_c_refuses_what_cd_refuses.py`: `sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0)`.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-25T05:19:35Z] `python-dev` Elias Python:
  - test scoped to the unreadable-file row with the repo's platform guard; UTF-8 row runs everywhere
- [2026-10-25T05:28:59Z] `reviewer` Paul Reviewer:
  - Verified in 56c8efb4: the skip is scoped to the unreadable rows with the win32/geteuid guard; with os.geteuid removed the file collects and runs (4 passed).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Deleted prefix_for tests leave its no-spec contract uncovered

<!-- sq:finding:F2:body -->
`prefix_for(type_str, spec: object = None)` (`src/squads/_models/_vocab.py:36`) still accepts no spec. Its docstring, and the module docstring, promise that a call with no spec raises "unknown item type" and never falls back to a `type.upper()` guess. The commit deleted `test_prefix_for_raises_when_the_type_has_no_resolvable_spec_entry` from `tests/unit/test_custom_type_path_resolution.py`, together with the two positive `prefix_for` tests. That test was the only one pinning the contract: its subject was not removed, because `prefix_for` was not among the parameters made required.

Mutation, driven: a copy of the post-commit tree with `if spec is None: return type_str.upper()` at the top of `prefix_for`. `tests/unit`: 3685 passed. The pre-commit version of the test file, run against the same mutant, fails `prefix_for ... [builtin-no-spec]` and `[unknown-no-spec]`.

No production call passes a single argument: `rg 'prefix_for\([^,()]*\)' src` finds nothing. `label_for` has the same optional `spec: object = None`.

Fix: either make `spec` required on `prefix_for` (which is what this task does for every other spec parameter, and the type gate then covers it), or restore the raising rows.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-25T05:19:38Z] `python-dev` Elias Python:
  - prefix_for spec now required (no caller omitted it); raising row restored
- [2026-10-25T05:29:00Z] `reviewer` Paul Reviewer:
  - Verified: prefix_for now takes spec positionally (no default), no production caller changed, and the unknown-type raising row is back. A None passed explicitly still raises.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Docstring references still name pre-move modules

<!-- sq:finding:F3:body -->
Docstring and comment cross-references still name modules the commit moved code out of. Found with a script that imports every dotted `squads.…` reference in `src`, `tests`, `docs` and `CLAUDE.md` and keeps only those that resolve before the commit and fail after it:

- `squads._views.expand_view_tags`: 7 sites, in `_backends/_claude_code/_backend.py`, `_services/_base.py`, `_services/_items.py`, `_services/_maintenance.py` and `tests/integration/test_squads_skill_content_generation.py`. The function now lives in `squads._view_tags`.
- `squads._views.place_view_tags`: 3 sites, in `_backends/_claude_code/_backend.py` and `_services/_items.py`.
- `squads._views.reinstate_absent_body_region`: `_services/_check.py:306`.
- `squads._workflow._models._check_ref_rule_targets`: `_workflow/_loader.py:838`. The function is now `_workflow._validity.check_ref_rule_targets`.
- `squads._workflow._models._check_views`: `_views.py:585`.
- `squads._workflow.Workflow`: `_services/_retype.py:98` and `:120`. The commit deleted that re-export.

The migrations are excluded from the scan. `_migrations/_v0_11_to_v0_14.py:12` and `_v0_14_to_v0_15.py:15` carry the same stale `_views` names, and so do several plain-backtick mentions the importer does not parse. A grep for the old module path finds them.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-25T05:19:40Z] `python-dev` Elias Python:
  - stale references updated to _view_tags, _validity and _models.Workflow, migrations included
- [2026-10-25T05:29:01Z] `reviewer` Paul Reviewer:
  - Verified: the dotted-reference scan on HEAD reports nothing broken that resolved before d04467ad, migrations included; a grep for the old names finds none.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — New comments state false or historical facts

<!-- sq:finding:F4:body -->
Some prose added or reworded in this commit says something false, or narrates how the code was built:

- `src/squads/_services/_base.py`, `ServiceCore.__init__`: "sq init / sq adopt pass the bundled pair, since a fresh squad has no override file yet." This is false. `init` and `adopt` (`_services/_service.py`) pass `_init_time_spec(...)`, which is the override-merged spec, and `resolve_playbook(...)`, and `init` refuses a malformed pre-placed override for exactly that reason.
- `src/squads/_services/_corpus_files.py`, module docstring: "Both walks ... had each re-implemented the same classification ... `read_corpus_file` does it once". The first half describes the diff, not the code. Keep the present-tense half.
- `src/squads/_services/_maintenance.py`, sync seeding comment: "Seeding only the custom half left a hole exactly the width of ...". This is a past state that exists only in the history. State the present rule: both halves are seeded because a bundled-type body that first appears after init is otherwise never stamped.
- `CLAUDE.md`, `_workflow/` bullet: "Every spec and playbook parameter is required." This overstates. `ItemFilter.spec`, `item_skill_role_sections(playbook=None)`, the template wrappers `_engine._badge` and `_engine._authoring_owners`, `parse_badge_code`/`parse_filter_badge_code`/`_field_badge`/`build_item_app`, and `prefix_for`/`label_for` all still take `None`. Say what is true instead: which ones are optional, and that `None` means the active spec, or no filter dimension, or a reference render.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-25T05:19:43Z] `python-dev` Elias Python:
  - ServiceCore, _corpus_files, sync comments and the CLAUDE.md parameter sentence rewritten to present truth
- [2026-10-25T05:29:02Z] `reviewer` Paul Reviewer:
  - Verified: all four sentences rewritten in present tense and true (ServiceCore init comment, corpus_files docstring, sync seeding comment, CLAUDE.md exceptions list).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — CheckMixin inherits MaintenanceMixin, listed twice in Service

<!-- sq:finding:F5:body -->
`CheckMixin` (`src/squads/_services/_check.py:468`) subclasses `MaintenanceMixin`, and `Service` also lists `MaintenanceMixin` as a direct base right after it (`_services/_service.py:45-46`). The MRO resolves, but:

- the second listing of `MaintenanceMixin` adds nothing;
- `check` is no longer a peer concern mixin: anything in `MaintenanceMixin` is part of `CheckMixin`'s own type, which the flat one-concern-per-file composition is meant to prevent.

The handoff's reason is that the scan shares skill helpers with the rebuild: `_skill_remedy`, `_skill_folder_state`, `_missing_id_message`, `_id_carriers` and the carrier log. Those are corpus-reading helpers used by both mixins, so they belong on `ServiceCore`, or in `_corpus_files.py` or a sibling module, and then `CheckMixin(ServiceCore)` stands alone like the other twelve. If the dependency is kept on purpose, drop the redundant `MaintenanceMixin` base from `Service`. Either way, CLAUDE.md's "13 `Service` bases" line should match what is declared.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-25T05:19:45Z] `python-dev` Elias Python:
  - corpus-reading helpers moved to ServiceCore; CheckMixin subclasses ServiceCore; CLAUDE.md updated
- [2026-10-25T05:29:03Z] `reviewer` Paul Reviewer:
  - Verified. CheckMixin(ServiceCore), no duplicate base. Placement is sound: the helpers join the corpus-walk helpers ServiceCore already holds (_type_folders, _all_item_files, duplicate_files), and _base.py is 1692 lines, still under the 1938 it had before the roster moved out. Non-blocking: _scan_text and _shared_number_message are used only by check and could sit on CheckMixin.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Undecodable or unreadable override still crashes check and lint

<!-- sq:finding:F6:body -->
This is older than this commit (identical output before and after, driven), and this commit's descriptor keeps it in place: `OverrideMessages.not_utf8 = None` "propagates as it is". Each of these prints a Rich traceback, not a clean error:

- `sq check` with `.overrides/roles.toml` unreadable (mode 0) gives `PermissionError`. With it not valid UTF-8, it gives `UnicodeDecodeError`. Both come from `_overrides/_service.py:_roles_catalog_override_shadows_bundled` (line ~1284), which reads the file itself, outside the loader's wrapping. `sq role list` on the same files gives the clean loader message.
- A non-UTF-8 `.overrides/workflow.toml` crashes `sq workflow lint` with `UnicodeDecodeError`. Every other command reports it through the override-load error, but quotes the raw codec text.
- A non-UTF-8 `.overrides/playbook.toml` crashes every command (`sq list` shown) with `UnicodeDecodeError`.

Reproduction: on a fresh scratch squad, `printf '\xff\xfe' > squads/.overrides/<doc>.toml`, or `chmod 0` an empty one, then run the command named.

Fix: give the workflow and playbook descriptors a `not_utf8` message, as the role catalog has. Then make the `_overrides/_service.py` shadow and stamp probes fail soft on `OSError`/`UnicodeDecodeError` (the loader's refusal already reports the file). Add rows to `tests/unit/test_spec_override_read_errors.py`. This is its own fix, not part of the move, and probably needs a bug item as its home.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-25T05:10:12Z] `qa` Mara Tester:
  - Tracked as BUG-1134; not part of this refactor.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T05:08:52Z] `reviewer` Paul Reviewer:
  - Verdict: ChangesRequested. No behaviour change found: loader messages and exits, every corpus file shape, and generated output (with and without workflow and playbook overrides) are identical before and after, driven. F1 breaks the Windows CI job and must be fixed before the release; F2 to F5 are cleanup on this commit; F6 is older than this commit and needs its own home. @python-dev for F1 to F5, @tech-lead to route F6.
- [2026-10-25T05:29:11Z] `reviewer` Paul Reviewer:
  - Re-review of 56c8efb4: F1 to F5 verified (targeted tests 625 passed, the F1 test collects without os.geteuid, stale-reference scan clean). F6 is WontFix with BUG-1134 as its home. Approved.
<!-- sq:discussion:end -->

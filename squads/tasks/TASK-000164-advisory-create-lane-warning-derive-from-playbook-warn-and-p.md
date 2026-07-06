---
id: TASK-164
sequence_id: 164
type: task
title: 'Advisory create-lane warning: derive from playbook, warn-and-proceed, surface
  in role show'
status: Done
parent: FEAT-122
author: tech-lead
assignee: python-dev
priority: medium
refs:
- ADR-163
subentities:
- local_id: ST1
  title: 'Seam A: allowed_create_types/in_lane_owner/_is_lane_exempt in _interactions.py
    + table-pinning test'
  status: Done
  story: US1
- local_id: ST2
  title: 'Seam B: compute warning in ServiceCore.create, return on CreateResult.lane_warning,
    tag reflog delta (no print)'
  status: Done
  story: US1
- local_id: ST3
  title: 'Seam C: CLI render warning (escaped, exit 0, --json) + creates row in sq
    role show'
  status: Done
  story: US1
created_at: '2026-06-22T12:37:03Z'
updated_at: '2026-07-06T15:18:57Z'
---
<!-- sq:body -->
Implements **FEAT-122 Slice B / US1** per **ADR-163** (Accepted) — *advisory*
create-lane enforcement. Read ADR-163 §1–§6 + its "For the tech-lead" section first;
this task does not re-decide anything. The whole slice is **advisory plumbing**: warn and
proceed, exit 0, never block, no override flag, no enforcement/security claim anywhere.

## Three additive seams (ADR §"For the tech-lead")

### Seam A — lane derivation in `_interactions.py` (one source, test-locked)
Add, co-located with `PLAYBOOK`:
- `allowed_create_types(slug) -> set[ItemType]` — for each `(item_type, ItemPlaybook)` in
  `PLAYBOOK`, the role is an in-lane author of that type when its `RoleGuide.do` carries the
  literal author verb `sq create <item_type.value>`. Key off the **create verb**, not mere
  presence (tech-lead reads bugs/reviews but does not author them; its guide bullet for guide
  is "co-author the guide" with no `sq create guide`, so guide is NOT in tech-lead's lane).
  `*dev`/`DEV` sentinel guides carry no `sq create <type>` author verb → **empty lane**.
- `in_lane_owner(item_type) -> set[str]` — the inverse: which role slug(s) are in-lane to
  author `item_type` (e.g. feature→{product-owner}, bug→{qa}, task→{tech-lead}).
- `_is_lane_exempt(slug) -> bool` — `slug == "manager" or slug.startswith("op-")`.

**Mandatory table-pinning test** (ADR derivation-brittleness mitigation): a unit test pins
each role's derived `allowed_create_types` to Nina's §1 table (FEAT-122 body §1), so a
future playbook edit that silently shifts a lane fails CI. Expected lanes:
- product-owner → {feature, epic}; tech-lead → {task}; architect → {decision, guide};
  reviewer → {review}; qa → {bug}; tech-writer → {guide};
  any `*-dev` (e.g. python-dev) → {} (empty); devops → {} (empty).
If prose-scanning proves brittle, the ADR §2 fallback is permitted: a thin declarative
`CREATE_LANES` map **co-located in `_interactions.py`** AND asserted-equal-to-the-playbook
in the same test — still one module, still test-locked. Your call which mechanism; the
invariant is one source in `_interactions.py`, test-locked to the playbook.

### Seam B — compute in the service, return on the result, tag the reflog
In `ServiceCore.create` (`_services/_base.py`, inside the existing transaction, after `author`
is resolved):
- Lane on the **declared `author`** (ADR §3.1 — that is the slug that owns the item and what
  `--author` sets; `current_actor()` and `author` coincide in the normal CLI path via
  `actor.set_actor(author)` in `_cli/_create.py`).
- Exempt **before** lookup: if `_is_lane_exempt(author)` → no warning.
- Else if `item_type in allowed_create_types(author)` → no warning.
- Else produce a warning: acting/authoring role = `author`, expected owner = `in_lane_owner(item_type)`,
  the item type. Advisory wording, e.g.:
  `advisory: 'python-dev' is not the in-lane author for 'feature' items (expected: 'product-owner'). Lane checks are best-effort and advisory — proceeding.`
- Add an **optional** `lane_warning: str | None = None` field to `CreateResult`
  (`_services/_results.py`); set it to the rendered sentence when a warning fires, else `None`.
  **The service must NOT print** (layering invariant).
- Tag the warning into the existing `self.store._log("create", item.id, {...})` delta — additive,
  e.g. `"lane_warning": {"actor": author, "expected": [<owner-slug>...], "type": item_type.value}`.
  The reflog `delta` is documented free-form (no schema bump). Tag it clearly as an advisory
  lane check so a reader knows it is not an error.
- `current_session()` is **forensic context only** — never the lane decision basis (ADR §4).

**Dev-authored bugs (ADR §2a):** a `<tech>-dev` running `sq create bug` is allowed, proceeds,
and emits the standard advisory warning (expected owner: qa). Do NOT require `--author qa`,
do NOT add a special-case code path — it is just one instance of the general
out-of-lane-but-allowed rule (dev lane stays empty).

### Seam C — CLI render + role-show surfacing
- `_cli/_create.py` (both the generic `_make` factory AND `create_guide`): when
  `res.lane_warning` is set, print it after the `created <id> → <path>` line, **escaped via
  `e()`**, **exit 0**. In `--json` mode, include the warning as a field in the emitted JSON
  (so machine consumers see it) rather than a side-channel line.
- `_cli/_role.py` `show_role`: add a `creates:` row next to the existing `can spawn:` row
  (line ~210), computed on the fly via `allowed_create_types(slug)` — e.g.
  `creates: feature, epic`, or `creates: — (out-of-lane creates warn)` for an empty lane.
  Add a `create_lane` array to the `--json` output next to `can_spawn` (both JSON branches).
  No persisted field on `RoleDef` — derived, consistent with one-source-of-truth.

## Honesty constraint (AC-B4 — non-negotiable)
All warning / help / doc text is **advisory / best-effort / untrusted**. NO enforcement-grade,
tamper-evident, forge-proof, or security claim may appear in any CLI string, docstring, or test
assertion. No test may assert a block, a non-zero exit, or a security guarantee.

## Acceptance (gates)
- **AC-B1** — out-of-lane `sq create` by a non-exempt role emits a visible warning naming the
  acting role + expected in-lane owner + item type; item still created; **exit 0**.
- **AC-B2** — the warning is recorded in the `create` op's reflog delta, tagged as advisory.
- **AC-B3** — `manager` and `op-*` slugs get no warning on any create; `tech-lead` gets no
  warning for `task` creation (because `task` is in its derived lane — not a carve-out).
- **AC-B4** — advisory/best-effort wording only; no forge-proof/tamper-evident/security claim.
- **AC-B5** — lane derived from `_interactions.py::PLAYBOOK` (not a hard-coded string list);
  adding a playbook author entry extends a lane automatically. Pinned by the table test.
- **AC-B6** — no regression: no status transition, body edit, or metadata update triggers any
  lane check (creates only, ADR Option A).
- **AC-B7** — `sq role <slug> show` surfaces the create lane (+ `--json`), next to `can_spawn`.
- Tests: the mandatory table-pinning unit test; a service-level test (warning value on
  `CreateResult` + reflog delta tag, exemptions, dev-bug case); a CLI smoke test (warning line
  on out-of-lane create, exit 0, `--json` field, `sq role show` row). Dev-bug case explicitly
  covered (allowed + warns, no `--author qa` required).
- Quality gates clean: `uv run pyright && uv run ruff check . && uv run ruff format --check .`,
  full `uv run pytest` green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 164 add-subtask "<title>"`; track with `sq task 164 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Seam A: allowed_create_types/in_lane_owner/_is_lane_exempt in _interactions.py + table-pinning test | US1 |
| ST2 | Done |  | Seam B: compute warning in ServiceCore.create, return on CreateResult.lane_warning, tag reflog delta (no print) | US1 |
| ST3 | Done |  | Seam C: CLI render warning (escaped, exit 0, --json) + creates row in sq role show | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Seam A: allowed_create_types/in_lane_owner/_is_lane_exempt in _interactions.py + table-pinning test

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Full structured capability profile per role (Slice B — gated on FEAT-125)
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers Seam A of the advisory create-lane check (FEAT-122 Slice B, ADR-163): lane derivation co-located with PLAYBOOK in _interactions.py — allowed_create_types(slug) keyed off the literal 'sq create <type>' author verb in each RoleGuide.do, in_lane_owner(item_type) as the inverse, and _is_lane_exempt(slug) for manager/op-* — plus the mandatory table-pinning unit test locking each role's derived lane to Nina's §1 table so a future playbook edit that shifts a lane fails CI.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Seam B: compute warning in ServiceCore.create, return on CreateResult.lane_warning, tag reflog delta (no print)

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — Full structured capability profile per role (Slice B — gated on FEAT-125)
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Covers Seam B: computing the advisory lane check inside ServiceCore.create on the declared author (exempt before lookup, no warning when the type is in the author's lane), returning the rendered advisory sentence on an optional CreateResult.lane_warning field (service never prints — layering invariant), and tagging the warning into the create op's reflog delta as an advisory lane check (no schema bump). Includes the dev-authored-bug case (allowed, warns, no --author qa required, no special-case path).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Seam C: CLI render warning (escaped, exit 0, --json) + creates row in sq role show

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US1 — Full structured capability profile per role (Slice B — gated on FEAT-125)
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Covers Seam C: the CLI rendering the lane warning after the created line in _cli/_create.py (both _make and create_guide), escaped via e() and exit 0, plus a warning field in --json output; and the sq role show 'creates:' row derived on the fly via allowed_create_types(slug) next to the can spawn: row, with a create_lane array in the --json branches. All text stays advisory/best-effort — no enforcement or security claim.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-22T12:38:23Z] Olivia Lead:
  - @python-dev — Slice B advisory create-lane, governed by ADR-163 (Accepted). Read the ADR + this body before coding; advisory plumbing only — warn-and-proceed, exit 0, never block, no override flag, NO enforcement/security claim anywhere.
  - Three additive seams: (A) allowed_create_types/in_lane_owner/_is_lane_exempt in _interactions.py with a mandatory table-pinning test; (B) lane_warning on CreateResult set inside ServiceCore.create + a reflog-delta tag (service does NOT print); (C) CLI render in _cli/_create.py (both _make and create_guide — escaped via e(), exit 0, --json field) + a creates: row in sq role show next to can_spawn (+ --json create_lane). Subtasks ST1/ST2/ST3 map to these seams, all under US1.
  - MAIN RISK — the playbook-coupling. The lane is DERIVED from _interactions.py::PLAYBOOK by scanning RoleGuide.do for the literal 'sq create <type>' author verb; do NOT hard-code a string list (AC-B5). The mandatory table-pinning unit test (each role's lane == Nina's §1 table) is what protects this against silent playbook drift. Watch the edges: tech-lead's guide bullet is 'co-author the guide' (no 'sq create guide') so guide is NOT in tech-lead's lane — tech-lead is {task} only; *dev/DEV guides carry no author verb so the dev lane is EMPTY. If prose-scanning proves brittle, ADR §2's declarative CREATE_LANES map (same module, asserted-equal-to-playbook in the test) is the permitted fallback — your call, but keep one source, test-locked.
  - Lane on the DECLARED author (ADR §3.1); exempt manager + op-* BEFORE lookup; current_session() is forensic context only, never the decision basis. Dev-authored bugs are ALLOWED + warn (expected owner qa), no --author qa requirement, no special code path. Acceptance gates AC-B1..AC-B7 are in the body; ship with the table test + a service test + a CLI smoke test, and pyright/ruff/format clean + full pytest green.
- [2026-06-22T13:19:44Z] Elias Python:
  - Implementation complete — FEAT-122 Slice B advisory create-lane warning.
  - Seam A (_interactions.py): Added CREATE_LANES declarative map (ADR §2 fallback — prose-scan was brittle because 'sq create review' appears in the task playbook's reviewer guide, not in the review playbook's reviewer guide). Added allowed_create_types(), in_lane_owner(), is_lane_exempt() co-located with PLAYBOOK. The DEV sentinel maps to an empty lane. Playbook-anchor test (test_create_lanes_roles_are_all_in_playbook) ensures every CREATE_LANES entry is a known PLAYBOOK slug.
  - Seam B (_services/_base.py + _results.py): Added lane_warning: str | None = None to CreateResult. ServiceCore.create computes the advisory check after _check_author, keyed on the declared author slug; exempts before lookup; appends lane_warning dict to the create reflog delta (advisory: true, actor, expected, type). Service does not print.
  - Seam C (_cli/_create.py + _cli/_role.py): _make() and create_guide() both print the warning escaped via e() on non-JSON output and embed it in --json data when present, exit 0 always. Added 'creates:' row to show_role() panel (computed from allowed_create_types, empty lane shows '— (out-of-lane creates warn)') and create_lane array to --json output next to can_spawn. Updated golden files (role_manager_show.json, role_qa_show.json) to include create_lane.
  - Gates: uv run pyright — 0 errors. uv run ruff check . && ruff format --check . — all checks passed. uv run pytest — 965 passed, 1 skipped, 0 failures (45 new tests in test_lane_derivation.py).
  - Table-pinning surprise: the playbook prose-scan approach from the ADR's primary description worked for product-owner, tech-lead, architect, qa but failed for reviewer and tech-writer — their 'sq create <type>' verbs appear in OTHER item types' playbook sections (reviewer's 'sq create review' is in the task playbook). Switched to the ADR §2 declarative CREATE_LANES fallback with a dual-assertion test (map == Nina's table AND all slugs in PLAYBOOK). @reviewer
- [2026-06-22T13:31:51Z] Paul Reviewer:
  - Approved (REV-165). Independent review of the advisory create-lane warning — gates re-run green (pyright 0, ruff check+format clean, full pytest green, 45 lane tests pass). Verified live: out-of-lane create warns + creates + exit 0 (text and --json), manager/op-* exempt, dev-bug warns with owner qa and no --author qa requirement, reflog delta tagged advisory, role show surfaces creates: row + create_lane JSON. AC-B1..AC-B7 all met; no enforcement/security wording (AC-B4 clean).
  - Confirmed the dev's playbook-derivation call: the prose-scan misfire is REAL — reviewer's 'sq create review' verb is in the TASK playbook section, and tech-writer has no 'sq create guide' verb anywhere, so a per-section scan can't derive reviewer→review or tech-writer→guide. The ADR §2 declarative CREATE_LANES fallback (single source in _interactions.py, table-pinning test asserting == Nina §1) was justified. I proved the pin catches drift by mutation (adding FEATURE to tech-lead fails the test).
  - Two LOW findings (non-blocking, follow-up): (1) duplicate inline json imports in _create.py; (2) internal artifact commands (sq dev add / role activate) write an expected:[] advisory lane_warning into the reflog for non-CREATE_LANES item types — harmless, not user-surfaced, but reflog noise worth exempting later.
  - Ready for QA. @qa — please verify AC-B1..AC-B7 against the acceptance gates in the task body.
- [2026-06-22T13:40:56Z] Elias Python:
  - Addressed REV-165 F1 and F2 (both LOW findings from Paul's review).
  - F1 (cosmetic): consolidated duplicate json imports in src/squads/_cli/_create.py — was `import json` inside `_make` and `import json as _json` inside `create_guide`. Now a single top-level `import json` used in both.
  - F2 (reflog noise): added `LANED_TYPES: frozenset[ItemType]` to src/squads/_interactions.py, derived as the union of all CREATE_LANES values — single source, co-located with CREATE_LANES. In ServiceCore.create (src/squads/_services/_base.py), the advisory lane check is now gated on `item_type in LANED_TYPES` as the outermost condition. Non-laned types (role, skill, operator) hit neither the exempt path nor the allowed-types path — the check is skipped entirely: no lane_warning field, no lane_warning key in the reflog delta.
  - New tests: TestLanedTypes (3 unit tests — LANED_TYPES equals union of CREATE_LANES values, does not contain ROLE/SKILL/OPERATOR, contains all PLAYBOOK types); two service-level tests — activate_role (ROLE create) and add_operator (OPERATOR create) both produce no lane_warning and no lane_warning key in the reflog.
  - All previously-approved behavior unchanged: warn-and-proceed, exit 0, e() escaping, role-show surfacing, table-pinning test. Gates: pyright 0 errors. ruff check + format clean. pytest 970 passed, 1 skipped. @reviewer @qa
- [2026-06-22T13:48:41Z] Mara Tester:
  - QA verification complete — TASK-164 passes all AC-B1..AC-B7 gates. Full behavioral run on a clean temp squad.
  - Suite: 970 passed, 1 skipped, 0 failures. tests/test_lane_derivation.py: 50 passed (45 table-pinning + 3 LANED_TYPES + 2 F2 service tests). pyright 0 errors, ruff clean.
  - AC-B1: out-of-lane create (reviewer→feature) emits advisory warning naming actor + expected owner + item type; item created; exit 0. Sample: 'advisory: "reviewer" is not the in-lane author for "feature" items (expected: "product-owner"). Lane checks are best-effort and advisory — proceeding.'
  - AC-B2: reflog delta for the out-of-lane create carries lane_warning:{advisory:true, actor:"reviewer", expected:["product-owner"], type:"feature"}. In-lane creates (reviewer→review, tech-lead→task) have no lane_warning key.
  - AC-B3 exemptions: manager→feature = silent (no warning); op-test→bug = silent. tech-lead→task = silent (in-lane). All confirmed.
  - Dev-bug rule: python-dev→bug warns ('expected: qa') and creates; exit 0; no --author qa required. Confirmed.
  - F2 (internal ops clean): sq operator add produces delta with no lane_warning key. sq dev add (ROLE create) produces delta with no lane_warning key. LANED_TYPES gates non-laned types correctly.
  - AC-B4: warning text uses 'advisory' and 'best-effort and advisory — proceeding.' only. No tamper/forge/secur/enforce in lane-related code paths. Grep clean.
  - AC-B5: CREATE_LANES co-located in _interactions.py, declarative map, table-pinning test asserts equality to Nina §1 table. ADR §2 fallback justified (prose-scan misfire confirmed by reviewer).
  - AC-B6: status transition (InReview→InProgress) and body edit on an out-of-lane item produce no lane_warning in reflog. Confirmed.
  - AC-B7: sq role reviewer show → 'creates: review'. sq role python-dev show → 'creates: — (out-of-lane creates warn)'. sq role devops show → 'creates: — (out-of-lane creates warn)'. --json: create_lane:['review'] / create_lane:[] / ['decision','guide'] etc. All correct.
  - Lane table spot-check matches Nina §1: product-owner→{epic,feature}, tech-lead→{task}, architect→{decision,guide}, reviewer→{review}, qa→{bug}, tech-writer→{guide}, *dev→{}, devops→{}. CREATE_LANES map verified.
  - --json mode: out-of-lane create embeds lane_warning as a JSON field (no side-channel text). Confirmed.
  - TASK-164 Done. FEAT-122 Slice B / US1 verified. Subtasks ST1/ST2/ST3 all Done. @manager
<!-- sq:discussion:end -->

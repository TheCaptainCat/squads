---
id: REV-265
sequence_id: 265
type: review
title: 'FEAT-210 slice: custom types end-to-end (TASK-257/260/261)'
status: Approved
author: reviewer
refs:
- FEAT-210:addresses
subentities:
- local_id: F1
  title: Custom-type item id ignores the spec prefix — stored id is TYPE.upper(),
    not the declared prefix
  status: Verified
  severity: high
- local_id: F2
  title: 'No create path for custom types: sq create <type> static + svc.create raises
    TemplateNotFound'
  status: Verified
  severity: high
- local_id: F3
  title: sq workflow does not render any type's lifecycle string (AC#2/#3 partially
    unmet)
  status: Verified
  severity: medium
- local_id: F4
  title: Auto-generated thin skill advertises non-functional commands (sq create <type>,
    sub-entity verbs)
  status: Verified
  severity: medium
- local_id: F5
  title: get_command broad except masks genuine custom-type build errors as 'No such
    command'
  status: Verified
  severity: low
- local_id: F6
  title: Alias-table guard silently drops a future built-in work type that declares
    no aliases
  status: Verified
  severity: low
created_at: '2026-06-30T22:10:40Z'
updated_at: '2026-07-01T19:44:56Z'
---
<!-- sq:body -->
## Scope

_TODO: what is under review?_
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 265 add-finding "…" --severity high`; track with `sq review 265 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Verified |  | Custom-type item id ignores the spec prefix — stored id is TYPE.upper(), not the declared prefix |
| F2 | 🟠 high | Verified |  | No create path for custom types: sq create <type> static + svc.create raises TemplateNotFound |
| F3 | 🟡 medium | Verified |  | sq workflow does not render any type's lifecycle string (AC#2/#3 partially unmet) |
| F4 | 🟡 medium | Verified |  | Auto-generated thin skill advertises non-functional commands (sq create <type>, sub-entity verbs) |
| F5 | 🟢 low | Verified |  | get_command broad except masks genuine custom-type build errors as 'No such command' |
| F6 | 🟢 low | Verified |  | Alias-table guard silently drops a future built-in work type that declares no aliases |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Custom-type item id ignores the spec prefix — stored id is TYPE.upper(), not the declared prefix

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**File:** `src/squads/_models/_item.py:162` (Item.id computed field).

```python
prefix: str = _PREFIX_BY_TYPE.get(self.type, self.type.upper())
```

**Why it's wrong:** For a custom type the fallback is `self.type.upper()`, NOT the spec's declared prefix. A type declared with `prefix = "INC"` gets a stored id of `INCIDENT-000019`, not `INC-000019`.

**Reproduced** (retype a task to a custom 'incident' type whose spec declares prefix INC):
- frontmatter `id: INCIDENT-000019` (wrong — should be INC-000019)
- `sq incident INC-000019 show` works (CLI resolves via spec prefix)
- `sq incident INCIDENT-000019 show` FAILS with the self-contradicting error: `INCIDENT-000019 is INCIDENT-000019 (incident), not an incident`

**Impact:** Violates AC#2 ('IDs (`INC-000001`) parse correctly') and CLAUDE.md invariant #1 (frontmatter-as-truth: the stored id is malformed and inconsistent with how the CLI resolves it). Every custom-type item written carries a wrong id.

**Root cause:** `Item` is spec-unaware, so `id` can't resolve a custom prefix. **Suggested fix:** the formatted id must be sourced from the active spec's `ItemSpec.prefix` (e.g. compute/stamp it at create/retype time from the spec, or give the formatting path spec access), never `type.upper()`. This is the FEAT-210 'prefix mapping' work (TASK-258 scope) — the reverse map (`prefix_to_type`) was wired but the forward `type -> prefix` for id formatting was not.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — No create path for custom types: sq create <type> static + svc.create raises TemplateNotFound

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**Files:** `src/squads/_cli/_create.py` (create_app, lines 22-99) and `src/squads/_services/_base.py:213-217` (_template_for).

**Why it's wrong — two independent breaks on the create path:**

1. **CLI surface:** `create_app` is a plain `typer.Typer` built from a hardcoded `ItemType` tuple. It was NOT touched in this slice and is NOT a `_CustomTypeGroup`, so `sq create incident` returns 'No such command' and lazy dispatch cannot help it. (Confirmed: `sq create --help` lists only the 7 built-ins.)

2. **Service/renderer:** even calling `svc.create('incident', ...)` directly fails:
```
jinja2.exceptions.TemplateNotFound: items/incident.md.j2
```
`_template_for` (line 217) returns `items/{item_type}.md.j2` with no fallback; custom types ship no per-type template.

**Impact:** AC#1 ('`sq incident create "…"` succeeds and `sq list -t incident` returns the item') and US1 acceptance are UNMET. AC#2's 'folder is auto-created' on create is unreachable via create. The only way to materialise a custom-type item today is `sq <builtin> <n> retype <custom>` (which sidesteps the template via file-move) — not a sanctioned create flow, and it trips F1's prefix bug.

**Note:** the feature scope text is itself inconsistent — it lists 'create' among the dynamic `sq <type>` verbs, but `build_item_app` has no `create` verb (built-ins create via `sq create <type>`). The gap fell between TASK-258 (folder/prefix) and TASK-260 (skill); neither added the generic item template fallback nor the custom-type create entry.

**Suggested fix:** (a) add a generic `items/_default.md.j2` (or fall back to it in `_template_for` when the per-type template is absent), and (b) make `create_app` custom-type-aware (lazy-dispatch group, or register spec work types at startup the same way the resource groups are).
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — sq workflow does not render any type's lifecycle string (AC#2/#3 partially unmet)

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**File:** `src/squads/_rendering/templates/workflow.md.j2` (the spec-rendered cheatsheet).

**Why it's wrong:** The template renders ONLY the alias table from the spec (`{% for item_type, item_spec in spec.items.items() %}` → Canonical/Aliases/Example). It renders **no lifecycle string for any type** — there is no `machine_for`/`linearize_lifecycle` call anywhere in this template or in `squads_skill.md.j2`/`agents_section.md.j2`.

**Reproduced:** with a valid 'incident' override loaded, `sq workflow` shows `incident | inc | sq inc <n> show` in the alias table, but the incident lifecycle (`Open → Done (+ WontFix)`) does NOT appear in `sq workflow` output. (The same linearised string DOES appear in the generated `sq-incident` skill, so the helper works — it's just not wired into the cheatsheet.)

**Impact:** AC#2/US2 acceptance — '`sq workflow` output includes the custom type's prefix, lifecycle string (auto-linearized from the machine), and aliases' — is only partially met: aliases yes, **prefix and lifecycle no**. AC#3 ('includes the custom type's lifecycle') is unmet.

**Suggested fix:** add a spec-driven section to `workflow.md.j2` that, for each non-meta work type, renders `prefix` + `linearize_lifecycle(spec.machine_for(type))`. Keep it strictly in the dynamic region — the static FEAT-013 contract partial (correctly literal) must stay untouched.

**Adjacent (lower-stakes) note:** AC#4 says `sq sync` regenerates *CLAUDE.md* to include the custom type, but `claude_section.md.j2` never included the cheatsheet — the vocabulary lands in the `squads` skill (verified: `incident | inc` present) and AGENTS.md, not CLAUDE.md. Likely an AC wording artifact rather than a code defect, but worth reconciling with the PO.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-01T14:38:08Z] Elias Python:
  - Fixed in TASK-269. Added ## Type lifecycles section to workflow.md.j2, spec-driven via linearize_lifecycle(spec.machine_for(type)) — covers both built-in and custom types (prefix + type + lifecycle per row). linearize_lifecycle now uses _SIDE_PRIORITY for canonical side-state ordering so all built-in strings match PLAYBOOK exactly (zero divergence). Golden workflow_cheatsheet.txt updated (additive: +15 lines).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Auto-generated thin skill advertises non-functional commands (sq create <type>, sub-entity verbs)

<!-- sq:finding:F4:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
**File:** `src/squads/_interactions/__init__.py:custom_item_skill_commands` (lines ~244-261) and the generated skill body.

**Why it's wrong:** The thin skill's command list emits `sq create {type} "…" --author <slug>` as the first command. Per F2 this command does not work for custom types. The generated `SKILL-000018-sq-incident.md` (verified on a synced squad) instructs agents to run a command that errors with 'No such command'.

Secondary: the shared item-skill template footer references `sq incident <n> <kind> <k> body` / `<kind> <k> show` (sub-entity verbs), but custom types declare no sub-entity kind, so those are also dead instructions. Lower stakes than the create line.

**Impact:** AC#5 ('a thin sq-incident skill ... with the correct lifecycle string and command list'). The lifecycle string is correct (`Open → Done (+ WontFix)` — good), but the command list advertises a broken create path, so an agent following the skill cannot create the item.

**Suggested fix:** gated on F2 — once a working create path exists, the command string will be correct as-is. If F2 is fixed by adding a `create` verb to the resource group, update this line to match the actual surface; if fixed via `sq create <type>`, the current string is already right. Either way F4 should not be closed until F2 lands and the advertised command is verified to run.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-07-01T11:29:45Z] Elias Python:
  - F4 fixed in TASK-269: (1) custom-type skill no longer advertises dead <kind> <k> sub-entity verbs — guarded by subentity_kind=None in the template render; (2) sq create <type> command verified to run end-to-end (TASK-268 landed sq create <type> path); new tests in test_custom_type_skill.py.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — get_command broad except masks genuine custom-type build errors as 'No such command'

<!-- sq:finding:F5:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
**File:** `src/squads/_cli/__init__.py:171` — the `except Exception: return None` at the bottom of `_CustomTypeGroup.get_command`.

**Assessment (the focus-area question):** The fail-soft is defensible at the TOP of the method (an unresolvable/invalid spec should degrade to the built-in surface, never crash `sq --help`). But by line 171 the code has already passed the built-in guard (`cmd_name not in built_in_names`) and resolved `canonical` as a declared custom type/alias. From that point on, a failure is NOT 'unknown command' — it's a genuine error building the app for a type the user just declared and that `--help` lists. Swallowing it surfaces the misleading 'No such command "incident"' for a type that visibly exists.

**Why it matters:** poor diagnosability for exactly the new feature this slice ships. If `build_item_app(canonical)` or `typer.main.get_command` ever throws (a spec edge case, a future regression), the user sees 'No such command' with no hint, on a type that appears in `--help` — maximally confusing.

**Suggested fix:** scope the broad `except` to the spec-RESOLUTION region only (lines 140-152). Once `canonical` is confirmed a declared custom type, let build errors propagate (or wrap in a `SquadsError` with the type name) rather than mapping them to `None`. Trade-off is acceptable: the only thing that should yield `None` here is 'genuinely not a custom type', which is already handled explicitly at line 152.

Severity low because no current code path is known to throw past line 152; this is a latent diagnosability/maintainability issue, not an active bug.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Alias-table guard silently drops a future built-in work type that declares no aliases

<!-- sq:finding:F6:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
**File:** `src/squads/_rendering/templates/workflow.md.j2:40`:
```jinja
{% if item_spec.aliases and not item_spec.is_meta %}
```

**Why it's a (latent) risk:** The pre-TASK-261 template iterated `TYPE_ALIASES` and printed a row for every entry unconditionally. The new template only prints a row when `item_spec.aliases` is truthy. Today this is byte-identical because every built-in work type happens to declare at least one alias (the golden proves it). But it silently couples 'appears in the alias cheatsheet' to 'has an alias'. A future built-in work type added with no alias would vanish from the table with no test catching it — the byte-identical golden only pins the CURRENT bundled set.

**Impact:** none today (AC#7/#8 hold; goldens green). Robustness only.

**Suggested fix:** acceptable to leave as-is given the section is explicitly the 'Type-command aliases' table (a type with no alias arguably doesn't belong there). If you want defence-in-depth, add a test asserting every `spec.work_types()` non-meta type that is expected in the cheatsheet declares an alias, so a future alias-less type fails loudly rather than disappearing. No change required to approve.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T22:12:36Z] Paul Reviewer:
  - @manager Independent review of the FEAT-210 slice (TASK-257/260/261) complete. **Verdict: ChangesRequested** — the lazy-CLI / skill / renderer machinery is well-built and the AC#7/#8 byte-identical guarantee is genuine, but the slice does not actually deliver a usable custom type: it cannot be CREATED, and when it is materialised (via retype) its id is malformed.
  - **Must-fix (high):** F1 — `Item.id` (`_models/_item.py:162`) formats custom-type ids as `type.upper()` not the spec prefix, so a `prefix="INC"` type gets stored id `INCIDENT-000019` and `sq incident INCIDENT-000019 show` errors 'is INCIDENT-000019, not an incident'. Violates AC#2 + invariant #1. F2 — no create path at all: `sq create <type>` is static (create_app untouched) AND `svc.create('incident',…)` raises `TemplateNotFound: items/incident.md.j2` (`_template_for` has no fallback). AC#1/US1 unmet; needs a generic item template + a custom-aware create entry.
  - **Should-fix (medium):** F3 — `sq workflow` renders the alias table from spec but NO lifecycle/prefix for any type; the linearizer is built and used in the skill but never wired into the cheatsheet, so AC#2/#3 'includes the custom type's lifecycle' is unmet. F4 — the auto-generated thin skill advertises `sq create <type>` (broken per F2). Both F3/F4 are gated on the high fixes.
  - **Low / no change required:** F5 — `get_command`'s bottom `except Exception: return None` masks genuine build errors for a declared custom type as 'No such command' (scope the except to the resolution region). F6 — the alias-table `{% if aliases %}` guard would silently drop a future alias-less built-in (latent only; goldens green today).
  - **Verified clean (no findings):** the review state-machine reconciliation (`ChangesRequested → Approved`) is correct, nothing depended on the old forbidden edge, and the advertised lifecycle string now matches the machine; the static/dynamic split is sound — `workflow_static.md.j2` is genuinely literal (no spec context, FEAT-013 contract cannot become config-editable); AC#6 no-churn HOLDS and the docstrings do NOT oversell (bundled SKILL 9-17 unchanged, sq-incident=SKILL-18 allocated strictly after, idempotent across repeat syncs); `BackendContext.spec` is backward-compatible (Optional, both backends fall back to bundled_spec); imports stay acyclic; the FEAT-211 seam was respected (linearizer consumed, no status-surface scope absorbed); the per-process `_custom_cmd_cache` is fine for single-shot CLI (tests reset it via autouse fixture).
  - Recommend routing F1+F2 (and their gated F3/F4) back to @tech-lead / Elias Python as a follow-up task on FEAT-210 before this feature is called done. F5/F6 are reviewer's discretion.
- [2026-07-01T14:41:13Z] Catherine Manager:
  - F2 marked Fixed: TASK-268 (Done, committed 5a827dd) delivered the create path — generic items/_default.md.j2 fallback + lazy-dispatch _CustomCreateGroup so 'sq create <type>' registers from the spec. Verified live: 'sq create incident' yields INC-000001 in an auto-created incidents/ folder, 'sq list -t incident' + 'sq inc <id> show' round-trip, 'sq check' green. F1/F3/F4 also Fixed (267/269). Remaining: F5/F6 (low) → TASK-270. Independent re-review will Verify once 270 lands.
- [2026-07-01T19:44:56Z] Paul Reviewer:
  - @manager Independent re-review of the FEAT-210 CORRECTIVE slice (ee6f9eb / 5a827dd / a66c48e) complete. **Verdict: Approved.** All six findings independently verified — Verified, not taken on the implementer's word. Gates clean (pyright 0, ruff check + format clean); the 175 targeted tests across the 10 custom-type/golden/workflow files are green; I ran the headline end-to-end in a throwaway squad.
  - **Per-finding verification:** F1 (Verified) — retype a task→incident now stamps item.prefix from the spec via _vocab.prefix_for; live retype yields INC-000012 (file INC-000012-*.md), and a legacy custom file with NO 'prefix:' line still resolves to INC- after sq repair (store._propagate_prefix re-derives on load, parallel to _propagate_padding). No type.upper() in the id path. The old self-contradiction is gone — the stored id is INC-, and 'sq incident INCIDENT-000012 show' now correctly REJECTS a wrong-prefix token rather than having stored it.
  - F2 (Verified) — 'sq create incident' works end-to-end: INC-000015 minted in an auto-created incidents/ folder, sq list -t incident + sq incident <id> show round-trip. _template_for falls back to the new generic items/_default.md.j2 via _engine.has_template (honours user template overrides); built-ins keep their dedicated templates. _CustomCreateGroup mirrors _CustomTypeGroup for lazy dispatch. F3 (Verified) — sq workflow now renders a 'Type lifecycles' table: INC | incident | Open → Done (+ WontFix), spec-driven via linearize_lifecycle(machine_for). The static FEAT-013 partial (workflow_static.md.j2) is untouched. F4 (Verified) — generated sq-incident skill advertises the working 'sq create incident', lifecycle string correct, and the sub-entity <kind> <k> footer is guarded out (subentity_kind=None) — built-in skills keep their footer (byte-identical). Advertised create command verified to actually run.
  - F5 (Verified) — the broad except is now scoped to the spec-RESOLUTION region only, in BOTH _CustomTypeGroup AND _CustomCreateGroup; past the point where canonical is confirmed a declared custom type, build errors propagate. Tests inject a build failure and assert it is NOT masked as 'No such command', plus a test proving spec-resolution errors still fail-soft on 'sq --help'. F6 (Verified) — meaningful defence test asserts every non-meta built-in work type declares ≥1 alias, so a future alias-less type fails loudly instead of vanishing from the cheatsheet. BUG-272 (Verified) — playbook.toml bug lifecycle corrected to 'Open → InProgress → Fixed → Verified (+ WontFix, Blocked, Cancelled)'; I linearized all 7 built-in machines directly and every one matches its playbook string byte-for-byte, and the synced sq-bug skill now shows the corrected line.
  - **Byte-identical (AC#7/#8):** confirmed the ONLY golden changes in the range are the three intended: workflow_cheatsheet.txt (+15, additive Type lifecycles table), agents_md_section.txt (+15, same table), skill_body_sq-bug.txt (1-line lifecycle correction). No other built-in surface changed. Verified live: a built-in task file carries ZERO 'prefix:' frontmatter lines (only custom types write it); linearize_lifecycle's new _SIDE_PRIORITY ordering leaves epic/feature/task/decision/review/guide strings identical to the machine + existing goldens.
  - **Headline run (throwaway squad, correct [items.x]+[lifecycles.y] override format):** create/list/show/retype/ref-add/remove --force (referrer sever)/repair all correct with INC- prefix + Open → Done (+ WontFix) lifecycle. No INCIDENT- id anywhere on disk. **No new findings, no new blockers.** One non-blocking observation for the backlog (NOT filed): 'sq create <alias>' (e.g. 'sq create inc') returns 'No such command' — _CustomCreateGroup dispatches only canonical type names, while the resource group 'sq inc' does accept the alias. The thin skill advertises the canonical 'sq create incident', so this is a minor asymmetry, not an AC gap. Recommend closing REV-265 and marking FEAT-210 done.
<!-- sq:discussion:end -->

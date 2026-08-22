---
id: BUG-756
sequence_id: 756
type: bug
title: Renaming a role via override never refreshes the item's own title field
status: Verified
author: qa
refs:
- BUG-744
- ADR-754
created_at: '2026-08-21T17:00:34Z'
updated_at: '2026-08-21T20:48:32Z'
---
<!-- sq:body -->
Driven on two shapes, both showing the same disagreement.

**Dev role.** Fresh squad, `sq dev add --tech python`, then `.overrides/roles/python-dev.toml`
declaring both `title = "Senior Python developer"` and `full_name = "Grace Hopper"`. After
`sq sync` (exit 0):

- `sq list -t role` -> `Elias Python` (stale)
- `sq role python-dev show` -> `Grace Hopper (python-dev)` (correct)
- the role's own markdown frontmatter: top-level `title: Elias Python` alongside
  `extra.full_name: Grace Hopper` in the same file — the record disagrees with itself
- generated `CLAUDE.md` roster -> `Grace Hopper` — `Senior Python developer` (correct)

**Bundled role.** Same squad shape, no dev role involved: `sq override scaffold --role
architect`, add `full_name = "Ada Lovelace"` to the scaffolded `architect.toml`, `sq sync`
(exit 0). Identical result: frontmatter keeps `title: Robert Architect` while
`extra.full_name` becomes `Ada Lovelace`; `sq list -t role` shows `Robert Architect`; `sq role
architect show` and the `CLAUDE.md` roster both show `Ada Lovelace`. `sq check` stays clean in
both cases — the skew guard does not see this as inconsistent.

So this is not dev-role-specific: any role override (bundled or developer) that declares
`full_name` produces the same split-brain record. The dev-role seam only reproduces the same
general defect on a different base-resolution path.

Surfaces that read the stale top-level `title:` field: `sq list`, `sq show`/`sq <type> <n>
show` on a role item, and anywhere else that renders `Item.title` directly for a role.
Surfaces that read the resolved catalog instead and so show the renamed value correctly: `sq
role <slug> show`, and the generated roster section both backends compile (`CLAUDE.md` /
`AGENTS.md`).

The one place that currently reconciles an override onto a live role item merges the
resolved definition's `to_extra()` output onto `item.extra` and mirrors that into the index —
by design it never touches the item's own `title:` field, only keys inside `extra`. That is
why `extra.full_name` tracks a declared rename while the record's own title does not; the
merge point is a real seam here (it already builds the resolved definition and writes the
item back in one transaction), but the top-level `title:` field is outside what it currently
reconciles.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T19:45:00Z] Robert Architect:
  - Same split driven on a second pair: create stamps description=role.mission, so a declared mission updates extra.mission and leaves the item description on the bundled text — sq role <slug> show then contradicts itself (card vs ## Mission). Settled with the name pair in ADR-766.
  - Adjacent, different shape: a declared description reaches nothing (absent from RoleDef._EXTRA_FIELD_KEYS), so the generated pointer keeps the bundled one-liner — needs its own item.
- [2026-08-21T19:47:50Z] Pierre Chat:
  - The adjacent defect Robert found - a declared description in a role override reaching nothing because the key is absent from RoleDefs extra-field table - is folded into this bug rather than filed separately. Same seam, same projection table, one dev. The skew-widening trap goes in the task body as a constraint.
- [2026-08-21T20:30:32Z] Catherine Manager:
  - Fix landed in 03c0802 on release/0.14 (TASK-767). Verified independently on a fresh squad with an architect override declaring full_name, mission and description: sq list now shows Ada Lovelace where it showed the stale bundled name, the item frontmatter carries the projected title and description, the CLAUDE.md roster agrees, and the declared description reaches the .claude pointer for the first time. The role file is still ROLE-000002-architect.md, so the rename did not move it - that was the data-loss risk in this fix. sq check exits 0.
  - The projection is declared as a table on RoleDef rather than two inline assignments, per ADR-766, so a future RoleDef field that also lands on a top-level item field cannot be half-wired. PERMITTED_EXTRA_SKEW membership is unchanged and now pinned literally in a test rather than re-derived, which is what stops the dropped description from silently widening the guard.
- [2026-08-21T20:48:31Z] Mara Tester:
  - Drove both field pairs on both role kinds on a fresh squad (backends claude_code + agents_md): architect (bundled) full_name/mission override and python-dev (dev) full_name/mission override. After sq sync, frontmatter title/description, index title/description, sq list -t role, sq role <slug> show's card AND its ## Mission body, CLAUDE.md and AGENTS.md rosters all agree on the declared value for both roles -- no split anywhere. sq check exits 0.
  - Declared description reached .claude/agents/<slug>.md for both roles (the adjacent defect folded into this bug).
  - Path unchanged across the rename: squads/agents/roles/ROLE-000002-architect.md stayed the same file/path after full_name changed the title -- no _rename/slug-recompute triggered, confirmed by listing the roles directory before and after sync.
  - Pre-split-corpus healing: hand-rolled a stale title in both the architect's frontmatter and the index (simulating an item split before this fix existed) while extra.full_name already carried the resolved name. sq list showed the stale name beforehand; a plain sq sync healed both frontmatter and index back to the correct name with no manual repair, and sq check stayed clean throughout.
<!-- sq:discussion:end -->

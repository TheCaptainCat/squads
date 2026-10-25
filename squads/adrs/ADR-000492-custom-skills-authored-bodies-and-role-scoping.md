---
id: ADR-492
sequence_id: 492
type: decision
title: 'Custom skills: authored bodies and role scoping'
status: Accepted
author: architect
refs:
- BUG-490:addresses
- FEAT-976
created_at: '2026-07-20T08:47:15Z'
updated_at: '2026-10-25T21:31:13Z'
---
<!-- sq:body -->
## Context

`sq skill add NAME` creates a `skill` roster item and its `.claude` pointer. A team-authored skill
has to be first-class in two ways: it carries an authored instructional body, and chosen roles
preload it. The motivating case (BUG-490) is a release-process runbook authored as a skill and
preloaded for `manager`, `devops` and `tech-writer`.

Two facts frame the design. A skill's pointer is generated for every skill, system or custom,
while a skill's **body** is either rendered by squads (a bundled skill or a per-item-type
`sq-<type>` skill, whose body is a declared view tag expanded at read time, ADR-776) or authored
by the team. And a role's preloaded-skill set surfaces in two places: the role pointer's `skills:`
list and the role's rendered `## Skills` section.

## Decision

### Pillar 1 — an authored, persisted body

A custom skill's body is authored content the author owns, exactly like an item body:

- `sq skill <n> body -m "…" | --file <path>` (with `--append`) writes the skill's `:body` marker
  region (marker-safe, invariant #3). No new region, template or storage.
- The write is refused only on a body squads renders: a body whose `:body` region renders a
  declared view (a role, a bundled skill, a per-item-type skill; `roster_body_view_name`) has its
  own validated authoring surface, and body prose would be a second, unvalidated one. A custom
  skill's body renders no view, so it is admitted.
- Neither `sq sync` nor `sq skill <n> regen` writes a custom skill's body: `regen` rewrites only the
  pointer, and sync renders only the skills squads itself produces. `repair` never reads or
  rewrites body regions. The authored body survives all three.

The create-time `agents/skill.md.j2` stub is the starting point the author replaces.

### Pillar 2 — what decides authorability, and what records provenance

**Authorability is derived, never stored.** Whether a body may be authored is a function of the
document itself (does its body render a declared view) and the active spec, evaluated at every
gate, so a squad that renames or drops a type re-derives cleanly.

**Provenance is stored.** Where a role or skill came from is the `origin` attribute in its
frontmatter, `system` or `project` (`ORIGIN_VALUES`), required and not settable, stamped at
creation (and by a migration for older squads) and shown under that name on every surface. Origin
is provenance only, a fixed record of where the entry came from: a project override of a bundled
role keeps `system`, and the authoring gate does not read it. Origin was ruled by op-pierre in
FEAT-976's discussion and in this decision's (2026-10-09); it has no decision record of its own.

Reconciliation with the invariants:

- **#1 (frontmatter is truth).** The authored body is in the `.md`; the index never carries it.
  `origin` and the scope edges are frontmatter, so `repair` rebuilds them.
- **#5 (`.claude` files are pointers).** Unchanged: every skill's pointer is generated.
- **#7 (generated files stamp themselves).** The pointer self-stamps. A custom skill's body is not a
  generated file; it carries no stamp, and adding one would be wrong, since that stamp signals that
  in-session edits are disposable.

### Pillar 3 — role scoping via a forward edge, inverted

- The scope link is a **forward edge on the skill**: `SKILL.refs += ROLE-n:scopes`, "this skill
  scopes to that role." `scopes` is a declared ref kind with the `preload` semantic role
  (`[ref_kinds.scopes]`, ADR-775), so the engine binds the behaviour to the role, never the
  spelling.
- **Role→skill membership is data-driven.** `skills_for_role` in `_interactions` stays the pure,
  index-blind system membership (always-on skills plus the role's item-type skills). The
  service-layer resolver (`RosterProjection.resolve_role_skills`) unions it with the inverted
  scope edges: for role `R`, the skills among `backrefs(R.id)` carrying an edge of the spec's
  `preload` kind to `R` (backrefs is kind-agnostic, so the resolver filters), mapped to slugs,
  deduped, system first then scoped in lexical order. Only live roles get scoped skills.
- **One resolved list feeds both surfaces.** It reaches every backend through `BackendContext`
  (`role_skills`), so the role pointer's `skills:` list and the role's rendered `## Skills`
  section agree, and a second backend stays consistent.
- **CLI: dedicated verbs.** `sq skill <n> link-role <slug>` / `unlink-role <slug>` write or remove
  the edge **and** regenerate the affected role's pointer at once. A raw
  `sq skill <n> ref add ROLE-n --kind scopes` writes the same edge but leaves the pointer stale until
  the next `sq sync`, which recomputes every role.

### Repair round-trip

`repair` reads each file's frontmatter and never the body region, and the index stores no body. A
custom skill's authored body is reconstructed by being left alone; the `scopes` edges are in
frontmatter `refs` and come back with the index.

## Edge cases

- **Unlink.** Removing the edge drops the skill from that role's pointer and `## Skills`; other
  roles are untouched.
- **Scoping versus availability.** Every skill under `.claude/skills/` is discoverable by name
  regardless of scoping; scoping controls only which role pointers preload it.
- **A custom skill with no role links** is valid: authored, discoverable, preloaded by nobody.
- **Deleting a scoped role.** The skill's edge dangles and `sq check` flags the dangling ref, a
  benefit of routing the link through `refs`.
- **Id allocation.** A custom skill allocates its SKILL id through the normal `create` transaction
  at `sq skill add` time; the bundled seeding lists are untouched, so no existing SKILL id churns.

## Alternatives considered

- **Derive provenance from the slug and the active spec instead of storing it.** Rejected
  (op-pierre, FEAT-976): provenance is a fact about creation, which the current slug and spec
  cannot recover once a project overrides, renames or drops what squads shipped.
- **Gate authorability on the stored origin.** Rejected: origin says where an entry came from,
  not whether its body is rendered; a system role or skill whose view is not selected has an
  authorable body.
- **Store scoping in a dedicated field (`roles = [slug, …]`).** Rejected: a second forward-edge
  mechanism with bespoke inversion, against invariant #4's single edge mechanism, and no free
  dangling-ref detection.
- **A body-generating template per custom skill.** Rejected: it would generate, not let an author
  own, the body.

## Consequences

- Custom skill bodies are authored artifacts with the same durability as item bodies:
  marker-safe, index-independent, repair-stable.
- Role scoping rides the forward-edge and backrefs machinery, inherits dangling-ref detection,
  and keeps the pointer and the role's `## Skills` section in sync through one resolver.
- The authorability gate and the preload kind are both resolved from the active spec, so a
  squad's own vocabulary is respected.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T08:48:17Z] `architect` Robert Architect:
  - @manager ADR-492 authored (Proposed) for BUG-490 — three pillars resolved. Pillar 1 (authored body): add `sq skill <n> body`; relax set_body's meta-guard for custom (non-template-owned) skills only. Pillar 2 (system vs custom): DERIVE it (slug ∈ bundled_skill_slugs ∪ custom_skill_slugs) — no stored flag. Pillar 3 (scoping): forward edge SKILL→ROLE:scopes (new ref kind), service-layer resolver unions system membership + inverted scopes edges, feeds pointer + role body; `link-role`/`unlink-role` verbs run a partial-sync hook.
  - Diverged from the design-session framing in 4 places, all verified against code: (1) sync/regen do NOT clobber custom skill bodies — regen is pointer-only, sync never iterates author-defined skills; the real gap is the missing write path. (2) No persisted system/custom flag — it's derivable, so a stored flag is redundant (don't-store-derivable) and the 'flag all bundled skills' migration is unnecessary. (3) There is no header stamp on skill *bodies* to omit — the stamp lives on the pointer (stays generated) + CLAUDE.md/AGENTS.md regions; a custom body is authored like a task body, so invariant #7 doesn't apply. (4) The migration becomes a no-op schema stamp 0.10→0.11 whose only job is to hard-stop pre-0.11 clients before they meet a scopes edge.
  - Left Proposed for op-pierre to review + accept — not self-accepted.
- [2026-10-09T18:35:04Z] `op-pierre` Pierre Chat:
  - 2026-10-09: the stored origin key that FEAT-976 introduces gets no decision record of its own. This decision is amended in place with a dated note pointing at FEAT-976 and the rulings on its discussion.
- [2026-10-25T21:31:13Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the three pillars are unchanged in intent. Folded the 2026-10-09 origin note into Pillar 2 (origin is stored provenance per op-pierre on FEAT-976; authorability stays derived). Corrected the gate: it follows whether the body renders a declared view (roster_body_view_name), not is_system_skill(slug, spec). Pillar 3 now names the preload ref-kind role (ADR-775) instead of VALID_REF_KINDS, and the role ## Skills section as rendered, not snapshotted into extra.skills. Removed the "what the code does today" survey, the 0.11 schema-stamp migration plan and the design-session divergences section.
<!-- sq:discussion:end -->

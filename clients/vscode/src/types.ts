/**
 * Shapes mirroring the frozen `sq --json` surfaces this extension consumes.
 *
 * These are hand-trimmed to the fields the client actually reads; they intentionally
 * don't model every key `sq` may emit (extra/unknown keys are ignored, not rejected).
 */

/** A per-item generic badge map: field code -> the item's badge code for that
 * field, non-null fields only, e.g. `{ "priority": "high" }`. Optional on every item-bearing
 * surface below — an older `sq` simply omits the key, which every consumer
 * treats the same as `{}` (no badges to render), never a parse failure. */
export type SqBadgeMap = Readonly<Record<string, string>>;

/** One node of `sq tree <root> --json` (recursive; `children` may be empty). Open/closed and
 * default visibility are no longer carried per-node — a client joins `status` through the
 * statuses catalog's `role` to the roles catalog (`domain/statusRole.ts`) instead. */
export interface SqTreeNode {
  readonly id: string;
  readonly type: string;
  readonly title: string;
  readonly status: string;
  readonly priority: string | null;
  readonly assignee: string | null;
  readonly blocked: boolean;
  readonly badges?: SqBadgeMap;
  readonly children: readonly SqTreeNode[];
}

/** One node of `sq graph <id> --json` (recursive; the ego-centric ref-graph BFS). The root
 * node's `edge_kind`/`direction` are always `null`; every other node carries the kind/direction
 * of the edge that discovered it. `seen: true` marks a node already visited elsewhere in the
 * traversal (re-emitted so the edge into it still shows, but not re-expanded — `children` is
 * always empty on a `seen` node). */
export interface SqGraphNode {
  readonly id: string;
  readonly type: string;
  readonly status: string;
  readonly priority: string | null;
  readonly assignee: string | null;
  readonly edge_kind: string | null;
  readonly direction: 'in' | 'out' | null;
  readonly seen: boolean;
  readonly children: readonly SqGraphNode[];
}

/** One entry of a type's `fields` array on `sq workflow types --json`: the
 * field code an item's `badges` map may carry for this type, its display label, and the
 * collection code it's bound to (bundled fields coincide with their collection, e.g. field
 * `priority` -> collection `priority`; a relabeled/custom field need not). */
export interface SqTypeField {
  readonly code: string;
  readonly label: string;
  readonly collection: string;
}

/** One entry of `sq workflow types --json` — the spec's declared type catalog (work types and
 * the reserved meta types alike), one object per type, already in the spec's resolved order.
 * `category` is the type's declared axis (`"work"` / `"records"` / `"roster"`) — the single
 * client-side source of which browse view a type belongs in (`domain/typeCategory.ts`), never a
 * hardcoded type-name list. `fields` is optional the same way `SqBadgeMap` is: an older `sq`
 * simply omits it, treated the same as an empty array (no field->collection binding known). */
export interface SqTypeCatalogEntry {
  readonly type: string;
  readonly order: number | null;
  readonly prefix: string;
  readonly reserved: boolean;
  readonly category: string;
  readonly fields?: readonly SqTypeField[];
}

/** One badge of a collection's vocabulary on `sq workflow collections --json`: its stable code
 * (what an item's `badges` map carries), display label, and rendered emoji glyph. */
export interface SqCollectionBadge {
  readonly code: string;
  readonly label: string;
  readonly emoji: string;
}

/** One entry of `sq workflow collections --json` — the spec's declared badge
 * collection vocabulary (priority, severity, and any custom axis), one object per collection. */
export interface SqCollectionCatalogEntry {
  readonly collection: string;
  readonly label: string;
  readonly ordered: boolean;
  readonly default: string | null;
  readonly badges: readonly SqCollectionBadge[];
}

/** One entry of `sq workflow statuses --json` — the spec's declared status
 * vocabulary, one object per status. `role` is the name of the status's declared semantic role
 * (e.g. `"active"`, `"superseded"`) — a reference into the separate `sq workflow roles --json`
 * catalog (`SqRoleCatalogEntry`), not a behaviour in itself. A client joins an item's `status`
 * string through this catalog's `role`, then that name through the roles catalog, to resolve
 * settled/hidden/colour — never by the literal status name, and no `terminal`/`is_open` field
 * survives on either surface (both are derived client-side from the referenced role's
 * `settled`). */
export interface SqStatusCatalogEntry {
  readonly status: string;
  readonly role: string | null;
  readonly badge: string | null;
}

/** One entry of `sq workflow roles --json` — the spec's declared role catalog: the
 * first-class object a status's `role` field names. `settled` is the old `terminal` concept
 * (a resting/end state); `hidden` is whether the role is excluded from the default (non-`--all`)
 * view; `color` is a semantic colour-intent from a closed vocabulary
 * (`positive`/`danger`/`warning`/`muted`/`neutral`/`info`) — a client maps it to its own theme
 * (see `domain/statusRole.ts`), falling back to `"neutral"` for any intent it doesn't recognize
 * so a future/custom intent never breaks rendering. */
export interface SqRoleCatalogEntry {
  readonly role: string;
  readonly settled: boolean;
  readonly hidden: boolean;
  readonly color: string;
}

/** One entry of `sq show <id> --json`'s `discussion` array — a single comment: author display
 * name, ISO timestamp, and markdown body. */
export interface SqDiscussionEntry {
  readonly author: string;
  readonly ts: string;
  readonly body: string;
}

/** One entry of `sq show <id> --json`'s `subentities` array — a story/subtask/finding tracked
 * on the parent item. `local_id` is kind-prefixed (`US<n>` story / `ST<n>` subtask / `F<n>`
 * finding) — the kind itself isn't a separate field, so the client never needs a hardcoded
 * kind list. `severity`/`story`/`assignee` are `null` unless set (`severity`: findings only;
 * `story`: subtasks only, the parent story's local id). */
export interface SqSubEntity {
  readonly local_id: string;
  readonly title: string;
  readonly status: string;
  readonly assignee: string | null;
  readonly severity: string | null;
  readonly story: string | null;
  readonly body: string;
}

/** The `sq show <id> --json` shape this client reads. Hand-trimmed like every other shape here
 * — only `discussion` (the preview's collapsible comments section) and `subentities` (the
 * preview's sub-entities section) are modeled; every other key `sq show --json` emits (id,
 * title, body, status, …) is ignored, not rejected. */
export interface SqShowJson {
  readonly discussion: readonly SqDiscussionEntry[];
  readonly subentities: readonly SqSubEntity[];
}

/** One matched region within a `sq search --json` hit: `region` is the compact, machine-stable
 * locator (`"title"`, `"body"`, `"discussion#<n>"`, a sub-entity's `"<kind>:<local_id>"`, …),
 * `location` is the same thing spelled out for humans, and `snippet` is in-context text around
 * the match — see `sq search --help` for the full region-naming contract. */
export interface SqSearchHitRegion {
  readonly region: string;
  readonly location: string;
  readonly snippet: string;
}

/** One row of `sq search <text> --json` — an item matching the query, with every region it
 * matched in (`hits`, possibly more than one per item; never absent, though it may be empty
 * in principle). */
export interface SqSearchHit {
  readonly id: string;
  readonly title: string;
  readonly type: string;
  readonly status: string;
  readonly hits: readonly SqSearchHitRegion[];
}

/** One row of `sq list --json`. Open/closed is no longer carried per-row — see `SqTreeNode`'s
 * doc comment: a client re-derives it from `status` through the statuses/roles catalog join. */
export interface SqListItem {
  readonly id: string;
  readonly sequence_id: number;
  readonly type: string;
  readonly title: string;
  readonly slug: string;
  readonly status: string;
  readonly description: string;
  readonly parent: string | null;
  readonly author: string | null;
  readonly assignee: string | null;
  readonly priority: string | null;
  readonly severity: string | null;
  readonly labels: readonly string[];
  readonly refs: readonly string[];
  readonly path: string;
  readonly created_at: string;
  readonly updated_at: string;
  readonly badges?: SqBadgeMap;
}

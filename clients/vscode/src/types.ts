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
 * default visibility are not carried per-node — a client joins `status` through the
 * statuses catalog's `role` to the roles catalog (`domain/statusRole.ts`) instead.
 *
 * `anchor` is true only for a root the bare (rootless) `sq tree` invented for itself: the item
 * sits on a parent cycle, so it has a parent and no forest of parentless items would ever have
 * rooted at it, and every member of that cycle is an equally good choice. It is optional the
 * same way `badges` is — an older `sq` omits the key, which means the same as `false` — but
 * absent and false are the only two readings, never "unknown": a consumer that renders a
 * flagged node like any other root asserts a hierarchy nobody wrote, which is the one thing the
 * flag exists to prevent (`domain/treeAnchor.ts`). Never set on an explicitly rooted tree.
 *
 * `path_only` (a terminal-only dimming hint for an ancestor kept solely to anchor a filter
 * match) is deliberately NOT on this wire — it is not modelled here because `sq` does not emit
 * it, not because the client chose to drop it. */
export interface SqTreeNode {
  readonly id: string;
  readonly type: string;
  readonly title: string;
  readonly status: string;
  readonly priority: string | null;
  readonly assignee: string | null;
  readonly blocked: boolean;
  readonly badges?: SqBadgeMap;
  readonly anchor?: boolean;
  readonly children: readonly SqTreeNode[];
}

/** One node of `sq graph <id> --json` (recursive; the ego-centric ref-graph BFS). The root
 * node's `edge_kind`/`edge_semantic`/`direction` are always `null`; every other node carries
 * the kind/semantic/direction of the edge that discovered it. `seen: true` marks a node already
 * visited elsewhere in the traversal (re-emitted so the edge into it still shows, but not
 * re-expanded — `children` is always empty on a `seen` node).
 *
 * `edge_kind` is the stored kind's own spelling — a project's own vocabulary, never a fixed
 * sentinel — and is what a display renders. `edge_semantic` is the kind's declared semantic
 * role (`"dependency"`, `"preload"`, `"supersession"`, some other project-declared role, or
 * `null` for a navigational kind) — the field a consumer branches on. It is optional because an
 * older `sq` predates it; its absence is treated exactly like `null` (no known semantic, render
 * the spelling) rather than rejected. Never branch on `edge_kind`'s spelling. */
export interface SqGraphNode {
  readonly id: string;
  readonly type: string;
  readonly status: string;
  readonly priority: string | null;
  readonly assignee: string | null;
  readonly edge_kind: string | null;
  readonly edge_semantic?: string | null;
  readonly direction: 'in' | 'out' | null;
  readonly seen: boolean;
  readonly children: readonly SqGraphNode[];
}

/** One entry of a type's `fields` array on `sq workflow types --json`. Bundled fields coincide
 * with their collection (e.g. field `priority` -> collection `priority`); a relabeled/custom
 * field need not. */
export interface SqTypeField {
  readonly code: string;
  readonly label: string;
  readonly collection: string;
}

/** A type's resolved display labels (`sq workflow types --json`'s `labels` object): singular
 * and plural, each in title case and lowercase. Pin-else-derive on the core side — a project
 * that doesn't relabel a type still gets these derived from the raw type name. */
export interface SqTypeLabels {
  readonly singular: string;
  readonly plural: string;
  readonly singular_lower: string;
  readonly plural_lower: string;
}

/** One entry of `sq workflow types --json` — the spec's declared type catalog, in the spec's
 * resolved order. `category` is the type's declared axis (`"work"` / `"records"` / `"roster"`)
 * — the single client-side source of which browse view a type belongs in
 * (`domain/typeCategory.ts`), never a hardcoded type-name list. `fields`/`labels` are optional
 * the same way `SqBadgeMap` is (an older `sq` simply omits them); a missing `fields` is treated
 * as `[]`, a missing `labels` falls back to the raw `type` string (`domain/typeLabels.ts`).
 * `subentity_kind` names the declared sub-entity kind this type hosts (`null` when it hosts
 * none) — the join key from an item to `SqSubEntityKindCatalogEntry`, since a sub-entity object
 * carries no kind of its own. Optional for the same skew reason as `fields`: an `sq` predating
 * it omits the key, and the join then degrades to raw field codes.
 *
 * The row also publishes `lifecycle`, deliberately unmodelled here: it names the state machine
 * a type binds, and nothing in this release publishes those machines, so it is a grouping key
 * (equal values mean two types share one machine) with no catalog to resolve against. Modelling
 * it would invite a resolver for a target that does not exist. */
export interface SqTypeCatalogEntry {
  readonly type: string;
  readonly order: number | null;
  readonly prefix: string;
  readonly reserved: boolean;
  readonly category: string;
  readonly fields?: readonly SqTypeField[];
  readonly labels?: SqTypeLabels;
  readonly subentity_kind?: string | null;
}

/** One entry of `sq workflow subentity-kinds --json` — the spec's declared sub-entity kind
 * vocabulary, one row per kind. Hand-trimmed like every shape here to what the client reads:
 * the identity key a type row's `subentity_kind` points at, and the kind's declared `fields`
 * (the same `{code, label, collection}` entry shape a type row's own `fields` carries — the
 * sub-entity field mechanism is the item one unforked, so its published shape is too). The
 * row's other declared keys are emitted by `sq` and ignored here, per this file's hand-trim
 * convention. */
export interface SqSubEntityKindCatalogEntry {
  readonly subentity_kind: string;
  readonly fields: readonly SqTypeField[];
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

/** One entry of `sq workflow statuses --json`. `role` names the status's declared semantic role
 * (e.g. `"active"`, `"superseded"`) — a reference into the separate `sq workflow roles --json`
 * catalog (`SqRoleCatalogEntry`), not a behaviour in itself. A client joins `status` -> `role` ->
 * the roles catalog to resolve settled/hidden/colour, never by the literal status name; no
 * `terminal`/`is_open` field survives on either surface (both derive client-side from the
 * referenced role's `settled`). */
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
 * so a future/custom intent never breaks rendering. `live` (defaults false server-side) is
 * the materialisation axis: an item whose status resolves to a live role is on offer to be
 * spawned/loaded/cited/assigned. It is deliberately narrower than "not settled" — a role can be
 * non-settled without being live. */
export interface SqRoleCatalogEntry {
  readonly role: string;
  readonly settled: boolean;
  readonly hidden: boolean;
  readonly color: string;
  readonly live: boolean;
}

/** One entry of `sq show <id> --json`'s `discussion` array — a single comment: author display
 * name, ISO timestamp, and markdown body. */
export interface SqDiscussionEntry {
  readonly author: string;
  readonly ts: string;
  readonly body: string;
}

/** One entry of `sq show <id> --json`'s `subentities` array — a story/subtask/finding tracked on
 * the parent item. `local_id` is kind-prefixed (`US<n>` story / `ST<n>` subtask / the finding
 * letter) — the kind itself isn't a separate field, so the client never needs a hardcoded kind
 * list. `story` is set for subtasks only (the parent story's local id).
 *
 * `badges` is the sub-entity's spec-resolved per-field map (field code -> badge code), the same
 * shape and the same generic mechanism the item level carries — a declared axis is read from
 * here, never from a modelled field named after one particular axis. Optional the same way the
 * item-level `SqBadgeMap` is.
 *
 * `discussion` is **optional**, not just possibly-empty: an older `sq` predating this field omits
 * the key entirely, and the shape guard (`isSqSubEntity`) must keep accepting that payload rather
 * than rejecting it — see that guard's doc for the failure direction this protects against. */
export interface SqSubEntity {
  readonly local_id: string;
  readonly title: string;
  readonly status: string;
  readonly assignee: string | null;
  readonly story: string | null;
  readonly body: string;
  readonly badges?: SqBadgeMap;
  readonly discussion?: readonly SqDiscussionEntry[];
}

/** The `sq show <id> --json` shape this client reads: `discussion` (the preview's collapsible
 * comments section), `subentities` (the preview's sub-entities section), and `type` — the item's
 * declared type, which is what joins its sub-entities to their kind's declared field labels
 * through the type catalog. `type` is guarded as optional for the usual skew reason: it must
 * never be the key whose absence blanks the whole preview. */
export interface SqShowJson {
  readonly discussion: readonly SqDiscussionEntry[];
  readonly subentities: readonly SqSubEntity[];
  readonly type?: string;
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

/** One row of `sq list --json`. Open/closed is not carried per-row — see `SqTreeNode`'s
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

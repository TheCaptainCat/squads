/**
 * Pure domain logic for the second activity-bar view (the "Roster" section): buckets
 * `sq list --json` rows into the 3 fixed reserved-type subfolders — Roles, Skills, Operators —
 * the complement of the work tree's reserved-type exclusion (`reservedTypes.ts`). Never
 * groupable (always exactly these 3 buckets, in this fixed order, each present even when empty,
 * items inside a bucket in numeric id order) but — like the work tree's show-closed toggle and
 * type filter — narrowable: `state` (`domain/metaFilter.ts`) hides archived-by-default entries
 * and/or restricts to one status before bucketing, so a bucket's count reflects what's actually
 * shown rather than everything fetched.
 * The 3 bucket *types* are the fixed `META_BUCKETS` list; each bucket's rendered *label* is
 * resolved from the type catalog via the shared `domain/typeLabels.ts::pluralLabel` resolver —
 * the same one the Records and Work trees route through — falling back to the raw type string
 * when the catalog fetch failed, hasn't completed, or the connected `sq` predates the resolved
 * `labels` field.
 *
 * A Role/Operator leaf additionally carries its memory pool as eager children — a glance-level
 * count+age suffix on the leaf's own label, each entry as a child — via `domain/memoryView.ts`,
 * which owns the memory-specific shaping (sort order, age formatting, the failed-fetch
 * rendering); this module only threads the already-fetched `MemoryRenderContext` through.
 */
import type { SqListItem } from '../types';
import {
  type BadgeVocabulary,
  type FieldBindingsByType,
  NO_BADGE_VOCABULARY,
  NO_FIELD_BINDINGS,
} from './badgeCatalog';
import {
  type DisplayNode,
  groupDisplayNode,
  iconForMetaType,
  itemLeaf,
  sortedItemLeaves,
} from './displayNode';
import {
  isMemoryEligibleType,
  memoryChildren,
  memoryLabelSuffix,
  type MemoryRenderContext,
  memoryTooltipLine,
  NO_MEMORY_CONTEXT,
} from './memoryView';
import { DEFAULT_META_VIEW_STATE, matchesMetaFilter, type MetaViewState } from './metaFilter';
import { NO_PRONOUNS_CONTEXT, pronounsBadge, type PronounsContext } from './pronouns';
import { META_BUCKETS } from './reservedTypes';
import { NO_ROLES, NO_STATUS_ROLES, type RoleCatalogMap, type StatusRoleMap } from './statusRole';
import { NO_LABELS, pluralLabel, type TypeLabelMap } from './typeLabels';

function rosterDescription(item: SqListItem, pronouns: PronounsContext): string {
  const badge = isMemoryEligibleType(item.type)
    ? pronounsBadge(item.slug, pronouns.pronouns, pronouns.enabled)
    : '';
  return badge === '' ? item.status : `${badge}  ${item.status}`;
}

/** Items in id order as flat leaves: the identity's pronouns and status as the description, the
 * roster icon. Only Role/Operator identities are memory-eligible, and only when
 * `metaTreeDataProvider.ts::refresh` fetched this one's pool (it fetches only for identities
 * surviving the current filter); everything else renders with no suffix and no children. */
function sortedLeaves(
  items: readonly SqListItem[],
  fieldBindings: FieldBindingsByType,
  badgeVocabulary: BadgeVocabulary,
  statusRoles: StatusRoleMap,
  roleCatalog: RoleCatalogMap,
  memory: MemoryRenderContext,
  pronouns: PronounsContext,
): DisplayNode[] {
  const context = { fieldBindings, badgeVocabulary, statusRoles, roleCatalog };
  return sortedItemLeaves(items, (item) => {
    const pool = isMemoryEligibleType(item.type) ? memory.pools.get(item.slug) : undefined;
    return itemLeaf(item, context, {
      description: rosterDescription(item, pronouns),
      iconId: iconForMetaType(item.type),
      ...(pool === undefined
        ? {}
        : {
            labelSuffix: memoryLabelSuffix(pool, memory.now),
            tooltipSuffix: memoryTooltipLine(pool, memory.now),
          }),
      children: memoryChildren(item.slug, pool, memory.now),
    });
  });
}

/** The optional per-leaf rendering inputs, bundled to stay under the max-params bar. */
export interface RosterRenderOptions {
  readonly memory?: MemoryRenderContext;
  readonly pronouns?: PronounsContext;
}

/** Builds the meta/roster view's roots: one group per `META_BUCKETS` entry, in that fixed
 * order, each always present (even with 0 items, whether from an empty fetch or a filter that
 * matched nothing in that bucket) and never merged/reordered by content — unless
 * `state.groupByType` is `false` (default `true`), which skips the 3 buckets and returns every
 * surviving item as one id-sorted flat list instead. `fieldBindings`/`badgeVocabulary` and
 * `statusRoles`/`roleCatalog` default to the graceful-fallback empty maps, degrading each leaf's
 * tooltip badges to raw codes / disabling the colour highlight rather than breaking the view.
 * `labelMap` defaults to `NO_LABELS`, resolving each bucket's header via the shared `pluralLabel`
 * resolver rather than a hardcoded literal — falls back to the raw type string the same way
 * every other tree does. `state` defaults to `DEFAULT_META_VIEW_STATE` (archived hidden, no
 * status filter, grouped) — see `domain/metaFilter.ts` for the predicate. `render.memory` (the
 * eagerly-fetched Role/Operator memory pools, plus the "now" the age text is computed against)
 * defaults to `NO_MEMORY_CONTEXT` — an empty pool map degrades every leaf to its pre-feature
 * rendering, same graceful-fallback shape as every other catalog here. `render.pronouns` (the
 * slug -> pronouns lookup and the `squads.showPronouns` setting) adds a de-emphasised
 * `(pronouns)` to a Role/Operator leaf's description; the default shows none. */
export function buildMetaView(
  items: readonly SqListItem[],
  fieldBindings: FieldBindingsByType = NO_FIELD_BINDINGS,
  badgeVocabulary: BadgeVocabulary = NO_BADGE_VOCABULARY,
  statusRoles: StatusRoleMap = NO_STATUS_ROLES,
  roleCatalog: RoleCatalogMap = NO_ROLES,
  labelMap: TypeLabelMap = NO_LABELS,
  state: MetaViewState = DEFAULT_META_VIEW_STATE,
  render: RosterRenderOptions = {},
): DisplayNode[] {
  const { memory = NO_MEMORY_CONTEXT, pronouns = NO_PRONOUNS_CONTEXT } = render;
  const bucketTypes = new Set(META_BUCKETS.map((bucket) => bucket.type));
  const visible = items.filter(
    (item) =>
      bucketTypes.has(item.type) && matchesMetaFilter(item, state, statusRoles, roleCatalog),
  );
  if (!state.groupByType) {
    return sortedLeaves(
      visible,
      fieldBindings,
      badgeVocabulary,
      statusRoles,
      roleCatalog,
      memory,
      pronouns,
    );
  }
  return META_BUCKETS.map(({ type }) => {
    const bucketItems = visible.filter((item) => item.type === type);
    return groupDisplayNode(
      `meta:${type}`,
      pluralLabel(type, labelMap),
      bucketItems.length,
      sortedLeaves(
        bucketItems,
        fieldBindings,
        badgeVocabulary,
        statusRoles,
        roleCatalog,
        memory,
        pronouns,
      ),
    );
  });
}

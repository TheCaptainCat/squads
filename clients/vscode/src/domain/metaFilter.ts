/**
 * Filter/group state for the meta/roster view (`domain/metaView.ts`, `metaTreeDataProvider.ts`):
 * hide-archived-by-default, a single-status restriction, and a group-by-type toggle. Smaller
 * than the work tree's `ListFilter`/`ViewState` (`domain/listView.ts`) — no type filter, since
 * the roster's 3 buckets already are the type dimension (`domain/reservedTypes.ts`); its
 * `groupByType` defaults to `true` here (grouped is today's shape), the opposite default from
 * the work tree's own (which stays untouched).
 *
 * The hide-archived/status-filter pair interact: a status filter always wins over hide-archived,
 * mirroring the `sq` CLI's own rule that `--status` reveals a matching closed/hidden item even
 * without `--all` (`sq list --help`) — so filtering to a hidden-role status (e.g. the bundled
 * `Archived`) shows it, rather than the two settings combining into an unconditionally empty tree.
 */
import type { SqListItem, SqStatusCatalogEntry } from '../types';
import { resolveRole, type RoleCatalogMap, type StatusRoleMap } from './statusRole';

export interface MetaViewState {
  readonly showArchived: boolean;
  readonly statusFilter: string | null;
  readonly groupByType: boolean;
}

export const DEFAULT_META_VIEW_STATE: MetaViewState = {
  showArchived: false,
  statusFilter: null,
  groupByType: true,
};

/** Every status the active spec declares, not only ones a current roster item happens to carry
 * — same source and sort as `sq ui`'s own status filter (`Select[str]` over `sorted(spec.statuses)`
 * in `_tui/_filter.py`), so a status with zero current roster items is still offered and a filter
 * that matches nothing is a real, reachable choice rather than one the quick-pick prevents. */
export function allDeclaredStatuses(catalog: readonly SqStatusCatalogEntry[]): string[] {
  return catalog.map((entry) => entry.status).sort((a, b) => a.localeCompare(b));
}

function isHiddenByDefault(
  item: SqListItem,
  statusRoles: StatusRoleMap,
  roleCatalog: RoleCatalogMap,
): boolean {
  return resolveRole(item.status, statusRoles, roleCatalog)?.hidden ?? false;
}

/** Module doc comment explains the status-filter-wins interaction. */
export function matchesMetaFilter(
  item: SqListItem,
  state: MetaViewState,
  statusRoles: StatusRoleMap,
  roleCatalog: RoleCatalogMap,
): boolean {
  if (state.statusFilter !== null) {
    return item.status === state.statusFilter;
  }
  return state.showArchived || !isHiddenByDefault(item, statusRoles, roleCatalog);
}

/** The Roster `TreeView`'s `.description` (the small text beside the view title) is where this
 * state's active-ness surfaces without opening a menu — the toggle's own icon swap
 * (`commands.ts`'s module doc comment) covers `showArchived` on its own, but a status filter is a
 * quick-pick, not a toggle, so it has no icon pair to swap. `undefined` (no description) is the
 * default/cleared state. */
export function describeMetaFilterState(state: MetaViewState): string | undefined {
  if (state.statusFilter !== null) {
    return `Filtered: ${state.statusFilter}`;
  }
  return state.showArchived ? 'Archived shown' : undefined;
}

/**
 * Filter/group state for the Records view (`domain/recordsView.ts`, `recordsTreeDataProvider.ts`).
 * `showTerminal` is the Records equivalent of the Roster's `showArchived`
 * (`domain/metaFilter.ts`) — same mechanism, a status's role `hidden` flag joined through the
 * statuses/roles catalogs (`domain/statusRole.ts::resolveRole`), never a literal status name, so
 * it survives a project renaming statuses through a workflow override. Named "terminal" rather
 * than "closed": a superseded decision or a deprecated guide isn't well described as "closed".
 * `groupByType` defaults to `true` here (grouped is today's only shape) — the opposite default
 * from the work tree's own `groupByType` (`domain/listView.ts`), which stays untouched.
 */
import type { SqListItem } from '../types';
import { resolveRole, type RoleCatalogMap, type StatusRoleMap } from './statusRole';

export interface RecordsViewState {
  readonly groupByType: boolean;
  readonly showTerminal: boolean;
}

export const DEFAULT_RECORDS_VIEW_STATE: RecordsViewState = {
  groupByType: true,
  showTerminal: false,
};

export function matchesRecordsFilter(
  item: SqListItem,
  state: RecordsViewState,
  statusRoles: StatusRoleMap,
  roleCatalog: RoleCatalogMap,
): boolean {
  return (
    state.showTerminal || !(resolveRole(item.status, statusRoles, roleCatalog)?.hidden ?? false)
  );
}

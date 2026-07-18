/**
 * Spec-driven status role join (F26): `sq workflow statuses --json` is the *only* source of a
 * status's semantic `role` (e.g. `"active"`) — item surfaces (tree/list) carry a plain `status`
 * string and nothing else, deliberately (no per-item `role`/`is_active` field). A client that
 * wants to style "work in flight" distinctly must join the item's `status` through this catalog
 * and key on the resolved `role`, never on the literal status name — the F20 anti-pattern this
 * mirrors on the status axis.
 */
import type { SqStatusCatalogEntry } from '../types';

/** status name -> its declared semantic role, or `null` when the status has none. */
export type StatusRoleMap = ReadonlyMap<string, string | null>;

/** The degrade-gracefully default: no known roles, so every status resolves to "no role" (never
 * active) — used when the statuses-catalog fetch failed or hasn't completed, so a stale/missing
 * catalog just means no green highlighting rather than a broken view. */
export const NO_STATUS_ROLES: StatusRoleMap = new Map();

export function buildStatusRoleMap(statuses: readonly SqStatusCatalogEntry[]): StatusRoleMap {
  return new Map(statuses.map((entry) => [entry.status, entry.role]));
}

/** Whether `status` carries the spec-declared `"active"` role ("work in flight") per `roleMap`
 * — never a literal status-name comparison. A status absent from the map (an unrecognized
 * status, or the graceful-fallback `NO_STATUS_ROLES`) is never active. */
export function isActiveRole(status: string, roleMap: StatusRoleMap): boolean {
  return roleMap.get(status) === 'active';
}

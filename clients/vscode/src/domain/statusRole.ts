/**
 * Spec-driven status role join: a status's behaviour is resolved in two steps, never a
 * literal status-name check —
 *
 * 1. `sq workflow statuses --json` names the status's declared role (e.g. `"active"`,
 *    `"in_force"`), if any — `StatusRoleMap`, the reference step.
 * 2. `sq workflow roles --json` is the role catalog itself: each role is a first-class object
 *    carrying `settled` (the old `terminal` concept), `hidden` (excluded from the default,
 *    non-`--all` view), and `color` (a semantic intent from a closed vocabulary) — `RoleCatalogMap`.
 *
 * `resolveRole` performs the full two-step join. Neither `terminal` nor `is_open` exists on any
 * `sq --json` surface any more — a client re-derives them from the resolved role's `settled`.
 */
import type { SqRoleCatalogEntry, SqStatusCatalogEntry } from '../types';

/** The closed semantic colour-intent vocabulary a role's `color` may declare — validated
 * server-side at load, but a client stays defensive: `toColorIntent` falls back to `"neutral"`
 * for anything outside this set so a future/custom intent never breaks rendering. */
export type ColorIntent = 'positive' | 'danger' | 'warning' | 'muted' | 'neutral' | 'info';

const COLOR_INTENTS: ReadonlySet<string> = new Set<ColorIntent>([
  'positive',
  'danger',
  'warning',
  'muted',
  'neutral',
  'info',
]);

function toColorIntent(value: string): ColorIntent {
  return COLOR_INTENTS.has(value) ? (value as ColorIntent) : 'neutral';
}

/** A role's resolved behaviour — `settled`/`hidden` as declared, `color` normalized through the
 * closed-vocabulary fallback above. */
export interface RoleSpec {
  readonly settled: boolean;
  readonly hidden: boolean;
  readonly color: ColorIntent;
}

/** role name -> its declared spec object. */
export type RoleCatalogMap = ReadonlyMap<string, RoleSpec>;

/** The degrade-gracefully default: no known roles — every join misses, so a status resolves to
 * no role (never settled/hidden, no colour) rather than a broken view when the roles-catalog
 * fetch failed or hasn't completed. */
export const NO_ROLES: RoleCatalogMap = new Map();

export function buildRoleCatalogMap(roles: readonly SqRoleCatalogEntry[]): RoleCatalogMap {
  return new Map(
    roles.map((entry) => [
      entry.role,
      { settled: entry.settled, hidden: entry.hidden, color: toColorIntent(entry.color) },
    ]),
  );
}

/** status name -> its declared role NAME, or `null` when the status has none. */
export type StatusRoleMap = ReadonlyMap<string, string | null>;

/** The degrade-gracefully default: no known statuses, so every status's role name resolves to
 * `undefined` (the same as "no role") — used when the statuses-catalog fetch failed or hasn't
 * completed. */
export const NO_STATUS_ROLES: StatusRoleMap = new Map();

export function buildStatusRoleMap(statuses: readonly SqStatusCatalogEntry[]): StatusRoleMap {
  return new Map(statuses.map((entry) => [entry.status, entry.role]));
}

/** The full join: `status` -> its declared role name (`statusRoles`) -> that role's spec object
 * (`roles`). Returns `null` when either catalog hasn't loaded, `status` is unrecognized, or its
 * role name doesn't (yet) appear in the roles catalog — every one of those cases degrades the
 * same way: no settled/hidden/colour behaviour, matching a status with no declared role at all
 * (the spec's fail-safe-visible default). Never a literal status-name or role-name comparison
 * elsewhere in the client — this is the one place that resolves a status's behaviour. */
export function resolveRole(
  status: string,
  statusRoles: StatusRoleMap,
  roles: RoleCatalogMap,
): RoleSpec | null {
  const roleName = statusRoles.get(status);
  if (roleName === undefined || roleName === null) {
    return null;
  }
  return roles.get(roleName) ?? null;
}

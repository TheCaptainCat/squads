/**
 * Resolves a `@<slug>` role mention (e.g. `@manager`, `@tech-lead` — found in a discussion
 * comment or any other markdown body the item preview renders) to its `ROLE-<n>` item, for
 * `domain/markdown.ts`'s `@<slug>` linkifier. Mirrors `badgeCatalog.ts`'s catalog-join shape:
 * built once per render from a `sq role list --json` fetch (`itemPreviewManager.ts`, fetched
 * alongside the dossier/tree/graph/show payloads, never cached — a project's roster can change
 * between refreshes), degrading to `NO_ROLE_DIRECTORY` on a failed/unreachable fetch so a mention
 * simply renders as plain text rather than breaking the preview.
 */
import type { SqRoleListRow } from '../types';
import { nameWithPronouns, NO_PRONOUNS_CONTEXT, type PronounsContext } from './pronouns';
import {
  NO_ROLES,
  NO_STATUS_ROLES,
  resolveRole,
  type RoleCatalogMap,
  type StatusRoleMap,
} from './statusRole';

/** One resolvable role mention target: the role item's id — the mention's navigation target,
 * routed through the same `a.sq-item-link` click->navigate mechanism plain item-id references
 * use, so no new message type is needed — and its hover/title text (name, slug, description). */
export interface RoleMention {
  readonly id: string;
  readonly hoverText: string;
}

/** slug -> its role item's mention info. */
export type RoleDirectory = ReadonlyMap<string, RoleMention>;

/** The degrade-gracefully default: no known roles, so every `@slug` is left as plain text — used
 * when the role-list fetch failed or hasn't completed. */
export const NO_ROLE_DIRECTORY: RoleDirectory = new Map();

/** The hover/title text for one role: its name + slug, plus its one-line description when it has
 * one (the `description` field of a `sq role list --json` row, the resolved description of a
 * catalog, template or item-defined role — not the stored field `sq list -t role --json` carries,
 * which is empty on a catalog or template role). */
function hoverTextFor(role: SqRoleListRow, pronouns: PronounsContext): string {
  const description = (role.description ?? '').trim();
  const name = nameWithPronouns(role.full_name, role.slug, pronouns.pronouns, pronouns.enabled);
  return description === '' ? `${name} (${role.slug})` : `${name} (${role.slug}) — ${description}`;
}

/** The status vocabulary that decides which roles are mention targets: `sq role list --json`
 * lists every role, and one whose status resolves to a hidden role (an archived role) is not a
 * target, as in the default `sq list` view. Both default to empty, so an unresolved status keeps
 * its role. */
export interface RoleStatusVocabulary {
  readonly statusRoles: StatusRoleMap;
  readonly roles: RoleCatalogMap;
}

export const NO_ROLE_STATUS_VOCABULARY: RoleStatusVocabulary = {
  statusRoles: NO_STATUS_ROLES,
  roles: NO_ROLES,
};

/** Builds the slug -> mention lookup from a `sq role list --json` fetch, leaving out the roles
 * whose status resolves to a hidden role. `pronouns`, when enabled, follows the name in the
 * hover text. */
export function buildRoleDirectory(
  roles: readonly SqRoleListRow[],
  pronouns: PronounsContext = NO_PRONOUNS_CONTEXT,
  vocabulary: RoleStatusVocabulary = NO_ROLE_STATUS_VOCABULARY,
): RoleDirectory {
  const map = new Map<string, RoleMention>();
  for (const role of roles) {
    if (resolveRole(role.status, vocabulary.statusRoles, vocabulary.roles)?.hidden === true) {
      continue;
    }
    map.set(role.slug, { id: role.id, hoverText: hoverTextFor(role, pronouns) });
  }
  return map;
}

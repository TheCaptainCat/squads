/**
 * Resolves a `@<slug>` role mention (e.g. `@manager`, `@tech-lead` — found in a discussion
 * comment or any other markdown body the item preview renders) to its `ROLE-<n>` item, for
 * `domain/markdown.ts`'s `@<slug>` linkifier. Mirrors `badgeCatalog.ts`'s catalog-join shape:
 * built once per render from a `sq list -t role --json` fetch (`itemPreviewManager.ts`, fetched
 * alongside the dossier/tree/graph/show payloads, never cached — a project's roster can change
 * between refreshes), degrading to `NO_ROLE_DIRECTORY` on a failed/unreachable fetch so a mention
 * simply renders as plain text rather than breaking the preview.
 */
import type { SqListItem } from '../types';

/** One resolvable role mention target: the role item's id — the mention's navigation target,
 * routed through the same `a.sq-item-link` click->navigate mechanism plain item-id references
 * use, so no new message type is needed — and its hover/title text (name, slug, mission). */
export interface RoleMention {
  readonly id: string;
  readonly hoverText: string;
}

/** slug -> its role item's mention info. */
export type RoleDirectory = ReadonlyMap<string, RoleMention>;

/** The degrade-gracefully default: no known roles, so every `@slug` is left as plain text — used
 * when the role-list fetch failed or hasn't completed. */
export const NO_ROLE_DIRECTORY: RoleDirectory = new Map();

/** The hover/title text for one role: its name + slug, plus its mission when it has one (`sq
 * list --json`'s `description` field on a role row) — "useful specifics from the role" per the
 * bug report, without reaching into the fuller `extra.responsibilities` a plain hover can't
 * usefully lay out. */
function hoverTextFor(role: SqListItem): string {
  const mission = role.description.trim();
  return mission === ''
    ? `${role.title} (${role.slug})`
    : `${role.title} (${role.slug}) — ${mission}`;
}

/** Builds the slug -> mention lookup from a `sq list -t role --json` fetch. Non-role rows (there
 * should be none, given the `-t role` filter, but a stale/misbehaving `sq` isn't trusted blindly)
 * are skipped rather than asserted against. */
export function buildRoleDirectory(roles: readonly SqListItem[]): RoleDirectory {
  const map = new Map<string, RoleMention>();
  for (const role of roles) {
    if (role.type !== 'role') {
      continue;
    }
    map.set(role.slug, { id: role.id, hoverText: hoverTextFor(role) });
  }
  return map;
}

/**
 * Pronouns for roster identities. `sq role list --json` and `sq operator list --json` rows carry
 * a resolved `pronouns` (a string, `null` when unset; absent on an older `sq`); a client joins
 * it to a role/operator by `slug`. Whether to show it is the client's own `squads.showPronouns`
 * setting — `[display]` in `.squads.toml` is never read here. Pure, vscode-free.
 */
import type { SqRosterIdentity } from '../types';

/** slug -> its non-empty pronouns. */
export type PronounsBySlug = ReadonlyMap<string, string>;

/** The degrade-gracefully default: no known pronouns (fetch failed, or an older `sq`). */
export const NO_PRONOUNS: PronounsBySlug = new Map();

/** Builds the slug -> pronouns lookup; unset, null and blank values are left out. */
export function buildPronounsMap(rows: readonly SqRosterIdentity[]): PronounsBySlug {
  const map = new Map<string, string>();
  for (const row of rows) {
    const pronouns = row.pronouns?.trim();
    if (pronouns !== undefined && pronouns !== '') {
      map.set(row.slug, pronouns);
    }
  }
  return map;
}

/** The lookup plus the setting: what a renderer needs to decide whether to show pronouns. */
export interface PronounsContext {
  readonly pronouns: PronounsBySlug;
  readonly enabled: boolean;
}

/** Nothing known, nothing shown. */
export const NO_PRONOUNS_CONTEXT: PronounsContext = { pronouns: NO_PRONOUNS, enabled: false };

/** The parenthesised pronouns for `slug`, or `''` when the setting is off or none are known —
 * never empty parentheses. Rendered in a de-emphasised slot (a tree item's description). */
export function pronounsBadge(slug: string, pronouns: PronounsBySlug, enabled: boolean): string {
  const value = enabled ? pronouns.get(slug) : undefined;
  return value === undefined ? '' : `(${value})`;
}

/** `Name (pronouns)` as plain text, or just `name` when the setting is off or none are known. */
export function nameWithPronouns(
  name: string,
  slug: string,
  pronouns: PronounsBySlug,
  enabled: boolean,
): string {
  const badge = pronounsBadge(slug, pronouns, enabled);
  return badge === '' ? name : `${name} ${badge}`;
}

/** Item id -> non-empty pronouns, for the preview, which is opened by id rather than slug. */
export function buildPronounsByIdMap(rows: readonly SqRosterIdentity[]): PronounsBySlug {
  const map = new Map<string, string>();
  for (const row of rows) {
    const pronouns = row.pronouns?.trim();
    if (row.id !== undefined && pronouns !== undefined && pronouns !== '') {
      map.set(row.id, pronouns);
    }
  }
  return map;
}

/** The pronouns shown after a role's or operator's preview heading: `undefined` when the setting
 * is off, the id is not in `rows`, or none are set. */
export function headingPronouns(
  id: string,
  rows: readonly SqRosterIdentity[],
  enabled: boolean,
): string | undefined {
  return enabled ? buildPronounsByIdMap(rows).get(id) : undefined;
}

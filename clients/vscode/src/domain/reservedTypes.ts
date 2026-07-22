/**
 * The three reserved meta types that exist in every squad regardless of a project's own
 * customized work-item vocabulary (roles, skills, and operators are infrastructure, not work).
 * Filtering keys on these exact type strings so the browse views stay spec-agnostic: a project
 * that renames/drops/re-prefixes its work-item types never needs this list touched.
 *
 * `META_BUCKETS` is the single source both directions read from: the work tree excludes these
 * types (`isReservedType`), and the meta/roster view (`domain/metaView.ts`) is their complement,
 * bucketed under these 3 fixed, ordered subfolders — never derived from `distinctTypes`, so it
 * can't grow a 4th bucket just because a project happens to have a differently-named type.
 *
 * The work tree ALSO excludes `records`-category types (decision/guide, plus any custom records
 * type): those get their own dedicated view (`domain/recordsView.ts`), the same way roster does.
 * That exclusion is driven by `domain/typeCategory.ts`'s spec-sourced category map, never a
 * hardcoded records-type list, so `isReservedType` takes it as a parameter.
 */
import { isRecordsCategory, NO_CATEGORIES, type TypeCategoryMap } from './typeCategory';

export const META_BUCKETS: readonly { readonly type: string; readonly label: string }[] = [
  { type: 'role', label: 'Roles' },
  { type: 'skill', label: 'Skills' },
  { type: 'operator', label: 'Operators' },
];

const RESERVED_TYPES: ReadonlySet<string> = new Set(META_BUCKETS.map((bucket) => bucket.type));

/** `categoryMap` defaults to `NO_CATEGORIES` — the type-catalog fetch failed or hasn't completed
 * — which degrades gracefully to a roster-only exclusion (the records exclusion below simply
 * never matches), rather than silently dropping every item out of the work tree because the
 * category can't be determined yet. */
export function isReservedType(
  type: string,
  categoryMap: TypeCategoryMap = NO_CATEGORIES,
): boolean {
  return RESERVED_TYPES.has(type) || isRecordsCategory(type, categoryMap);
}

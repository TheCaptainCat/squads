/**
 * Spec-driven type ordering for group-by-type and the type-filter quick-pick (F1), sourced from
 * `sq workflow types --json` rather than any hardcoded type list.
 *
 * A type absent from the map — including the whole-map-empty case, when the catalog fetch
 * failed or hasn't completed yet — is treated the same as an explicit `null` (unordered): it
 * sorts after every ordered type, tying with any other unordered type. That means an empty map
 * degrades the whole sort to plain type-name order with no separate fallback branch to
 * maintain — the graceful-degradation path the caller needs when `getTypeCatalog` fails.
 */
import type { SqTypeCatalogEntry } from '../types';

/** type name -> resolved order (`null` = unordered, the spec's un-ordered/custom type). */
export type TypeOrderMap = ReadonlyMap<string, number | null>;

/** The degrade-gracefully default: every type unordered, so callers that can't fetch the
 * catalog get a plain type-name sort instead of a broken/thrown view. */
export const NO_TYPE_ORDER: TypeOrderMap = new Map();

export function buildTypeOrderMap(catalog: readonly SqTypeCatalogEntry[]): TypeOrderMap {
  return new Map(catalog.map((entry) => [entry.type, entry.order]));
}

/** Ascending by resolved order; a type missing from the map (or explicitly unordered) sorts
 * after every ordered type; ties — including two unordered types — break by type name. */
export function compareTypesByOrder(orderMap: TypeOrderMap, a: string, b: string): number {
  const orderA = orderMap.get(a) ?? null;
  const orderB = orderMap.get(b) ?? null;
  if (orderA === null || orderB === null) {
    return orderA === orderB ? a.localeCompare(b) : orderA === null ? 1 : -1;
  }
  return orderA === orderB ? a.localeCompare(b) : orderA - orderB;
}

export function sortTypesByOrder(types: readonly string[], orderMap: TypeOrderMap): string[] {
  return [...types].sort((a, b) => compareTypesByOrder(orderMap, a, b));
}

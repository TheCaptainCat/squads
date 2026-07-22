/**
 * Spec-driven type category , sourced from `sq workflow types --json`'s `category`
 * field rather than any hardcoded type list — the single client-side source of which browse view
 * a type belongs in: `work` types live in the sidebar work tree, `records` types (decision/guide,
 * plus any custom records type a project declares) get their own dedicated view
 * (`domain/recordsView.ts`), `roster` types (role/skill/operator) stay the fixed roster buckets
 * (`domain/reservedTypes.ts`/`domain/metaView.ts`).
 *
 * Mirrors `domain/typeOrder.ts`'s graceful-degradation shape: a type absent from the map —
 * including the whole-map-empty case, when the catalog fetch failed or hasn't completed yet —
 * has no known category, so callers fall back to their own pre-category behaviour rather than
 * dropping items.
 */
import type { SqTypeCatalogEntry } from '../types';

/** The one records category name this client keys on — every other value (`work`, `roster`, or
 * an unrecognized custom category) is not-records. */
export const RECORDS_CATEGORY = 'records';

/** type name -> its declared category (`"work"` / `"records"` / `"roster"`, or a project's own). */
export type TypeCategoryMap = ReadonlyMap<string, string>;

/** The degrade-gracefully default: no known categories — used when the type-catalog fetch failed
 * or hasn't completed. Callers must treat an empty map as "can't tell", not "nothing is records". */
export const NO_CATEGORIES: TypeCategoryMap = new Map();

export function buildCategoryMap(catalog: readonly SqTypeCatalogEntry[]): TypeCategoryMap {
  return new Map(catalog.map((entry) => [entry.type, entry.category]));
}

/** Whether `type` is declared `records`-category per `categoryMap`. A type absent from the map
 * (including the whole-map-empty graceful fallback) is never records — callers that need to
 * distinguish "not records" from "don't know" should check `categoryMap.size` themselves
 * (`domain/reservedTypes.ts::isReservedType` does exactly this). */
export function isRecordsCategory(type: string, categoryMap: TypeCategoryMap): boolean {
  return categoryMap.get(type) === RECORDS_CATEGORY;
}

/** Every declared `records`-category type in `categoryMap`, in the map's own (insertion) order —
 * feeds `domain/recordsView.ts`'s per-type bucket list. Spec-driven: a project with a custom
 * records type gets a bucket for it with no client change; an empty/unavailable catalog yields no
 * buckets rather than guessing at a hardcoded list. */
export function recordsTypes(categoryMap: TypeCategoryMap): string[] {
  return [...categoryMap.entries()]
    .filter(([, category]) => category === RECORDS_CATEGORY)
    .map(([type]) => type);
}

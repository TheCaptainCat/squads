/**
 * Spec-driven type display labels, sourced from `sq workflow types --json`'s `labels` object
 * rather than any hardcoded per-type string. The single shared resolver every per-type group
 * header routes through: the Records tree (`domain/recordsView.ts`), the Work tree's
 * group-by-type headers (`domain/listView.ts`), and the Roster tree's 3 fixed buckets
 * (`domain/reservedTypes.ts`/`domain/metaView.ts`) all call `pluralLabel` instead of rendering
 * the raw type string or a TS-literal label — one source of truth for "what a bucket is called".
 *
 * Mirrors `domain/typeOrder.ts`/`domain/typeCategory.ts`'s graceful-degradation shape: a type
 * absent from the map — including the whole-map-empty case, when the catalog fetch failed, has
 * not completed yet, or the connected `sq` predates the resolved `labels` field — falls back to
 * the raw type string, so every caller keeps working (just with a lowercase/unpluralized header)
 * rather than breaking.
 */
import type { SqTypeCatalogEntry, SqTypeLabels } from '../types';

/** type name -> its resolved labels (`undefined` when the catalog entry carries no `labels`,
 * e.g. an older `sq`). */
export type TypeLabelMap = ReadonlyMap<string, SqTypeLabels>;

/** The degrade-gracefully default: no known labels — used when the type-catalog fetch failed
 * or hasn't completed. Every lookup then falls back to the raw type string. */
export const NO_LABELS: TypeLabelMap = new Map();

export function buildTypeLabelMap(catalog: readonly SqTypeCatalogEntry[]): TypeLabelMap {
  const map = new Map<string, SqTypeLabels>();
  for (const entry of catalog) {
    if (entry.labels !== undefined) {
      map.set(entry.type, entry.labels);
    }
  }
  return map;
}

/** The plural display label for `type` — every per-type group header's single source of truth.
 * Resolves `labelMap.get(type)?.plural`, falling back to the raw `type` string when the type is
 * absent from the map (unknown type, empty/failed catalog fetch, or an older `sq` with no
 * `labels` field on that entry). */
export function pluralLabel(type: string, labelMap: TypeLabelMap): string {
  return labelMap.get(type)?.plural ?? type;
}

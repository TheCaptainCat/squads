/**
 * Spec-driven per-item badge rendering (F19/F20). An item's generic
 * `badges` map (`{"priority": "high"}`, field code -> badge code) carries only stable codes —
 * never a glyph or a hardcoded field/collection name — so rendering the real badge (`🟠 High`)
 * means joining two catalogs, both cached once per refresh alongside the existing type-catalog
 * fetch (`treeDataProvider.ts`):
 *
 * 1. `sq workflow types --json`'s per-type `fields` array binds a field code to the collection
 *    it draws its vocabulary from (`buildFieldBindings`) — for the bundled axes this is the
 *    identity (field `priority` -> collection `priority`), but a relabeled/custom field need
 *    not be, so this binding is never skipped.
 * 2. `sq workflow collections --json` is each collection's badge vocabulary — code, label,
 *    emoji (`buildBadgeVocabulary`).
 *
 * `resolveItemBadges` joins an item's `badges` map through both, degrading gracefully (raw code
 * text, never a dropped entry or a thrown error) when a binding or vocabulary entry is missing —
 * a stale cache or an in-flight catalog fetch, not a reason to hide the item's data.
 */
import type { SqBadgeMap, SqCollectionCatalogEntry, SqTypeCatalogEntry } from '../types';

export interface ResolvedBadge {
  /** The field's display label (e.g. "Priority", "Severity", or a custom axis's own label). */
  readonly fieldLabel: string;
  /** The badge's display label (e.g. "High"). Falls back to the raw code when the collection
   * catalog doesn't (yet, or ever) recognize it. */
  readonly badgeLabel: string;
  /** The rendered glyph (e.g. "🟠"), or `null` when no vocabulary entry was found — text-only
   * fallback rather than a missing/placeholder glyph. */
  readonly emoji: string | null;
}

interface FieldBinding {
  readonly label: string;
  readonly collection: string;
}

/** type name -> (field code -> its label + bound collection code). */
export type FieldBindingsByType = ReadonlyMap<string, ReadonlyMap<string, FieldBinding>>;

/** The degrade-gracefully default: no known bindings, so every field falls back to its own raw
 * code as both key and lookup — used when the type-catalog fetch failed or hasn't completed. */
export const NO_FIELD_BINDINGS: FieldBindingsByType = new Map();

export function buildFieldBindings(types: readonly SqTypeCatalogEntry[]): FieldBindingsByType {
  return new Map(
    types.map((entry) => [
      entry.type,
      new Map(
        (entry.fields ?? []).map((field) => [
          field.code,
          { label: field.label, collection: field.collection },
        ]),
      ),
    ]),
  );
}

/** collection code -> (badge code -> {label, emoji}). */
export type BadgeVocabulary = ReadonlyMap<
  string,
  ReadonlyMap<string, { readonly label: string; readonly emoji: string }>
>;

/** The degrade-gracefully default: no known vocabulary, so every badge falls back to its raw
 * code as text — used when the collections-catalog fetch failed or hasn't completed. */
export const NO_BADGE_VOCABULARY: BadgeVocabulary = new Map();

export function buildBadgeVocabulary(
  collections: readonly SqCollectionCatalogEntry[],
): BadgeVocabulary {
  return new Map(
    collections.map((entry) => [
      entry.collection,
      new Map(
        entry.badges.map((badge) => [badge.code, { label: badge.label, emoji: badge.emoji }]),
      ),
    ]),
  );
}

/** Resolves an item's `badges` map (defaulting to `{}` when the surface omitted it — an older
 * `sq`) into renderable badges, in the map's own key order. Every entry in `badges` always
 * yields a `ResolvedBadge` — a missing field binding or vocabulary entry degrades to raw-code
 * text (`fieldCode`/`badgeCode`, `emoji: null`) rather than being dropped, so a stale/failed
 * catalog fetch never hides that the item actually carries the field. */
export function resolveItemBadges(
  itemType: string,
  badges: SqBadgeMap | undefined,
  fieldBindings: FieldBindingsByType,
  vocabulary: BadgeVocabulary,
): readonly ResolvedBadge[] {
  const bindingsForType = fieldBindings.get(itemType);
  return Object.entries(badges ?? {}).map(([fieldCode, badgeCode]) => {
    const binding = bindingsForType?.get(fieldCode);
    const badgeEntry =
      binding !== undefined ? vocabulary.get(binding.collection)?.get(badgeCode) : undefined;
    return {
      fieldLabel: binding?.label ?? fieldCode,
      badgeLabel: badgeEntry?.label ?? badgeCode,
      emoji: badgeEntry?.emoji ?? null,
    };
  });
}

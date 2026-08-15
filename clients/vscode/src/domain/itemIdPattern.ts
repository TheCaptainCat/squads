/**
 * Which text is an item id, resolved from the spec's own declared prefixes rather than from a
 * grammar this client invents.
 *
 * `ItemSpec.prefix` is a free-form string on the core side: a project may declare a hyphenated
 * prefix, a lowercase one, or a single character, and `sq create` will mint ids with it. A
 * client that hardcodes a shape instead of reading the prefixes it already fetches gets both
 * failure directions at once — it mangles an id whose real prefix is longer than the shape
 * matches (linking a *suffix* of it to an item that does not exist), and it drops an id whose
 * prefix the shape rejects outright, silently deleting an authored cross-reference.
 *
 * So the matcher is built from `sq workflow types --json`'s `prefix` column
 * (`buildItemIdMatcher`), and the id token is bounded by "no word character or hyphen on either
 * side" rather than `\b`: with prefixes `WIDGET` and `MY-WIDGET` both declared, `\b` would let
 * `MY-WIDGET-19` match on its `WIDGET-19` tail. Longest prefix first, for the same reason.
 *
 * `DEFAULT_ITEM_ID_MATCHER` is the no-catalog fallback (a failed or not-yet-completed fetch):
 * the generic uppercase-led shape this module always used, so a normal id still linkifies while
 * the catalog is unavailable. Its one behavioural difference from that older pattern is the
 * boundary above — an unrecognised hyphenated id now renders as plain text instead of an
 * affirmatively broken link into its own tail.
 */
import type { SqTypeCatalogEntry } from '../types';

export interface ItemIdMatcher {
  /** Global — finds every id token inside a run of prose. */
  readonly inline: RegExp;
  /** Anchored — decides whether a whole string (a markdown link's url) is itself an id. */
  readonly full: RegExp;
}

/** The shape assumed when no declared prefix is known: an uppercase-letter-led run of
 * uppercase letters/digits. */
const GENERIC_PREFIX = '[A-Z][A-Z0-9]*';

/** Neither side of an id token may touch a word character or a hyphen — see the module doc for
 * the mangling this prevents. */
const LEFT_BOUNDARY = '(?<![\\w-])';
const RIGHT_BOUNDARY = '(?![\\w-])';

function matcherFor(prefixAlternation: string): ItemIdMatcher {
  return {
    inline: new RegExp(`${LEFT_BOUNDARY}(?:${prefixAlternation})-\\d+${RIGHT_BOUNDARY}`, 'g'),
    full: new RegExp(`^(?:${prefixAlternation})-\\d+$`),
  };
}

export const DEFAULT_ITEM_ID_MATCHER: ItemIdMatcher = matcherFor(GENERIC_PREFIX);

/** A declared prefix is an arbitrary string, so it is escaped before going into the pattern —
 * a prefix carrying a regex metacharacter must match itself, never act as syntax. */
function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Longest first so an alternation never settles for a prefix that is another one's tail;
 * ties broken lexicographically, so the built pattern is stable across runs. */
function byLengthThenName(a: string, b: string): number {
  if (a.length !== b.length) {
    return b.length - a.length;
  }
  return a < b ? -1 : Number(a > b);
}

/** Builds the matcher for a squad's declared type catalog. Falls back to
 * `DEFAULT_ITEM_ID_MATCHER` when the catalog declares no usable prefix at all, which keeps a
 * degenerate/empty catalog behaving like a missing one rather than matching nothing. */
export function buildItemIdMatcher(types: readonly SqTypeCatalogEntry[]): ItemIdMatcher {
  const prefixes = [...new Set(types.map((entry) => entry.prefix))]
    .filter((prefix) => prefix !== '')
    .sort(byLengthThenName);
  if (prefixes.length === 0) {
    return DEFAULT_ITEM_ID_MATCHER;
  }
  return matcherFor(prefixes.map(escapeRegExp).join('|'));
}

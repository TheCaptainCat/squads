/**
 * Shared numeric/natural-order comparator for sq item ids (e.g. a review numbered 9 sorts
 * before one numbered 48). Plain `localeCompare`/`<` sorts ids char-by-char, which is wrong the
 * moment a numeric suffix crosses a digit-count boundary ('48' < '9' lexicographically). One
 * `Intl.Collator` instance, reused everywhere an id (or a bare sequence number rendered as a
 * string) is sorted, so the defect can only be fixed once and can't recur at a new call site.
 */
const idCollator = new Intl.Collator(undefined, { numeric: true });

export function compareIds(a: string, b: string): number {
  return idCollator.compare(a, b);
}

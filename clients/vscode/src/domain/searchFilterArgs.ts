/**
 * Type/status narrowing for the search QuickPick: single-valued (the CLI's `--type`/`--status`
 * options are last-value-wins, so there's no OR semantics to build for), AND-composed with the
 * query text server-side — this only builds the argv, never re-matches or filters rows itself.
 */

export interface SearchNarrowing {
  readonly type: string | null;
  readonly status: string | null;
}

export const NO_NARROWING: SearchNarrowing = { type: null, status: null };

/** The `--type`/`--status` argv `getSearch`'s `filterArgs` parameter appends between the query
 * text and `--json`, exactly as `sq search` composes its own filters. Either, both, or neither
 * may be set; a cleared narrowing (`null`) omits that flag entirely rather than passing an
 * "all"/empty-string sentinel. */
export function buildSearchFilterArgs(narrowing: SearchNarrowing): string[] {
  const args: string[] = [];
  if (narrowing.type !== null) {
    args.push('--type', narrowing.type);
  }
  if (narrowing.status !== null) {
    args.push('--status', narrowing.status);
  }
  return args;
}

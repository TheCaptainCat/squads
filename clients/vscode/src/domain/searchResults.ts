/**
 * Turns `sq search --json` hits into the QuickPick's row shape — vscode-free so the mapping is
 * unit-testable with no host. `itemId` is carried alongside the display fields precisely so the
 * accept path (see `itemPreviewManager.ts`'s `openFromTree`) can resolve a selection back to an
 * id without re-parsing the label.
 */
import type { SqSearchHit } from '../types';

export interface SearchResultRow {
  readonly itemId: string;
  readonly label: string;
  readonly description: string;
  readonly detail: string;
}

const SNIPPET_SEPARATOR = '  ·  ';

/** One hit's matched regions, joined for the QuickPick `detail` line. A hit with an empty
 * `hits` array (no matched region reported, in principle) renders an empty detail rather than
 * throwing — never a crash on a shape `sq search` is free to emit. */
function joinSnippets(hit: SqSearchHit): string {
  return hit.hits.map((region) => region.snippet).join(SNIPPET_SEPARATOR);
}

export function hitToResultRow(hit: SqSearchHit): SearchResultRow {
  return {
    itemId: hit.id,
    label: `${hit.id}  ${hit.title}`,
    description: `${hit.type} · ${hit.status}`,
    detail: joinSnippets(hit),
  };
}

/** This mapping hands rows to the QuickPick in the exact order `sq search --json` returned them
 * — a pure display-shape mapping that performs no re-ranking, re-matching, or filtering of its
 * own. That is not the same as a guarantee about what the user sees rendered: VS Code's own
 * QuickPick filter (`matchOnDescription`/`matchOnDetail`, see `searchQuickPick.ts`'s module doc
 * comment) re-sorts the *surviving* rows by its own fuzzy-match score against the current value
 * before display — a widget-layer reordering this module has no control over and does not
 * attempt to counteract. */
export function hitsToResultRows(hits: readonly SqSearchHit[]): SearchResultRow[] {
  return hits.map(hitToResultRow);
}

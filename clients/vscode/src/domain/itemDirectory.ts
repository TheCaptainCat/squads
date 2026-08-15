/**
 * Resolves an item id found in rendered prose (a task, a decision, a bug — anywhere
 * `domain/markdown.ts` turns a token into a navigable anchor) to the hover text that anchor
 * carries. Sibling of `domain/roleDirectory.ts`, deliberately the same shape: built once per
 * render from one batched `sq list --json --all` fetch (`itemPreviewManager.ts`), never cached,
 * degrading to `NO_ITEM_DIRECTORY` on a failed/unreachable fetch.
 *
 * One batched fetch rather than a lookup per reference is the point. The preview links every id
 * the prose happens to mention, so resolving each one on its own would make a render's cost
 * scale with how much a body cites — a long discussion could fire dozens of processes. This
 * costs exactly one, whatever the prose contains.
 *
 * `--all` rather than the default view: prose overwhelmingly cites *settled* work (an accepted
 * decision, a done task), and the default list hides exactly those, so a directory built without
 * it would fail to resolve the majority of real references. That is a separate visibility policy
 * from the roster fetch, which keeps the default view on purpose — an archived role is not on
 * offer as a mention target.
 */
import type { SqListItem } from '../types';

/** item id -> its hover/title text. */
export type ItemDirectory = ReadonlyMap<string, string>;

/** The degrade-gracefully default: no known items, so every id anchor renders with no `title`
 * and simply carries no tooltip — used when the list fetch failed or hasn't completed. The link
 * still navigates either way; the hover is an enrichment, never the mechanism. */
export const NO_ITEM_DIRECTORY: ItemDirectory = new Map();

/** Builds the id -> hover text lookup from a `sq list --json --all` fetch. A row whose title is
 * blank is skipped rather than stored: its hover text would be the id, which is exactly the text
 * the reader is already hovering over, and no tooltip reads better than an empty one. */
export function buildItemDirectory(items: readonly SqListItem[]): ItemDirectory {
  const map = new Map<string, string>();
  for (const item of items) {
    const title = item.title.trim();
    if (title !== '') {
      map.set(item.id, `${item.id} — ${title}`);
    }
  }
  return map;
}

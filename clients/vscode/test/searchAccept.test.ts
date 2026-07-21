import { describe, expect, it } from 'vitest';

import { decideAccept } from '../src/domain/searchAccept';

describe('decideAccept', () => {
  it('resolves a selected result to an "open" decision carrying its item id', () => {
    expect(decideAccept({ itemId: 'TASK-3' })).toEqual({ kind: 'open', itemId: 'TASK-3' });
  });

  it('resolves no selection to a "submit" decision (Enter bypassing the debounce, not an accept)', () => {
    expect(decideAccept(undefined)).toEqual({ kind: 'submit' });
  });

  it('resolves an empty items list (post-clear, mid-debounce) the same as no selection', () => {
    // Mirrors the QuickPick clearing its rows on every keystroke (searchQuickPick.ts): once
    // `items` is `[]`, `selectedItems[0]` is `undefined` — a stale row from the *previous* query
    // can never still be `selectedItems[0]` for Enter to (wrongly) accept.
    const items: readonly { itemId: string }[] = [];

    expect(decideAccept(items[0])).toEqual({ kind: 'submit' });
  });
});

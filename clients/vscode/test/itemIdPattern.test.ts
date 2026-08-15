import { describe, expect, it } from 'vitest';

import {
  buildItemIdMatcher,
  DEFAULT_ITEM_ID_MATCHER,
  type ItemIdMatcher,
} from '../src/domain/itemIdPattern';
import type { SqTypeCatalogEntry } from '../src/types';

function catalogEntry(type: string, prefix: string): SqTypeCatalogEntry {
  return { type, order: null, prefix, reserved: false, category: 'work' };
}

function matcherFor(...prefixes: readonly string[]): ItemIdMatcher {
  return buildItemIdMatcher(
    prefixes.map((prefix, index) => catalogEntry(`t${String(index)}`, prefix)),
  );
}

/** `inline` is a global regex; `String.replace` resets its `lastIndex`, but `test` does not, so
 * every assertion goes through a replace to stay independent of call order. */
function inlineMatches(matcher: ItemIdMatcher, text: string): string[] {
  return text.match(matcher.inline) ?? [];
}

/**
 * The prefix shapes an adopter can actually declare. `ItemSpec.prefix` is a bare string with no
 * validator on the core side, so none of these is hypothetical — each is a shape a squad can
 * have on disk today, and each is checked in both positions a client renders an id in: found in
 * prose, and standing alone as a markdown link's url.
 */
const PREFIX_FAMILIES: readonly { readonly name: string; readonly prefix: string }[] = [
  { name: 'the conventional uppercase prefix', prefix: 'TASK' },
  { name: 'a hyphenated prefix', prefix: 'MY-WIDGET' },
  { name: 'an underscored prefix', prefix: 'MY_WIDGET' },
  { name: 'a single-character prefix', prefix: 'W' },
  { name: 'a lowercase prefix', prefix: 'widget' },
  { name: 'a mixed-case prefix', prefix: 'MyWidget' },
  { name: 'a digit-bearing prefix', prefix: 'A1' },
  { name: 'a prefix carrying a regex metacharacter', prefix: 'C++' },
];

describe('buildItemIdMatcher: every declared prefix shape, in both positions', () => {
  for (const { name, prefix } of PREFIX_FAMILIES) {
    const id = `${prefix}-19`;
    const matcher = matcherFor(prefix);

    it(`matches ${name} whole, in prose`, () => {
      expect(inlineMatches(matcher, `see ${id} for detail`)).toEqual([id]);
    });

    it(`matches ${name} whole, as a link url`, () => {
      expect(matcher.full.test(id)).toBe(true);
    });

    it(`matches ${name} at the very start and end of a run`, () => {
      expect(inlineMatches(matcher, id)).toEqual([id]);
      expect(inlineMatches(matcher, `${id}, and more`)).toEqual([id]);
    });

    it(`never matches a mere tail of ${name}`, () => {
      // The failure the hardcoded grammar produced: a prefix longer than the assumed shape got
      // its tail matched, linking to an id that does not exist.
      const matches = inlineMatches(matcher, id);
      expect(matches.every((match) => match === id)).toBe(true);
    });
  }
});

describe('buildItemIdMatcher: prefixes that are tails or extensions of each other', () => {
  it('prefers the longest declared prefix over one that is its tail', () => {
    const matcher = matcherFor('WIDGET', 'MY-WIDGET');
    expect(inlineMatches(matcher, 'see MY-WIDGET-19')).toEqual(['MY-WIDGET-19']);
    expect(inlineMatches(matcher, 'see WIDGET-19')).toEqual(['WIDGET-19']);
  });

  it('does not match a declared prefix appearing as the tail of an undeclared longer one', () => {
    const matcher = matcherFor('WIDGET');
    expect(inlineMatches(matcher, 'see MY-WIDGET-19')).toEqual([]);
  });

  it('is stable regardless of the catalog order it was built from', () => {
    const forward = matcherFor('WIDGET', 'MY-WIDGET');
    const reverse = matcherFor('MY-WIDGET', 'WIDGET');
    expect(forward.inline.source).toBe(reverse.inline.source);
  });
});

describe('buildItemIdMatcher: what is not an id', () => {
  const matcher = matcherFor('TASK', 'MY-WIDGET');

  it('does not match an undeclared prefix', () => {
    expect(inlineMatches(matcher, 'see NOPE-19')).toEqual([]);
    expect(matcher.full.test('NOPE-19')).toBe(false);
  });

  it('does not match a bare sub-entity local id (no dash, no digits after a dash)', () => {
    expect(inlineMatches(matcher, 'F9 and US1 and ST3')).toEqual([]);
  });

  it('does not match a declared prefix with no sequence number', () => {
    expect(inlineMatches(matcher, 'the TASK- placeholder')).toEqual([]);
    expect(inlineMatches(matcher, 'a TASK on its own')).toEqual([]);
  });

  it('does not match inside a longer word or a trailing hyphenated run', () => {
    expect(inlineMatches(matcher, 'xTASK-19')).toEqual([]);
    expect(inlineMatches(matcher, 'TASK-19x')).toEqual([]);
    expect(inlineMatches(matcher, 'TASK-19-2')).toEqual([]);
  });

  it('is case-sensitive: a declared uppercase prefix does not match its lowercase spelling', () => {
    expect(inlineMatches(matcher, 'see task-19')).toEqual([]);
  });
});

describe('buildItemIdMatcher: degenerate catalogs', () => {
  it('falls back to the generic matcher when the catalog is empty', () => {
    expect(buildItemIdMatcher([]).inline.source).toBe(DEFAULT_ITEM_ID_MATCHER.inline.source);
  });

  it('falls back to the generic matcher when every declared prefix is empty', () => {
    expect(matcherFor('', '').inline.source).toBe(DEFAULT_ITEM_ID_MATCHER.inline.source);
  });

  it('ignores an empty prefix alongside real ones rather than matching everything', () => {
    const matcher = matcherFor('', 'TASK');
    expect(inlineMatches(matcher, 'see TASK-19 and -19')).toEqual(['TASK-19']);
  });

  it('tolerates a duplicate prefix declared by two types', () => {
    const matcher = matcherFor('TASK', 'TASK');
    expect(inlineMatches(matcher, 'see TASK-19')).toEqual(['TASK-19']);
  });
});

describe('DEFAULT_ITEM_ID_MATCHER: the no-catalog fallback', () => {
  it('still matches a conventional uppercase id', () => {
    expect(inlineMatches(DEFAULT_ITEM_ID_MATCHER, 'see TASK-452 and ADR-427')).toEqual([
      'TASK-452',
      'ADR-427',
    ]);
    expect(DEFAULT_ITEM_ID_MATCHER.full.test('TASK-452')).toBe(true);
  });

  it('leaves an unrecognisable hyphenated id alone instead of matching its tail', () => {
    // Without a catalog the fallback cannot know `MY-WIDGET` is one prefix — but matching
    // `WIDGET-19` out of it would emit a link to an item that does not exist, which is worse
    // than leaving the text alone.
    expect(inlineMatches(DEFAULT_ITEM_ID_MATCHER, 'see MY-WIDGET-19')).toEqual([]);
  });
});

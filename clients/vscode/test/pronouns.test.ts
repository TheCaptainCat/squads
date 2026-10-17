import { describe, expect, it } from 'vitest';

import {
  buildPronounsMap,
  nameWithPronouns,
  NO_PRONOUNS,
  pronounsBadge,
} from '../src/domain/pronouns';

const MAP = buildPronounsMap([
  { slug: 'manager', pronouns: 'she/her' },
  { slug: 'qa', pronouns: null },
  { slug: 'architect' },
  { slug: 'op-alex', pronouns: '  ' },
  { slug: 'op-sam', pronouns: 'they/them' },
]);

describe('buildPronounsMap', () => {
  it('keeps only non-blank pronouns, keyed by slug', () => {
    expect([...MAP.entries()]).toEqual([
      ['manager', 'she/her'],
      ['op-sam', 'they/them'],
    ]);
  });
});

describe('pronounsBadge / nameWithPronouns', () => {
  it.each([
    ['set, setting on', 'manager', true, '(she/her)', 'Catherine Manager (she/her)'],
    ['set, setting off', 'manager', false, '', 'Catherine Manager'],
    ['null, setting on', 'qa', true, '', 'Catherine Manager'],
    ['absent key, setting on', 'architect', true, '', 'Catherine Manager'],
    ['blank, setting on', 'op-alex', true, '', 'Catherine Manager'],
    ['unknown slug, setting on', 'nobody', true, '', 'Catherine Manager'],
  ])('%s', (_case, slug, enabled, badge, named) => {
    expect(pronounsBadge(slug, MAP, enabled)).toBe(badge);
    expect(nameWithPronouns('Catherine Manager', slug, MAP, enabled)).toBe(named);
  });

  it('shows nothing without a lookup', () => {
    expect(pronounsBadge('manager', NO_PRONOUNS, true)).toBe('');
  });
});

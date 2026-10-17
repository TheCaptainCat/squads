import { describe, expect, it } from 'vitest';

import {
  buildPronounsByIdMap,
  buildPronounsMap,
  headingPronouns,
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

describe('buildPronounsByIdMap', () => {
  it('keys non-blank pronouns by item id and skips rows without an id or value', () => {
    const map = buildPronounsByIdMap([
      { id: 'ROLE-1', slug: 'manager', pronouns: 'she/her' },
      { id: 'ROLE-2', slug: 'qa', pronouns: null },
      { id: 'OP-10', slug: 'op-x' },
      { slug: 'old', pronouns: 'he/him' },
    ]);
    expect([...map.entries()]).toEqual([['ROLE-1', 'she/her']]);
  });
});

describe('headingPronouns', () => {
  const rows = [
    { id: 'ROLE-1', slug: 'manager', pronouns: 'she/her' },
    { id: 'OP-10', slug: 'op-x', pronouns: null },
    { id: 'ROLE-9', slug: 'old' },
  ];
  it.each([
    ['set, setting on', 'ROLE-1', true, 'she/her'],
    ['set, setting off', 'ROLE-1', false, undefined],
    ['null', 'OP-10', true, undefined],
    ['absent key (older sq)', 'ROLE-9', true, undefined],
    ['not a roster id', 'TASK-1', true, undefined],
  ])('%s', (_case, id, enabled, expected) => {
    expect(headingPronouns(id, rows, enabled)).toBe(expected);
  });
});

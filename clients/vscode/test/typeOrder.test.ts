import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  buildTypeOrderMap,
  compareTypesByOrder,
  NO_TYPE_ORDER,
  sortTypesByOrder,
} from '../src/domain/typeOrder';
import type { SqTypeCatalogEntry } from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const TYPE_CATALOG_FIXTURE = JSON.parse(readFixture('type-catalog.json')) as SqTypeCatalogEntry[];

describe('buildTypeOrderMap / sortTypesByOrder', () => {
  it('sorts the committed fixture into the spec order epic->feature->task->bug->decision->review->guide', () => {
    const orderMap = buildTypeOrderMap(TYPE_CATALOG_FIXTURE);
    const types = ['guide', 'bug', 'epic', 'review', 'task', 'decision', 'feature'];

    expect(sortTypesByOrder(types, orderMap)).toEqual([
      'epic',
      'feature',
      'task',
      'bug',
      'decision',
      'review',
      'guide',
    ]);
  });

  it('sorts an un-ordered (null) type last, after every ordered type', () => {
    const orderMap = buildTypeOrderMap([
      { type: 'task', order: 30, prefix: 'TASK', reserved: false, category: 'work' },
      { type: 'widget', order: null, prefix: 'WID', reserved: false, category: 'work' },
      { type: 'epic', order: 10, prefix: 'EPIC', reserved: false, category: 'work' },
    ]);

    expect(sortTypesByOrder(['widget', 'task', 'epic'], orderMap)).toEqual([
      'epic',
      'task',
      'widget',
    ]);
  });

  it('breaks a tie between two un-ordered types by type name', () => {
    const orderMap = buildTypeOrderMap([
      { type: 'zeta', order: null, prefix: 'Z', reserved: false, category: 'work' },
      { type: 'alpha', order: null, prefix: 'A', reserved: false, category: 'work' },
    ]);

    expect(sortTypesByOrder(['zeta', 'alpha'], orderMap)).toEqual(['alpha', 'zeta']);
  });

  it('breaks a tie between two equally-ordered types by type name', () => {
    const orderMap = buildTypeOrderMap([
      { type: 'zeta', order: 10, prefix: 'Z', reserved: false, category: 'work' },
      { type: 'alpha', order: 10, prefix: 'A', reserved: false, category: 'work' },
    ]);

    expect(sortTypesByOrder(['zeta', 'alpha'], orderMap)).toEqual(['alpha', 'zeta']);
  });

  it('treats a type entirely absent from the map the same as an explicit null order', () => {
    const orderMap = buildTypeOrderMap([
      { type: 'task', order: 30, prefix: 'TASK', reserved: false, category: 'work' },
    ]);

    expect(sortTypesByOrder(['unknown', 'task'], orderMap)).toEqual(['task', 'unknown']);
  });

  it('NO_TYPE_ORDER (the graceful-fallback default) degrades to a plain type-name sort', () => {
    expect(sortTypesByOrder(['task', 'bug', 'epic'], NO_TYPE_ORDER)).toEqual([
      'bug',
      'epic',
      'task',
    ]);
  });
});

describe('compareTypesByOrder', () => {
  it('is a valid comparator: symmetric sign flip and self-equality', () => {
    const orderMap = buildTypeOrderMap(TYPE_CATALOG_FIXTURE);

    expect(compareTypesByOrder(orderMap, 'epic', 'task')).toBeLessThan(0);
    expect(compareTypesByOrder(orderMap, 'task', 'epic')).toBeGreaterThan(0);
    expect(compareTypesByOrder(orderMap, 'task', 'task')).toBe(0);
  });
});

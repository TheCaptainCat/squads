import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import { isReservedType } from '../src/domain/reservedTypes';
import { buildCategoryMap, NO_CATEGORIES } from '../src/domain/typeCategory';
import type { SqTypeCatalogEntry } from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const TYPE_CATALOG_FIXTURE = JSON.parse(readFixture('type-catalog.json')) as SqTypeCatalogEntry[];

describe('isReservedType', () => {
  it('excludes the 3 roster types regardless of any category map', () => {
    expect(isReservedType('role')).toBe(true);
    expect(isReservedType('skill')).toBe(true);
    expect(isReservedType('operator')).toBe(true);
  });

  it('does not exclude an ordinary work type with no category map', () => {
    expect(isReservedType('task')).toBe(false);
    expect(isReservedType('bug')).toBe(false);
  });

  it('with a category map, ALSO excludes records-category types (decision/guide)', () => {
    const categoryMap = buildCategoryMap(TYPE_CATALOG_FIXTURE);

    expect(isReservedType('decision', categoryMap)).toBe(true);
    expect(isReservedType('guide', categoryMap)).toBe(true);
    // A work type stays included.
    expect(isReservedType('task', categoryMap)).toBe(false);
  });

  it('excludes a custom records-category type driven by the category map, never a hardcoded name', () => {
    const categoryMap = buildCategoryMap([
      { type: 'contract', order: 55, prefix: 'CTR', reserved: false, category: 'records' },
    ]);

    expect(isReservedType('contract', categoryMap)).toBe(true);
  });

  it('with NO_CATEGORIES (the graceful fallback), degrades to roster-only exclusion — a records type is NOT dropped', () => {
    expect(isReservedType('decision', NO_CATEGORIES)).toBe(false);
    expect(isReservedType('guide')).toBe(false);
  });
});

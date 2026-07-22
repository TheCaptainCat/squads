import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  buildCategoryMap,
  isRecordsCategory,
  NO_CATEGORIES,
  recordsTypes,
} from '../src/domain/typeCategory';
import type { SqTypeCatalogEntry } from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const TYPE_CATALOG_FIXTURE = JSON.parse(readFixture('type-catalog.json')) as SqTypeCatalogEntry[];

describe('buildCategoryMap', () => {
  it('maps each type in the committed fixture to its declared category', () => {
    const categoryMap = buildCategoryMap(TYPE_CATALOG_FIXTURE);

    expect(categoryMap.get('task')).toBe('work');
    expect(categoryMap.get('decision')).toBe('records');
    expect(categoryMap.get('guide')).toBe('records');
    expect(categoryMap.get('role')).toBe('roster');
  });
});

describe('isRecordsCategory', () => {
  const categoryMap = buildCategoryMap(TYPE_CATALOG_FIXTURE);

  it('is true for a records-category type', () => {
    expect(isRecordsCategory('decision', categoryMap)).toBe(true);
    expect(isRecordsCategory('guide', categoryMap)).toBe(true);
  });

  it('is false for a work or roster type', () => {
    expect(isRecordsCategory('task', categoryMap)).toBe(false);
    expect(isRecordsCategory('role', categoryMap)).toBe(false);
  });

  it('is false for a type absent from the map, including the whole-map-empty (NO_CATEGORIES) case', () => {
    expect(isRecordsCategory('decision', NO_CATEGORIES)).toBe(false);
    expect(isRecordsCategory('unknown', categoryMap)).toBe(false);
  });
});

describe('recordsTypes', () => {
  it('lists every declared records-category type from the committed fixture', () => {
    const categoryMap = buildCategoryMap(TYPE_CATALOG_FIXTURE);

    expect(recordsTypes(categoryMap)).toEqual(['decision', 'guide']);
  });

  it('is spec-driven: a custom records-category type is picked up with no code change', () => {
    const categoryMap = buildCategoryMap([
      ...TYPE_CATALOG_FIXTURE,
      { type: 'contract', order: 55, prefix: 'CTR', reserved: false, category: 'records' },
    ]);

    expect(recordsTypes(categoryMap)).toEqual(['decision', 'guide', 'contract']);
  });

  it('is empty when no type is declared records-category', () => {
    expect(recordsTypes(NO_CATEGORIES)).toEqual([]);
  });
});

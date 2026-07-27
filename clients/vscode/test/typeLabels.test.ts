import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import { buildTypeLabelMap, NO_LABELS, pluralLabel } from '../src/domain/typeLabels';
import type { SqTypeCatalogEntry } from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const TYPE_CATALOG_FIXTURE = JSON.parse(readFixture('type-catalog.json')) as SqTypeCatalogEntry[];

describe('buildTypeLabelMap', () => {
  it('maps each type in the committed fixture to its resolved labels object', () => {
    const labelMap = buildTypeLabelMap(TYPE_CATALOG_FIXTURE);

    expect(labelMap.get('task')).toEqual({
      singular: 'Task',
      plural: 'Tasks',
      singular_lower: 'task',
      plural_lower: 'tasks',
    });
    expect(labelMap.get('role')).toEqual({
      singular: 'Role',
      plural: 'Roles',
      singular_lower: 'role',
      plural_lower: 'roles',
    });
  });

  it('omits a type whose catalog entry carries no labels (an older sq)', () => {
    const labelMap = buildTypeLabelMap([
      { type: 'task', order: 30, prefix: 'TASK', reserved: false, category: 'work' },
    ]);

    expect(labelMap.has('task')).toBe(false);
  });
});

describe('pluralLabel', () => {
  const labelMap = buildTypeLabelMap(TYPE_CATALOG_FIXTURE);

  it('resolves the pinned/derived plural label from the catalog (labels.plural)', () => {
    expect(pluralLabel('decision', labelMap)).toBe('Decisions');
    expect(pluralLabel('role', labelMap)).toBe('Roles');
  });

  it('falls back to the raw type string when the type is absent from the map', () => {
    expect(pluralLabel('unknown', labelMap)).toBe('unknown');
  });

  it('falls back to the raw type string with NO_LABELS (empty/failed catalog fetch)', () => {
    expect(pluralLabel('task', NO_LABELS)).toBe('task');
  });

  it('falls back to the raw type string for a catalog entry that carries no labels (older sq)', () => {
    const olderSqLabelMap = buildTypeLabelMap([
      { type: 'task', order: 30, prefix: 'TASK', reserved: false, category: 'work' },
    ]);

    expect(pluralLabel('task', olderSqLabelMap)).toBe('task');
  });
});

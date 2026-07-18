import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  buildBadgeVocabulary,
  buildFieldBindings,
  NO_BADGE_VOCABULARY,
  NO_FIELD_BINDINGS,
  resolveItemBadges,
} from '../src/domain/badgeCatalog';
import type { SqCollectionCatalogEntry, SqTypeCatalogEntry } from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const TYPE_CATALOG_FIXTURE = JSON.parse(readFixture('type-catalog.json')) as SqTypeCatalogEntry[];
const COLLECTIONS_CATALOG_FIXTURE = JSON.parse(
  readFixture('collections-catalog.json'),
) as SqCollectionCatalogEntry[];

describe('resolveItemBadges', () => {
  const fieldBindings = buildFieldBindings(TYPE_CATALOG_FIXTURE);
  const badgeVocabulary = buildBadgeVocabulary(COLLECTIONS_CATALOG_FIXTURE);

  it('resolves a bug’s priority and severity badges to their real glyph + label, from the committed fixtures', () => {
    const resolved = resolveItemBadges(
      'bug',
      { priority: 'high', severity: 'critical' },
      fieldBindings,
      badgeVocabulary,
    );

    expect(resolved).toEqual([
      { fieldLabel: 'Priority', badgeLabel: 'High', emoji: '🟠' },
      { fieldLabel: 'Severity', badgeLabel: 'Critical', emoji: '🔴' },
    ]);
  });

  it('returns no badges for an empty badges map', () => {
    expect(resolveItemBadges('bug', {}, fieldBindings, badgeVocabulary)).toEqual([]);
  });

  it('treats an absent badges map (an older sq predating the surface) the same as empty', () => {
    expect(resolveItemBadges('bug', undefined, fieldBindings, badgeVocabulary)).toEqual([]);
  });

  it('falls back to the raw field code and badge code when the type has no known field binding', () => {
    // A custom axis (e.g. "impact") the committed type-catalog fixture doesn't declare for bugs.
    const resolved = resolveItemBadges('bug', { impact: 'urgent' }, fieldBindings, badgeVocabulary);

    expect(resolved).toEqual([{ fieldLabel: 'impact', badgeLabel: 'urgent', emoji: null }]);
  });

  it('falls back to the raw badge code when the collection vocabulary has no matching entry', () => {
    // "priority" is a known field bound to the "priority" collection, but "extreme" isn't a
    // badge that collection's committed fixture declares.
    const resolved = resolveItemBadges(
      'bug',
      { priority: 'extreme' },
      fieldBindings,
      badgeVocabulary,
    );

    expect(resolved).toEqual([{ fieldLabel: 'Priority', badgeLabel: 'extreme', emoji: null }]);
  });

  it('with NO_FIELD_BINDINGS/NO_BADGE_VOCABULARY (the graceful-fallback defaults), renders raw codes for everything', () => {
    const resolved = resolveItemBadges(
      'bug',
      { priority: 'high', severity: 'critical' },
      NO_FIELD_BINDINGS,
      NO_BADGE_VOCABULARY,
    );

    expect(resolved).toEqual([
      { fieldLabel: 'priority', badgeLabel: 'high', emoji: null },
      { fieldLabel: 'severity', badgeLabel: 'critical', emoji: null },
    ]);
  });

  it('resolves badges per item type, not a single global field set (an epic has no severity field)', () => {
    // An epic's badges map never carries "severity" in practice (the surface only emits fields
    // the spec declares for that type), but if it somehow did, the epic type's field bindings
    // (priority only) don't know it — same raw-code fallback as any other unbound field.
    const resolved = resolveItemBadges(
      'epic',
      { priority: 'low', severity: 'medium' },
      fieldBindings,
      badgeVocabulary,
    );

    expect(resolved).toEqual([
      { fieldLabel: 'Priority', badgeLabel: 'Low', emoji: '🟢' },
      { fieldLabel: 'severity', badgeLabel: 'medium', emoji: null },
    ]);
  });
});

describe('buildFieldBindings / buildBadgeVocabulary', () => {
  it('builds an empty binding map for a type with no declared fields (e.g. the reserved role type)', () => {
    const fieldBindings = buildFieldBindings(TYPE_CATALOG_FIXTURE);

    expect(fieldBindings.get('role')?.size).toBe(0);
  });

  it('treats a type absent from the catalog the same as one with no fields', () => {
    const fieldBindings = buildFieldBindings(TYPE_CATALOG_FIXTURE);

    expect(fieldBindings.get('widget')).toBeUndefined();
  });

  it('builds a badge vocabulary keyed by collection code, one entry per declared badge', () => {
    const badgeVocabulary = buildBadgeVocabulary(COLLECTIONS_CATALOG_FIXTURE);

    expect(badgeVocabulary.get('severity')?.get('info')).toEqual({ label: 'Info', emoji: '🔵' });
  });
});

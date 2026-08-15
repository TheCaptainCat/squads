import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  buildBadgeVocabulary,
  buildFieldBindings,
  buildSubEntityFieldBindings,
  NO_BADGE_VOCABULARY,
  NO_FIELD_BINDINGS,
  resolveItemBadges,
} from '../src/domain/badgeCatalog';
import type {
  SqCollectionCatalogEntry,
  SqSubEntityKindCatalogEntry,
  SqTypeCatalogEntry,
} from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const TYPE_CATALOG_FIXTURE = JSON.parse(readFixture('type-catalog.json')) as SqTypeCatalogEntry[];
const COLLECTIONS_CATALOG_FIXTURE = JSON.parse(
  readFixture('collections-catalog.json'),
) as SqCollectionCatalogEntry[];
const SUBENTITY_KINDS_FIXTURE = JSON.parse(
  readFixture('subentity-kinds-catalog.json'),
) as SqSubEntityKindCatalogEntry[];

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

/**
 * The item type -> `subentity_kind` -> kind row -> `fields` join, which is how a sub-entity's
 * badge gets the label its spec declares for it. Rows follow the published catalog shapes; the
 * kind rows are trimmed to the two keys this client reads.
 */
describe('buildSubEntityFieldBindings', () => {
  function typeRow(type: string, subentityKind: string | null): SqTypeCatalogEntry {
    return {
      type,
      order: null,
      prefix: type.toUpperCase(),
      reserved: false,
      category: 'work',
      fields: [{ code: 'priority', label: 'Priority', collection: 'priority' }],
      subentity_kind: subentityKind,
    };
  }

  function kindRow(kind: string, code: string, label: string): SqSubEntityKindCatalogEntry {
    return { subentity_kind: kind, fields: [{ code, label, collection: code }] };
  }

  it('resolves the real bundled join from the committed catalog fixtures', () => {
    // Both sides captured from live `sq`: a review hosts the `finding` kind, whose declared
    // axis is `severity`. The item's OWN fields (priority) must not leak into this.
    const bindings = buildSubEntityFieldBindings(TYPE_CATALOG_FIXTURE, SUBENTITY_KINDS_FIXTURE);

    expect(
      resolveItemBadges('review', { severity: 'high' }, bindings, NO_BADGE_VOCABULARY),
    ).toEqual([{ fieldLabel: 'Severity', badgeLabel: 'high', emoji: null }]);
    expect(bindings.get('review')?.has('priority')).toBe(false);
    // A type hosting a kind that declares no field binds nothing, and an epic hosts no kind
    // at all — neither is an error, both degrade to the raw code.
    expect(bindings.get('task')?.size).toBe(0);
    expect(bindings.get('epic')).toBeUndefined();
  });

  it('labels a sub-entity badge from the kind its type hosts, not from the item’s own fields', () => {
    const bindings = buildSubEntityFieldBindings(
      [typeRow('review', 'finding')],
      [kindRow('finding', 'severity', 'Severity')],
    );

    expect(
      resolveItemBadges('review', { severity: 'high' }, bindings, NO_BADGE_VOCABULARY),
    ).toEqual([{ fieldLabel: 'Severity', badgeLabel: 'high', emoji: null }]);
  });

  it('follows a relabelled axis: the declared label wins over the raw field code', () => {
    const bindings = buildSubEntityFieldBindings(
      [typeRow('review', 'finding')],
      [kindRow('finding', 'impact', 'Impact')],
    );

    expect(resolveItemBadges('review', { impact: 'high' }, bindings, NO_BADGE_VOCABULARY)).toEqual([
      { fieldLabel: 'Impact', badgeLabel: 'high', emoji: null },
    ]);
  });

  it('binds each type to its own kind when several kinds are declared', () => {
    const bindings = buildSubEntityFieldBindings(
      [typeRow('review', 'finding'), typeRow('task', 'subtask'), typeRow('epic', null)],
      [kindRow('finding', 'severity', 'Severity'), kindRow('subtask', 'effort', 'Effort')],
    );

    expect(bindings.get('review')?.get('severity')?.label).toBe('Severity');
    expect(bindings.get('task')?.get('effort')?.label).toBe('Effort');
    expect(bindings.get('epic')).toBeUndefined();
  });

  it('leaves a type unbound when the kind catalog is unavailable, degrading to the raw code', () => {
    const bindings = buildSubEntityFieldBindings([typeRow('review', 'finding')], []);

    expect(bindings.get('review')).toBeUndefined();
    expect(
      resolveItemBadges('review', { severity: 'high' }, bindings, NO_BADGE_VOCABULARY),
    ).toEqual([{ fieldLabel: 'severity', badgeLabel: 'high', emoji: null }]);
  });

  it('leaves a type unbound when the type row predates the subentity_kind key', () => {
    const legacyRow: SqTypeCatalogEntry = {
      type: 'review',
      order: null,
      prefix: 'REV',
      reserved: false,
      category: 'work',
    };

    const bindings = buildSubEntityFieldBindings(
      [legacyRow],
      [kindRow('finding', 'severity', 'Severity')],
    );

    expect(bindings.get('review')).toBeUndefined();
  });

  it('binds a kind that declares several fields, and none it does not declare', () => {
    const bindings = buildSubEntityFieldBindings(
      [typeRow('review', 'finding')],
      [
        {
          subentity_kind: 'finding',
          fields: [
            { code: 'severity', label: 'Severity', collection: 'severity' },
            { code: 'confidence', label: 'Confidence', collection: 'confidence' },
          ],
        },
      ],
    );

    expect(
      resolveItemBadges(
        'review',
        { severity: 'high', confidence: 'low', mystery: 'x' },
        bindings,
        NO_BADGE_VOCABULARY,
      ),
    ).toEqual([
      { fieldLabel: 'Severity', badgeLabel: 'high', emoji: null },
      { fieldLabel: 'Confidence', badgeLabel: 'low', emoji: null },
      { fieldLabel: 'mystery', badgeLabel: 'x', emoji: null },
    ]);
  });
});

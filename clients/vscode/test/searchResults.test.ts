import { describe, expect, it } from 'vitest';

import { hitsToResultRows, hitToResultRow } from '../src/domain/searchResults';
import type { SqSearchHit } from '../src/types';

function hit(overrides: Partial<SqSearchHit> = {}): SqSearchHit {
  return {
    id: 'TASK-3',
    title: 'Implement login',
    type: 'task',
    status: 'InProgress',
    hits: [{ region: 'title', location: 'title', snippet: 'Implement login' }],
    ...overrides,
  };
}

describe('hitToResultRow', () => {
  it('maps id/title into the label and type/status into the description', () => {
    const row = hitToResultRow(hit());

    expect(row.itemId).toBe('TASK-3');
    expect(row.label).toBe('TASK-3  Implement login');
    expect(row.description).toBe('task · InProgress');
  });

  it('joins multiple matched regions into one detail line', () => {
    const row = hitToResultRow(
      hit({
        hits: [
          { region: 'title', location: 'title', snippet: 'Implement login' },
          { region: 'subtask:ST1', location: 'subtask:ST1', snippet: '### ST1 — Write handler' },
        ],
      }),
    );

    expect(row.detail).toBe('Implement login  ·  ### ST1 — Write handler');
  });

  it('renders an empty detail for a hit with no matched regions, without throwing', () => {
    const row = hitToResultRow(hit({ hits: [] }));

    expect(row.detail).toBe('');
  });
});

describe('hitsToResultRows', () => {
  it('maps every hit, preserving sq search --json order (no client re-ranking)', () => {
    const rows = hitsToResultRows([
      hit({ id: 'TASK-3' }),
      hit({ id: 'BUG-4', title: 'Login crashes', type: 'bug', status: 'Open' }),
    ]);

    expect(rows.map((row) => row.itemId)).toEqual(['TASK-3', 'BUG-4']);
  });

  it('maps an empty result set to an empty array (zero matches, not an error)', () => {
    expect(hitsToResultRows([])).toEqual([]);
  });
});

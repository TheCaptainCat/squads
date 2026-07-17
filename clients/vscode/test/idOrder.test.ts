import { describe, expect, it } from 'vitest';

import { compareIds } from '../src/domain/idOrder';

describe('compareIds', () => {
  it('sorts numerically, not lexicographically: REV-48 before REV-447', () => {
    expect(['REV-447', 'REV-48'].sort(compareIds)).toEqual(['REV-48', 'REV-447']);
  });

  it('agrees with plain localeCompare within the same digit count', () => {
    expect(['TASK-2', 'TASK-1'].sort(compareIds)).toEqual(['TASK-1', 'TASK-2']);
  });

  it('is stable across a wide spread of digit counts', () => {
    const ids = ['BUG-100', 'BUG-9', 'BUG-2', 'BUG-10'];
    expect([...ids].sort(compareIds)).toEqual(['BUG-2', 'BUG-9', 'BUG-10', 'BUG-100']);
  });

  it('falls back to alphabetic order across different type prefixes', () => {
    expect(['TASK-1', 'BUG-1'].sort(compareIds)).toEqual(['BUG-1', 'TASK-1']);
  });
});
